import requests
import json

BASE_URL = "http://localhost:8000/api"

def login():
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Login failed:", response.text)
        return None

def test_update_plan():
    token = login()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # Get plans
    response = requests.get(f"{BASE_URL}/plans")
    plans = response.json()
    if not plans:
        print("No plans found")
        return

    plan = plans[0]
    plan_id = plan["id"]
    print(f"Updating plan {plan_id}...")

    new_title = plan["title"] + " Updated"

    # Simulate frontend payload
    frontend_payload = {
        "id": str(plan_id),
        "title": new_title,
        "price": plan["price"],
        "description": plan["description"],
        "features": plan["features"],
        "color": plan["color"],
        "is_visible": plan["is_visible"],
        "created_at_jalali": plan.get("created_at_jalali"),
        "extra_field": "should_be_ignored"
    }
    
    print(f"Sending payload: {json.dumps(frontend_payload, indent=2, ensure_ascii=False)}")

    response = requests.put(f"{BASE_URL}/plans/{plan_id}", json=frontend_payload, headers=headers)
    
    if response.status_code == 200:
        updated_plan = response.json()
        print("Update successful!")
        print("Old title:", plan["title"])
        print("New title:", updated_plan["title"])
        
        if updated_plan["title"] == new_title:
            print("✅ Verification successful")
        else:
            print("❌ Verification failed: Title did not change")
    else:
        print("Update failed:", response.text)

if __name__ == "__main__":
    test_update_plan()
