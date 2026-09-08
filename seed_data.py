import random
from datetime import datetime, timezone, timedelta
from app import create_app, db
from app.models import Shop, User, Product, Sale, SaleItem

app = create_app()

def generate_sales_until_today():
    with app.app_context():
        print("📊 Analyzing existing sales history to model current retail flow...")
        
        # 1. Fetch reference parameters
        existing_sales = Sale.query.all()
        all_products = Product.query.all()
        all_users = User.query.all()
        all_shops = Shop.query.all()

        if not all_products or not all_shops:
            print("❌ Error: Missing core master data (Shops or Products). Seeding aborted.")
            return
            
        if not all_users:
            print("⚠️ Warning: No users found. Sales will be logged without an operational user footprint.")
            user_id = None
        else:
            user_id = all_users[0].id # Assign to the first available reference user profile

        # 2. Determine historical start window boundary
        if existing_sales:
            oldest_sale_time = min(s.timestamp for s in existing_sales)
            # If the timestamp is naive, give it UTC zone context
            if oldest_sale_time.tzinfo is None:
                oldest_sale_time = oldest_sale_time.replace(tzinfo=timezone.utc)
            print(f"📈 Found {len(existing_sales)} baseline transaction templates. Starting timeline extrapolation...")
        else:
            oldest_sale_time = datetime.now(timezone.utc) - timedelta(days=30)
            print("ℹ️ No base transaction matrices found. Initiating a default 30-day chronological model layout...")

        target_end_date = datetime.now(timezone.utc)
        current_date_pointer = oldest_sale_time
        
        days_to_generate = (target_end_date - oldest_sale_time).days
        if days_to_generate <= 0:
            days_to_generate = 7
            
        print(f"📅 Simulating transaction streams over a {days_to_generate}-day timeline up to today ({target_end_date.strftime('%Y-%m-%d')})...")

        appended_sales_count = 0
        appended_items_count = 0

        # 3. Time-progression generation loop
        while current_date_pointer <= target_end_date:
            print(f"⏳ Processing transaction logs for date: {current_date_pointer.strftime('%Y-%m-%d')}...")
            
            for shop in all_shops:
                daily_sales_volume = random.randint(4, 12)
                
                for _ in range(daily_sales_volume):
                    random_hour = random.randint(8, 18)
                    random_minute = random.randint(0, 59)
                    
                    sale_timestamp = datetime(
                        current_date_pointer.year,
                        current_date_pointer.month,
                        current_date_pointer.day,
                        random_hour,
                        random_minute,
                        tzinfo=timezone.utc
                    )
                    
                    if sale_timestamp > target_end_date:
                        continue

                    new_sale = Sale(
                        timestamp=sale_timestamp,
                        total_amount=0.0,
                        shop_id=shop.id,
                        user_id=user_id
                    )
                    db.session.add(new_sale)
                    
                    # We link items through the relationship property list instead of running manual flushes!
                    basket_size = random.randint(1, 4)
                    selected_products = random.sample(all_products, k=min(basket_size, len(all_products)))
                    
                    running_cart_total = 0.0
                    
                    for product in selected_products:
                        item_qty = random.randint(1, 5)
                        line_total = item_qty * product.price
                        running_cart_total += line_total
                        
                        new_item = SaleItem(
                            product_id=product.id,
                            quantity=item_qty,
                            unit_price=product.price,
                            total_price=line_total
                        )
                        # Appending to the relationship lets SQLAlchemy batch-insert everything seamlessly
                        new_sale.items.append(new_item)
                        appended_items_count += 1
                    
                    new_sale.total_amount = running_cart_total
                    appended_sales_count += 1
            
            # 🚀 Bulk-commit at the end of each day to drastically reduce cloud network latency
            db.session.commit()
            current_date_pointer += timedelta(days=1)

        print(f"🎉 Success! Generated and appended {appended_sales_count} new sales tickets.")
        print(f"🛒 Injected {appended_items_count} itemized item breakdowns into Neon up to today's date context.")

if __name__ == "__main__":
    generate_sales_until_today()
