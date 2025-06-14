from parkingManagement import app, db, ADMIN_PASSWORD, ADMIN_USERNAME
from flask import render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from parkingManagement.forms import RegistrationForm, LoginForm, ParkingLotForm, BookingForm
from parkingManagement.modals import User, ParkingLot, ParkingSpot, Booking
from sqlalchemy.exc import SQLAlchemyError

@app.route('/')
def home_page():
    if not current_user.is_authenticated:
        return render_template('public_home.html', active_page='home')
    parking_lots = ParkingLot.query.all()
    booking_form = BookingForm()
    user_history = []
    allocated_spot = session.pop('allocated_spot', None)
    allocated_lot = session.pop('allocated_lot', None)
    if current_user.is_authenticated:
        user_history = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.entry_time.desc()).all()
    return render_template('home.html', active_page='home', parking_lots=parking_lots, booking_form=booking_form, user_history=user_history, allocated_spot=allocated_spot, allocated_lot=allocated_lot)

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
    lot_id = request.form.get('lot_id')
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

@app.route('/book_now', methods=['POST'])
def book_now():
    if not current_user.is_authenticated:
        flash('Please login to book a parking spot.', category='warning')
        return redirect(url_for('login_page'))
    lot_id = request.form.get('lot_id')
    vehicle_number = request.form.get('vehicle_number')
    vehicle_brand = request.form.get('vehicle_brand')
    vehicle_model = request.form.get('vehicle_model')
    from datetime import datetime
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        flash('Parking lot not found.', category='danger')
        return redirect(url_for('home_page'))
    # Find a free spot in the lot
    spot = ParkingSpot.query.filter_by(parking_lot_id=lot.id, status='free').first()
    if not spot:
        flash('No free spots available in this lot.', category='danger')
        return redirect(url_for('home_page'))
    # Calculate cost as 1 hour for now (can be updated later)
    cost = lot.price_per_hour
    booking = Booking(
        spot_id=spot.id,
        user_id=current_user.id,
        entry_time=datetime.now(),
        exit_time=None,
        vehicle_number=vehicle_number,
        vehicle_brand=vehicle_brand,
        vehicle_model=vehicle_model,
        cost=cost
    )
    spot.status = 'occupied'
    db.session.add(booking)
    db.session.commit()
    # Store spot number in session for modal popup
    session['allocated_spot'] = spot.id
    session['allocated_lot'] = lot.prime_location
    return redirect(url_for('home_page'))

@app.route('/release_spot/<int:booking_id>', methods=['POST'])
def release_spot(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user.id:
        return jsonify({'error': 'Invalid booking.'}), 400
    if booking.exit_time is not None:
        return jsonify({'error': 'Spot already released.'}), 400
    from datetime import datetime
    exit_time = datetime.now()
    entry_time = booking.entry_time
    lot = ParkingLot.query.get(ParkingSpot.query.get(booking.spot_id).parking_lot_id)
    price_per_hour = lot.price_per_hour if lot else 0
    duration_hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
    total_cost = price_per_hour * duration_hours
    # Return details for confirmation popup
    return jsonify({
        'entry_time': entry_time.strftime('%Y-%m-%d %H:%M'),
        'exit_time': exit_time.strftime('%Y-%m-%d %H:%M'),
        'price_per_hour': price_per_hour,
        'total_cost': total_cost
    })

@app.route('/pay_release/<int:booking_id>', methods=['POST'])
def pay_release(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user.id or booking.exit_time is not None:
        return jsonify({'error': 'Invalid booking.'}), 400
    from datetime import datetime
    exit_time = datetime.now()
    entry_time = booking.entry_time
    lot = ParkingLot.query.get(ParkingSpot.query.get(booking.spot_id).parking_lot_id)
    price_per_hour = lot.price_per_hour if lot else 0
    duration_hours = max(1, int((exit_time - entry_time).total_seconds() // 3600))
    total_cost = price_per_hour * duration_hours
    booking.exit_time = exit_time
    booking.cost = total_cost
    spot = ParkingSpot.query.get(booking.spot_id)
    spot.status = 'free'
    lot.revenue_per_lot += total_cost
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/spot_info/<int:spot_id>')
def admin_spot_info(spot_id):
    from datetime import datetime
    spot = ParkingSpot.query.get(spot_id)
    if not spot:
        return jsonify({'error': 'Spot not found.'}), 404
    lot = ParkingLot.query.get(spot.parking_lot_id)
    if not lot:
        return jsonify({'error': 'Parking lot not found.'}), 404
    booking = Booking.query.filter_by(spot_id=spot.id, exit_time=None).first()
    booking_info = {}
    if booking:
        user = User.query.get(booking.user_id)
        booking_info = {
            'user_name': user.name if user else 'Unknown',
            'user_email': user.emailId if user else 'Unknown',
            'vehicle_number': booking.vehicle_number,
            'vehicle_brand': booking.vehicle_brand,
            'vehicle_model': booking.vehicle_model,
            'entry_time': booking.entry_time.strftime('%Y-%m-%d %H:%M') if booking.entry_time else ''
        }
    return jsonify({
        'lot': {
            'prime_location': lot.prime_location,
            'address': lot.address,
            'pincode': lot.pincode,
            'price_per_hour': lot.price_per_hour,
            'max_spots': lot.max_spots
        },
        'spot': {
            'id': spot.id,
            'status': spot.status
        },
        'booking': booking_info
    })