import os

class Config:
    # SQLite database path
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'devkey')
