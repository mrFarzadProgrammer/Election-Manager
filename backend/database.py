# database.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'election_manager.db')}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def _ensure_sqlite_table_column(table_name: str, column_name: str, sql_type: str) -> None:
    """Best-effort migration for SQLite: add a column if missing.

    This project doesn't use Alembic; without this, adding new columns breaks existing
    SQLite databases because `create_all()` won't ALTER existing tables.
    """
    if "sqlite" not in DATABASE_URL:
        return
    try:
        insp = inspect(engine)
        if not insp.has_table(table_name):
            return
        cols = {c.get("name") for c in insp.get_columns(table_name)}
        if column_name in cols:
            return
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))
    except Exception:
        # Non-fatal: app can still run against a fresh DB created with create_all().
        return


# v1.1+ schema additions
_ensure_sqlite_table_column("users", "constituency", "VARCHAR")

# v1.2+ schema additions (bot submissions)
_ensure_sqlite_table_column("bot_submissions", "constituency", "VARCHAR")
_ensure_sqlite_table_column("bot_submissions", "tag", "VARCHAR")

# v1.3+ schema additions (questions/FAQ)
_ensure_sqlite_table_column("bot_submissions", "answered_at", "DATETIME")
_ensure_sqlite_table_column("bot_submissions", "is_public", "BOOLEAN DEFAULT 0")
_ensure_sqlite_table_column("bot_submissions", "is_featured", "BOOLEAN DEFAULT 0")

# v1.4+ schema additions (bot build requests)
_ensure_sqlite_table_column("bot_submissions", "requester_full_name", "VARCHAR")
_ensure_sqlite_table_column("bot_submissions", "requester_contact", "VARCHAR")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
