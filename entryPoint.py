import os
from flask import send_from_directory
# Import factory engine and db tracking context instance layout
from app import create_app, db  
# Explicitly import all 10 updated core models
from app.models import (
    Shop, 
    User, 
    Product, 
    LiveInventory, 
    DailyInventorySnapshot, 
    PhysicalInventoryCount, 
    Sale, 
    SaleItem,
    InventoryAuditMerge
)

app = create_app()

# Complete Flask shell context engine configuration mapping
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'Shop': Shop,
        'User': User,
        'Product': Product, 
        'LiveInventory': LiveInventory,
        'DailyInventorySnapshot': DailyInventorySnapshot,
        'PhysicalInventoryCount': PhysicalInventoryCount,
        'Sale': Sale,
        'SaleItem': SaleItem,
        'InventoryAuditMerge': InventoryAuditMerge
    }

if __name__ == '__main__':
    # Fallback to local dev port constraints if running direct instead of via WSGI gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
