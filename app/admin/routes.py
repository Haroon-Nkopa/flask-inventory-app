from . import admin_bp

from flask import render_template, request, redirect, url_for, flash, session
from ..models import Shop, db, User
from werkzeug.security import generate_password_hash
from flask_login import login_required, current_user


# Admin-only decorator
def admin_required(f):
    from functools import wraps
    from flask import abort
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Default route -> render admin login
@admin_bp.route('/', methods=['GET'])
def admin():
    if current_user.is_authenticated and current_user.role == 'admin':
        session['next_url'] = 'admin.register_shop'
        return redirect(url_for(session.get('next_url')))
    # Redirect to admin login page
    session['next_url'] = request.endpoint
    return redirect(url_for('auth.admin_login')) #this point to the admin login route in auth blueprint

@admin_bp.route('/shops', methods=['GET', 'POST'])
@admin_required
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
        return redirect(url_for('main.enter_shop'))

    shops = Shop.query.all()
    return render_template('admin/shops.html', shops=shops)


@admin_bp.route('/add_user_to_shop', methods=['GET', 'POST'])
@admin_required
def add_user_to_shop():

    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role', 'user')

        # ⬇️ MULTIPLE shops supported
        shop_ids = request.form.getlist('shop_ids')

        # Basic validation
        if not username or not password or not shop_ids:
            flash("All fields are required.", "danger")
            return redirect(url_for('admin.add_user_to_shop'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('admin.add_user_to_shop'))

        # Create user
        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )

        # Attach shops
        shops = Shop.query.filter(Shop.id.in_(shop_ids)).all()
        user.shops = shops

        db.session.add(user)
        db.session.commit()

        flash(f"User {username} created successfully.", "success")
        return redirect(url_for('admin.add_user_to_shop'))

    # GET → show form
    shops = Shop.query.all()
    return render_template(
        'admin/add_user_to_shop.html',
        shops=shops
    )
    pass