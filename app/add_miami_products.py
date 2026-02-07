from app import create_app, db
from app.models import Product, Shop
import random

# Initialize Flask app context
app = create_app()
app.app_context().push()

SHOP_ID = 3  # Miami / City shop ID

shop = Shop.query.get(SHOP_ID)
if not shop:
    raise Exception("Shop with ID 3 not found!")

liquor_products = [
    ("Castle Lager", "Beer", "330ml"),
    ("Black Label", "Beer", "330ml"),
    ("Hansa Pilsener", "Beer", "330ml"),
    ("Flying Fish", "Beer", "330ml"),
    ("Savanna Dry", "Cider", "330ml"),
    ("Savanna Light", "Cider", "330ml"),
    ("Hunters Dry", "Cider", "330ml"),
    ("Hunters Gold", "Cider", "330ml"),
    ("Smirnoff Vodka", "Spirits", "750ml"),
    ("Absolut Vodka", "Spirits", "750ml"),
    ("Ciroc Vodka", "Spirits", "750ml"),
    ("Russian Bear Vodka", "Spirits", "750ml"),
    ("Gordon’s Gin", "Spirits", "750ml"),
    ("Tanqueray Gin", "Spirits", "750ml"),
    ("Bombay Sapphire Gin", "Spirits", "750ml"),
    ("Johnny Walker Red Label", "Whisky", "750ml"),
    ("Johnny Walker Black Label", "Whisky", "750ml"),
    ("Jameson Irish Whiskey", "Whisky", "750ml"),
    ("Chivas Regal 12Y", "Whisky", "750ml"),
    ("Jack Daniel’s", "Whisky", "750ml"),
    ("Grant’s Whisky", "Whisky", "750ml"),
    ("Famous Grouse", "Whisky", "750ml"),
    ("Bells Whisky", "Whisky", "750ml"),
    ("Amarula Cream", "Liqueur", "750ml"),
    ("Jägermeister", "Liqueur", "750ml"),
    ("Southern Comfort", "Liqueur", "750ml"),
    ("Bacardi Rum", "Rum", "750ml"),
    ("Captain Morgan", "Rum", "750ml"),
    ("Havana Club Rum", "Rum", "750ml"),
    ("KWV Brandy 3Y", "Brandy", "750ml"),
    ("KWV Brandy 5Y", "Brandy", "750ml"),
    ("Richelieu Brandy", "Brandy", "750ml"),
    ("Van Ryn’s Brandy", "Brandy", "750ml"),
    ("Nederburg Red Wine", "Wine", "750ml"),
    ("Nederburg White Wine", "Wine", "750ml"),
    ("Robertson Winery Red", "Wine", "750ml"),
    ("4th Street Sweet Red", "Wine", "750ml"),
    ("4th Street Sweet White", "Wine", "750ml"),
    ("JC Le Roux Brut", "Sparkling Wine", "750ml"),
    ("JC Le Roux Demi-Sec", "Sparkling Wine", "750ml"),
    ("Moët & Chandon", "Champagne", "750ml"),
    ("Brutal Fruit Ruby Apple", "Cider", "275ml"),
    ("Brutal Fruit Litchi", "Cider", "275ml"),
    ("Brutal Fruit Spritzer", "Cider", "275ml"),
    ("Heineken", "Beer", "330ml"),
    ("Corona Extra", "Beer", "330ml"),
    ("Stella Artois", "Beer", "330ml"),
    ("Budweiser", "Beer", "330ml"),
    ("Red Bull Vodka Ready Drink", "Ready-to-Drink", "275ml"),
    ("Smirnoff Spin", "Ready-to-Drink", "275ml"),
]

added = 0

for name, category, size in liquor_products:
    existing = Product.query.filter_by(name=name, shop_id=SHOP_ID).first()
    if existing:
        print(f"Skipping existing product: {name}")
        continue

    price = round(random.uniform(18, 220), 2)
    batch_size = random.choice([6, 12, 24])
    batch_price = round(price * batch_size * 0.85, 2)

    product = Product(
        name=name,
        category=category,
        size=size,
        price=price,
        batch_size=batch_size,
        batch_price=batch_price,
        lower_bound=random.randint(3, 15),
        batch_number=f"BATCH-{random.randint(1000, 9999)}",
        shop_id=SHOP_ID
    )

    db.session.add(product)
    added += 1

db.session.commit()

print(f"✅ Added {added} liquor products to shop '{shop.name}' (ID {SHOP_ID})")
