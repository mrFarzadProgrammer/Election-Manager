# database.py
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'election_manager.db')}")


def _env_int(name: str, default: int) -> int:
    try:
        raw = (os.getenv(name) or "").strip()
        return int(raw) if raw else int(default)
    except Exception:
        return int(default)


if "sqlite" in DATABASE_URL:
    sqlite_timeout = _env_int("SQLITE_BUSY_TIMEOUT_SEC", 30)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": sqlite_timeout},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA busy_timeout={sqlite_timeout * 1000}")
            cursor.close()
        except Exception:
            return
else:
    pool_size = _env_int("DB_POOL_SIZE", 10)
    max_overflow = _env_int("DB_MAX_OVERFLOW", 20)
    pool_timeout = _env_int("DB_POOL_TIMEOUT_SEC", 30)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
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


def _backfill_sqlite_commitments_status_updated_at() -> None:
    """Best-effort data migration for SQLite.

    Older databases may have NULL values in bot_commitments.status_updated_at
    (e.g., the column was added later via ALTER TABLE). Our API response models
    require a datetime, so we backfill to keep responses valid.
    """
    if "sqlite" not in DATABASE_URL:
        return
    try:
        insp = inspect(engine)
        if not insp.has_table("bot_commitments"):
            return
        cols = {c.get("name") for c in insp.get_columns("bot_commitments")}
        if "status_updated_at" not in cols:
            return

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE bot_commitments
                    SET status_updated_at = COALESCE(status_updated_at, published_at, created_at, CURRENT_TIMESTAMP)
                    WHERE status_updated_at IS NULL
                    """
                )
            )
    except Exception:
        # Non-fatal: endpoints also defensively fill values.
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

# v1.5+ schema additions (MVP learning panel)
_ensure_sqlite_table_column("bot_submissions", "answer_views_count", "INTEGER DEFAULT 0")
_ensure_sqlite_table_column("bot_submissions", "channel_click_count", "INTEGER DEFAULT 0")

_ensure_sqlite_table_column("bot_commitments", "view_count", "INTEGER DEFAULT 0")
_ensure_sqlite_table_column("bot_commitments", "category", "VARCHAR")
_ensure_sqlite_table_column("bot_commitments", "published_at", "DATETIME")
_ensure_sqlite_table_column("bot_commitments", "status_updated_at", "DATETIME")

_backfill_sqlite_commitments_status_updated_at()

_ensure_sqlite_table_column("bot_user_registry", "platform", "VARCHAR")
_ensure_sqlite_table_column("bot_user_registry", "total_interactions", "INTEGER DEFAULT 0")
_ensure_sqlite_table_column("bot_user_registry", "asked_question", "BOOLEAN DEFAULT 0")
_ensure_sqlite_table_column("bot_user_registry", "left_comment", "BOOLEAN DEFAULT 0")
_ensure_sqlite_table_column("bot_user_registry", "viewed_commitment", "BOOLEAN DEFAULT 0")
_ensure_sqlite_table_column("bot_user_registry", "became_lead", "BOOLEAN DEFAULT 0")
_ensure_sqlite_table_column("bot_user_registry", "selected_role", "VARCHAR")
_ensure_sqlite_table_column("bot_user_registry", "phone", "VARCHAR")

# v1.6+ schema additions (MVP monitoring)
_ensure_sqlite_table_column("bot_ux_logs", "expected_action", "VARCHAR")
_ensure_sqlite_table_column("admin_export_logs", "export_type", "VARCHAR")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
