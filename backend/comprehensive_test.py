#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def test_section(name):
    print(f"\n{bcolors.HEADER}{bcolors.BOLD}━━━ {name} ━━━{bcolors.ENDC}")

def success(msg):
    print(f"{bcolors.OKGREEN}✓ {msg}{bcolors.ENDC}")

def fail(msg):
    print(f"{bcolors.FAIL}✗ {msg}{bcolors.ENDC}")

def info(msg):
    print(f"{bcolors.OKCYAN}ℹ {msg}{bcolors.ENDC}")

# Global variables
token = None
candidate_id = None
plan_id = None
ticket_id = None
registered_username = None  # ✅ ذخیره username برای login

test_section("1️⃣  بررسی سلامت سرور")
try:
    resp = requests.get(f"{BASE_URL}/health")
    if resp.status_code == 200:
        success(f"سرور سالم است")
    else:
        fail(f"خطا: {resp.status_code}")
except Exception as e:
    fail(f"خطا اتصال: {e}")

test_section("2️⃣  ثبت نام و ورود")
try:
    # Register
    timestamp = int(time.time())
    register_data = {
        "username": f"admin_{timestamp}",
        "password": "admin123",
        "email": f"admin_{timestamp}@test.com",
        "full_name": "Admin User"
    }
    
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    
    if resp.status_code == 200:
        registered_username = register_data["username"]  # ✅ ذخیره username
        user_id = resp.json()["id"]
        success(f"ثبت نام موفق - Admin ID: {user_id}")
    else:
        fail(f"ثبت نام: {resp.status_code} - {resp.text}")
    
    # Login - ✅ از متغیر ذخیره شده استفاده
    if registered_username:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": registered_username,
            "password": "admin123"
        })
        
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            success(f"ورود موفق - Token: {token[:20]}...")
        else:
            fail(f"ورود: {resp.status_code} - {resp.text}")
        
except Exception as e:
    fail(f"خطا: {e}")

test_section("3️⃣  ایجاد و دریافت کاندید")
if token:
    try:
        # Create candidate
        headers = {"Authorization": f"Bearer {token}"}
        timestamp = int(time.time())
        resp = requests.post(f"{BASE_URL}/api/candidates", 
            json={
                "name": "علی احمدی",
                "username": f"ali_{timestamp}",
                "password": "pass123",
                "phone": f"09{timestamp % 1000000000}",
                "bot_name": "AliBot",
                "bot_token": f"bot_{timestamp}",  # ✅ یونیک کردن
                "slogan": "دولت پاک",
                "bio": "نامزد خوب",
                "city": "تهران",
                "province": "تهران"
            },
            headers=headers
        )
        
        if resp.status_code in [200, 201]:
            candidate_id = resp.json()["id"]
            success(f"کاندید ایجاد شد - ID: {candidate_id}")
        else:
            fail(f"ایجاد کاندید: {resp.status_code} - {resp.text}")
        
        # Get candidate
        if candidate_id:
            resp = requests.get(f"{BASE_URL}/api/candidates/{candidate_id}")
            if resp.status_code == 200:
                data = resp.json()
                success(f"دریافت کاندید: {data.get('name')}")
            else:
                fail(f"دریافت: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("4️⃣  بروزرسانی کاندید")
if token and candidate_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.put(f"{BASE_URL}/api/candidates/{candidate_id}",
            json={
                "slogan": "دولت پاک و حساب‌کار",
                "bio": "تجربه۲۰ سال"
            },
            headers=headers
        )
        
        if resp.status_code == 200:
            success(f"کاندید بروزرسانی شد")
        else:
            fail(f"بروزرسانی: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("5️⃣  ایجاد و دریافت پلن")
if token and candidate_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/api/plans",
            json={
                "title": "پلن اقتصادی",
                "price": "رایگان",
                "description": "تقویت اقتصاد",
                "features": ["کاهش تورم", "شغل"],
                "candidate_id": candidate_id
            },
            headers=headers
        )
        
        if resp.status_code in [200, 201]:
            plan_id = resp.json()["id"]
            success(f"پلن ایجاد شد - ID: {plan_id}")
        else:
            fail(f"ایجاد پلن: {resp.status_code} - {resp.text}")
        
        # Get plans
        resp = requests.get(f"{BASE_URL}/api/plans")
        if resp.status_code == 200:
            success(f"دریافت {len(resp.json())} پلن")
        else:
            fail(f"دریافت پلن‌ها: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("6️⃣  بروزرسانی پلن")
if token and plan_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.put(f"{BASE_URL}/api/plans/{plan_id}",
            json={"description": "تقویت اقتصاد و جذب سرمایه"},
            headers=headers
        )
        
        if resp.status_code == 200:
            success(f"پلن بروزرسانی شد")
        else:
            fail(f"بروزرسانی: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("7️⃣  ایجاد و دریافت رای (Ticket)")
if candidate_id:
    try:
        timestamp = int(time.time())
        resp = requests.post(f"{BASE_URL}/api/tickets",
            json={
                "user_id": f"user_{timestamp}",
                "candidate_id": candidate_id
            }
        )
        
        if resp.status_code in [200, 201]:
            ticket_id = resp.json()["id"]
            success(f"رای ایجاد شد - ID: {ticket_id}")
        else:
            fail(f"ایجاد رای: {resp.status_code} - {resp.text}")
        
        # Get tickets
        resp = requests.get(f"{BASE_URL}/api/tickets")
        if resp.status_code == 200:
            success(f"دریافت {len(resp.json())} رای")
        else:
            fail(f"دریافت رای‌ها: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("8️⃣  تایید و شمارش رای")
if token and ticket_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/verify",
            json={"status": "approved"},
            headers=headers
        )
        
        if resp.status_code in [200, 204]:
            success(f"رای تایید شد")
        else:
            fail(f"تایید: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("9️⃣  دریافت اطلاعات کاربر جاری")
if token:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            success(f"کاربر: {data.get('username')} ({data.get('role')})")
        else:
            fail(f"دریافت: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("🔟 حذف پلن")
if token and plan_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.delete(f"{BASE_URL}/api/plans/{plan_id}", headers=headers)
        
        if resp.status_code in [200, 204]:
            success(f"پلن حذف شد")
        else:
            fail(f"حذف: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

test_section("1️⃣1️⃣  حذف کاندید")
if token and candidate_id:
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.delete(f"{BASE_URL}/api/candidates/{candidate_id}", headers=headers)
        
        if resp.status_code in [200, 204]:
            success(f"کاندید حذف شد")
        else:
            fail(f"حذف: {resp.status_code}")
            
    except Exception as e:
        fail(f"خطا: {e}")

print(f"\n{bcolors.OKGREEN}{bcolors.BOLD}✨ تمام تست‌ها انجام شد!{bcolors.ENDC}\n")
