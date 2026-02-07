from app import create_app, db
from app.models import Product, InventoryRecord
from datetime import date, timedelta
import random

app = create_app()
app.app_context().push()

SHOP_ID = 1  # GIANT

products = Product.query.filter_by(shop_id=SHOP_ID).all()
if not products:
    raise Exception("No products found for Giant!")

# Date range: First week of January -> Today
start_date = date(date.today().year, 1, 3)
end_date = date.today()

# Stock count days: Mon, Wed, Fri
stock_days = [0, 2, 4]

print(f"Generating GIANT inventory history from {start_date} to {end_date}")

# Category sales behavior
sales_speed = {
    "Soft Drinks": (5, 15),
    "Snacks": (4, 12),
    "Bakery": (4, 10),
    "Juice": (3, 9),
    "Energy Drink": (3, 8),
    "Breakfast": (2, 6),
    "Groceries": (1, 5),
    "Staples": (1, 4),
    "Canned Food": (1, 4),
    "Hot Beverages": (0, 3),
    "Household": (0, 2),
}

added = 0

for product in products:
    # Starting stock based on category
    if product.category in ["Soft Drinks", "Snacks", "Bakery"]:
        stock = random.randint(40, 120)
    elif product.category in ["Groceries", "Staples"]:
        stock = random.randint(20, 60)
    else:
        stock = random.randint(8, 35)

    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() in stock_days:
            # Skip duplicates
            existing = InventoryRecord.query.filter_by(
                product_id=product.id,
                date=current_date
            ).first()

            if existing:
                current_date += timedelta(days=1)
                continue

            # Payday boost (15th & 25th)
            payday_boost = 1.0
            if current_date.day in [15, 25]:
                payday_boost = 1.6

            # Weekend boost
            weekend_boost = 1.2 if current_date.weekday() in [4, 5] else 1.0

            low, high = sales_speed.get(product.category, (1, 4))
            sold = int(random.randint(low, high) * payday_boost * weekend_boost)

            # Reduce stock
            stock = max(stock - sold, 0)

            # Restock logic
            if stock <= product.lower_bound or stock == 0:
                restock = random.randint(15, 80)
                stock += restock

            record = InventoryRecord(
                product_id=product.id,
                date=current_date,
                quantity=stock
            )

            db.session.add(record)
            added += 1

        current_date += timedelta(days=1)

db.session.commit()

print(f"✅ Added {added} inventory records for GIANT shop")
