from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from logging.handlers import RotatingFileHandler
import logging
import os

from .models import db, User
from .main import main as main_blueprint
from .admin import admin_bp
from .auth import auth_bp

migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # ---------- LOGGING SETUP ----------
    if not app.debug and not app.testing:
        log_dir = os.path.join(app.root_path, '..', 'logs')
        log_dir = os.path.abspath(log_dir)

        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10240,
            backupCount=10
        )

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

        app.logger.info('Flask Inventory App startup')
    # ---------- END LOGGING ----------

    # bind SQLAlchemy
    db.init_app(app)
    migrate.init_app(app, db)

    # login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.admin_login"
    login_manager.login_message_category = "warning"

    # register blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # user loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
