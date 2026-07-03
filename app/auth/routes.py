from flask import render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from ..models import User
from . import auth_bp
from ..decorators import shop_required



@auth_bp.route('/login', methods=['GET', 'POST'])
@shop_required
def login():

    next_endpoint = session.get('next_url')

    if current_user.is_authenticated:

        if next_endpoint:
            return redirect(url_for(next_endpoint))
        

        

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('auth.login'))

        if not check_password_hash(user.password, password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for('auth.login'))

        # Login user
        login_user(user)

        flash(
            f"Welcome back, {user.username}!",
            "success"
        )

        # Redirect to requested page
        next_endpoint = session.pop('next_url', None)
        
        if next_endpoint:
            return redirect(url_for(next_endpoint))

        # Default destination
        return redirect(url_for('main.shop'))

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET'])
def logout():

    logout_user()
    session.clear()

    return redirect(url_for('main.enter_shop'))