import requests
import sys

BASE_URL = "http://localhost:8001/api"

def test():
    # 1. Login Admin
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Candidate
    cand_data = {
        "name": "Test Cand",
        "username": "testcand_active",
        "password": "password123",
        "bot_name": "testbot",
        "bot_token": "123:token"
    }
    resp = requests.post(f"{BASE_URL}/candidates", json=cand_data, headers=headers)
    if resp.status_code != 200:
        print("Create candidate failed:", resp.text)
        # Try to get existing
        resp = requests.get(f"{BASE_URL}/candidates", headers=headers)
        cands = resp.json()
        cand = next((c for c in cands if c["username"] == "testcand_active"), None)
        if not cand:
            return
        cand_id = cand["id"]
    else:
        cand_id = resp.json()["id"]
    
    print(f"Candidate ID: {cand_id}")

    # 3. Update is_active to False
    print("Updating is_active to False...")
    resp = requests.put(f"{BASE_URL}/candidates/{cand_id}", json={"is_active": False}, headers=headers)
    if resp.status_code != 200:
        print("Update failed:", resp.text)
        return
    
    print("Update response:", resp.json())

    # 4. Verify Candidate
    resp = requests.get(f"{BASE_URL}/candidates/{cand_id}", headers=headers)
    cand = resp.json()
    print(f"Candidate is_active: {cand['is_active']}")

    # 5. Verify User (Need to check DB or try login)
    # Try login as candidate
    print("Trying login as candidate...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "testcand_active", "password": "password123"})
    print(f"Login status (should be 401 or similar if inactive): {resp.status_code}")
    if resp.status_code == 200:
        print("FAIL: Candidate can still login!")
    else:
        print("SUCCESS: Candidate cannot login.")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print(e)
