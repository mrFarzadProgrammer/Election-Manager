from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


_INDEX_STMTS: list[str] = [
    # Registry: used by admin_mvp overview (distinct users) and active users
    "CREATE INDEX IF NOT EXISTS ix_bot_user_registry_candidate_last_seen ON bot_user_registry (candidate_id, last_seen_at)",
    "CREATE INDEX IF NOT EXISTS ix_bot_user_registry_candidate_telegram ON bot_user_registry (candidate_id, telegram_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_bot_user_registry_last_seen ON bot_user_registry (last_seen_at)",

    # Submissions: used by candidate/admin MVP queries
    "CREATE INDEX IF NOT EXISTS ix_bot_submissions_candidate_type_id ON bot_submissions (candidate_id, type, id)",
    "CREATE INDEX IF NOT EXISTS ix_bot_submissions_type_status ON bot_submissions (type, status)",

    # Commitments
    "CREATE INDEX IF NOT EXISTS ix_bot_commitments_candidate_id ON bot_commitments (candidate_id)",

    # Monitoring/logs
    "CREATE INDEX IF NOT EXISTS ix_bot_ux_logs_candidate_created ON bot_ux_logs (candidate_id, created_at)",
]


def ensure_indexes(engine: Engine) -> None:
    try:
        with engine.begin() as conn:
            for stmt in _INDEX_STMTS:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    # Best-effort: don't block startup.
                    pass
    except Exception:
        pass
