#create admin blueprint 
from flask import Blueprint
from flask_login import LoginManager

#create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

from . import routes