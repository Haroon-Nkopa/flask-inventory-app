#import create_app from __init__.py
from app import create_app, db  
from app.models import Product, InventoryRecord

app = create_app()

# Optional: Flask shell context for convenience
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Product': Product, 'InventoryRecord': InventoryRecord}