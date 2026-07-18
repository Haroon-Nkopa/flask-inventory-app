import random
from datetime import datetime, timedelta

# Import the db instance and the application factory creator from your app folder
from app import db 
from app import create_app  # Adjust this if your factory function has a different name

from app.models import Product, InventoryRecord  # Adjust this to match your models file path

def seed_inventory_data(days_to_seed=30):
    """
    Seeds historical daily inventory counts for all existing products.
    """
    # 1. Initialize the app instance using your factory setup
    app = create_app()
    
    # 2. Push the application context manually so SQLAlchemy can access the database
    with app.app_context():
        print("Starting inventory database seeding...")
        
        # Fetch all existing products to link records to
        products = Product.query.all()
        if not products:
            print("Error: No products found in the database. Seed products first!")
            return

        print(f"Found {len(products)} products to seed.")

        # Generate the range of dates
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days_to_seed)
        
        records_to_add = []
        current_date = start_date

        # Loop through days and products
        while current_date <= end_date:
            for product in products:
                random_quantity = random.randint(10, 150)
                
                record = InventoryRecord(
                    product_id=product.id,
                    date=current_date,
                    quantity=random_quantity
                )
                records_to_add.append(record)
                
            current_date += timedelta(days=1)

        # Bulk save to database safely
        try:
            db.session.bulk_save_objects(records_to_add)
            db.session.commit()
            print(f"Successfully seeded {len(records_to_add)} inventory records!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during seeding: {e}")

if __name__ == "__main__":
    seed_inventory_data(days_to_seed=30)
