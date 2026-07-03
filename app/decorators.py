from functools import wraps
from flask import session, redirect, url_for, flash, abort, request
from flask_login import current_user, logout_user


def shop_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the shop_id is stored in the session
        if 'shop_id' not in session:
            flash("Please enter your shop first.", "warning")
            return redirect(url_for('main.enter_shop'))
        return f(*args, **kwargs)
    return decorated_function

def payment_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Safety fallback: Ensure they even chose a shop first
        if 'shop_id' not in session:
            flash("Please enter your shop first.", "warning")
            return redirect(url_for('main.enter_shop'))
            
        # 2. Check the cached session payment boolean value
        if not session.get('shop_paid', False):
            flash("This shop's subscription is inactive. Please process payment.", "danger")
            return redirect(url_for('subscription.billing'))
            
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if not current_user.is_authenticated:

                session['next_url'] = request.endpoint

                flash(
                    "Please sign in to continue.",
                    "warning"
                )

                return redirect(url_for('auth.login'))

            if current_user.role not in allowed_roles:
               flash(
                   "You are not allowed to access that page.",
                   "danger"
               )

               return redirect(request.referrer or url_for('main.shop'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator