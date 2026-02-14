from __future__ import annotations

from datetime import datetime

from database import SessionLocal
from models import BotSubmission


def main() -> None:
    db = SessionLocal()
    try:
        # Candidate/user id that owns the bot (per existing setup in this workspace)
        candidate_id = 2

        # Create a single, public, answered QUESTION submission for formatting tests.
        submission = BotSubmission(
            candidate_id=candidate_id,
            telegram_user_id="test_user_1",
            telegram_username="test_user_1",
            type="QUESTION",
            topic="اشتغال",
            constituency=None,
            text="آیا در صورت ورود به مجلس در زمینه اشتغال طرحی خواهید داشت؟",
            status="ANSWERED",
            answer=(
                "بله، ایجاد اشتغال پایدار از اولویت‌های اصلی من است و با تمرکز بر حمایت از کسب‌وکارهای "
                "محلی و تسهیل سرمایه‌گذاری، برنامه مشخصی ارائه می‌دهم."
            ),
            answered_at=datetime.utcnow(),
            is_public=True,
            is_featured=False,
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)
        print(f"seeded_question_id={submission.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
