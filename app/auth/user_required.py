from functools import wraps
from flask import redirect, session, url_for, flash, request
from flask_login import current_user

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        # 1️⃣ Ensure a shop is selected in session
        if 'shop_id' not in session:
            flash('Please select a shop first.', 'warning')
            return redirect(url_for('main.enter_shop'))

        if not current_user.is_authenticated:
            session['next_url'] = request.endpoint
            flash("Please log in first.", "danger")
            return redirect(url_for('auth.admin_login'))

        # 3️⃣ Ensure user belongs to this shop
        current_shop_id = session['shop_id']
        user_shop_ids = [shop.id for shop in current_user.shops]  # get all shop IDs the user belongs to
        if current_shop_id not in user_shop_ids:
            flash('You are not authorized for this shop', 'danger')
            session.clear()
            return redirect(url_for('auth.admin_login'))

        return f(*args, **kwargs)

    return decorated_function
