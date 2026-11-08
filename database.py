import sqlite3

def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            target_gender TEXT,
            is_premium INTEGER DEFAULT 0,
            status TEXT DEFAULT 'free'
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def update_user_profile(user_id, name, age, gender):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, age=?, gender=? WHERE user_id=?", (name, age, gender, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, age, gender, target_gender, is_premium, status FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def set_premium(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def set_user_status(user_id, status):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE name IS NOT NULL")
    total_registered = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status != 'free'")
    total_online = cursor.fetchone()[0]
    conn.close()
    return total_registered, total_online
  
