import database
import models
import auth

def seed_database():
    """پاکسازی و ایجاد فقط کاربر ادمین"""
    db = database.SessionLocal()
    try:
        # ایجاد کاربر ادمین اگر وجود نداشته باشد
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

        print("✅ Database is now clean with only 1 Admin user.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # ابتدا جداول را می‌سازد
    models.Base.metadata.create_all(bind=database.engine)
    seed_database()