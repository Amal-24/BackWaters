import os
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime

load_dotenv()

# MongoDB connection (using local or environment variable)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://amal:1234@houseboatmanagement.2dz6fvw.mongodb.net/")
client = MongoClient(MONGO_URI)
db = client['houseboat_management']
boats_collection = db['boats']

def get_all_boats(search_query=None):
    if search_query:
        return list(boats_collection.find({"name": {"$regex": search_query, "$options": "i"}}))
    return list(boats_collection.find())

def get_boat_by_id(boat_id):
    return boats_collection.find_one({"_id": ObjectId(boat_id)})

def add_boat(name, rooms, ac_type):
    boat = {
        "name": name,
        "rooms": int(rooms),
        "ac_type": ac_type,
        "bookings": [],
        "fuel_expenses": []
    }
    return boats_collection.insert_one(boat)

def update_boat(boat_id, name, rooms, ac_type):
    return boats_collection.update_one(
        {"_id": ObjectId(boat_id)},
        {"$set": {"name": name, "rooms": int(rooms), "ac_type": ac_type}}
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
