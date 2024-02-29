from flask import Flask, request, jsonify, render_template
from models import db, Reservation
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
import os

app = Flask(__name__)
metrics = PrometheusMetrics(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://dmitriy:321123@localhost/club')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


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
        return jsonify(message="Бронь успешно отменена")
    return jsonify(message="Бронь не найдена"), 404

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    print("Получено уведомление: ", data)
    return jsonify({"message": "Уведомление получено"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5003)
