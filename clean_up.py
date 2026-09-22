from datetime import datetime, timezone
from app import create_app, db
from app.models import (
    Product, 
    LiveInventory, 
    PhysicalInventoryCount, 
    InventoryAuditMerge, 
    Shop
)

# 1. Initialize the Flask application lifecycle context
app = create_app()

with app.app_context():
    TARGET_SHOP_NAME = "Majara Ext6"
    print(f"📦 Starting physical count merge workflow for shop: '{TARGET_SHOP_NAME}'...")

    # 2. Fetch the target shop database entry to locate product isolation rules
    shop = Shop.query.filter_by(name=TARGET_SHOP_NAME).first()
    if not shop:
        print(f"❌ Error: Shop named '{TARGET_SHOP_NAME}' could not be located in database records.")
        exit(1)

    # 3. Fetch all products belonging to this specific shop
    # (Adjust this filter if your Product model links to shop using a different attribute name, like shop_id)
    shop_products = Product.query.filter_by(shop_id=shop.id).all()
    product_ids = [p.id for p in shop_products]

    if not product_ids:
        print("ℹ️ No active products found registered to this shop location.")
        exit(0)

    # 4. Fetch the latest physical count entry for each product today
    today_date = datetime.now(timezone.utc).date()
    
    # Query today's physical stock entries matching this shop's product matrix scope
    physical_counts = PhysicalInventoryCount.query.filter(
        PhysicalInventoryCount.product_id.in_(product_ids),
        PhysicalInventoryCount.date == today_date
    ).order_by(PhysicalInventoryCount.timestamp.desc()).all()

    if not physical_counts:
        print(f"✅ Sync complete: No new physical count entries logged today ({today_date}) for this shop location.")
        exit(0)

    # Keep track of products processed to only apply the newest audit log if duplicates exist
    processed_product_ids = set()
    updates_counter = 0

    try:
        for count_record in physical_counts:
            # Skip if we already captured a newer submission stamp in this batch run
            if count_record.product_id in processed_product_ids:
                continue
            
            p_id = count_record.product_id
            physical_qty = count_record.counted_quantity
            operator_user_id = count_record.user_id

            # 5. Fetch or initialize the corresponding LiveInventory row entry
            live_stock = LiveInventory.query.filter_by(product_id=p_id).first()
            
            # Safe initialization fallback if table entry doesn't exist yet
            if not live_stock:
                live_stock = LiveInventory(product_id=p_id, quantity=0)
                db.session.add(live_stock)
                db.session.flush() # Yields operational ID assignments early

            old_live_qty = live_stock.quantity

            # Only proceed and record log tracking metrics if numbers don't match
            if old_live_qty != physical_qty:
                # 6. Instantiate the historical balance override audit trail ledger
                audit_merge_trail = InventoryAuditMerge(
                    product_id=p_id,
                    user_id=operator_user_id,
                    live_record=old_live_qty,
                    audited_record=physical_qty,
                    merge_reason=f"Daily stock take override synchronization logic run for {TARGET_SHOP_NAME}.",
                    date=today_date
                )
                db.session.add(audit_merge_trail)

                # 7. Apply the physical inventory override straight to the live state tracker
                live_stock.quantity = physical_qty
                updates_counter += 1
                print(f" 🔄 Updated Product ID {p_id}: Live Stock balance adjusted ({old_live_qty} ➡️ {physical_qty})")

            processed_product_ids.add(p_id)

        # 8. Commit the session block safely
        if updates_counter > 0:
            db.session.commit()
            print(f"🚀 Success! Successfully applied {updates_counter} physical count overrides directly to Live Inventory columns.")
        else:
            print("✅ All running live counts perfectly match today's audited quantities. No changes required.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Transaction failed. Database session rolled back safely. System error: {e}")
