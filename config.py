import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    raw_db_url = os.environ.get('DATABASE_URL')
    
    if raw_db_url and raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = raw_db_url or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #  FIX: Removed 'connect_timeout' to prevent the psycopg2 initialization crash
    if raw_db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_recycle": 280      
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # email server settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') 
    ADMINS = ['rethabilejames26@gmail.com']
    