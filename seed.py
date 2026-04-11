from werkzeug.security import generate_password_hash
from app import db, create_app
from app.models import User, Shop

app = create_app()

with app.app_context():
    # 1. Create the Shop
    shop_name = "Giant"
    existing_shop = Shop.query.filter_by(name=shop_name).first()
    
    if not existing_shop:
        new_shop = Shop(name=shop_name)
        db.session.add(new_shop)
        print(f"Shop '{shop_name}' created.")
    else:
        new_shop = existing_shop
        print(f"Shop '{shop_name}' already exists.")

    # 2. Create the User
    username = "rethabile"
    existing_user = User.query.filter_by(username=username).first()
    
    if not existing_user:
        hashed_pw = generate_password_hash("admin123")
        new_user = User(
            username=username,
            password=hashed_pw,
            role='admin'
        )
        db.session.add(new_user)
        print(f"User '{username}' created.")
    else:
        new_user = existing_user
        print(f"User '{username}' already exists.")

    # 3. Link User to Shop (Relationship)
    if new_shop not in new_user.shops:
        new_user.shops.append(new_shop)
        print(f"Linked {username} to {shop_name}.")
    else:
        print(f"{username} is already linked to {shop_name}.")

    # Commit all changes
    db.session.commit()
    print("Database seeding completed successfully!")
