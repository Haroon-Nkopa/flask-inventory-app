import sys
import os
from datetime import datetime, timezone
from flask import Flask
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Automatically patch the python path to prevent ModuleNotFoundError issues
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Remove db from here to prevent instance splitting!
from models import (
    Shop, User, Product, 
    LiveInventory, DailyInventorySnapshot, PhysicalInventoryCount
)


# Flat model placeholder mapping your legacy tracking database layout

def run_migration(app):
    with app.app_context():
        # 1. Extract the bound database extension
        db = app.extensions['sqlalchemy']
        
        # 2. Local fallback definition for legacy data records
        class OldInventoryRecord(db.Model):
            __tablename__ = 'inventory_record'
            id = db.Column(db.Integer, primary_key=True)
            product_id = db.Column(db.Integer, nullable=False)
            date = db.Column(db.Date, nullable=False)
            quantity = db.Column(db.Integer, default=0)

        # FIXED: Tell Flask-SQLAlchemy to physically build any newly declared models 
        # (like live_inventory, daily_inventory_snapshot, etc.) if they don't exist yet.
        print("🛠️ Verifying database schema and building missing tables...")
        db.create_all()

        print("🚀 Starting optimized enterprise inventory migration engine...")
        start_time = datetime.now(timezone.utc)

        # ================================================================
        # OPTIMIZATION: SINGLE BULK USER CACHING FOR SYSTEM SEED SIGNATURE
        # ================================================================
        system_fallback_user = db.session.query(User).first()
        if not system_fallback_user:
            print("❌ CRITICAL: Migration aborted. System requires at least one active User.")
            sys.exit(1)
            
        print(f"ℹ️ System fallback profile cached: '{system_fallback_user.username}' (ID: {system_fallback_user.id})")

        # ================================================================
        # STEP 1: IMPROVED DUPLICATE-PRODUCT MERGING LOGIC (PREVENTS CRASHES)
        # ================================================================
        print("🔍 Scanning for cross-shop duplicate product name collisions...")
        
        # Avoiding unnecessary database queries inside loops using bulk lookups
        duplicates_query = db.session.query(
            Product.shop_id, 
            func.lower(Product.name).label('clean_name')
        ).group_by(Product.shop_id, func.lower(Product.name)).having(func.count(Product.id) > 1).all()

        if duplicates_query:
            print(f"⚠️ Detected {len(duplicates_query)} duplicate product lines. Merging matrices...")
            
            for dup in duplicates_query:
                # Load all colliding variants to resolve structural master data
                conflicting_products = db.session.query(Product).filter(
                    Product.shop_id == dup.shop_id,
                    func.lower(Product.name) == dup.clean_name
                ).order_by(Product.id.asc()).all()
                
                master_product = conflicting_products[0]
                duplicate_products = conflicting_products[1:]
                
                print(f"  🔹 Preserving Master Item: '{master_product.name}' (ID: {master_product.id})")
                
                for dup_prod in duplicate_products:
                    print(f"  ❌ Purging duplicate Product ID: {dup_prod.id} -> Re-routing histories")
                    
                    # Mass-merge and redirect legacy log tracking targets instantly
                    db.session.query(OldInventoryRecord).filter_by(product_id=dup_prod.id).update(
                        {"product_id": master_product.id}, 
                        synchronize_session=False
                    )
                    db.session.delete(dup_prod)
            
            db.session.flush()
            print("✅ Deduplication engine completed execution successfully.")
        else:
            print("✅ No duplicate product names found per shop context. Proceeding...")

        # ================================================================
        # OPTIMIZATION: BATCH CACHING SHOP USERS (ELIMINATES INNER-LOOP QUERIES)
        # ================================================================
        print("📋 Preloading and mapping context-aware team signatures to memory dictionaries...")
        shop_user_map = {}
        
        # Load all shops pre-loaded with their users to avoid N+1 query loops
        all_shops = db.session.query(Shop).options(joinedload(Shop.users)).all()
        for shop in all_shops:
            if shop.users:
                shop_user_map[shop.id] = shop.users[0].id
            else:
                shop_user_map[shop.id] = system_fallback_user.id
                print(f"  ⚠️ Shop '{shop.name}' (ID: {shop.id}) has no assigned users. Falling back to default system user.")

        # ================================================================
        # OPTIMIZATION: ELIMINATING THE N+1 QUERY PROBLEM VIA JOINEDLOAD BULK LOOKUPS
        # ================================================================
        print("📦 Preloading unified structural data models...")
        
        # Preloading products with all their downstream relationships cached in memory tables
        products_cache = {
            p.id: p for p in db.session.query(Product).options(
                joinedload(Product.live_inventory),
                joinedload(Product.daily_snapshots),
                joinedload(Product.physical_counts)
            ).all()
        }

        try:
            # Batch lookups for old inventory logs
            old_records = db.session.query(OldInventoryRecord).order_by(OldInventoryRecord.date.asc()).all()
            print(f"📈 Found {len(old_records)} old flat row history logs to migrate.")
        except Exception as e:
            print(f"❌ Failed to extract data from 'inventory_record' table. Table might already be dropped: {str(e)}")
            sys.exit(1)

        # In-memory dictionary tracking tracking values
        latest_product_quantities = {}
        migrated_snapshots_count = 0
        migrated_audits_count = 0

        # ================================================================
        # STEP 2: TRANSACTIONAL LEAN LOG PARSING
        # ================================================================
        for record in old_records:
            # OPTIMIZATION: Replacing deprecated Product.query.get() with in-memory map lookup
            product = products_cache.get(record.product_id)
            if not product:
                continue # Skip dead/orphaned rows cleanly

            # Update latest stock pointer positions sequentially
            latest_product_quantities[record.product_id] = record.quantity

            # --- Map to Daily Inventory Snapshots (Using preloaded memory cache check) ---
            snapshot_exists = any(s.date == record.date for s in product.daily_snapshots)
            if not snapshot_exists:
                snapshot = DailyInventorySnapshot(
                    product_id=record.product_id,
                    date=record.date,
                    closing_quantity=record.quantity
                )
                db.session.add(snapshot)
                product.daily_snapshots.append(snapshot) # Update cache reference state
                migrated_snapshots_count += 1

            # --- Map to Physical Inventory Count (Context-Aware Signature assignment) ---
            audit_exists = any(a.date == record.date for a in product.physical_counts)
            if not audit_exists:
                # Combine dates cleanly matching UTC boundaries
                combined_timestamp = datetime.combine(record.date, datetime.min.time(), tzinfo=timezone.utc)
                assigned_user_id = shop_user_map.get(product.shop_id, system_fallback_user.id)

                audit = PhysicalInventoryCount(
                    product_id=record.product_id,
                    date=record.date,
                    timestamp=combined_timestamp,
                    counted_quantity=record.quantity,
                    notes="Migrated transactional trace line entry from old architecture ledger books.",
                    user_id=assigned_user_id
                )
                db.session.add(audit)
                product.physical_counts.append(audit) # Update cache reference state
                migrated_audits_count += 1

        # ================================================================
        # STEP 3: SEED REFRESHED REAL-TIME STATE MONITOR TABLES
        # ================================================================
        print("⚡ Synchronising real-time Live Inventory monitors...")
        live_seeded_count = 0

        # Safe parsing over bulk lookup cache keys
        for p_id, product in products_cache.items():
            if not product.live_inventory:
                final_qty = latest_product_quantities.get(p_id, 0)
                
                # Using timezone-aware timestamps (datetime.now(timezone.utc))
                live_rec = LiveInventory(
                    product_id=p_id,
                    quantity=final_qty,
                    last_updated=datetime.now(timezone.utc)
                )
                db.session.add(live_rec)
                live_seeded_count += 1

        # ================================================================
        # STEP 4: STRICT ACID TRANSACTIONAL ROLLBACK MONITORING
        # ================================================================
        try:
            print("💾 Saving checkpoints and flushing data transactions...")
            db.session.commit()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            print("🎉 MIGRATION ENGINE COMPLETED SUCCESSFUL RUN!")
            print(f"⏱️ Total processing duration: {duration:.2f} seconds")
            print(f"🔹 Daily Snapshots Generated: {migrated_snapshots_count}")
            print(f"🔹 Physical Verification Audits Generated: {migrated_audits_count}")
            print(f"🔹 Live Inventory Monitors Seeded: {live_seeded_count}")
            
        except Exception as e:
            # Keeping the migration transactional with proper rollback handling
            db.session.rollback()
            print(f"❌ CRITICAL RUNTIME EXCEPTION CAUGHT: Database rolled back safety matrix. Error details: {str(e)}")


if __name__ == '__main__':
    # 1. Safely add the workspace root to python paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # 2. Try loading create_app from any possible variation dynamically
    create_app = None
    
    try:
        from app import create_app
    except ImportError:
        try:
            # If inside app/ folder, create_app might be inside __init__.py directly
            import app
            if hasattr(app, 'create_app'):
                create_app = app.create_app
        except ImportError:
            pass

    if not create_app:
        try:
            from run import create_app
        except ImportError:
            try:
                from main import create_app
            except ImportError:
                print("❌ CRITICAL PATH ERROR: Could not locate 'create_app' entry point.")
                print("Please make sure your main factory file is accessible from the python environment.")
                sys.exit(1)
        
    flask_app = create_app()
    run_migration(flask_app)


