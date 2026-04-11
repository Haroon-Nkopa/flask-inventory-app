from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db, create_app
from app.models import User, Shop, Product, InventoryRecord, Sale, SaleItem

app = create_app()

with app.app_context():
    # 1. Setup Shop and User
    shop = Shop.query.filter_by(name="Giant").first()
    if not shop:
        shop = Shop(name="Giant")
        db.session.add(shop)
    
    user = User.query.filter_by(username="rethabile").first()
    if not user:
        user = User(username="rethabile", password=generate_password_hash("admin123"), role='admin')
        db.session.add(user)
    
    if shop not in user.shops:
        user.shops.append(shop)
    
    db.session.flush()

    # 2. Define Products
    product_list = [
        {"name": "Coke 2L", "price": 25.0, "cat": "Soda", "start_qty": 50},
        {"name": "White Bread", "price": 18.5, "cat": "Bakery", "start_qty": 30},
        {"name": "Milk 1L", "price": 22.0, "cat": "Dairy", "start_qty": 40}
    ]

    # 3. Generate Data for the last 3 days
    for day_offset in range(3, -1, -1):  # From 3 days ago to today
        current_date = date.today() - timedelta(days=day_offset)
        current_time = datetime.now() - timedelta(days=day_offset)

        for p_data in product_list:
            # Get or Create Product
            product = Product.query.filter_by(name=p_data['name'], shop_id=shop.id).first()
            if not product:
                product = Product(
                    name=p_data['name'], 
                    price=p_data['price'], 
                    category=p_data['cat'], 
                    shop_id=shop.id,
                    lower_bound=5
                )
                db.session.add(product)
                db.session.flush()

            # Record Daily Inventory Snapshot
            # We'll simulate that each day we have 2-5 sales per product
            sold_today = 3 if day_offset > 0 else 0 # Assume 3 sold each past day
            
            # Update or create the record for this specific day
            record = InventoryRecord.query.filter_by(product_id=product.id, date=current_date).first()
            if not record:
                # Calculate quantity: start_qty minus what was sold in previous days
                remaining_qty = p_data['start_qty'] - ((3 - day_offset) * 3)
                record = InventoryRecord(product_id=product.id, date=current_date, quantity=remaining_qty)
                db.session.add(record)

            # 4. Create a Sale entry (Only for past days to simulate history)
            if day_offset > 0:
                sale = Sale(
                    timestamp=current_time,
                    total_amount=product.price * 2,
                    shop_id=shop.id,
                    user_id=user.id
                )
                db.session.add(sale)
                db.session.flush()

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=2,
                    unit_price=product.price,
                    total_price=product.price * 2
                )
                db.session.add(sale_item)

    db.session.commit()
    print("Database seeded with history, sales, and products successfully!")
