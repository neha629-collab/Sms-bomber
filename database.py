# database.py (ব্যান ম্যানেজমেন্টসহ চূড়ান্ত সংস্করণ)
import os
import psycopg2
import json
from psycopg2 import sql

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def populate_initial_apis(cur):
    initial_apis = [
        {'name': 'Easy', 'url': 'https://core.easy.com.bd/api/v1/registration', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'password': '{random_string:?n*8}', 'password_confirmation': '{random_string:?n*8}', 'device_key': '{random_string:?i*32}', 'name': '{random_string:?l*6}', 'mobile': '{number}', 'email': '{random_string:?n*8}info@gmail.com'}},
        {'name': 'TrainingBD', 'url': 'https://training.gov.bd/backoffice/api/user/sendOtp', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'mobile': '{number}'}},
        {'name': 'Qcoom', 'url': 'https://auth.qcoom.com/api/v1/otp/send', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'mobileNumber': '+88{number}'}},
        {'name': 'Apex4u', 'url': 'https://api.apex4u.com/api/auth/login', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'phoneNumber': '{number}'}},
        {'name': 'Osudpotro', 'url': 'https://api.osudpotro.com/api/v1/users/send_otp', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'os': 'web', 'mobile': '+88-{number}', 'language': 'en', 'deviceToken': 'web'}},
        {'name': 'BusBD', 'url': 'https://api.busbd.com.bd/api/auth', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'phone': '+88{number}'}},
        {'name': 'Grameenphone', 'url': 'https://bkshopthc.grameenphone.com/api/v1/fwa/request-for-otp', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'phone': '{number}', 'language': 'en', 'email': ''}},
        {'name': 'Deshal', 'url': 'https://app.deshal.net/api/auth/login', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'phone': '{number}'}},
        {'name': 'Chorki', 'url': 'https://api-dynamic.chorki.com/v2/auth/login?country=BD&platform=web&language=en', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'number': '+88{number}'}},
        {'name': 'Robi', 'url': 'https://da-api.robi.com.bd/da-nll/otp/send', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'msisdn': '{number}'}},
        {'name': 'Shikho', 'url': 'https://api.shikho.com/public/activity/otp', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'phone': '{number}', 'intent': 'ap-discount-request'}},
        {'name': 'Garibook', 'url': 'https://api.garibookadmin.com/api/v3/user/login', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/3.9.1'}, 'data_template': {'recaptcha_token': 'garibookcaptcha', 'mobile': '{number}', 'channel': 'web'}},
        {'name': 'Pathao', 'url': 'https://api.pathao.com/v2/auth/register', 'method': 'POST', 'headers': {'User-Agent': 'okhttp/4.12.0'}, 'data_template': {'country_prefix': '880', 'national_number': '{number_slice:1}', 'country_id': 1}},
        {'name': 'Fundesh', 'url': 'https://fundesh.com.bd/api/auth/generateOTP?service_key=', 'method': 'POST', 'headers': {'User-Agent': 'Mozilla/5.0'}, 'data_template': {'msisdn': '{number_slice:1}'}}
    ]
    for api in initial_apis:
        cur.execute(
            "INSERT INTO apis (name, url, method, headers, data_template) VALUES (%s, %s, %s, %s, %s);",
            (api['name'], api['url'], api['method'], json.dumps(api['headers']), json.dumps(api['data_template']))
        )
    print(f"Populated {len(initial_apis)} initial APIs into the database.")

def setup_database():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # --- users টেবিল আপডেট করা হয়েছে ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        first_name VARCHAR(255),
                        username VARCHAR(255),
                        join_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_banned BOOLEAN DEFAULT FALSE
                    );
                """)
                # --- বাকি টেবিলগুলো অপরিবর্তিত ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        log_id SERIAL PRIMARY KEY, user_id BIGINT, target_number VARCHAR(20),
                        amount INT, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS apis (
                        api_id SERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE, url TEXT NOT NULL,
                        method VARCHAR(10) NOT NULL, headers JSONB, data_template JSONB, is_active BOOLEAN DEFAULT TRUE
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS admins (
                        user_id BIGINT PRIMARY KEY
                    );
                """)
                
                cur.execute("SELECT COUNT(*) FROM apis;")
                if cur.fetchone()[0] == 0:
                    populate_initial_apis(cur)

                conn.commit()
                print("Database tables checked/created successfully.")
        finally:
            conn.close()

# --- নতুন ব্যান ম্যানেজমেন্ট ফাংশন ---
def ban_user(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_banned = TRUE WHERE user_id = %s;", (user_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    return False

def unban_user(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_banned = FALSE WHERE user_id = %s;", (user_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    return False

def is_user_banned(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT is_banned FROM users WHERE user_id = %s;", (user_id,))
                result = cur.fetchone()
                return result[0] if result else False
        finally:
            conn.close()
    return False

def get_all_banned_users():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE is_banned = TRUE;")
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    return []

# ... (বাকি সব ফাংশন অপরিবর্তিত থাকবে) ...
def add_admin(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING;", (user_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    return False
def remove_admin(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM admins WHERE user_id = %s;", (user_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    return False
def get_all_admins():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM admins;")
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    return []
def is_admin_in_db(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM admins WHERE user_id = %s;", (user_id,))
                return cur.fetchone() is not None
        finally:
            conn.close()
    return False
def add_or_update_user(user_id: int, first_name: str, username: str):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, first_name, username) VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET first_name = EXCLUDED.first_name, username = EXCLUDED.username;
                """, (user_id, first_name, username))
                conn.commit()
        finally:
            conn.close()
def add_log(user_id: int, target_number: str, amount: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO logs (user_id, target_number, amount) VALUES (%s, %s, %s);", (user_id, target_number, amount))
                conn.commit()
        finally:
            conn.close()
def get_public_stats():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users;")
                total_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM logs;")
                total_tasks = cur.fetchone()[0]
                return total_users, total_tasks
        finally:
            conn.close()
    return 0, 0
def get_all_user_ids():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE is_banned = FALSE;")
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    return []
def get_user_stats(user_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM logs WHERE user_id = %s;", (user_id,))
                task_count = cur.fetchone()[0]
                cur.execute("SELECT first_name, username FROM users WHERE user_id = %s;", (user_id,))
                user_info = cur.fetchone()
                return user_info, task_count
        finally:
            conn.close()
    return None, 0
def get_all_apis():
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT api_id, name, url, method, headers, data_template, is_active FROM apis ORDER BY name;")
                return cur.fetchall()
        finally:
            conn.close()
    return []
def add_api(name, url, method, headers, data_template):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO apis (name, url, method, headers, data_template) VALUES (%s, %s, %s, %s, %s);",
                    (name, url, method, json.dumps(headers), json.dumps(data_template))
                )
                conn.commit()
                return True
        except psycopg2.IntegrityError:
            return False
        finally:
            conn.close()
    return False
def remove_api(api_id: int):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM apis WHERE api_id = %s;", (api_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    return False