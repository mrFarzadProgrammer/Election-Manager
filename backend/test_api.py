#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
تست کامل API
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# رنگ‌های ANSI برای کنسول
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"تست: {name}")
    print(f"{'='*60}{Colors.ENDC}")

def print_success(msg: str):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg: str):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

# ============================================================================
# Global variables
# ============================================================================
admin_token = None
admin_user_id = None
candidate_id = None
ticket_id = None
plan_id = None

# ============================================================================
# Test 1: Health Check
# ============================================================================
def test_health_check():
    print_test("بررسی سلامت سرور")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            print_success(f"سرور سالم است: {resp.json()}")
            return True
        else:
            print_error(f"سرور پاسخ نداد: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا در اتصال: {str(e)}")
        return False

# ============================================================================
# Test 2: Register Admin User
# ============================================================================
def test_register_admin():
    global admin_user_id
    print_test("ثبت نام کاربر Admin")
    
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "email": "admin@test.com",
        "full_name": "Admin User"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        if resp.status_code in [200, 201]:
            data = resp.json()
            admin_user_id = data.get("id")
            print_success(f"Admin ثبت نام شد: {data}")
            return True
        elif resp.status_code == 400:
            print_info("Admin قبلاً ثبت نام شده است")
            return True
        else:
            print_error(f"خطا در ثبت نام: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 3: Admin Login
# ============================================================================
def test_admin_login():
    global admin_token
    print_test("ورود Admin")
    
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            admin_token = data.get("access_token")
            print_success(f"Admin وارد شد - Token: {admin_token[:20]}...")
            return True
        else:
            print_error(f"خطا در ورود: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 4: Get Candidates
# ============================================================================
def test_get_candidates():
    print_test("دریافت لیست کاندیدها")
    
    try:
        resp = requests.get(f"{BASE_URL}/api/candidates")
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"تعداد کاندیدهای موجود: {len(data)}")
            if data:
                print_info(f"اولین کاندید: {data[0]}")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 5: Create Candidate
# ============================================================================
def test_create_candidate():
    global candidate_id
    print_test("ایجاد کاندید جدید")
    
    if not admin_token:
        print_error("هیچ توکن Admin موجود نیست")
        return False
    
    payload = {
        "name": "علی احمدی",
        "username": f"ali_test_{datetime.now().timestamp()}",
        "password": "testpass123",
        "phone": f"098{int(datetime.now().timestamp()) % 1000000000}",
        "bot_name": "AliBot",
        "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "slogan": "یک دولت بهتر",
        "bio": "من یک نامزد خوب هستم",
        "city": "تهران",
        "province": "تهران"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.post(f"{BASE_URL}/api/candidates", json=payload, headers=headers)
        if resp.status_code in [200, 201]:
            data = resp.json()
            candidate_id = data.get("id")
            print_success(f"کاندید ایجاد شد: {data.get('name')} (ID: {candidate_id})")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 6: Get Candidate by ID
# ============================================================================
def test_get_candidate():
    print_test("دریافت اطلاعات کاندید")
    
    if not candidate_id:
        print_error("هیچ کاندید موجود نیست")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/api/candidates/{candidate_id}")
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"کاندید دریافت شد: {data.get('name')}")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 7: Update Candidate
# ============================================================================
def test_update_candidate():
    print_test("بروزرسانی اطلاعات کاندید")
    
    if not candidate_id or not admin_token:
        print_error("اطلاعات ناکافی")
        return False
    
    payload = {
        "slogan": "دولت پاک و حساب‌کار",
        "bio": "تجربه ۲۰ سال در مدیریت"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.put(f"{BASE_URL}/api/candidates/{candidate_id}", json=payload, headers=headers)
        if resp.status_code == 200:
            print_success("کاندید بروزرسانی شد")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 8: Create Plan
# ============================================================================
def test_create_plan():
    global plan_id
    print_test("ایجاد پلن برای کاندید")
    
    if not candidate_id or not admin_token:
        print_error("اطلاعات ناکافی")
        return False
    
    payload = {
        "title": "پلن اقتصادی",
        "price": "رایگان",
        "description": "تقویت اقتصاد کشور",
        "features": ["کاهش تورم", "ایجاد شغل", "حمایت از صادرات"],
        "color": "#3b82f6",
        "candidate_id": candidate_id
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.post(f"{BASE_URL}/api/plans", json=payload, headers=headers)
        if resp.status_code in [200, 201]:
            data = resp.json()
            plan_id = data.get("id")
            print_success(f"پلن ایجاد شد: {data.get('title')} (ID: {plan_id})")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 9: Get Plans
# ============================================================================
def test_get_plans():
    print_test("دریافت لیست پلن‌ها")
    
    try:
        resp = requests.get(f"{BASE_URL}/api/plans")
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"تعداد پلن‌های موجود: {len(data)}")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 10: Create Ticket (Vote)
# ============================================================================
def test_create_ticket():
    global ticket_id
    print_test("ایجاد تیکت رای (Voting)")
    
    if not candidate_id:
        print_error("هیچ کاندید موجود نیست")
        return False
    
    payload = {
        "user_id": f"user_{int(datetime.now().timestamp())}",
        "candidate_id": candidate_id
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/tickets", json=payload)
        if resp.status_code in [200, 201]:
            data = resp.json()
            ticket_id = data.get("id")
            print_success(f"تیکت رای ایجاد شد (ID: {ticket_id})")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 11: Get Tickets
# ============================================================================
def test_get_tickets():
    print_test("دریافت لیست تیکت‌های رای")
    
    try:
        resp = requests.get(f"{BASE_URL}/api/tickets")
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"تعداد تیکت‌های موجود: {len(data)}")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 12: Verify Ticket
# ============================================================================
def test_verify_ticket():
    print_test("تایید و شمارش رای")
    
    if not ticket_id or not admin_token:
        print_error("اطلاعات ناکافی")
        return False
    
    payload = {"status": "approved"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.put(f"{BASE_URL}/api/tickets/{ticket_id}/verify", json=payload, headers=headers)
        if resp.status_code in [200, 204]:
            print_success("رای تایید شد")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 13: Update Plan
# ============================================================================
def test_update_plan():
    print_test("بروزرسانی پلن")
    
    if not plan_id or not admin_token:
        print_error("اطلاعات ناکافی")
        return False
    
    payload = {
        "description": "تقویت اقتصاد و جذب سرمایه خارجی"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.put(f"{BASE_URL}/api/plans/{plan_id}", json=payload, headers=headers)
        if resp.status_code == 200:
            print_success("پلن بروزرسانی شد")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            print_info(f"پاسخ: {resp.text}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Test 14: Get Current User
# ============================================================================
def test_get_current_user():
    print_test("دریافت اطلاعات کاربر جاری")
    
    if not admin_token:
        print_error("هیچ توکن موجود نیست")
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"کاربر جاری: {data.get('username')} ({data.get('role')})")
            return True
        else:
            print_error(f"خطا: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"خطا: {str(e)}")
        return False

# ============================================================================
# Main Test Runner
# ============================================================================
def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════╗")
    print("║         تست جامع API سامانه انتخابات             ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    tests = [
        ("بررسی سلامت سرور", test_health_check),
        ("ثبت نام Admin", test_register_admin),
        ("ورود Admin", test_admin_login),
        ("دریافت کاندیدها", test_get_candidates),
        ("ایجاد کاندید", test_create_candidate),
        ("دریافت کاندید", test_get_candidate),
        ("بروزرسانی کاندید", test_update_candidate),
        ("ایجاد پلن", test_create_plan),
        ("دریافت پلن‌ها", test_get_plans),
        ("بروزرسانی پلن", test_update_plan),
        ("ایجاد رای", test_create_ticket),
        ("دریافت رای‌ها", test_get_tickets),
        ("تایید رای", test_verify_ticket),
        ("دریافت کاربر جاری", test_get_current_user),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"خطا غیر منتظره: {str(e)}")
            results.append((name, False))
    
    # خلاصه نتایج
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════╗")
    print("║                    خلاصه نتایج                    ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if result else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BOLD}نتیجه نهایی: {passed}/{total} تست موفق{Colors.ENDC}\n")
    
    if passed == total:
        print(f"{Colors.OKGREEN}🎉 همه تست‌ها موفق بود!{Colors.ENDC}\n")
    else:
        print(f"{Colors.WARNING}⚠️  برخی تست‌ها ناموفق بود!{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
