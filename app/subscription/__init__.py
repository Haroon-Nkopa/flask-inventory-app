from flask import Blueprint

#create a blueprint subscription 
subscription  = Blueprint('subscription', __name__, url_prefix ='/subscription')

from . import routes
