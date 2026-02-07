from app import create_app, db
from app.models import Product, Shop
import random

app = create_app()
app.app_context().push()

SHOP_ID = 1  # giant

shop = Shop.query.get(SHOP_ID)
if not shop:
    raise Exception("Giant shop not found!")

products_list = [
    ("Fanta Orange", "Soft Drinks", "2L"),
    ("Sprite", "Soft Drinks", "2L"),
    ("Pepsi", "Soft Drinks", "2L"),
    ("Mountain Dew", "Soft Drinks", "2L"),
    ("Creme Soda", "Soft Drinks", "2L"),
    ("Sparletta Iron Brew", "Soft Drinks", "2L"),
    ("Sparletta Twist", "Soft Drinks", "2L"),
    ("Cappy Juice", "Juice", "1L"),
    ("Liqui-Fruit Orange", "Juice", "1L"),
    ("Liqui-Fruit Mango", "Juice", "1L"),
    ("Oros", "Juice Concentrate", "2L"),
    ("Energade", "Energy Drink", "500ml"),
    ("Powerade", "Energy Drink", "500ml"),
    ("Red Bull", "Energy Drink", "250ml"),
    ("Monster Energy", "Energy Drink", "500ml"),
    ("Mayonnaise", "Groceries", "750g"),
    ("Tomato Sauce", "Groceries", "700ml"),
    ("All Gold Tomato Sauce", "Groceries", "700ml"),
    ("White Sugar", "Groceries", "2.5kg"),
    ("Sunlight Dishwashing Liquid", "Household", "750ml"),
    ("Handy Andy", "Household", "750ml"),
    ("Jik Bleach", "Household", "750ml"),
    ("Omo Washing Powder", "Household", "2kg"),
    ("Ace Maize Meal", "Staples", "2.5kg"),
    ("Iwisa Maize Meal", "Staples", "2.5kg"),
    ("Spekko Rice", "Staples", "2kg"),
    ("Tastic Rice", "Staples", "2kg"),
    ("Albany White Bread", "Bakery", "700g"),
    ("Albany Brown Bread", "Bakery", "700g"),
    ("Blue Ribbon White Bread", "Bakery", "700g"),
    ("Simba Chips Cheese & Onion", "Snacks", "120g"),
    ("Simba Chips BBQ", "Snacks", "120g"),
    ("Doritos Nacho Cheese", "Snacks", "120g"),
    ("NikNaks", "Snacks", "135g"),
    ("Cadbury Dairy Milk", "Confectionery", "80g"),
    ("Lunch Bar", "Confectionery", "48g"),
    ("Tex Chocolate Bar", "Confectionery", "40g"),
    ("PS Chocolate", "Confectionery", "40g"),
    ("Ricoffy Coffee", "Hot Beverages", "250g"),
    ("Nescafé Classic", "Hot Beverages", "200g"),
    ("Five Roses Tea", "Hot Beverages", "100 Bags"),
    ("Jungle Oats", "Breakfast", "1kg"),
    ("Kellogg’s Cornflakes", "Breakfast", "500g"),
    ("Weet-Bix", "Breakfast", "450g"),
    ("Koo Baked Beans", "Canned Food", "410g"),
    ("Koo Chakalaka", "Canned Food", "410g"),
    ("Pilchards in Tomato Sauce", "Canned Food", "400g"),
    ("Bull Brand Corned Meat", "Canned Food", "340g"),
]

added = 0
skipped = 0

for name, category, size in products_list:
    existing = Product.query.filter_by(name=name, shop_id=SHOP_ID).first()
    if existing:
        skipped += 1
        print(f"Skipping existing product: {name}")
        continue

    price = round(random.uniform(8, 95), 2)
    batch_size = random.choice([6, 12, 24])
    batch_price = round(price * batch_size * 0.88, 2)

    product = Product(
        name=name,
        category=category,
        size=size,
        price=price,
        batch_size=batch_size,
        batch_price=batch_price,
        lower_bound=random.randint(3, 12),
        batch_number=f"GIANT-{random.randint(1000,9999)}",
        shop_id=SHOP_ID
    )

    db.session.add(product)
    added += 1

db.session.commit()

print(f"✅ Added {added} products to Giant shop")
print(f"⏭ Skipped {skipped} duplicates")
