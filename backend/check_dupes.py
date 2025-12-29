from sqlalchemy.orm import Session
from database import SessionLocal
from models import Candidate

def check_duplicates():
    db = SessionLocal()
    candidates = db.query(Candidate).all()
    tokens = {}
    for c in candidates:
        if c.bot_token:
            if c.bot_token in tokens:
                print(f"DUPLICATE FOUND! Token {c.bot_token} is used by {tokens[c.bot_token]} and {c.name}")
            else:
                tokens[c.bot_token] = c.name
    print("Check complete.")
    db.close()

if __name__ == "__main__":
    check_duplicates()
