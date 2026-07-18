import random
from app import create_app, db
from app.models import Product, Shop

# Names of realistic retail products to mix and match
PRODUCT_NAMES = [
    "Coca-Cola", "Sprite", "Fanta Orange", "Still Water", "Sparkling Water",
    "Fresh Milk", "Cheddar Cheese", "Salted Butter", "Plain Yogurt", "Eggs 12 Pack",
    "White Bread", "Brown Bread", "Chocolate Chip Cookies", "Potato Chips", "Peanuts",
    "Basmati Rice", "Spaghetti", "Sunflower Oil", "All Purpose Flour", "White Sugar",
    "Instant Coffee", "Rooibos Tea", "Long Life Milk", "Tomato Sauce", "Mayonnaise",
    "Dishwashing Liquid", "Laundry Detergent", "Toilet Paper 9 Pack", "Hand Soap", "Toothpaste",
    "Shampoo", "Shower Gel", "Bleach", "Garbage Bags", "Kitchen Towels",
    "Apple Juice", "Orange Juice", "Oats Breakfast Cereal", "Corn Flakes", "Muesli",
    "Canned Tomatoes", "Canned Beans", "Tuna in Oil", "Sweet Corn", "Spaghetti Sauce"
]

CATEGORIES = ["Beverages", "Dairy", "Bakery", "Snacks", "Grains & Cooking", "Household", "Personal Care", "Breakfast"]
SIZES = ["330ml", "500ml", "1L", "2L", "500g", "1kg", "2kg", "100g", "250g", "Standard"]

def seed_retail_products():
    app = create_app()
    with app.app_context():
        # 1. Fetch an existing shop to assign the products to
        shop = Shop.query.filter_by(name="new").first()
        if not shop:
            print("Error: No Shop found in the database! Please create a Shop first.")
            return

        print(f"Seeding 50 products for shop: {shop.name} (ID: {shop.id})...")
        
        count = 0
        attempts = 0
        # Loop until we successfully add 50 unique products
        while count < 50 and attempts < 200:
            attempts += 1
            
            # Pick attributes randomly
            base_name = random.choice(PRODUCT_NAMES)
            size = random.choice(SIZES)
            name = f"{base_name} {size}"  # Ensures variety to prevent name clashes
            
            # Check if this exact product name already exists for this shop
            exists = Product.query.filter_by(name=name, shop_id=shop.id).first()
            if exists:
                continue

            # Generate realistic financial values
            price = round(random.uniform(15.00, 150.00), 2)  # Retail price
            batch_size = random.choice([1, 6, 12, 24])       # Packaging count
            # Wholesale batch price slightly lower than retail total
            batch_price = round((price * batch_size) * random.uniform(0.75, 0.85), 2)
            
            product = Product(
                name=name,
                category=random.choice(CATEGORIES),
                price=price,
                batch_size=batch_size,
                batch_price=batch_price,
                lower_bound=random.randint(5, 20),
                size=size,
                batch_number=f"B{random.randint(1000, 9999)}",
                shop_id=shop.id
            )
            
            db.session.add(product)
            count += 1

        try:
            db.session.commit()
            print(f"Success! Added {count} new retail products to the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during commit: {e}")

if __name__ == "__main__":
    seed_retail_products()
