from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# 1️⃣ Define association table first
user_shop = db.Table(
    'user_shop',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('shop_id', db.Integer, db.ForeignKey('shop.id'), primary_key=True)
)

# 2️⃣ Define models
class Shop(db.Model):
    __tablename__ = 'shop'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False)

    products = db.relationship('Product', back_populates='shop', cascade="all, delete-orphan")
    users = db.relationship('User', secondary=user_shop, back_populates='shops')

    def __repr__(self):
        return f"<Shop {self.name}>"


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')

    shops = db.relationship('Shop', secondary=user_shop, back_populates='users')

    def __repr__(self):
        return f"<User {self.username}>"


class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(120))
    
    # Retail price
    price = db.Column(db.Float, nullable=False)

    # Batch info
    batch_size = db.Column(db.Integer, default=1)  # e.g., 12 bottles per carton
    batch_price = db.Column(db.Float)              # wholesale price per batch

    # Stock control
    lower_bound = db.Column(db.Integer, default=0)  # minimum units before restocking

    # Optional fields
    size = db.Column(db.String(50))          # e.g., "2L", "500g"
    batch_number = db.Column(db.String(50))  # e.g., "B1234"

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    shop = db.relationship('Shop', back_populates='products')

    records = db.relationship('InventoryRecord', back_populates='product', cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint('name', 'shop_id', name='unique_product_name_per_shop'),
    )

    def __repr__(self):
        return f'<Product {self.name} ({self.size})>'


class InventoryRecord(db.Model):
    __tablename__ = 'inventory_record'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, default=0)

    product = db.relationship('Product', back_populates='records')

    __table_args__ = (
        db.UniqueConstraint('product_id', 'date', name='unique_product_per_day'),
    )

    def __repr__(self):
        return f"<InventoryRecord {self.product_id} - {self.date} - {self.quantity}>"
        

class Sale(db.Model):
    __tablename__ = 'sale'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Track which shop and user made the sale
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationship to the specific items in this sale
    items = db.relationship('SaleItem', backref='sale', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sale {self.id} - Total: R{self.total_amount}>"


class SaleItem(db.Model):
    __tablename__ = 'sale_item'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)  # Price at time of sale
    total_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def __repr__(self):
        return f"<SaleItem {self.product.name} x {self.quantity}>"
