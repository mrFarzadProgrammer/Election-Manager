import requests
import asyncio
from unittest.mock import MagicMock
from database import SessionLocal
from models import BotUser
from bot_runner import save_bot_user

# --- Part 1: Ticket System Test (API) ---
BASE_URL = "http://localhost:8000/api"

def test_ticket_flow():
    print("--- Testing Ticket Flow ---")
    # 1. Login as Admin
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print(f"Admin login failed: {resp.text}")
        return
    admin_token = resp.json()["access_token"]

    # 2. Create Candidate (if not exists)
    headers = {"Authorization": f"Bearer {admin_token}"}
    cand_payload = {
        "name": "Ticket Tester",
        "username": "ticket_tester",
        "password": "password123",
        "bot_name": "ticket_bot",
        "bot_token": "123:TICKET",
        "is_active": True
    }
    
    # Try to create, ignore if fails (likely duplicate)
    requests.post(f"{BASE_URL}/candidates", json=cand_payload, headers=headers)
    
    # 3. Login as Candidate
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "ticket_tester", "password": "password123"})
    if resp.status_code != 200:
        print(f"Candidate login failed: {resp.text}")
        return
    cand_token = resp.json()["access_token"]

    # 4. Create Ticket
    ticket_payload = {"subject": "Test Ticket Subject", "message": "Test Ticket Message"}
    resp = requests.post(f"{BASE_URL}/tickets", json=ticket_payload, headers={"Authorization": f"Bearer {cand_token}"})
    if resp.status_code == 200:
        print("✅ Ticket created successfully")
    else:
        print(f"❌ Ticket creation failed: {resp.text}")

    # 5. Verify as Admin
    resp = requests.get(f"{BASE_URL}/tickets", headers=headers)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch tickets as admin: {resp.text}")
        return

    tickets = resp.json()
    found = False
    for t in tickets:
        if t['subject'] == "Test Ticket Subject":
            print(f"✅ Admin found the ticket. Candidate ID: {t['candidate_id']}")
            found = True
            break
    if not found:
        print("❌ Admin did not find the ticket")

# --- Part 2: Bot User Tracking Test (Unit Test) ---
async def test_bot_tracking():
    print("\n--- Testing Bot User Tracking ---")
    
    # Mock Update object
    mock_update = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.username = "test_tg_user"
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_update.effective_user = mock_user

    # Call save_bot_user
    try:
        await save_bot_user(mock_update, "test_bot_name")
        print("✅ save_bot_user executed without error")
    except Exception as e:
        print(f"❌ save_bot_user failed: {e}")
        return

    # Verify in DB
    db = SessionLocal()
    try:
        user = db.query(BotUser).filter(BotUser.telegram_id == "123456789").first()
        if user:
            print(f"✅ BotUser found in DB: {user.username} (ID: {user.telegram_id})")
            print(f"   Bot Name Used: {user.bot_name}")
            
            # Clean up
            db.delete(user)
            db.commit()
            print("   (Test data cleaned up)")
        else:
            print("❌ BotUser not found in DB")
    finally:
        db.close()

if __name__ == "__main__":
    test_ticket_flow()
    asyncio.run(test_bot_tracking())
