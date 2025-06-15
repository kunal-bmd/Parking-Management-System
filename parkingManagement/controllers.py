from flask import render_template, redirect, url_for, flash, session, request, jsonify, make_response
from flask_login import login_user, logout_user, current_user, login_required
from parkingManagement import app, db, ADMIN_PASSWORD, ADMIN_USERNAME
from parkingManagement.forms import RegistrationForm, LoginForm, ParkingLotForm, BookingForm
from parkingManagement.modals import User, ParkingLot, ParkingSpot, Booking
from sqlalchemy.exc import SQLAlchemyError
import io
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter, defaultdict
import matplotlib.dates as mdates

matplotlib.use('Agg')


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

    return render_template(
        'home.html',
        active_page='home',
        parking_lots=parking_lots,
        booking_form=booking_form,
        user_history=user_history,
        allocated_spot=allocated_spot,
        allocated_lot=allocated_lot
    )


@app.route('/admin_home', methods=['GET', 'POST'])
def admin_home_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))

    form = ParkingLotForm()
    lots = ParkingLot.query.all()
    lots_data = []

    # For each lot, get spots and occupancy
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
        return jsonify({'error': 'Invalid booking.'}, 400)

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


@app.route('/admin/user_summary')
def admin_user_summary():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))

    # Gather user stats
    users = User.query.all()
    total_users = len(users)

    # Active bookings (exit_time is None)
    active_bookings = Booking.query.filter_by(exit_time=None).count()

    # Registered vehicles (count unique vehicle_number in Booking)
    total_vehicles = len(set(b.vehicle_number for b in Booking.query.all()))

    # Bookings per user (bar chart)
    bookings_user_labels = [u.name for u in users]
    bookings_user_counts = [Booking.query.filter_by(user_id=u.id).count() for u in users]

    # User table data
    user_table = []
    for u in users:
        user_table.append({
            'name': u.name,
            'email': u.emailId,
            'type': 'User',
            'vehicle_count': len(set(b.vehicle_number for b in Booking.query.filter_by(user_id=u.id))),
            'booking_count': Booking.query.filter_by(user_id=u.id).count()
        })

    # Revenue and revenue per lot
    total_revenue = sum(lot.revenue_per_lot for lot in ParkingLot.query.all())
    revenue_per_lot = [(lot.prime_location, lot.revenue_per_lot) for lot in ParkingLot.query.all()]

    return render_template(
        'admin_user_summary.html',
        total_users=total_users,
        active_bookings=active_bookings,
        total_vehicles=total_vehicles,
        bookings_user_labels=bookings_user_labels,
        bookings_user_counts=bookings_user_counts,
        users=user_table,
        total_revenue=round(total_revenue, 2),
        revenue_per_lot=revenue_per_lot,
        active_page='summary'
    )


@app.route('/admin/bookings_bar_chart')
def bookings_bar_chart():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))

    users = User.query.all()
    labels = [u.name if u.name else f"User {u.id}" for u in users]
    counts = [Booking.query.filter_by(user_id=u.id).count() for u in users]

    fig, ax = plt.subplots(figsize=(max(6, len(labels)), 4), facecolor='#343a40')
    ax.bar(labels, counts, color='#17a2b8')
    ax.set_xlabel('User', color='white')
    ax.set_ylabel('Bookings', color='white')
    ax.set_title('Bookings per User', color='white')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')
    fig.patch.set_facecolor('#343a40')
    ax.set_facecolor('#343a40')
    for spine in ax.spines.values():
        spine.set_color('white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return make_response(buf.read(), 200, {'Content-Type': 'image/png'})


@app.route('/admin/revenue_per_lot_chart')
def revenue_per_lot_chart():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login_page'))

    lots = ParkingLot.query.all()
    labels = [lot.prime_location for lot in lots]
    revenues = [lot.revenue_per_lot for lot in lots]

    fig, ax = plt.subplots(figsize=(max(6, len(labels)), 4), facecolor='#343a40')
    ax.bar(labels, revenues, color='#dc3545')
    ax.set_xlabel('Lot', color='white')
    ax.set_ylabel('Revenue (₹)', color='white')
    ax.set_title('Revenue per Lot', color='white')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')
    fig.patch.set_facecolor('#343a40')
    ax.set_facecolor('#343a40')
    for spine in ax.spines.values():
        spine.set_color('white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return make_response(buf.read(), 200, {'Content-Type': 'image/png'})


@app.route('/user/summary')
@login_required
def user_summary():
    user_id = current_user.id
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.entry_time).all()
    total_bookings = len(bookings)
    active_bookings = sum(1 for b in bookings if b.exit_time is None)
    total_spent = sum(b.cost for b in bookings if b.exit_time is not None)

    # Prepare booking data for table
    booking_table = []
    for b in bookings:
        lot = ParkingLot.query.get(ParkingSpot.query.get(b.spot_id).parking_lot_id) if b.spot_id else None
        booking_table.append({
            'lot_name': lot.prime_location if lot else '-',
            'spot_id': b.spot_id,
            'vehicle_number': b.vehicle_number,
            'vehicle_brand': b.vehicle_brand,
            'vehicle_model': b.vehicle_model,
            'entry_time': b.entry_time.strftime('%Y-%m-%d %H:%M') if b.entry_time else '-',
            'exit_time': b.exit_time.strftime('%Y-%m-%d %H:%M') if b.exit_time else None,
            'cost': b.cost
        })

    return render_template(
        'user_summary.html',
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        total_spent=round(total_spent, 2),
        bookings=booking_table
    )


@app.route('/user/bookings_over_time_chart')
@login_required
def user_bookings_over_time_chart():
    user_id = current_user.id
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.entry_time).all()

    # Group by month
    months = [b.entry_time.strftime('%Y-%m') for b in bookings if b.entry_time]
    count_by_month = Counter(months)
    sorted_months = sorted(count_by_month.keys())
    counts = [count_by_month[m] for m in sorted_months]

    fig, ax = plt.subplots(figsize=(max(6, len(sorted_months)), 4), facecolor='#343a40')
    ax.plot(sorted_months, counts, marker='o', color='#ffc107')
    ax.set_xlabel('Month', color='white')
    ax.set_ylabel('Bookings', color='white')
    ax.set_title('Bookings Over Time', color='white')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')
    fig.patch.set_facecolor('#343a40')
    ax.set_facecolor('#343a40')
    for spine in ax.spines.values():
        spine.set_color('white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return make_response(buf.read(), 200, {'Content-Type': 'image/png'})


@app.route('/user/spending_over_time_chart')
@login_required
def user_spending_over_time_chart():
    user_id = current_user.id
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.entry_time).all()
    spending_by_month = defaultdict(float)
    for b in bookings:
        if b.entry_time and b.exit_time:
            month = b.entry_time.strftime('%Y-%m')
            spending_by_month[month] += b.cost
    sorted_months = sorted(spending_by_month.keys())
    spending = [spending_by_month[m] for m in sorted_months]

    fig, ax = plt.subplots(figsize=(max(6, len(sorted_months)), 4), facecolor='#343a40')
    ax.bar(sorted_months, spending, color='#28a745')
    ax.set_xlabel('Month', color='white')
    ax.set_ylabel('Spent (₹)', color='white')
    ax.set_title('Spending Over Time', color='white')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')
    fig.patch.set_facecolor('#343a40')
    ax.set_facecolor('#343a40')
    for spine in ax.spines.values():
        spine.set_color('white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return make_response(buf.read(), 200, {'Content-Type': 'image/png'})