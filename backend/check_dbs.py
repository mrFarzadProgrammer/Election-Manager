import sqlite3
import os

def check_db(path, name):
    print(f"--- Checking {name} at {path} ---")
    if not os.path.exists(path):
        print("File does not exist.")
        return

    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password FROM users WHERE username='admin'")
        user = cursor.fetchone()
        if user:
            print(f"Found admin with hash: {user[2][:20]}...")
        else:
            print("Admin user NOT found.")
        conn.close()
    except Exception as e:
        print(f"Error reading DB: {e}")

root_db = os.path.join(os.path.dirname(os.getcwd()), "election_manager.db")
backend_db = "election_manager.db"

check_db(root_db, "Root DB")
check_db(backend_db, "Backend DB")
