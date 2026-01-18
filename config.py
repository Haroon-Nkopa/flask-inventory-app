import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # SQLite database path
    SQLALCHEMY_DATABASE_URI = (
	os.environ.get("DATABASE_URI")
	or "sqlite:///"+ os.path.join(basedir, "inventory.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'devkey')
