from functools import wraps
from flask import session, redirect, url_for, flash

def shop_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the shop_id is stored in the session
        if 'shop_id' not in session:
            flash("Please enter your shop first. from shop_required decorator", "warning")
            return redirect(url_for('main.enter_shop'))
        print("shop_id found in session:", session['shop_id'])
        return f(*args, **kwargs)
    return decorated_function

