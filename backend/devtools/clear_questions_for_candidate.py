from __future__ import annotations

import sys

from _bootstrap import ensure_backend_on_path

ensure_backend_on_path()

from database import SessionLocal
import models


def clear_candidate_questions(candidate_id: int) -> None:
    db = SessionLocal()
    try:
        question_ids = [
            row[0]
            for row in (
                db.query(models.BotSubmission.id)
                .filter(
                    models.BotSubmission.type == "QUESTION",
                    models.BotSubmission.candidate_id == int(candidate_id),
                )
                .all()
            )
        ]

        if not question_ids:
            print(f"No QUESTION submissions found for candidate_id={candidate_id}. Nothing to delete.")
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
            "Deleted candidate QUESTION data: "
            f"candidate_id={candidate_id}, submissions={deleted_submissions}, votes={deleted_votes}, publish_logs={deleted_publish_logs}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _parse_candidate_id(argv: list[str]) -> int:
    if len(argv) < 2 or not str(argv[1]).strip():
        raise SystemExit("Usage: python backend/devtools/clear_questions_for_candidate.py <candidate_id>")
    try:
        return int(str(argv[1]).strip())
    except Exception:
        raise SystemExit("candidate_id must be an integer")


if __name__ == "__main__":
    clear_candidate_questions(_parse_candidate_id(sys.argv))
