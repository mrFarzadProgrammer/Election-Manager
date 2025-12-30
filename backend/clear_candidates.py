from database import SessionLocal
from models import User

def clear_candidates():
    db = SessionLocal()
    try:
        # Delete all users where role is not ADMIN
        deleted_count = db.query(User).filter(User.role != 'ADMIN').delete()
        db.commit()
        print(f"Successfully deleted {deleted_count} candidates.")
        
        # Verify remaining users
        remaining = db.query(User).all()
        print(f"Remaining users: {len(remaining)}")
        for u in remaining:
            print(f" - {u.username} ({u.role})")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_candidates()
