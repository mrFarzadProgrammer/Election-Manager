import database
import models
import auth
import random
import jdatetime

def seed_database():
    """ایجاد دیتای اولیه: ادمین، پلن‌ها و ۲۰ کاندیدای نمونه"""
    db = database.SessionLocal()
    try:
        # 1. ایجاد کاربر ادمین
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            admin_user = models.User(
                username="admin",
                email="admin@electionmanager.com",
                full_name="System Admin",
                hashed_password=auth.get_password_hash("admin123"),
                role="ADMIN"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user created: admin / admin123")
        else:
            print("ℹ️ Admin already exists.")

        # 2. ایجاد پلن‌های توافق شده
        if db.query(models.Plan).count() == 0:
            plans = [
                models.Plan(
                    title="بسته رویش (شروع)",
                    price="900,000",
                    description="حضور دیجیتال خود را ثبت کنید. مناسب برای شروع معرفی در حوزه‌های کوچک.",
                    features=[
                        "پروفایل اختصاصی کاندیدا",
                        "ثبت بیوگرافی و شعار انتخاباتی",
                        "گالری تصاویر (محدود به ۳ عکس)",
                        "ثبت ۱ آدرس ستاد انتخاباتی",
                        "لینک شبکه‌های اجتماعی",
                        "فاقد ربات تلگرام اختصاصی",
                        "پشتیبانی تیکت معمولی"
                    ],
                    color="#4caf50", # Green
                    is_visible=True
                ),
                models.Plan(
                    title="بسته پویش (استاندارد)",
                    price="3,500,000",
                    description="ارتباط موثر با رای‌دهندگان را آغاز کنید. مناسب شوراهای شهر.",
                    features=[
                        "تمام امکانات بسته رویش",
                        "ربات تلگرام اختصاصی (با نام و عکس شما)",
                        "پیام خوش‌آمدگویی متنی خودکار",
                        "گالری تصاویر (تا ۱۰ عکس)",
                        "انتشار ۲ فایل صوتی (ویس نماینده)",
                        "ثبت ۳ آدرس ستاد انتخاباتی",
                        "امکان پاسخ به سوالات مردم (تا ۵۰ مورد)",
                        "ارسال پیام انبوه (۱۰۰۰ عدد در ماه)"
                    ],
                    color="#2196f3", # Blue
                    is_visible=True
                ),
                models.Plan(
                    title="بسته جهش (پیشرفته)",
                    price="8,500,000",
                    description="صدای خود را به گوش همه برسانید. مناسب کاندیداهای مجلس.",
                    features=[
                        "تمام امکانات بسته پویش",
                        "پیام خوش‌آمدگویی صوتی (ویس)",
                        "گالری تصاویر (تا ۵۰ عکس)",
                        "انتشار ۱۰ فایل صوتی و ویدئویی",
                        "ثبت ۱۰ آدرس ستاد انتخاباتی",
                        "ارسال پیام انبوه (۱۰,۰۰۰ عدد در ماه)",
                        "مشاهده آمار بازدید و هواداران شهر",
                        "مدیریت هوشمند کانال (قفل گروه/کانال)",
                        "اولویت در پشتیبانی فنی"
                    ],
                    color="#9c27b0", # Purple
                    is_visible=True
                ),
                models.Plan(
                    title="بسته پیروزی (VIP)",
                    price="18,000,000",
                    description="مدیریت تمام عیار کمپین با ابزارهای انحصاری و مشاوره.",
                    features=[
                        "تمام امکانات بسته جهش",
                        "گالری تصاویر و مدیا نامحدود",
                        "ارسال پیام انبوه نامحدود",
                        "ثبت آدرس ستادها نامحدود",
                        "مشاوره اختصاصی کمپین انتخاباتی",
                        "فیلترینگ هوشمند محتوا و نظرات توهین‌آمیز",
                        "تحلیل آماری دقیق رقبا در شهر",
                        "شخصی‌سازی کامل منوی ربات",
                        "خط اختصاصی پشتیبانی تلفنی (VIP)",
                        "تضمین آپتایم ۱۰۰٪ در روز انتخابات"
                    ],
                    color="#ff9800", # Orange/Gold
                    is_visible=True
                )
            ]
            db.add_all(plans)
            db.commit()
            print("✅ Plans created.")
        else:
            print("ℹ️ Plans already exist.")

        # 3. ایجاد ۲۰ کاندیدای نمونه
        first_names = ["علی", "محمد", "رضا", "حسین", "مهدی", "حسن", "سعید", "حمید", "محسن", "احمد", "سارا", "مریم", "زهرا", "فاطمه", "نرگس", "کیان", "آرش", "کوروش", "داریوش", "بهرام"]
        last_names = ["رضایی", "محمدی", "حسینی", "احمدی", "کریمی", "موسوی", "جعفری", "صادقی", "رحیمی", "کاظمی", "عباسی", "باقری", "زندی", "راد", "تهرانی", "شیرازی", "تبریزی", "کرمانی", "یزدانی", "نوری"]
        cities = ["تهران", "مشهد", "اصفهان", "شیراز", "تبریز", "کرج", "اهواز", "قم", "رشت", "ساری", "کرمان", "ارومیه", "یزد", "همدان", "زاهدان"]
        slogans = [
            "برای آینده‌ای بهتر", "تغییر برای پیشرفت", "صدای مردم", "خدمت صادقانه", 
            "شفافیت و عدالت", "شهر هوشمند، شهروند شاد", "با هم می‌سازیم", "تدبیر و امید",
            "جوانی، انرژی، تغییر", "تجربه و تخصص", "هوای تازه برای شهر", "توسعه پایدار"
        ]

        # تعداد کاندیداهای فعلی
        current_count = db.query(models.User).filter(models.User.role == "CANDIDATE").count()
        target_count = 20
        needed = target_count - current_count

        if needed > 0:
            print(f"Creating {needed} new candidates...")
            for i in range(needed):
                fname = random.choice(first_names)
                lname = random.choice(last_names)
                full_name = f"{fname} {lname}"
                
                # ساخت نام کاربری یکتا
                base_username = f"candidate_{current_count + i + 1}"
                username = base_username
                counter = 1
                while db.query(models.User).filter(models.User.username == username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1

                # ساخت شماره موبایل رندوم
                phone = f"0912{random.randint(1000000, 9999999)}"
                while db.query(models.User).filter(models.User.phone == phone).first():
                    phone = f"0912{random.randint(1000000, 9999999)}"

                new_candidate = models.User(
                    username=username,
                    email=f"{username}@example.com",
                    phone=phone,
                    full_name=full_name,
                    hashed_password=auth.get_password_hash("123456"), # رمز پیش‌فرض
                    role="CANDIDATE",
                    is_active=True,
                    city=random.choice(cities),
                    slogan=random.choice(slogans),
                    bio=f"من {full_name} هستم، کاندیدای شورای شهر با هدف خدمت به مردم و ارتقای سطح زندگی شهروندان.",
                    bot_name=f"{username}_bot",
                    bot_token=f"TOKEN_{username}_{random.randint(10000,99999)}",
                    created_at_jalali=jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                    vote_count=random.randint(100, 5000) # Random vote count for dashboard testing
                )
                db.add(new_candidate)
            
            db.commit()
            print(f"✅ {needed} Candidates created successfully.")
        else:
            print("ℹ️ Enough candidates already exist (>= 20).")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # ابتدا جداول را می‌سازد
    models.Base.metadata.create_all(bind=database.engine)
    seed_database()