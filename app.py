from flask import Flask
from flask import request, jsonify
from models import db, MenuItem, Order, Reservation
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/food_ordering.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

is_db_initialized = False
#zxc#zxc
@app.before_request
def create_tables():
    global is_db_initialized
    if not is_db_initialized:
        db.create_all()
        is_db_initialized = True

@app.route('/menu', methods=['GET'])
def get_menu():
    menu_items = MenuItem.query.all()
    return jsonify(menu=[{'id': item.id, 'name': item.name, 'price': item.price} for item in menu_items])

@app.route('/order', methods=['POST'])
def make_order():
    data = request.json
    item_ids = data['item_ids']

    total_price = 0
    order_items = []

    for item_id in item_ids:
        item = MenuItem.query.get(item_id)
        if item:
            total_price += item.price
            order_items.append(item.name)
        else:
            return jsonify(message="Item not found", item_id=item_id), 404

    new_order = Order(items=str(order_items), total_price=total_price)
    db.session.add(new_order)
    db.session.commit()

    return jsonify(order_id=new_order.id, total_price=total_price, items=order_items)

@app.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return jsonify(orders=[
        {'id': order.id, 'items': order.items, 'total_price': order.total_price, 'order_time': order.order_time} for
        order in orders])

@app.route('/reserve', methods=['POST'])
def reserve_seat():
    data = request.json
    new_reservation = Reservation(
        user_name=data.get('user_name', 'Unknown'),
        seat_number=data['seat_number'],
        time=datetime.strptime(data['time'], '%Y-%m-%d %H:%M:%S')
    )
    db.session.add(new_reservation)
    db.session.commit()
    return jsonify(message="Reservation made successfully", reservation_id=new_reservation.id)

@app.route('/reservations', methods=['GET'])
def get_reservations():
    reservations = Reservation.query.all()
    reservations_list = [
        {
            'id': reservation.id,
            'user_name': reservation.user_name,
            'seat_number': reservation.seat_number,
            'time': reservation.time.strftime('%Y-%m-%d %H:%M:%S')
        } for reservation in reservations
    ]
    return jsonify(reservations=reservations_list)

@app.route('/check_availability', methods=['POST'])
def check_availability():
    data = request.json
    seat_number = data['seat_number']
    time = datetime.strptime(data['time'], '%Y-%m-%d %H:%M:%S')
    reservation = Reservation.query.filter_by(seat_number=seat_number, time=time).first()
    if reservation:
        return jsonify(available=False)
    return jsonify(available=True)

@app.route('/cancel_reservation/<int:reservation_id>', methods=['DELETE'])
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if reservation:
        db.session.delete(reservation)
        db.session.commit()
        return jsonify(message="Reservation cancelled successfully")
    return jsonify(message="Reservation not found"), 404


if __name__ == '__main__':
    app.run(debug=True, port=5002)
