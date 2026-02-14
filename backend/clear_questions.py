from __future__ import annotations

from database import SessionLocal
import models


def clear_all_questions() -> None:
    db = SessionLocal()
    try:
        # Collect question submission IDs first (so we can delete dependent rows).
        question_ids = [
            row[0]
            for row in db.query(models.BotSubmission.id)
            .filter(models.BotSubmission.type == "QUESTION")
            .all()
        ]

        if not question_ids:
            print("No QUESTION submissions found. Nothing to delete.")
            return

        deleted_votes = (
            db.query(models.BotQuestionVote)
            .filter(models.BotQuestionVote.submission_id.in_(question_ids))
            .delete(synchronize_session=False)
        )
        deleted_publish_logs = (
            db.query(models.BotSubmissionPublishLog)
            .filter(models.BotSubmissionPublishLog.submission_id.in_(question_ids))
            .delete(synchronize_session=False)
        )
        deleted_submissions = (
            db.query(models.BotSubmission)
            .filter(models.BotSubmission.id.in_(question_ids))
            .delete(synchronize_session=False)
        )

        db.commit()
        print(
            "Deleted QUESTION data: "
            f"submissions={deleted_submissions}, votes={deleted_votes}, publish_logs={deleted_publish_logs}"
        )

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_all_questions()
