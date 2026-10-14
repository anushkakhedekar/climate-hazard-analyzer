from pymongo import MongoClient, ASCENDING
from .config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
weather = db["weather_years"]   # raw cache: one doc per (grid cell, year)
results = db["analyses"]        # computed analysis cache

def init_indexes():
    weather.create_index([("loc_key", ASCENDING), ("year", ASCENDING)], unique=True)
    results.create_index("key", unique=True)
    results.create_index("created_at", expireAfterSeconds=60 * 60 * 24 * 30)  # TTL: 30 days