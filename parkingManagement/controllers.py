from parkingManagement import app, db, ADMIN_PASSWORD, ADMIN_USERNAME
from flask import render_template, redirect, url_for, flash, session, request
from flask_login import login_user, logout_user, current_user, login_required
from parkingManagement.forms import RegistrationForm, LoginForm, ParkingLotForm
from parkingManagement.modals import User, ParkingLot, ParkingSpot
from sqlalchemy.exc import SQLAlchemyError

@app.route('/')
def home_page():
    return render_template('home.html', active_page='home')

@app.route('/admin_home', methods=['GET', 'POST'])
def admin_home_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))
    form = ParkingLotForm()
    lots = ParkingLot.query.all()
    # For each lot, get spots and occupancy
    lots_data = []
    for lot in lots:
        spots = ParkingSpot.query.filter_by(parking_lot_id=lot.id).all()
        occupied = sum(1 for s in spots if s.status == 'occupied')
        lots_data.append({
            'lot': lot,
            'spots': spots,
            'occupied': occupied,
            'total': lot.max_spots
        })
    if form.validate_on_submit():
        try:
            lot = ParkingLot(
                prime_location=form.prime_location.data,
                address=form.address.data,
                pincode=form.pincode.data,
                price_per_hour=form.price_per_hour.data,
                max_spots=form.max_spots.data,
                revenue_per_lot=0.0
            )
            db.session.add(lot)
            db.session.commit()
            # Create empty spots for the lot
            for _ in range(lot.max_spots):
                spot = ParkingSpot(parking_lot_id=lot.id, status='free')
                db.session.add(spot)
            db.session.commit()
            flash('Parking lot created successfully!', category='success')
            return redirect(url_for('admin_home_page'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating parking lot: ' + str(e), category='danger')
    return render_template('admin_home.html', form=form, lots_data=lots_data, active_page='admin_home')

@app.route('/logout')
def logout_page():
    if session.get('admin_logged_in'):
        session.pop('admin_logged_in')
        flash('Admin logged out.', category='info')
        return redirect(url_for('login_page'))
    logout_user()
    flash('Logged out successfully.', category='info')
    return redirect(url_for('login_page'))

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            password=form.password.data,  # You should hash the password in production
            emailId=form.emailId.data,
            name=form.name.data,
            address=form.address.data,
            pincode=form.pincode.data
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)  # Auto-login after registration
        flash('Account created and logged in successfully!', category='success')
        return redirect(url_for('home_page'))
    return render_template('register.html', form=form, active_page='register')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        # Admin login check
        if form.username.data == ADMIN_USERNAME and form.password.data == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Admin logged in successfully!', category='success')
            return redirect(url_for('admin_home_page'))
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password_correction(form.password.data):
            login_user(user)
            flash('Logged in successfully!', category='success')
            return redirect(url_for('home_page'))
        else:
            flash(f'Invalid username or password.', category='danger')
    return render_template('login.html', form=form, active_page='login')

@app.route('/admin/users')
def admin_users_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))
    users = User.query.all()
    return render_template('admin_users.html', users=users, active_page='users')

@app.route('/delete_lot', methods=['POST'])
def delete_lot():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))
    lot_id = request.form.get('lot_id')
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        flash('Parking lot not found.', category='danger')
        return redirect(url_for('admin_home_page'))
    spots = ParkingSpot.query.filter_by(parking_lot_id=lot.id).all()
    if any(s.status == 'occupied' for s in spots):
        flash("Can't delete as some spots are occupied.", category='danger')
        return redirect(url_for('admin_home_page'))
    try:
        for spot in spots:
            db.session.delete(spot)
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted successfully.', category='success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('Error deleting parking lot: ' + str(e), category='danger')
    return redirect(url_for('admin_home_page'))

@app.route('/edit_lot', methods=['POST'])
def edit_lot():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))
    lot_id = "2"
    if not lot_id or not lot_id.isdigit():
        flash('Invalid parking lot ID.', category='danger')
        return redirect(url_for('admin_home_page'))
    lot = ParkingLot.query.get(int(lot_id))
    if not lot:
        flash('Parking lot not found.', category='danger')
        return redirect(url_for('admin_home_page'))
    price_per_hour = request.form.get('price_per_hour')
    max_spots = request.form.get('max_spots')
    try:
        lot.price_per_hour = float(price_per_hour)
        old_max_spots = lot.max_spots
        lot.max_spots = int(max_spots)
        db.session.commit()
        # If max_spots increased, add new spots
        if lot.max_spots > old_max_spots:
            for _ in range(lot.max_spots - old_max_spots):
                spot = ParkingSpot(parking_lot_id=lot.id, status='free')
                db.session.add(spot)
            db.session.commit()
        # If max_spots decreased, remove extra spots (only if they are free)
        elif lot.max_spots < old_max_spots:
            spots = ParkingSpot.query.filter_by(parking_lot_id=lot.id).all()
            removable = [s for s in spots if s.status != 'occupied']
            to_remove = old_max_spots - lot.max_spots
            if len(removable) < to_remove:
                flash('Cannot reduce max spots below number of occupied spots.', category='danger')
                lot.max_spots = old_max_spots
                db.session.commit()
                return redirect(url_for('admin_home_page'))
            for spot in removable[:to_remove]:
                db.session.delete(spot)
            db.session.commit()
        flash('Parking lot updated successfully.', category='success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating parking lot: ' + str(e), category='danger')
    return redirect(url_for('admin_home_page'))