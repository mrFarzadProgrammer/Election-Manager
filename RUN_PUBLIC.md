# اجرای پروژه + لینک تست اینترنتی (Windows)

این راهنما برای اینه که **پنل (Frontend)** و **بک‌اند (API)** و **بات تلگرام** رو روی ویندوز اجرا کنی و یک **لینک عمومی** بدی تا دیگران از اینترنت تست کنن.

## پیش‌نیازها

- Node.js (نسخه 18+ پیشنهاد می‌شود)
- Python 3.11+
- دسترسی اینترنت (برای نصب پکیج‌ها و برای تلگرام)

## 1) اجرای بک‌اند (FastAPI)

در ریشه پروژه یک venv می‌تونی بسازی (اگر قبلاً ساخته نشده):

```powershell
python -m venv venv
```

فعال‌سازی venv:

```powershell
./venv/Scripts/Activate.ps1
```

نصب پکیج‌های بک‌اند:

```powershell
cd backend
pip install -r requirements.txt
```

اجرای API:

```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: `http://127.0.0.1:8000/docs`

### ساخت دیتابیس و اکانت ادمین (اگر لازم شد)

اگر دیتابیس خالی است یا می‌خواهی سریع دیتا نمونه داشته باشی:

```powershell
cd backend
python devtools/seed_data.py
```

اکانت پیش‌فرض:

- Admin: `admin`
- Password: `admin123`

اگر می‌خواهی دیتابیس را کامل ریست کنی:

```powershell
cd backend
python devtools/reset_db.py
```

## 2) اجرای پنل (React + Vite)

در یک ترمینال جدید:

```powershell
cd frontend
npm install
npm run dev
```

- پنل لوکال: `http://localhost:5173/`

نکته: در این پروژه Vite طوری تنظیم شده که مسیرهای `/api` و `/uploads` را به بک‌اند روی `127.0.0.1:8000` پروکسی کند؛ بنابراین کاربر نهایی از مرورگر فقط با همان آدرس پنل کار می‌کند.

## 3) اجرای بات تلگرام

در یک ترمینال جدید (با venv فعال):

```powershell
cd backend
python bot_runner.py
```

بات‌ها از دیتابیس خوانده می‌شوند و برای کاندیداهایی که `bot_token` معتبر دارند polling شروع می‌شود.

نکته: دیتای نمونه در `seed_data.py` توکن‌های فیک می‌سازد (برای تست پنل). برای اجرای واقعی بات باید در پنل (یا دیتابیس) `bot_token` واقعی Telegram را برای کاندیدا تنظیم کنی.

## 4) عمومی‌کردن برای تست اینترنتی (سریع‌ترین روش: Tunnel)

بهترین روش برای تست سریع اینه که **فقط پنل** رو عمومی کنی (پورت 5173). چون درخواست‌های API به شکل same-origin به `/api` می‌خورن و Vite پروکسی می‌کنه به بک‌اند روی همین سیستم؛ بنابراین نیاز نیست پورت 8000 رو مستقیم روی اینترنت باز کنی.

### گزینه A: Cloudflare Tunnel (بدون باز کردن پورت)

1) `cloudflared` را نصب کن:

- روش پیشنهادی: از سایت Cloudflare دانلود و نصب کن.

2) در یک ترمینال جدید اجرا کن:

```powershell
cloudflared tunnel --url http://localhost:5173
```

خروجی یک URL شبیه `https://something.trycloudflare.com` می‌دهد. همان لینک را بده دیگران تست کنند.

### گزینه B: ngrok (بدون باز کردن پورت)

1) ngrok را نصب و لاگین کن.
2) سپس:

```powershell
ngrok http 5173
```

لینک HTTPS که ngrok می‌دهد را به بقیه بده.

## 5) گزینه جایگزین: باز کردن مستقیم پورت (فقط اگر لازم شد)

اگر می‌خواهی بدون Tunnel و مستقیم با IP عمومی تست کنند، باید:

- روی مودم/روتر port-forward انجام بدهی (5173 و احتمالاً 8000)
- روی فایروال ویندوز اجازه inbound بدهی

این روش برای تست عمومی توصیه نمی‌شود (امنیت و دردسر بیشتر).

## 6) نکات امنیتی مهم (برای انتشار عمومی)

- برای تست سریع، بهتر است `APP_ENV` را روی `development` نگه داری.
- اگر `APP_ENV=production` بگذاری، باید `SECRET_KEY` و `REFRESH_SECRET_KEY` قوی تنظیم کنی و CORS را درست ست کنی.
- Vite dev server برای اینترنت، مناسب production نیست؛ فقط برای تست کوتاه‌مدت.

### روش بهتر برای تست اینترنتی (Single-Port / شبیه پروداکشن)

اگر می‌خواهی به جای Vite dev، یک خروجی build شده داشته باشی که از داخل بک‌اند سرو شود:

1) Build فرانت:

```powershell
cd frontend
npm run build
```

2) اجرای بک‌اند با سرو کردن فرانت (پورت 8000):

```powershell
cd backend
$env:SERVE_FRONTEND='1'
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

3) تونل را روی پورت 8000 بزن (مثلاً localtunnel):

```powershell
cd backend
npx localtunnel --port 8000
```

در این حالت، دیگران فقط یک لینک می‌بینند و هم UI و هم API روی همان Origin کار می‌کند.

## مشکلات رایج

- اگر تلگرام وصل نمی‌شود، VPN/فیلترشکن سیستم را چک کن.
- اگر دیگران صفحه را باز می‌کنند ولی API کار نمی‌کند، مطمئن شو که همچنان Vite server در حال اجراست و Tunnel به `5173` وصل است.
