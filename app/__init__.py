from flask import Flask, send_from_directory, render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from logging.handlers import RotatingFileHandler
import logging
import os

from .models import db, User
from .main import main as main_blueprint
from .admin import admin_bp
from .auth import auth_bp
from .subscription import subscription

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
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # register blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(subscription)

    # user loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Standard safe rollback for database crashes
        return render_template('errors/500.html'), 500


    @app.route('/sw.js')
    def serve_service_worker():
        # Points directly to the 'app' folder where sw.js lives
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(base_dir, 'sw.js', mimetype='application/javascript')

    @app.route('/manifest.json')
    def serve_manifest():
        # Points to 'app/static/manifest.json'
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        return send_from_directory(static_dir, 'manifest.json', mimetype='application/json')

    return app
