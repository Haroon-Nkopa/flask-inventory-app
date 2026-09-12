def test_create_product_api_success(test_client, setup_mock_data, test_app):
    """Tests creating a product with an authorized logged-in user session."""
    
    # 1. Log the seeded user into Flask-Login context
    from app.models import User
    from flask_login import login_user
    
    with test_app.test_request_context():
        user = User.query.get(1)
        login_user(user)
        
    # 2. Inject your custom shop session requirements required by @shop_required
    with test_client.session_transaction() as sess:
        sess['shop_id'] = 1
        sess['shop_name'] = "Test Shop"
        sess['shop_paid'] = True

    # 3. Make the API call
    payload = {
        "name": "orange juice",
        "category": "Beverages",
        "price": 22.50
    }
    response = test_client.post('/api/products', json=payload)
    
    assert response.status_code == 201
