import os
import database
import models
import auth

def reset_all():
    # Use absolute path to match database.py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(BASE_DIR, "election_manager.db")
    
    # 1. حذف فایل دیتابیس قدیمی اگر وجود داشته باشد
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"✅ Old database '{db_file}' deleted.")
        except PermissionError:
            print(f"⚠️ Could not delete '{db_file}'. It might be in use. Tables will be recreated if possible.")

    # 2. ساخت جداول جدید
    models.Base.metadata.create_all(bind=database.engine)
    print("✅ New tables created.")

    # 3. ایجاد کاربر ادمین
    db = database.SessionLocal()
    try:
        admin_user = models.User(
            username="admin",
            email="admin@electionmanager.com",
            full_name="System Admin",
            hashed_password=auth.get_password_hash("admin123"), # هش کردن پسورد
            role="ADMIN",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("✅ Admin user created: admin / admin123")
        
        # Verify immediately
        check = db.query(models.User).filter(models.User.username == "admin").first()
        if check:
            print(f"✅ Verification: Admin found in DB. ID: {check.id}")
        else:
            print("❌ Verification: Admin NOT found in DB!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_all()