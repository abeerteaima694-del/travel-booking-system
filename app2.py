from flask import Flask, request, jsonify
from functools import wraps
import sqlite3
app = Flask(__name__)
# Singleton 
class Database:
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.conn = sqlite3.connect("travel.db", check_same_thread=False)
            cls._instance.conn.row_factory = sqlite3.Row
        return cls._instance
db = Database().conn
db.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT,
    destination TEXT,
    seats INTEGER)''')
db.commit()
# . Flyweight 
class DestinationFactory:
    cache = {}
    @classmethod
    def get_destination(cls, destination):
        if destination not in cls.cache:
            cls.cache[destination] = {"destination": destination}
        return cls.cache[destination]
#  Observer
class EventBus:
    subscribers = []
    @classmethod
    def subscribe(cls, subscriber):
        cls.subscribers.append(subscriber)
    @classmethod
    def notify(cls, data):
        for sub in cls.subscribers:
            sub(data)
def log_booking(data):
    print("New booking notification:", data)
EventBus.subscribe(log_booking)
#  Decorator (Authentication) 
def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token != "Bearer secret123":
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper
#  Strategy + OCP 
class Discount:
    def apply(self, seats):
        return seats

class BonusSeatDiscount(Discount):
    def apply(self, seats):
        return seats + 1
# Pure Function
def validate_seats(seats):
    return isinstance(seats, int) and seats > 0

#. Service Layer (SRP) 
class BookingService:
    def __init__(self, db):
        self.db = db
    def create_booking(self, data, discount):
        if not validate_seats(data.get("seats")):
            return {"error": "Invalid seats"}
        DestinationFactory.get_destination(data["destination"])   # Flyweight
        final_seats = discount.apply(data["seats"])
        self.db.execute(
            "INSERT INTO bookings(user_name, destination, seats) VALUES(?,?,?)",
            (data["user_name"], data["destination"], final_seats))
        self.db.commit()
        EventBus.notify(data)        # Observer
        return {"message": "Booking created successfully", "seats": final_seats}
    def get_bookings(self):
        rows = self.db.execute("SELECT * FROM bookings").fetchall()
        return [dict(row) for row in rows]
    def update_booking(self, booking_id, data):
        self.db.execute("UPDATE bookings SET seats=? WHERE id=?", 
                       (data["seats"], booking_id))
        self.db.commit()
        return {"message": "Booking updated"}
    def delete_booking(self, booking_id):
        self.db.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
        self.db.commit()
        return {"message": "Booking deleted"}
#  Facade + DIP
class BookingFacade:
    def __init__(self, service):
        self.service = service
    def book(self, data):
        discount = BonusSeatDiscount() if data.get("offer") else Discount()
        return self.service.create_booking(data, discount)
service = BookingService(db)
facade = BookingFacade(service)
# (RESTful CRUD) 
@app.route("/")
def home():
    return jsonify({"message": "Travel Booking System - Project 47 is running"})
@app.route("/bookings", methods=["POST"])
@auth_required
def create_booking():
    if not request.json:
        return jsonify({"error": "JSON data required"}), 400
    return jsonify(facade.book(request.json))
@app.route("/bookings", methods=["GET"])
@auth_required
def get_bookings():
    return jsonify(service.get_bookings())
@app.route("/bookings/<int:id>", methods=["PUT"])
@auth_required
def update_booking(id):
    return jsonify(service.update_booking(id, request.json))
@app.route("/bookings/<int:id>", methods=["DELETE"])
@auth_required
def delete_booking(id):
    return jsonify(service.delete_booking(id))
if __name__ == "__main__":
    print("server is running")
    app.run(debug=True)