# import_seed_data.py
import random
from datetime import date, timedelta
from app import db
from app.models import InventoryRecord, Product

def generate_inventory():
    # List of actual product IDs in your DB for shop_id=1
    product_ids = list(range(1, 49))

    # Stock parameters per product
    max_stock = {pid: 100 for pid in product_ids}  # max stock per product
    lower_bound = {pid: 10 for pid in product_ids} # restock threshold

    # Generate dates: every Monday, Thursday, Sunday from Jan 1 to today
    start_date = date(2026, 1, 1)
    end_date = date.today()
    delta = timedelta(days=1)
    dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in [0, 3, 6]:  # Monday=0, Thursday=3, Sunday=6
            dates.append(current_date)
        current_date += delta

    # Track current stock per product
    current_stock = {pid: max_stock[pid] for pid in product_ids}

    records_to_add = []

    for pid in product_ids:
        for d in dates:
            # Restock if below threshold
            if current_stock[pid] <= lower_bound[pid]:
                current_stock[pid] = max_stock[pid]
            
            # Sold today: random 5%-30% of current stock
            sold = random.randint(max(1, int(current_stock[pid]*0.05)), max(1, int(current_stock[pid]*0.3)))
            current_stock[pid] -= sold
            
            # Create InventoryRecord object
            record = InventoryRecord(
                product_id=pid,
                date=d,
                quantity=sold
            )
            records_to_add.append(record)

    # Bulk insert
    db.session.bulk_save_objects(records_to_add)
    db.session.commit()
    print(f"Inserted {len(records_to_add)} inventory records.")

if __name__ == "__main__":
    generate_inventory()
