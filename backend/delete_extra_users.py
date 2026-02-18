from sqlalchemy import create_engine, text

# مسیر دیتابیس را تنظیم کن
engine = create_engine('sqlite:///backend/election_manager.db')

with engine.connect() as conn:
    conn.execute(text("DELETE FROM users WHERE username IN ('testadmin', 'admin_1770983686')"))
    conn.commit()
    result = conn.execute(text("SELECT username, role FROM users"))
    print("کاربران باقی‌مانده:")
    for row in result:
        print(row)
