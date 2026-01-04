from pymongo import MongoClient
import certifi

MONGO_URI = (
    "mongodb+srv://manideep:manideep@cluster0.mg7lyp3.mongodb.net/"
    "?retryWrites=true&w=majority"
)

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["facerecognx"]

# Old CLI-based collections (you can still keep them)
users_collection = db["users"]
attendance_collection = db["attendance"]

# New collections for web app
teachers_collection = db["teachers"]
students_collection = db["students"]
web_attendance_collection = db["web_attendance"]
