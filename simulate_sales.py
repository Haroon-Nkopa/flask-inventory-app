import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models import Product, Sale, SaleItem, User, Shop

def simulate_sales(num_sales=30):
    app = create_app()
    with app.app_context():
        # 1. Fetch dependencies needed to reference relationships
        shop = Shop.query.first()
        user = User.query.filter_by(role='admin').first() or User.query.first()
        products = Product.query.filter_by(shop_id=shop.id).all() if shop else []

        if not shop or not user or not products:
            print("Error: Missing prerequisites. Ensure you have a Shop, a User, and Products in your database.")
            return

        print(f"Simulating {num_sales} sales over the past 7 days...")

        for i in range(num_sales):
            # Generate a random transaction timestamp spanning the last 7 days
            random_days_ago = random.randint(0, 7)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            sale_time = datetime.utcnow() - timedelta(days=random_days_ago, hours=random_hours, minutes=random_minutes)

            # Pick between 1 and 5 unique items for this specific customer basket
            basket_size = min(random.randint(1, 5), len(products))
            selected_products = random.sample(products, basket_size)

            # Create the initial parent Sale object with a placeholder total
            sale = Sale(
                timestamp=sale_time,
                total_amount=0.0,
                shop_id=shop.id,
                user_id=user.id
            )
            db.session.add(sale)
            
            # We must flush the session so 'sale.id' is generated for child rows
            db.session.flush()

            running_total = 0.0

            # Build out individual line items for the sale
            for product in selected_products:
                quantity = random.randint(1, 4)
                unit_price = product.price
                item_total = round(quantity * unit_price, 2)
                running_total += item_total

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=item_total
                )
                db.session.add(sale_item)

            # Update parent record with the true calculated basket cost
            sale.total_amount = round(running_total, 2)

        try:
            db.session.commit()
            print(f"Success! Simulated {num_sales} checkout receipts with itemized records.")
        except Exception as e:
            db.session.rollback()
            print(f"Database transaction rolled back due to error: {e}")

if __name__ == "__main__":
    # Simulates 30 sales by default; adjust the number inside the parentheses to change it
    simulate_sales(30)
