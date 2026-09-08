from . import admin_bp

from flask import render_template, request, redirect, url_for, flash, session, abort, jsonify
from ..models import Shop, db, User
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from ..decorators import roles_required

@admin_bp.route('/', methods=['GET', 'POST'])
def admin_login():
    """Isolated landing page and authentication handler for system administrators."""
    # 1. If already authenticated as an admin, bypass and send to dashboard
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'admin':
        return redirect(url_for('admin.register_shop'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # 2. Database validation check
        user = User.query.filter_by(username=username).first()
        
        # 3. Security verification (Checks password AND strictly enforces 'admin' role)
        if user and check_password_hash(user.password, password):
            if user.role == 'admin':
                login_user(user)
                flash('Welcome back to the Control Panel, Administrator.', 'success')
                return redirect(url_for('admin.register_shop'))
            else:
                flash('Access Denied: This portal is restricted to system administrators.', 'danger')
                return redirect(url_for('admin.admin_login'))
        else:
            flash('Invalid admin credentials. Please try again.', 'danger')
            return redirect(url_for('admin.admin_login'))

    # GET → Render the brand-new dedicated login template
    return render_template('admin/admin_login.html')

@admin_bp.route('/logout')
@login_required
def admin_logout():
    """Logs out the current administrator."""
    logout_user()
    session.clear()
    flash('You have logged out of the Admin Portal.', 'info')
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/shops', methods=['GET', 'POST'])
@roles_required('admin')
@login_required
def register_shop():
    if request.method == 'POST':
        shop_name = request.form['name'].strip()
        if Shop.query.filter_by(name=shop_name).first():
            flash('Shop already exists!', 'warning')
            return redirect(url_for('admin.register_shop'))
        else:
            new_shop = Shop(name=shop_name)
            db.session.add(new_shop)
            db.session.commit()
            flash(f'Shop "{shop_name}" registered successfully!', 'success')
        return redirect(url_for('admin.register_shop'))

    shops = Shop.query.order_by(Shop.name).all()
    return render_template('admin/shops.html', shops=shops)



@admin_bp.route('/toggle-shop-paid', methods=['POST'])
@roles_required('admin')
def toggle_shop_paid():
    data = request.get_json() or {}
    shop_id = data.get('shop_id')
    shop = Shop.query.get(shop_id)
    if not shop:
        return jsonify({'success': False, 'error': 'Shop not found'}), 404
    shop.paid = not shop.paid
    db.session.commit()
    return jsonify({
        'success': True, 
        'new_status': shop.paid,
        'message': f"Shop '{shop.name}' is now {'Paid' if shop.paid else 'Unpaid'}."
    })

@admin_bp.route('/add_user_to_shop', methods=['GET', 'POST'])
@roles_required('admin')
def add_user_to_shop():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role', 'user')
        shop_ids = request.form.getlist('shop_ids')

        if not username or not password or not shop_ids:
            flash("All fields are required.", "danger")
            return redirect(url_for('admin.add_user_to_shop'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('admin.add_user_to_shop'))

        user = User(username=username, password=generate_password_hash(password), role=role)
        shops = Shop.query.filter(Shop.id.in_(shop_ids)).all()
        user.shops = shops
        db.session.add(user)
        db.session.commit()
        flash(f"User {username} created successfully.", "success")
        return redirect(url_for('admin.add_user_to_shop'))

    shops = Shop.query.all()
    return render_template('admin/add_user_to_shop.html', shops=shops)
