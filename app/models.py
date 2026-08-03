from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin



db = SQLAlchemy()

#  1. Association Table for Many-to-Many Relationships
user_shop = db.Table(
    'user_shop',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('shop_id', db.Integer, db.ForeignKey('shop.id'), primary_key=True)
)

#  2. Shop Configuration Model
class Shop(db.Model):
    __tablename__ = 'shop'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False)

    products = db.relationship('Product', back_populates='shop', cascade="all, delete-orphan")
    users = db.relationship('User', secondary=user_shop, back_populates='shops')

    def __repr__(self):
        return f"<Shop {self.name}>"


#  3. System User Account Registry
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')

    shops = db.relationship('Shop', secondary=user_shop, back_populates='users')

    def __repr__(self):
        return f"<User {self.username}>"


#  4. Core Inventory Master Data
class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(120))
    price = db.Column(db.Float, nullable=False)
    batch_size = db.Column(db.Integer, default=1)
    batch_price = db.Column(db.Float)
    lower_bound = db.Column(db.Integer, default=0)
    size = db.Column(db.String(50))
    batch_number = db.Column(db.String(50))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

    shop = db.relationship('Shop', back_populates='products')

    # Target Structural Control Hooks
    live_inventory = db.relationship(
        "LiveInventory",
        back_populates="product",
        uselist=False, # Strict 1-to-1 operational constraint
        cascade="all, delete-orphan"
    )

    daily_snapshots = db.relationship(
        "DailyInventorySnapshot",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    physical_counts = db.relationship(
        "PhysicalInventoryCount",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint('name', 'shop_id', name='unique_product_name_per_shop'),
    )

    def __repr__(self):
        return f"<Product {self.name}>"


#  5. Real-time Live State Monitor (1-to-1 Mapping)

class LiveInventory(db.Model):
    __tablename__ = 'live_inventory'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, unique=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    
    # Updated to modern, timezone-aware UTC functions
    last_updated = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    product = db.relationship("Product", back_populates="live_inventory")


#  6. Historical Closing Snapshots (1-to-Many Mapping)
class DailyInventorySnapshot(db.Model):
    __tablename__ = 'daily_inventory_snapshot'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    closing_quantity = db.Column(db.Integer, default=0, nullable=False)

    product = db.relationship("Product", back_populates="daily_snapshots")

    __table_args__ = (
        db.UniqueConstraint('product_id', 'date', name='unique_snapshot_per_product_per_day'),
    )



# 7. Physical Internal Count Audit Ledger (1-to-Many Mapping)
class PhysicalInventoryCount(db.Model):
    __tablename__ = 'physical_inventory_count'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    counted_quantity = db.Column(db.Integer, nullable=False)
    
    # 1. Optional note column (nullable=True means it is explicitly optional)
    notes = db.Column(db.Text, nullable=True)
    
    # 2. Track the logged-in system user via ForeignKey matching your User table layout
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Database Relationship mappings
    product = db.relationship("Product", back_populates="physical_counts")
    user = db.relationship("User") # Links to the operational user footprint details

    def __repr__(self):
        return f"<PhysicalCount Product ID {self.product_id} by User ID {self.user_id}: {self.counted_quantity}>"


#  8. Unified Sales Logging Model
class Sale(db.Model):
    __tablename__ = 'sale'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    items = db.relationship('SaleItem', backref='sale', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sale {self.id} - Total: R{self.total_amount}>"


#  9. Itemized Transaction Breakdown Records
class SaleItem(db.Model):
    __tablename__ = 'sale_item'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def __repr__(self):
        return f"<SaleItem Product ID: {self.product_id} x {self.quantity}>"
