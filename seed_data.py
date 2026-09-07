import random
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

# Application context imports matching factory constraints
from entryPoint import app
from app import db
from app.models import (
    user_shop, Shop, User, Product, LiveInventory, 
    DailyInventorySnapshot, PhysicalInventoryCount, 
    Sale, SaleItem, InventoryAuditMerge
)

# 🌐 Explicit Secure Target Connection Definition Override
NEON_TARGET_URI = "postgresql://neondb_owner:npg_FMUOsD09dbEV@ep-royal-mountain-av9pacew-pooler.c-11.us-east-1.aws.neon.tech/neondb?sslmode=require"

def clean_database():
    """Truncates legacy table records sequentially to safeguard relational constraints."""
    print("🧹 Wiping legacy transactional ledger fragments...")
    
    # 1. Clear the association table first to break the foreign key dependencies
    db.session.execute(db.delete(user_shop))
    
    # 2. Proceed with transactional tables in dependent relational order
    db.session.query(InventoryAuditMerge).delete()
    db.session.query(SaleItem).delete()
    db.session.query(Sale).delete()
    db.session.query(PhysicalInventoryCount).delete()
    db.session.query(DailyInventorySnapshot).delete()
    db.session.query(LiveInventory).delete()
    db.session.query(Product).delete()
    db.session.query(Shop).delete()
    db.session.query(User).delete()
    db.session.commit()
    print("✅ Clear down operation complete.")

def seed_data():
    clean_database()
    
    print("\n🏪 Phase 1: Structuring Shop and System User Footprints...")
    retail_shop = Shop(name="Apex General Store", paid=True)
    db.session.add(retail_shop)
    db.session.commit()
    
    manager = User(
        username="manager_alex", 
        password=generate_password_hash("AdminSecure2026!"), 
        role="manager"
    )
    cashier = User(
        username="cashier_sam", 
        password=generate_password_hash("StaffPass2026"), 
        role="user"
    )
    
    db.session.add_all([manager, cashier])
    db.session.commit()

    # Defensive relationship mapping checks to prevent user_shop link-table constraints failure
    if manager not in retail_shop.users:
        retail_shop.users.append(manager)
    if cashier not in retail_shop.users:
        retail_shop.users.append(cashier)
    db.session.commit()

    print("📦 Phase 2: Generating Core Inventory Master Data...")
    sample_catalog = [
        {"name": "Whole Milk 1L", "category": "Dairy", "price": 18.50, "batch_size": 12, "batch_price": 200.00, "lower_bound": 15, "size": "1L"},
        {"name": "Cheddar Cheese 500g", "category": "Dairy", "price": 55.00, "batch_size": 6, "batch_price": 280.00, "lower_bound": 8, "size": "500g"},
        {"name": "White Bread Loaf", "category": "Bakery", "price": 15.00, "batch_size": 10, "batch_price": 120.00, "lower_bound": 20, "size": "700g"},
        {"name": "Chocolate Chip Cookies", "category": "Bakery", "price": 22.00, "batch_size": 24, "batch_price": 400.00, "lower_bound": 12, "size": "250g"},
        {"name": "Instant Coffee 200g", "category": "Pantry", "price": 85.00, "batch_size": 6, "batch_price": 450.00, "lower_bound": 5, "size": "200g"},
        {"name": "Ceylon Tea Bags 100s", "category": "Pantry", "price": 34.50, "batch_size": 12, "batch_price": 360.00, "lower_bound": 10, "size": "200g"},
        {"name": "Basmati Rice 2kg", "category": "Pantry", "price": 48.00, "batch_size": 8, "batch_price": 340.00, "lower_bound": 10, "size": "2kg"},
        {"name": "Sunflower Oil 2L", "category": "Pantry", "price": 69.90, "batch_size": 4, "batch_price": 250.00, "lower_bound": 6, "size": "2L"},
        {"name": "Sparkling Water 500ml", "category": "Beverages", "price": 12.00, "batch_size": 24, "batch_price": 220.00, "lower_bound": 30, "size": "500ml"},
        {"name": "Cola Soda Can 330ml", "category": "Beverages", "price": 14.50, "batch_size": 24, "batch_price": 280.00, "lower_bound": 48, "size": "330ml"},
    ]

    products_list = []
    now_utc = datetime.now(timezone.utc)

    for index, item in enumerate(sample_catalog, start=101):
        product = Product(
            name=item["name"],
            category=item["category"],
            price=item["price"],
            batch_size=item["batch_size"],
            batch_price=item["batch_price"],
            lower_bound=item["lower_bound"],
            size=item["size"],
            batch_number=f"BCH-2026-{index}",
            shop_id=retail_shop.id
        )
        db.session.add(product)
        products_list.append(product)
    db.session.commit()

    print("📊 Phase 3: Initializing Live State Tracks & History Trails...")
    for p in products_list:
        initial_qty = random.randint(10, 100)
        live_state = LiveInventory(
            product=p,
            quantity=initial_qty,
            last_updated=now_utc
        )
        db.session.add(live_state)

        for day_offset in range(5, 0, -1):
            target_date = (now_utc - timedelta(days=day_offset)).date()
            simulated_closing = max(0, initial_qty + random.randint(-15, 15))
            snapshot = DailyInventorySnapshot(
                product=p,
                date=target_date,
                closing_quantity=simulated_closing
            )
            db.session.add(snapshot)

        audit_date = now_utc - timedelta(days=2)
        physical_count = PhysicalInventoryCount(
            product=p,
            date=audit_date.date(),
            timestamp=audit_date,
            counted_quantity=initial_qty + 2,
            notes="Bi-weekly compliance checkpoint validation.",
            user_id=manager.id
        )
        db.session.add(physical_count)

        if random.random() > 0.7:
            audit_merge = InventoryAuditMerge(
                product=p,
                user_id=manager.id,
                live_record=initial_qty + 5,
                audited_record=initial_qty,
                merge_reason=random.choice(["Damaged goods on delivery", "Expired shelf inventory item", "Stock intake typo correction"]),
                date=(now_utc - timedelta(days=1)).date(),
                timestamp=now_utc - timedelta(days=1)
            )
            db.session.add(audit_merge)
    db.session.commit()

    print("💸 Phase 4: Mocking Real Transaction Ledger Metrics...")
    for sale_idx in range(15):
        sale_time = now_utc - timedelta(hours=random.randint(1, 48))
        selected_products = random.sample(products_list, k=random.randint(1, 3))
        
        sale_items = []
        running_total = 0.0
        
        for p in selected_products:
            purchased_qty = random.randint(1, 3)
            item_total = purchased_qty * p.price
            running_total += item_total
            
            sale_item = SaleItem(
                product_id=p.id,
                quantity=purchased_qty,
                unit_price=p.price,
                total_price=item_total
            )
            sale_items.append(sale_item)
            
            if p.live_inventory:
                p.live_inventory.quantity = max(0, p.live_inventory.quantity - purchased_qty)

        new_sale = Sale(
            timestamp=sale_time,
            total_amount=running_total,
            shop_id=retail_shop.id,
            user_id=cashier.id,
            items=sale_items
        )
        db.session.add(new_sale)
    
    db.session.commit()
    print("🎉 Neon branch database successfully populated with mock store records!")

if __name__ == "__main__":
    print("🔗 Forcing SQLAlchemy engine pointer redirection to Neon branch...")
    app.config["SQLALCHEMY_DATABASE_URI"] = NEON_TARGET_URI
    
    with app.app_context():
        print("🧱 Verifying structural tables matching target branch schema definitions...")
        db.create_all()
        seed_data()
