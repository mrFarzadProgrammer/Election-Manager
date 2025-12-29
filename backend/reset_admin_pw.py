from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import User
from auth import get_password_hash
import sys

def reset_admin_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("Admin user not found!")
            return
        
        new_password = "admin123"
        hashed = get_password_hash(new_password)
        user.hashed_password = hashed
        db.commit()
        print(f"Successfully reset password for user 'admin' to '{new_password}'")
        print(f"New hash: {hashed}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
