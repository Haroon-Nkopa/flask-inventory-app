from datetime import datetime, timezone
from sqlalchemy import func
from app import db
from app.models import Product, Sale, SaleItem, User, PhysicalInventoryCount, LiveInventory, InventoryAuditMerge

def get_product_discrepancies_timeline(shop_id):
    """
    Identifies stock count variances and builds chronological timelines.
    Returns: Tuple (counts_metadata_dict, timeline_phrases_dict)
    """
    counts_metadata = {}
    timeline_phrases = {}

    products = db.session.query(Product).filter(Product.shop_id == shop_id).all()
    
    for p in products:
        last_audit = db.session.query(PhysicalInventoryCount)\
            .filter(PhysicalInventoryCount.product_id == p.id)\
            .order_by(PhysicalInventoryCount.timestamp.desc())\
            .first()
            
        if not last_audit:
            continue
            
        live_qty = p.live_inventory.quantity if p.live_inventory else 0
        audited_qty = last_audit.counted_quantity
        
        if live_qty == audited_qty:
            continue

        # FIXED: Add selling_price and last_audit_date here so the values aren't empty/0.0
        counts_metadata[p.id] = {
            "product_name": p.name,
            "live_quantity": live_qty,
            "audited_quantity": audited_qty,
            "selling_price": p.price,                              # Pulls from Product model
            "last_audit_date": last_audit.date.strftime('%Y-%m-%d') # Pulls from Physical count model
        }

        # Fetch sales since physical verification log
        sales_since_audit = db.session.query(
                SaleItem.quantity,
                Sale.timestamp,
                User.username
            )\
            .join(Sale, SaleItem.sale_id == Sale.id)\
            .outerjoin(User, Sale.user_id == User.id)\
            .filter(SaleItem.product_id == p.id, Sale.timestamp >= last_audit.timestamp)\
            .order_by(Sale.timestamp.asc())\
            .all()

        # If no sales happened but variances exist, initialize empty array
        if not sales_since_audit:
            timeline_phrases[p.name] = [f"No logged sales recorded since physical count on {last_audit.timestamp.strftime('%Y-%m-%d %H:%M')}."]
            continue

        intervals = []
        current_user_name = sales_since_audit[0].username or "System/Unknown"
        interval_start_time = last_audit.timestamp
        current_qty_sum = 0
        
        for item in sales_since_audit:
            item_user = item.username or "System/Unknown"
            
            if item_user != current_user_name:
                intervals.append({
                    "user": current_user_name,
                    "num_sold": current_qty_sum,
                    "start": interval_start_time.strftime("%Y-%m-%d %H:%M"),
                    "end": item.timestamp.strftime("%Y-%m-%d %H:%M")
                })
                current_user_name = item_user
                interval_start_time = item.timestamp
                current_qty_sum = item.quantity
            else:
                current_qty_sum += item.quantity

        intervals.append({
            "user": current_user_name,
            "num_sold": current_qty_sum,
            "start": interval_start_time.strftime("%Y-%m-%d %H:%M"),
            "end": sales_since_audit[-1].timestamp.strftime("%Y-%m-%d %H:%M")
        })

        formatted_phrases = []
        for iv in intervals:
            phrase = f"{iv['user']} sold {iv['num_sold']} {p.name} from {iv['start']} to {iv['end']}"
            formatted_phrases.append(phrase)
            
        timeline_phrases[p.name] = formatted_phrases

    return counts_metadata, timeline_phrases


def execute_inventory_merge(product_id, actual_count, reason, current_user_id):
    """
    Executes a database merge operation for inventory variance.
    Returns: Tuple (bool, str) indicating (success_status, message)
    """
    try:
        # 1. Locate the target live inventory record
        live_record = LiveInventory.query.filter_by(product_id=product_id).first()
        if not live_record:
            return False, "Target Live Inventory record missing for this product."
            
        old_live_qty = live_record.quantity
        
        # 2. Fetch the latest physical count record to sync it up with reality
        latest_audit = PhysicalInventoryCount.query.filter_by(product_id=product_id)\
                        .order_by(PhysicalInventoryCount.timestamp.desc()).first()
        
        # 3. Create historical reference trace inside the merge ledger table
        merge_log = InventoryAuditMerge(
            product_id=product_id,
            user_id=current_user_id,
            live_record=old_live_qty,
            audited_record=actual_count,
            merge_reason=reason,
            date=datetime.now(timezone.utc).date(),
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(merge_log)

        # 4. Synchronise live tracking balance properties
        live_record.quantity = actual_count
        
        # 5. Correct the audit tracker entry to prevent discrepancy loops
        if latest_audit:
            latest_audit.counted_quantity = actual_count
            latest_audit.notes = f"[Merged Override]: {reason} (Prior count state: {latest_audit.counted_quantity})"
        else:
            # Fallback behavior: Generate an explicit audit state if an anomaly occurs
            new_audit_stub = PhysicalInventoryCount(
                product_id=product_id,
                counted_quantity=actual_count,
                user_id=current_user_id,
                notes=f"[System Backfill Merge Variance]: {reason}"
            )
            db.session.add(new_audit_stub)

        # 6. Commit execution state safely
        db.session.commit()
        return True, f"Inventory variances reconciled cleanly. Live track re-balanced to {actual_count}."

    except Exception as e:
        db.session.rollback()
        return False, f"Database execution engine error: {str(e)}"
