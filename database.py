# database.py (Replit DB-এর জন্য সম্পূর্ণ নতুন সংস্করণ)
from replit import db
import time

# --- User Management ---
def add_or_update_user(user_id: int, first_name: str, username: str):
    user_key = f"user_{user_id}"
    if user_key not in db:
        db[user_key] = {
            "first_name": first_name,
            "username": username,
            "join_date": int(time.time())
        }

# --- Admin Management ---
def add_admin(user_id: int):
    if "admins" not in db:
        db["admins"] = []
    
    admins = db["admins"]
    if user_id not in admins:
        admins.append(user_id)
        db["admins"] = admins
        return True
    return False

def remove_admin(user_id: int):
    if "admins" not in db:
        return False
        
    admins = db["admins"]
    if user_id in admins:
        admins.remove(user_id)
        db["admins"] = admins
        return True
    return False

def get_all_admins():
    return db.get("admins", [])

def is_admin_in_db(user_id: int):
    return user_id in db.get("admins", [])

# --- Log Management ---
def add_log(user_id: int, target_number: str, amount: int):
    log_key = f"log_{int(time.time())}_{random.randint(100, 999)}"
    db[log_key] = {
        "user_id": user_id,
        "target": target_number,
        "amount": amount,
        "timestamp": int(time.time())
    }

# --- Statistics ---
def get_public_stats():
    user_keys = db.prefix("user_")
    log_keys = db.prefix("log_")
    return len(user_keys), len(log_keys)

def get_all_user_ids():
    return [int(key.split('_')[1]) for key in db.prefix("user_")]

def get_user_stats(user_id: int):
    user_key = f"user_{user_id}"
    if user_key not in db:
        return None, 0
    
    user_info = db[user_key]
    log_keys = db.prefix("log_")
    task_count = sum(1 for key in log_keys if db[key].get("user_id") == user_id)
    
    return (user_info.get("first_name"), user_info.get("username")), task_count

# --- API Management (Replit DB version) ---
def setup_initial_apis():
    if "apis" in db:
        return
    
    initial_apis = [
        # ... (আগের API তালিকাটি এখানে থাকবে) ...
    ]
    db["apis"] = initial_apis
    print(f"Populated {len(initial_apis)} initial APIs into the database.")

def get_all_apis():
    return db.get("apis", [])

# Note: Add/Remove API functions would need to be rewritten for Replit DB if needed.
# For now, we will use a pre-populated list.
