import re
from datetime import datetime

BTN_INTRO = "🤖 معرفی نماینده"
BTN_PROGRAMS = "✅ برنامه‌ها"
BTN_FEEDBACK = "💬 نظر / دغدغه"
BTN_FEEDBACK_LEGACY = "✍️ ارسال نظر / دغدغه"
BTN_QUESTION = "❓ سؤال از نماینده"
BTN_CONTACT = "☎️ ارتباط با نماینده"

# UX-first main menu (max 5 buttons)
BTN_COMMITMENTS = "📜 تعهدات نماینده"
BTN_ABOUT_MENU = "📂 درباره نماینده"
BTN_OTHER_MENU = "⚙️ سایر امکانات"

# Submenus
BTN_ABOUT_INTRO = "🏛 معرفی نماینده"
BTN_HQ_ADDRESSES = "📍 آدرس ستادها"
BTN_VOICE_INTRO = "🎙 معرفی صوتی نماینده"

BTN_BUILD_BOT = "🛠 ساخت بات اختصاصی"
BTN_ABOUT_BOT = "🤖 درباره این بات"

# Telegram 'request contact' button for consultation lead capture.
BTN_SEND_CONTACT = "📞 ارسال شماره تماس"

BTN_PROFILE_SUMMARY = "👤 سوابق"
BTN_BACK = "🔙 بازگشت"

BTN_REGISTER_QUESTION = "✅ ثبت سؤال"
BTN_SEARCH_QUESTION = "🔍 جستجو در پرسش‌ها"

# Strict step-based question UX (MVP)
BTN_VIEW_QUESTIONS = "👀 مشاهده سؤال‌ها"
BTN_ASK_NEW_QUESTION = "✍️ ثبت سؤال جدید"
BTN_VIEW_BY_CATEGORY = "📂 دسته‌بندی‌ها"
BTN_VIEW_BY_SEARCH = "🔎 جستجو"
BTN_SELECT_TOPIC = "▶️ انتخاب موضوع"

# Fixed categories (MVP)
QUESTION_CATEGORIES: list[str] = [
    "اشتغال",
    "اقتصاد و معیشت",
    "شفافیت",
    "مسکن",
    "سایر",
]

BTN_BOT_REQUEST = "✅ ثبت درخواست مشاوره"

ROLE_REPRESENTATIVE = "نماینده"
ROLE_CANDIDATE = "کاندیدا"
ROLE_TEAM = "تیم"

STATE_MAIN = "MAIN"
STATE_ABOUT_MENU = "ABOUT_MENU"
STATE_ABOUT_DETAIL = "ABOUT_DETAIL"
STATE_OTHER_MENU = "OTHER_MENU"
STATE_COMMITMENTS_VIEW = "COMMITMENTS_VIEW"
STATE_PROGRAMS = "PROGRAMS"
STATE_FEEDBACK_TEXT = "FEEDBACK_TEXT"
STATE_QUESTION_TEXT = "QUESTION_TEXT"
STATE_QUESTION_MENU = "QUESTION_MENU"
STATE_QUESTION_SEARCH = "QUESTION_SEARCH"
STATE_QUESTION_CATEGORY = "QUESTION_CATEGORY"

# Strict step-based states (preferred)
STATE_QUESTION_ENTRY = "QUESTION_ENTRY"
STATE_QUESTION_VIEW_METHOD = "QUESTION_VIEW_METHOD"
STATE_QUESTION_VIEW_CATEGORY = "QUESTION_VIEW_CATEGORY"
STATE_QUESTION_VIEW_LIST = "QUESTION_VIEW_LIST"
STATE_QUESTION_VIEW_ANSWER = "QUESTION_VIEW_ANSWER"
STATE_QUESTION_VIEW_RESULTS = "QUESTION_VIEW_RESULTS"
STATE_QUESTION_VIEW_SEARCH_TEXT = "QUESTION_VIEW_SEARCH_TEXT"
STATE_QUESTION_ASK_ENTRY = "QUESTION_ASK_ENTRY"
STATE_QUESTION_ASK_TOPIC = "QUESTION_ASK_TOPIC"
STATE_QUESTION_ASK_OTHER_TOPIC = "QUESTION_ASK_OTHER_TOPIC"
STATE_QUESTION_ASK_TEXT = "QUESTION_ASK_TEXT"

STATE_BOTREQ_NAME = "BOTREQ_NAME"
STATE_BOTREQ_ROLE = "BOTREQ_ROLE"
STATE_BOTREQ_CONSTITUENCY = "BOTREQ_CONSTITUENCY"
STATE_BOTREQ_CONTACT = "BOTREQ_CONTACT"


def flow_type_from_state(state: str | None) -> str | None:
    s = (state or "").strip()
    if s in {STATE_FEEDBACK_TEXT}:
        return "comment"
    if s in {
        STATE_QUESTION_TEXT,
        STATE_QUESTION_MENU,
        STATE_QUESTION_SEARCH,
        STATE_QUESTION_CATEGORY,
        STATE_QUESTION_ENTRY,
        STATE_QUESTION_VIEW_METHOD,
        STATE_QUESTION_VIEW_CATEGORY,
        STATE_QUESTION_VIEW_LIST,
        STATE_QUESTION_VIEW_ANSWER,
        STATE_QUESTION_VIEW_RESULTS,
        STATE_QUESTION_VIEW_SEARCH_TEXT,
        STATE_QUESTION_ASK_ENTRY,
        STATE_QUESTION_ASK_TOPIC,
        STATE_QUESTION_ASK_OTHER_TOPIC,
        STATE_QUESTION_ASK_TEXT,
    }:
        return "question"
    if s in {STATE_BOTREQ_NAME, STATE_BOTREQ_ROLE, STATE_BOTREQ_CONSTITUENCY, STATE_BOTREQ_CONTACT}:
        return "lead"
    return None


PROGRAM_QUESTIONS = [
    "برنامه عملی شما برای شفاف‌سازی تصمیمات شورای شهر و مقابله با رانت دقیقاً چیه؟ (نه شعار؛ ابزار، سامانه یا مکانیزم مشخص)",
    "برای کاهش ترافیک روزمره تهران، چه اقدام کوتاه‌مدت و چه اصلاح بلندمدتی در نظر دارید؟",
    "شورای شهر چه نقشی می‌تونه در کنترل اجاره‌بها و ساماندهی بازار مسکن داشته باشه و برنامه شما چیه؟",
    "اگر اختیار داشتید فقط روی «یک تغییر محله‌ای» تمرکز کنید که سریع حس بشه، اون چیه؟",
    "برنامه مشخص شما برای کاهش آلودگی هوا چیه و چه بخشی از اون در اختیار شوراست؟",
    "چطور می‌خواید فاصله خدمات شهری بین شمال و جنوب تهران رو کمتر کنید؟",
    "آیا برنامه‌ای برای استفاده از داده، هوش مصنوعی یا شهر هوشمند در تصمیمات شهری دارید؟ کجا دقیقاً؟",
    "مردم چطور می‌تونن بعد از انتخاب شما، در تصمیمات شهری نظر بدن و اثر واقعی بذارن؟",
    "اگر یک تصمیم شما با اعتراض مردم مواجه شد، سازوکار پاسخگویی‌تون چیه؟",
    "آیا متعهد می‌شید بعد از انتخابات، همین مسیر ارتباطی با مردم حفظ بشه و گزارش‌های منظم، شفاف و غیرتبلیغاتی ارائه بدید؟",
]

FEEDBACK_INTRO_TEXT = (
    "🟢 <b>نظر / دغدغه</b>\n"
    "──────────────\n"
    "📌 <b>ثبت و انتقال:</b> پیام شما ثبت می‌شود و به نماینده منتقل خواهد شد.\n"
    "🎯 <b>هدف:</b> شنیدن صدای مردم و شناسایی دغدغه‌های پرتکرار.\n"
    "🛡 <b>نحوه پاسخ:</b> پاسخ‌ها به‌صورت کلی و عمومی ارائه می‌شود (نه فردی).\n"
    "❓ <b>پاسخ مستقیم می‌خواهید؟</b> از بخش «❓ سؤال از نماینده» استفاده کنید."
)


def parse_question_list_choice(user_text: str | None, *, normalize_button_text) -> int | None:
    t = normalize_button_text(user_text)
    m = re.match(r"^(\d{1,2})\)", t)
    if not m:
        if re.fullmatch(r"\d{1,3}", t):
            try:
                return int(t)
            except Exception:
                return None
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None
