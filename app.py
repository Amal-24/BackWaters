import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from database import *
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me-secret')

# Custom JSON encoder for MongoDB ObjectIds and datetimes
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

app.json_encoder = MongoJSONEncoder

# Authentication helpers

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
@login_required
def index():
    search_query = request.args.get('search')
    boats = get_all_boats(search_query)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return render_template('index.html', boats=boats, search_query=search_query, today=today)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = verify_user(username, password)
        if user and not user.get('is_admin'):
            session['user'] = user['username']
            session['is_admin'] = False
            return redirect(url_for('index'))
        message = 'Invalid credentials or administrative login required on admin page.'
    return render_template('login.html', message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            message = 'Please provide both username and password.'
        elif get_user_by_username(username):
            message = 'Username already exists. Please choose another.'
        else:
            create_user(username, password)
            session['user'] = username
            session['is_admin'] = False
            return redirect(url_for('index'))
    return render_template('register.html', message=message)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = verify_user(username, password)
        if user and user.get('is_admin'):
            session['user'] = user['username']
            session['is_admin'] = True
            return redirect(url_for('index'))
        message = 'Invalid admin credentials.'
    return render_template('admin_login.html', message=message)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/boat/add', methods=['POST'])
@login_required
@admin_required
def boat_add():
    name = request.form.get('name')
    rooms = request.form.get('rooms')
    ac_type = request.form.get('ac_type')
    price_per_room = request.form.get('price_per_room')
    add_boat(name, rooms, ac_type, price_per_room)
    return redirect(url_for('index'))


@app.route('/boat/update/<boat_id>', methods=['POST'])
@login_required
@admin_required
def boat_update(boat_id):
    name = request.form.get('name')
    rooms = request.form.get('rooms')
    ac_type = request.form.get('ac_type')
    price_per_room = request.form.get('price_per_room')
    update_boat(boat_id, name, rooms, ac_type, price_per_room)
    return redirect(url_for('index'))


@app.route('/boat/delete/<boat_id>', methods=['POST'])
@login_required
@admin_required
def boat_delete(boat_id):
    delete_boat(boat_id)
    return redirect(url_for('index'))


@app.route('/booking/add/<boat_id>', methods=['POST'])
@login_required
def booking_add(boat_id):
    guest_name = request.form.get('guest_name')
    date_str = request.form.get('date')
    revenue = request.form.get('revenue')
    rooms_booked = request.form.get('rooms_booked', 1)
    add_booking(boat_id, guest_name, date_str, revenue, rooms_booked)
    return redirect(url_for('boat_details', boat_id=boat_id))


@app.route('/booking/delete/<boat_id>/<int:booking_index>', methods=['POST'])
@login_required
@admin_required
def booking_delete(boat_id, booking_index):
    boat = get_boat_by_id(boat_id)
    if boat and 0 <= booking_index < len(boat['bookings']):
        boat['bookings'].pop(booking_index)
        boats_collection.update_one({'_id': ObjectId(boat_id)}, {'$set': {'bookings': boat['bookings']}})
    return redirect(url_for('boat_details', boat_id=boat_id))


@app.route('/fuel/add/<boat_id>', methods=['POST'])
@login_required
@admin_required
def fuel_add(boat_id):
    date_str = request.form.get('date')
    amount = request.form.get('amount')
    add_fuel_expense(boat_id, date_str, amount)
    return redirect(request.referrer or url_for('index'))


@app.route('/boat/<boat_id>')
@login_required
def boat_details(boat_id):
    boat = get_boat_by_id(boat_id)
    if not boat:
        return redirect(url_for('index'))
    return render_template('details.html', boat=boat, now=datetime.now())


@app.route('/analysis')
@login_required
@admin_required
def analysis():
    report = get_profitability_analysis()
    return render_template('analysis.html', report=report, now=datetime.now())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
