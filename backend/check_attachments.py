from database import SessionLocal
from models import TicketMessage

db = SessionLocal()
msgs = db.query(TicketMessage).filter(TicketMessage.attachment_url != None).all()

for msg in msgs:
    print(f"Message ID: {msg.id}")
    print(f"Sender Role: {msg.sender_role}")
    print(f"Text: {msg.text}")
    print(f"Attachment URL: {msg.attachment_url}")
    print(f"Attachment Type: {msg.attachment_type}")
    print("-" * 20)
