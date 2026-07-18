import os

# Get the base directory of the project for the SQLite file
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for signing cookies and protecting forms
    # In production, this should be a random string from an environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Database configuration
    # This creates 'app.db' in your project root
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    # Disable tracking to save memory/performance
    SQLALCHEMY_TRACK_MODIFICATIONS = False
