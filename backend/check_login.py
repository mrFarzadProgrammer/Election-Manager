from database import SessionLocal
from models import User
from auth import verify_password

def check_admin_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("User 'admin' not found!")
            return

        password_to_check = "admin123"
        is_valid = verify_password(password_to_check, user.hashed_password)
        
        print(f"User: {user.username}")
        print(f"Hashed Password in DB: {user.hashed_password}")
        print(f"Checking password '{password_to_check}': {is_valid}")
        
        if is_valid:
            print("✅ Password is correct.")
        else:
            print("❌ Password is INCORRECT.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_password()
