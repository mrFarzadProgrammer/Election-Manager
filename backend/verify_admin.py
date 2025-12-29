import database
import models
import auth

def verify():
    db = database.SessionLocal()
    user = db.query(models.User).filter(models.User.username == "admin").first()
    if user:
        print(f"FOUND_USER: {user.username}, Role: {user.role}, Active: {user.is_active}")
        if auth.verify_password("admin123", user.hashed_password):
             print("PASSWORD_VALID: True")
        else:
             print("PASSWORD_VALID: False")
    else:
        print("FOUND_USER: None")
    db.close()

if __name__ == "__main__":
    verify()