"""Inspect Telegram bot user registry.

Usage:
  python backend/inspect_bot_user_registry.py
  python backend/inspect_bot_user_registry.py --candidate-id 19
  python backend/inspect_bot_user_registry.py --limit 50

This reads the SQLite/Postgres DB configured by database.py.
"""

from __future__ import annotations

import argparse
from datetime import datetime

from database import SessionLocal
from models import BotUserRegistry


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    s = SessionLocal()
    try:
        q = s.query(BotUserRegistry)
        if args.candidate_id is not None:
            q = q.filter(BotUserRegistry.candidate_id == args.candidate_id)

        rows = q.order_by(BotUserRegistry.last_seen_at.desc()).limit(args.limit).all()

        print(f"Rows: {len(rows)}")
        for r in rows:
            print(
                f"candidate_id={r.candidate_id} | telegram_user_id={r.telegram_user_id} | "
                f"username={r.telegram_username or '-'} | chat={r.chat_type or '-'} | "
                f"city={r.candidate_city or '-'} | province={r.candidate_province or '-'} | constituency={r.candidate_constituency or '-'} | "
                f"first={_fmt_dt(r.first_seen_at)} | last={_fmt_dt(r.last_seen_at)}"
            )
    finally:
        s.close()


if __name__ == "__main__":
    main()
