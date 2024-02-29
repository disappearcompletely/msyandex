from flask import Flask
from flask import request, jsonify, render_template
from models import db, MenuItem, Order, Reservation
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
from keycloak import KeycloakOpenID
import os

app = Flask(__name__)
metrics = PrometheusMetrics(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://dmitriy:321123@localhost/club')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

is_db_initialized = False

keycloakid = KeycloakOpenID(server_url='http://keycloak:8080/', client_id='mscc', realm_name='cc', client_secret_key='sjftvpMkf1t5IEl0bw0IXwjjIE0HXkOq')

token = ''

def token_get(password, user_name):
    global token
    token = keycloakid.token(grant_type=['password'], username = user_name, password = password)

@app.route('/login')
def login():
    login = request.args.get('login')
    password = request.args.get('password')
    token_get(password, login)
    return '''<h1>Logged in</h1>'''.format(login)

def check_user_roles():
    global token
    try:
        userinfo = keycloakid.userinfo(token["access_token"])
        token_info = keycloakid.introspect(token["access_token"])
        if "moder" not in token_info["realm_access"]["roles"]:
            print('no role')
        return token_info
    except Exception as e:
        return ('error')

@app.before_request
def create_tables():
    global is_db_initialized
    if not is_db_initialized:
        db.create_all()
        is_db_initialized = True

@app.route('/')
def home():
    if check_user_roles() != 'error':
        return render_template('index.html')
    else:
        return('please,login')

@app.route('/menu', methods=['POST'])
def add_menu_item():
    if check_user_roles():
        data = request.json
        name = data.get('name')
        price = data.get('price')
        if not name or price is None:
            return jsonify({"error": "Имя или цена пропущены"}), 400
        new_item = MenuItem(name=name, price=price)
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Позиция была создана", "id": new_item.id}), 201
    else:
        return('please,login')

@app.route('/menu', methods=['GET'])
def get_menu():
    if check_user_roles():
        menu_items = MenuItem.query.all()
        return jsonify(menu=[{'id': item.id, 'name': item.name, 'price': item.price} for item in menu_items])
    else:
        return ('please, login')

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
            return jsonify(message="Заказ не найден", item_id=item_id), 404

    new_order = Order(items=str(order_items), total_price=total_price)
    db.session.add(new_order)
    db.session.commit()

    return jsonify(order_id=new_order.id, total_price=total_price, items=order_items)

@app.route('/orders', methods=['GET'])
def get_orders():
    if check_user_roles():
        orders = Order.query.all()
        return jsonify(orders=[
            {'id': order.id, 'items': order.items, 'total_price': order.total_price, 'order_time': order.order_time} for
            order in orders])
    else:
        return('please, login')

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
    return jsonify(message="Место успешно забронировано", reservation_id=new_reservation.id)

@app.route('/reservations', methods=['GET'])
def get_reservations():
    if check_user_roles():
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
    else:
        return('please, login')

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
        return jsonify(message="Бронь успешно отменена")
    return jsonify(message="Бронь не найдена"), 404


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5002'))
    app.run(debug=True, port=port)