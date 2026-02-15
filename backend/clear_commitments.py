from database import SessionLocal
from models import BotCommitment, CommitmentProgressLog, CommitmentTermsAcceptance

def clear_commitments():
    db = SessionLocal()
    try:
        # Clear acceptance records so the full commitments onboarding can be re-tested.
        accept_count = db.query(CommitmentTermsAcceptance).delete()
        print(f"Deleted {accept_count} commitment terms acceptances.")

        # Delete all progress logs first (due to foreign key relationship)
        logs_count = db.query(CommitmentProgressLog).delete()
        print(f"Deleted {logs_count} commitment progress logs.")
        
        # Delete all commitments
        commitment_count = db.query(BotCommitment).delete()
        db.commit()
        print(f"Successfully deleted {commitment_count} commitments.")
        
        # Verify
        remaining = db.query(BotCommitment).count()
        print(f"Remaining commitments: {remaining}")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_commitments()
