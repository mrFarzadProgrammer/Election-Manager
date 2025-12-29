#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import time

# Wait a bit for server to start
time.sleep(1)

BASE_URL = "http://127.0.0.1:8000"

print("تست 1: Health Check")
try:
    resp = requests.get(f"{BASE_URL}/health")
    print(f"✓ Health: {resp.status_code} - {resp.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\nتست 2: Register")
try:
    resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": "testadmin",
        "password": "test123",
        "email": "test@test.com",
        "full_name": "Test Admin"
    })
    print(f"✓ Register: {resp.status_code} - {resp.json()}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\nتست 3: Login")
try:
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "testadmin",
        "password": "test123"
    })
    print(f"✓ Login: {resp.status_code}")
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"  Token: {token[:30]}...")
except Exception as e:
    print(f"✗ Error: {e}")

print("\nتست 4: Get Candidates")
try:
    resp = requests.get(f"{BASE_URL}/api/candidates")
    print(f"✓ Candidates: {resp.status_code} - {len(resp.json())} candidates")
except Exception as e:
    print(f"✗ Error: {e}")
