import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🚀 MANDATORY PRODUCTION FIX FOR RENDER & NEON:
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,      # Recycles connections before Render drops them
        "connect_timeout": 10     # Gives Neon time to wake up if it scaled down to zero
    }
