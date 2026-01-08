from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_user
from werkzeug.security import check_password_hash
from ..models import User  # import your User model
from . import auth_bp


@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
   
    if current_user.is_authenticated:
        print(session.get('next_url, user is already authenticated'))
        return redirect(url_for(session.get('next_url')))
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for('auth.admin_login'))

        # Check role
        if user.role != "admin":
            flash("You do not have admin privileges.", "danger")
            return redirect(url_for('auth.admin_login'))

        # Login the user (add to session)
        login_user(user)
        flash(f"Welcome, {user.username}!", "success")
        
        #lets add extra session data. 
        session['user_id']= user.id
        session['username']= user.username
        session['role']= user.role
        print(session.get('next_url'))

        #next_url = session.pop('next_url', None)
        return redirect(url_for(session.get('next_url')) or url_for('admin.admin'))

        #return redirect(url_for(session.get('next_url')))

    print(session.get('next_url'))
    # GET request -> show login form
    return render_template('auth/admin_login.html')

