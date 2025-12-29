import requests

def test_login():
    url = "http://localhost:8000/api/auth/login"
    payload = {
        "username": "admin",
        "password": "admin123"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful via HTTP")
        else:
            print("❌ Login failed via HTTP")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
