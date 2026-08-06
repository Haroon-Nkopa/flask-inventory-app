from sqlalchemy import func
from .. import db
from ..models import (
    Product, 
    LiveInventory, 
    PhysicalInventoryCount
)

def get_inventory_discrepancies(shop_id):
    """
    Compares the latest physical inventory audit counts against active live quantities
    for a specific shop. Returns a list of dictionaries detailing any mismatches.
    """
    # 1. Subquery: Extract the absolute latest physical count timestamp per product
    latest_count_subquery = db.session.query(
        PhysicalInventoryCount.product_id,
        func.max(PhysicalInventoryCount.timestamp).label('max_timestamp')
    ).group_by(PhysicalInventoryCount.product_id).subquery()

    # 2. Main Query: Join the latest audit records with live inventory quantities
    # We restrict products by shop_id to maintain clean context boundaries
    discrepancies_query = db.session.query(
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            func.coalesce(LiveInventory.quantity, 0).label('live_quantity'),
            PhysicalInventoryCount.counted_quantity.label('audited_quantity')
        )\
        .join(LiveInventory, Product.id == LiveInventory.product_id)\
        .join(latest_count_subquery, Product.id == latest_count_subquery.c.product_id)\
        .join(
            PhysicalInventoryCount, 
            (PhysicalInventoryCount.product_id == latest_count_subquery.c.product_id) & 
            (PhysicalInventoryCount.timestamp == latest_count_subquery.c.max_timestamp)
        )\
        .filter(Product.shop_id == shop_id)\
        .all()

    discrepancies_list = []

    # 3. Filter and parse discrepancies in memory
    for row in discrepancies_query:
        live_qty = int(row.live_quantity)
        audited_qty = int(row.audited_quantity)
        
        # Calculate the operational variance
        difference = audited_qty - live_qty

        # If a variance exists, capture it into standard key-value pairs
        if difference != 0:
            discrepancies_list.append({
                "product_id": int(row.product_id),
                "product_name": str(row.product_name),
                "live_quantity": live_qty,
                "audited_quantity": audited_qty,
                "difference": difference
            })

    return discrepancies_list
