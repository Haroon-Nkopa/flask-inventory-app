import pytest
import os
from app import create_app, db
from app.models import Shop, User, Product, LiveInventory 

@pytest.fixture(scope='function')
def test_app():
    """Configures the application and an isolated database freshly per test function."""
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })

    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'test-secret-key-123'

    with app.app_context():
        db.session.remove()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def test_client(test_app):
    """Provides a clean test client instance per test function."""
    with test_app.test_client() as client:
        yield client

@pytest.fixture(scope='function')
def setup_mock_data(test_app):
    """Seeds mock database items adaptively matching your schema definitions."""
    with test_app.app_context():
        db.session.rollback()

        # 1. Create a mock shop
        mock_shop = Shop(id=1, name="Test Shop", paid=True)
        db.session.add(mock_shop)
        db.session.commit()

        # 2. Build User model safely by verifying column attributes dynamically
        mock_user = User()
        mock_user.id = 1
        
        # Check and assign username field variations
        if hasattr(User, 'username'):
            mock_user.username = "testuser"
        elif hasattr(User, 'name'):
            mock_user.name = "testuser"

        # Check and assign email field only if it exists
        if hasattr(User, 'email'):
            mock_user.email = "test@example.com"

        # Check and assign role field safely
        if hasattr(User, 'role'):
            mock_user.role = "owner"

        # Handle passwords safely
        if hasattr(mock_user, 'set_password'):
            mock_user.set_password("password123")
        elif hasattr(User, 'password_hash'):
            mock_user.password_hash = "hashed_stub"
        elif hasattr(User, 'password'):
            mock_user.password = "password123"
        
        db.session.add(mock_user)
        db.session.commit()

        # 3. Create a mock product
        mock_product = Product(
            id=101,
            name="cola",
            category="Beverages",
            price=15.00,
            shop_id=1
        )
        db.session.add(mock_product)
        
        # 4. Create live inventory linked to the mock product
        mock_inventory = LiveInventory(product_id=101, quantity=10)
        db.session.add(mock_inventory)
        db.session.commit()

    yield
