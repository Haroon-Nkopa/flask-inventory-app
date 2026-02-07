from app import create_app, db
from app.models import Product, InventoryRecord
from datetime import date, timedelta
import random

# Setup Flask app context
app = create_app()
app.app_context().push()

SHOP_ID = 3

# Get Miami products
products = Product.query.filter_by(shop_id=SHOP_ID).all()
if not products:
    raise Exception("No products found for Miami shop!")

# Time range: First week of January -> Today
start_date = date(date.today().year, 1, 3)
end_date = date.today()

# 3 stock counts per week (Mon, Wed, Fri)
stock_days = [0, 2, 4]

print(f"Generating inventory records from {start_date} to {end_date}")

# Category sales speed (higher = sells faster)
sales_speed = {
    "Beer": (4, 12),
    "Cider": (3, 10),
    "Ready-to-Drink": (3, 9),
    "Spirits": (1, 4),
    "Whisky": (1, 3),
    "Brandy": (1, 3),
    "Rum": (1, 3),
    "Wine": (1, 3),
    "Champagne": (0, 2),
    "Sparkling Wine": (0, 2),
    "Liqueur": (0, 2),
}

added = 0

for product in products:
    # Starting stock depends on product type
    if product.category in ["Beer", "Cider", "Ready-to-Drink"]:
        stock = random.randint(40, 90)
    else:
        stock = random.randint(10, 35)

    current_date = start_date

    while current_date <= end_date:
        # Only count stock on Mon/Wed/Fri
        if current_date.weekday() in stock_days:
            # Avoid duplicate record
            existing = InventoryRecord.query.filter_by(
                product_id=product.id,
                date=current_date
            ).first()

            if existing:
                current_date += timedelta(days=1)
                continue

            # Determine sales rate
            low, high = sales_speed.get(product.category, (1, 4))
            sold = random.randint(low, high)

            # Simulate stock drop
            stock = max(stock - sold, 0)

            # Simulate restock when low
            if stock <= product.lower_bound or stock == 0:
                restock_amount = random.randint(20, 80)
                stock += restock_amount

            record = InventoryRecord(
                product_id=product.id,
                date=current_date,
                quantity=stock
            )

            db.session.add(record)
            added += 1

        current_date += timedelta(days=1)

db.session.commit()

print(f"✅ Added {added} inventory records for Miami shop")
