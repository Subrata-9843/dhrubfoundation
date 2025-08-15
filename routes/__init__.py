from flask import Blueprint

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
donations_bp = Blueprint('donations', __name__, url_prefix='/donations')
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from . import main, admin, donations, auth