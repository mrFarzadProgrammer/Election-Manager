import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, BotUser

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

FAILED_BOT_COOLDOWN = timedelta(minutes=5)


def looks_like_telegram_token(token: str | None) -> bool:
    if not token:
        return False
    token = token.strip()
    if not token or token.startswith("TOKEN_"):
        return False
    if ":" not in token:
        return False
    bot_id, secret = token.split(":", 1)
    return bot_id.isdigit() and len(secret) >= 20

# --- Helper for Non-Blocking DB Access ---
async def run_db_query(func, *args, **kwargs):
    """Runs a synchronous DB function in a separate thread."""
    return await asyncio.to_thread(func, *args, **kwargs)

def get_candidate_sync(candidate_id: int):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == candidate_id, User.role == "CANDIDATE").first()
    finally:
        db.close()

def save_bot_user_sync(user_data: dict, candidate_name: str):
    db = SessionLocal()
    try:
        bot_user = db.query(BotUser).filter(BotUser.telegram_id == user_data['id']).first()
        if not bot_user:
            bot_user = BotUser(
                telegram_id=user_data['id'],
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                bot_name=candidate_name
            )
            db.add(bot_user)
        else:
            bot_user.username = user_data.get('username')
            bot_user.first_name = user_data.get('first_name')
            bot_user.last_name = user_data.get('last_name')
            bot_user.bot_name = candidate_name
        db.commit()
    except Exception as e:
        logger.error(f"Error saving bot user: {e}")
    finally:
        db.close()

async def save_bot_user(update: Update, candidate_name: str):
    user = update.effective_user
    if not user:
        return
    
    user_data = {
        'id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    
    await run_db_query(save_bot_user_sync, user_data, candidate_name)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    candidate_id = context.bot_data.get("candidate_id")
    if not candidate_id:
        await update.message.reply_text("خطا: شناسه کاندیدا یافت نشد.")
        return

    # Use non-blocking DB call
    # Note: We need to fetch all needed data because session closes
    def get_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c: return None
            return {
                'name': c.full_name,
                'bot_name': c.bot_name,
                'slogan': c.slogan
            }
        finally:
            db.close()

    candidate = await run_db_query(get_candidate_data, candidate_id)
    
    if not candidate:
        await update.message.reply_text("خطا: اطلاعات کاندیدا یافت نشد.")
        return

    # Save User Data
    await save_bot_user(update, candidate['bot_name'] or candidate['name'])

    welcome_text = f"سلام! من بات {candidate['name']} هستم.\n\n"

    if candidate['slogan']:
        welcome_text += f"📣 {candidate['slogan']}\n\n"
    
    welcome_text += "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"

    keyboard = [
        [KeyboardButton("📄 رزومه"), KeyboardButton("💡 برنامه‌ها")],
        [KeyboardButton("📍 ستاد"), KeyboardButton("📞 تماس")],
        [KeyboardButton("💳 حمایت مالی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu messages and group management."""
    text = update.message.text
    candidate_id = context.bot_data.get("candidate_id")
    chat_type = update.message.chat.type
    
    logger.info(f"Received message: '{text}' for candidate_id: {candidate_id} in {chat_type}")

    if not candidate_id:
        return

    def get_full_candidate_data(cid):
        db = SessionLocal()
        try:
            c = db.query(User).filter(User.id == cid, User.role == "CANDIDATE").first()
            if not c: return None
            return {
                'name': c.full_name,
                'bot_name': c.bot_name,
                'resume': c.resume,
                'ideas': c.ideas,
                'address': c.address,
                'phone': c.phone,
                'socials': c.socials,
                'bot_config': c.bot_config
            }
        finally:
            db.close()

    candidate = await run_db_query(get_full_candidate_data, candidate_id)

    if not candidate:
        return

    bot_config = candidate.get('bot_config') or {}

    socials = candidate.get('socials') or {}
    if isinstance(socials, dict):
        # Normalize socials keys between snake_case (frontend) and camelCase (bot expectations)
        if 'telegramChannel' not in socials and 'telegram_channel' in socials:
            socials['telegramChannel'] = socials.get('telegram_channel')
        if 'telegramGroup' not in socials and 'telegram_group' in socials:
            socials['telegramGroup'] = socials.get('telegram_group')
        # instagram key is already same in both, but keep for completeness
        if 'instagram' not in socials and 'instagram' in socials:
            socials['instagram'] = socials.get('instagram')

    # Backward/forward compatibility between frontend and bot expectations
    # Frontend currently stores keys like:
    #   auto_lock_enabled, lock_start_time, lock_end_time, anti_link_enabled, forbidden_words
    # Bot runner historically reads:
    #   groupLockEnabled, lockStartTime, lockEndTime, blockLinks, badWords
    if isinstance(bot_config, dict):
        if 'groupLockEnabled' not in bot_config and 'auto_lock_enabled' in bot_config:
            bot_config['groupLockEnabled'] = bool(bot_config.get('auto_lock_enabled'))
        if 'lockStartTime' not in bot_config and 'lock_start_time' in bot_config:
            bot_config['lockStartTime'] = bot_config.get('lock_start_time')
        if 'lockEndTime' not in bot_config and 'lock_end_time' in bot_config:
            bot_config['lockEndTime'] = bot_config.get('lock_end_time')
        if 'blockLinks' not in bot_config and 'anti_link_enabled' in bot_config:
            bot_config['blockLinks'] = bool(bot_config.get('anti_link_enabled'))
        if 'badWords' not in bot_config and 'forbidden_words' in bot_config:
            raw = bot_config.get('forbidden_words')
            if isinstance(raw, str):
                bot_config['badWords'] = [w.strip() for w in raw.split(',') if w.strip()]


    # --- Group Management Logic ---
    if chat_type in ['group', 'supergroup']:
        # 1. Check Group Lock
        if bot_config.get('groupLockEnabled'):
            start_time = bot_config.get('lockStartTime')
            end_time = bot_config.get('lockEndTime')
            
            if start_time and end_time:
                now = datetime.now().time()
                try:
                    start = datetime.strptime(start_time, "%H:%M").time()
                    end = datetime.strptime(end_time, "%H:%M").time()
                    
                    is_locked = False
                    if start <= end:
                        is_locked = start <= now <= end
                    else: # Crosses midnight
                        is_locked = start <= now or now <= end
                    
                    if is_locked:
                        try:
                            await update.message.delete()
                            # Optional: Send warning message (can be spammy)
                            # await update.message.reply_text("⛔ گروه در ساعات مشخص شده قفل است.")
                        except Exception as e:
                            logger.error(f"Failed to delete message in locked group: {e}")
                        return
                except ValueError:
                    logger.error("Invalid time format in bot_config")

        # 2. Check Bad Words
        bad_words = bot_config.get('badWords', [])
        if bad_words and isinstance(bad_words, list):
            text_lower = text.lower()
            for word in bad_words:
                if word.strip() and word.strip().lower() in text_lower:
                    try:
                        await update.message.delete()
                        # await update.message.reply_text("⛔ پیام شما حاوی کلمات نامناسب بود و حذف شد.")
                    except Exception as e:
                        logger.error(f"Failed to delete bad word message: {e}")
                    return

        # 3. Check Links
        if bot_config.get('blockLinks'):
            url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            if url_pattern.search(text):
                try:
                    await update.message.delete()
                    # await update.message.reply_text("⛔ ارسال لینک در این گروه ممنوع است.")
                except Exception as e:
                    logger.error(f"Failed to delete link message: {e}")
                return

    # --- Private Chat Menu Logic ---
    # Save User Data
    await save_bot_user(update, candidate['bot_name'] or candidate['name'])

    response = "اطلاعاتی ثبت نشده است."
    
    if text == "📄 رزومه":
        response = candidate['resume'] or "رزومه‌ای ثبت نشده است."
    elif text == "💡 برنامه‌ها":
        response = candidate['ideas'] or "برنامه‌ای ثبت نشده است."
    elif text == "📍 ستاد":
        response = candidate['address'] or "آدرس ستاد ثبت نشده است."
    elif text == "📞 تماس":
        response = f"شماره تماس: {candidate['phone'] or '---'}\n"
        if socials:
            if socials.get('telegramChannel'):
                response += f"\nکانال تلگرام: {socials['telegramChannel']}"
            if socials.get('telegramGroup'):
                response += f"\nگروه تلگرام: {socials['telegramGroup']}"
            if socials.get('instagram'):
                response += f"\nاینستاگرام: {socials['instagram']}"
    elif text == "💳 حمایت مالی":
        response = "برای حمایت مالی لطفاً با ستاد تماس بگیرید."

    await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def run_bot(candidate: User):
    """Runs a single bot instance."""
    try:
        if not candidate.bot_token:
            logger.warning(f"Candidate {candidate.full_name} has no bot token.")
            return

        if not looks_like_telegram_token(candidate.bot_token):
            logger.warning(
                f"Candidate {candidate.full_name} has an invalid bot token format. Skipping start."
            )
            return

        logger.info(f"Starting bot for {candidate.full_name} (@{candidate.bot_name})...")
        
        # Configure connection timeouts
        request = HTTPXRequest(connection_pool_size=8, read_timeout=20, write_timeout=20, connect_timeout=20)
        
        application = Application.builder().token(candidate.bot_token).request(request).build()
        
        # Store candidate ID in bot_data for handlers to access
        application.bot_data["candidate_id"] = candidate.id

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info(f"Bot for {candidate.full_name} is running.")
        
        # Keep the bot running
        return application

    except Exception as e:
        logger.error(f"Failed to start bot for {candidate.full_name}: {e}")
        return None

# Global dictionary to track running bots: candidate_id -> Application
running_bots = {}

# candidate_id -> last failure UTC time
failed_bots = {}

async def check_for_new_candidates():
    """Periodically checks for new active candidates and starts their bots."""
    while True:
        try:
            def get_active_candidates():
                db = SessionLocal()
                try:
                    return db.query(User).filter(User.role == "CANDIDATE", User.is_active == True).all()
                finally:
                    db.close()

            candidates = await run_db_query(get_active_candidates)
            
            active_ids = set()
            
            for candidate in candidates:
                active_ids.add(candidate.id)
                
                # If candidate is active but bot is not running, start it
                if candidate.id not in running_bots:
                    last_failed_at = failed_bots.get(candidate.id)
                    if last_failed_at and (datetime.now(timezone.utc) - last_failed_at) < FAILED_BOT_COOLDOWN:
                        continue

                    if candidate.bot_token:
                        logger.info(f"Found new active candidate: {candidate.full_name}. Starting bot...")
                        app = await run_bot(candidate)
                        if app:
                            running_bots[candidate.id] = app
                            failed_bots.pop(candidate.id, None)
                        else:
                            failed_bots[candidate.id] = datetime.now(timezone.utc)
            
            # Optional: Stop bots for candidates that are no longer active
            # (Implementation omitted for simplicity, but good to have)

        except Exception as e:
            logger.error(f"Error in candidate check loop: {e}")
        
        # Wait 10 seconds before next check
        await asyncio.sleep(10)

async def main():
    """Main entry point to run all candidate bots."""
    logger.info("Starting Bot Runner Service...")
    
    # Start the update checker loop as a background task
    checker_task = asyncio.create_task(check_for_new_candidates())
    
    # Keep the script running indefinitely
    stop_signal = asyncio.Event()
    try:
        await stop_signal.wait()
    except KeyboardInterrupt:
        logger.info("Stopping bots...")
        stop_signal.set()
        checker_task.cancel()
        
        for app in running_bots.values():
            if app.updater.running:
                await app.updater.stop()
            if app.running:
                await app.stop()
                await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
