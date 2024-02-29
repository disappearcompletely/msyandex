from flask import Flask, request, jsonify, render_template
from models import db, MenuItem, Order
from prometheus_flask_exporter import PrometheusMetrics
import requests
import os

app = Flask(__name__)
metrics = PrometheusMetrics(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://dmitriy:321123@localhost/club')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu', methods=['POST'])
def add_menu_item():
    data = request.json
    name = data.get('name')
    price = data.get('price')
    if not name or price is None:
        return jsonify({"error": "Missing name or price"}), 400
    new_item = MenuItem(name=name, price=price)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({"message": "Позиция была создана", "id": new_item.id}), 201

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
            return jsonify(message="Заказ не найден", item_id=item_id), 404
    new_order = Order(items=str(order_items), total_price=total_price)
    db.session.add(new_order)
    db.session.commit()
    send_notification(f"Новый заказ создан с ID {new_order.id}. Проверьте доступность необходимых ресурсов.")
    return jsonify(order_id=new_order.id, total_price=total_price, items=order_items)

@app.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return jsonify(orders=[
        {'id': order.id, 'items': order.items, 'total_price': order.total_price, 'order_time': order.order_time} for order in orders])

def send_notification(message):
    notification_url = 'http://reservation_service:5003/notify'
    data = {"message": message}
    response = requests.post(notification_url, json=data)
    return response.json()


if __name__ == '__main__':
    app.run(debug=True, port=5002)