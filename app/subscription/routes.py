from . import subscription 
from flask import render_template, request, jsonify
from werkzeug.security import generate_password_hash
from ..models import db, Shop, User

@subscription.route('/', methods=['GET'])
def subscription_landing():
    """Renders the subscription pricing and plan page."""
    # This page displays your tiers and the button to initiate checkout
    return render_template('subscription/subscription.html')

@subscription.route('/billing')
def billing():
    """Renders the subscription management page."""
    return render_template('subscription/billing.html')

@subscription.route('/process/', methods=['POST'])
def process_subscription():

    shop_name = request.form.get('shop_name', '').strip().title()
    owner_name = request.form.get('owner_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    password = request.form.get('password', '').strip()

    # Validation
    if not all([shop_name, owner_name, phone_number, password]):
        return jsonify({
            "status": "error",
            "message": "Please complete all fields."
        }), 400

    # Use phone number as username
    username = phone_number

    # Check if shop already exists
    existing_shop = Shop.query.filter_by(name=shop_name).first()
    if existing_shop:
        return jsonify({
            "status": "error",
            "message": "Edit the name"
        }), 400

    # Check if user already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({
            "status": "error",
            "message": "This phone number is already registered."
        }), 400

    try:
        # Create shop
        shop = Shop(
            name=shop_name
            #would be better if we get the shop location for analysis. 
        )

        # Create owner account
        user = User(
            username=username,
            password=generate_password_hash(password),
            role='owner'
        )

        # Link owner to shop
        user.shops.append(shop)

        db.session.add(shop)
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Shop created successfully.",
            "shop": shop.name,
            "username": username
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500