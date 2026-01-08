#define a app factory function
from flask import Flask
#import migrate
from flask_migrate import Migrate
#import db from models
from .models import db , User
#import login manager
from flask_login import LoginManager


#import main blueprint
from .main import main as main_blueprint
from .admin import  admin_bp
from .auth import auth_bp



migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # bind SQLAlchemy to app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = "auth.admin_login"
    login_manager.login_message_category = "warning"

    # register the main blueprint
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    
    
    return app