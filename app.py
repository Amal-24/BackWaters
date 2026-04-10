from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import *
from bson.objectid import ObjectId
import json
from datetime import datetime

app = Flask(__name__)

# Custom JSON encoder for MongoDB ObjectIds and datetimes
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

app.json_encoder = MongoJSONEncoder

@app.route('/')
def index():
    search_query = request.args.get('search')
    boats = get_all_boats(search_query)
    return render_template('index.html', boats=boats, search_query=search_query)

@app.route('/boat/add', methods=['POST'])
def boat_add():
    name = request.form.get('name')
    rooms = request.form.get('rooms')
    ac_type = request.form.get('ac_type')
    add_boat(name, rooms, ac_type)
    return redirect(url_for('index'))

@app.route('/boat/update/<boat_id>', methods=['POST'])
def boat_update(boat_id):
    name = request.form.get('name')
    rooms = request.form.get('rooms')
    ac_type = request.form.get('ac_type')
    update_boat(boat_id, name, rooms, ac_type)
    return redirect(url_for('index'))

@app.route('/boat/delete/<boat_id>', methods=['POST'])
def boat_delete(boat_id):
    delete_boat(boat_id)
    return redirect(url_for('index'))

@app.route('/booking/add/<boat_id>', methods=['POST'])
def booking_add(boat_id):
    guest_name = request.form.get('guest_name')
    date_str = request.form.get('date')
    revenue = request.form.get('revenue')
    add_booking(boat_id, guest_name, date_str, revenue)
    return redirect(request.referrer or url_for('index'))

@app.route('/fuel/add/<boat_id>', methods=['POST'])
def fuel_add(boat_id):
    date_str = request.form.get('date')
    amount = request.form.get('amount')
    add_fuel_expense(boat_id, date_str, amount)
    return redirect(request.referrer or url_for('index'))

@app.route('/boat/<boat_id>')
def boat_details(boat_id):
    boat = get_boat_by_id(boat_id)
    if not boat:
        return redirect(url_for('index'))
    return render_template('details.html', boat=boat)

@app.route('/analysis')
def analysis():
    report = get_profitability_analysis()
    return render_template('analysis.html', report=report, now=datetime.now())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
