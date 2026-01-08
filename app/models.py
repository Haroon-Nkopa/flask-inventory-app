from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

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
    price = db.Column(db.Float)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    shop = db.relationship('Shop', back_populates='products')

    records = db.relationship('InventoryRecord', back_populates='product', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Product {self.name}>'


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
