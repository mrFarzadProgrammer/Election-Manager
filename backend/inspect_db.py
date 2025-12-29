from database import SessionLocal
from models import Candidate, User

def inspect_candidates():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users.")
        for u in users:
            print(f"User: {u.username}, Role: {u.role}")

        candidates = db.query(Candidate).all()
        print(f"Found {len(candidates)} candidates.")
        for c in candidates:
            print(f"ID: {c.id}, Name: {c.name}, Username: {c.username}, Active: {c.is_active}")
            print(f"  Bot Token: '{c.bot_token}'")
            print(f"  Resume: '{c.resume}'")
            print(f"  Ideas: '{c.ideas}'")
            print(f"  Address: '{c.address}'")
            print("-" * 20)
    finally:
        db.close()

if __name__ == "__main__":
    inspect_candidates()
