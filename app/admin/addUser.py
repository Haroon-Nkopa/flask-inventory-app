#!/usr/bin/env python
# app/admin/addUser.py

import os
import sys
from getpass import getpass
from werkzeug.security import generate_password_hash

# --- Add project root to sys.path ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.models import db, User

app = create_app()

def main():
    """Add a new user from the terminal."""
    with app.app_context():
        username = input("Enter username: ").strip()
        password = getpass("Enter password: ").strip()
        role = input("Enter role (admin/user) [default: user]: ").strip() or "user"

        if User.query.filter_by(username=username).first():
            print(f"❌ User '{username}' already exists.")
            return

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ User '{username}' added successfully with role '{role}'.")

if __name__ == "__main__":
    main()
