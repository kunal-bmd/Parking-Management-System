from parkingManagement import db, login_manager
from parkingManagement import bcrypt 
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=128), nullable=False)
    emailId = db.Column(db.String(length=50), nullable=False, unique=True)
    name = db.Column(db.String(length=50), nullable=False)
    address = db.Column(db.String(length=100), nullable=False)
    pincode = db.Column(db.String(length=10), nullable=False)

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        try:
            return bcrypt.check_password_hash(self.password_hash, attempted_password)
        except (ValueError, TypeError):
            return False

class ParkingLot(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    prime_location = db.Column(db.String(length=100), nullable=False)
    address = db.Column(db.String(length=100), nullable=False)
    pincode = db.Column(db.String(length=10), nullable=False)
    price_per_hour = db.Column(db.Float(), nullable=False)
    max_spots = db.Column(db.Integer(), nullable=False)
    revenue_per_lot = db.Column(db.Float(), nullable=False)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    parking_lot_id = db.Column(db.Integer(), db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(length=20), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    spot_id = db.Column(db.Integer(), db.ForeignKey('parking_spot.id'), nullable=False)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    entry_time = db.Column(db.DateTime(), nullable=False)
    exit_time = db.Column(db.DateTime(), nullable=True)
    vehicle_number = db.Column(db.String(length=20), nullable=False)
    vehicle_brand = db.Column(db.String(length=30), nullable=False)
    vehicle_model = db.Column(db.String(length=30), nullable=False)
    cost = db.Column(db.Float(), nullable=False)

