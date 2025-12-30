import requests
import json

try:
    response = requests.get("http://localhost:8000/api/candidates")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Data count: {len(data)}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
