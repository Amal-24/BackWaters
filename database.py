import os
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import certifi

load_dotenv()

# MongoDB connection URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://amal:1234@houseboatmanagement.2dz6fvw.mongodb.net/?retryWrites=true&w=majority")
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

try:
    # Try with certifi CA bundle
    client = MongoClient(
        MONGO_URI,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )
    # Test connection
    client.admin.command('ping')
    print("✓ Connected to MongoDB Atlas")
except Exception as e:
    print(f"Warning: {e}")
    # Fallback: disable cert verification for development only
    client = MongoClient(
        MONGO_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )

db = client['houseboat_management']
boats_collection = db['boats']
users_collection = db['users']


def create_user(username, password, is_admin=False):
    user = {
        'username': username.strip().lower(),
        'password_hash': generate_password_hash(password),
        'is_admin': bool(is_admin)
    }
    return users_collection.insert_one(user)


def get_user_by_username(username):
    if not username:
        return None
    return users_collection.find_one({'username': username.strip().lower()})


def verify_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user.get('password_hash', ''), password):
        return user
    return None


def ensure_default_admin():
    admin = get_user_by_username(ADMIN_USERNAME)
    if not admin:
        create_user(ADMIN_USERNAME, ADMIN_PASSWORD, is_admin=True)
        print(f"✓ Default admin created: {ADMIN_USERNAME}")


def get_all_boats(search_query=None):
    if search_query:
        return list(boats_collection.find({"name": {"$regex": search_query, "$options": "i"}}))
    return list(boats_collection.find())


def get_boat_by_id(boat_id):
    return boats_collection.find_one({"_id": ObjectId(boat_id)})


def add_boat(name, rooms, ac_type, price_per_room):
    boat = {
        "name": name,
        "rooms": int(rooms),
        "ac_type": ac_type,
        "price_per_room": float(price_per_room),
        "bookings": [],
        "fuel_expenses": []
    }
    return boats_collection.insert_one(boat)


def update_boat(boat_id, name, rooms, ac_type, price_per_room):
    return boats_collection.update_one(
        {"_id": ObjectId(boat_id)},
        {"$set": {"name": name, "rooms": int(rooms), "ac_type": ac_type, "price_per_room": float(price_per_room)}}
    )


def delete_boat(boat_id):
    return boats_collection.delete_one({"_id": ObjectId(boat_id)})


def add_booking(boat_id, guest_name, date_str, revenue, rooms_booked=1):
    booking_date = datetime.strptime(date_str, "%Y-%m-%d")
    booking = {
        "guest_name": guest_name,
        "date": booking_date,
        "revenue": float(revenue),
        "rooms_booked": int(rooms_booked)
    }
    return boats_collection.update_one(
        {"_id": ObjectId(boat_id)},
        {"$push": {"bookings": booking}}
    )


def add_fuel_expense(boat_id, date_str, amount):
    expense_date = datetime.strptime(date_str, "%Y-%m-%d")
    expense = {
        "date": expense_date,
        "amount": float(amount)
    }
    return boats_collection.update_one(
        {"_id": ObjectId(boat_id)},
        {"$push": {"fuel_expenses": expense}}
    )


def get_profitability_analysis():
    # Current month start and end
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    
    pipeline = [
        {
            "$project": {
                "name": 1,
                "monthly_bookings": {
                    "$filter": {
                        "input": "$bookings",
                        "as": "booking",
                        "cond": { "$gte": ["$$booking.date", month_start] }
                    }
                },
                "monthly_expenses": {
                    "$filter": {
                        "input": "$fuel_expenses",
                        "as": "expense",
                        "cond": { "$gte": ["$$expense.date", month_start] }
                    }
                }
            }
        },
        {
            "$project": {
                "name": 1,
                "total_revenue": { "$sum": "$monthly_bookings.revenue" },
                "total_fuel_cost": { "$sum": "$monthly_expenses.amount" }
            }
        },
        {
            "$project": {
                "name": 1,
                "total_revenue": 1,
                "total_fuel_cost": 1,
                "profit": { "$subtract": ["$total_revenue", "$total_fuel_cost"] }
            }
        }
    ]
    
    return list(boats_collection.aggregate(pipeline))


ensure_default_admin()
