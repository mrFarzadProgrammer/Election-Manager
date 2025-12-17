# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./election.db"

# تنظیمات اتصال به دیتابیس SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# این همان تابعی است که ارور می‌داد (get_db)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
