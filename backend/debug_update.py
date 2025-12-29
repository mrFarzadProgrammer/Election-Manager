#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# Register and login
resp = requests.post(f"{BASE_URL}/api/auth/register", json={
    "username": f"admin_{int(time.time())}",
    "password": "admin123",
    "email": f"admin_{int(time.time())}@test.com",
    "full_name": "Admin User"
})

print(f"Register: {resp.status_code}")

# Login
resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": resp.json()["username"],
    "password": "admin123"
})

token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create candidate
resp = requests.post(f"{BASE_URL}/api/candidates", 
    json={
        "name": "علی احمدی",
        "username": f"ali_{int(time.time())}",
        "password": "pass123",
        "phone": f"09{int(time.time()) % 1000000000}",
        "bot_name": "AliBot",
        "bot_token": "123456:ABC",
    },
    headers=headers
)

if resp.status_code in [200, 201]:
    candidate_id = resp.json()["id"]
    print(f"✓ Created candidate: {candidate_id}")
    
    # Now try to update
    print("\nTrying to update...")
    resp = requests.put(f"{BASE_URL}/api/candidates/{candidate_id}",
        json={
            "slogan": "دولت پاک و حساب‌کار",
            "bio": "تجربه۲۰ سال"
        },
        headers=headers
    )
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
else:
    print(f"Failed to create: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
