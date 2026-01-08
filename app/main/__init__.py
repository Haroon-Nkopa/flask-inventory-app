#define the main blueprint
from flask import Blueprint 
main = Blueprint('main', __name__)  
from . import routes