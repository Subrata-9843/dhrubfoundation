import os
import uuid
import io
import json
import qrcode
import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
from contextlib import redirect_stderr

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.sql import func
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.file import FileField, FileRequired, FileAllowed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure environment
from dotenv import load_dotenv
load_dotenv()

# Suppress WeasyPrint warnings
os.environ['GIO_EXTRA_MODULES'] = ''
os.environ['GIO_MODULE_DIR'] = ''
try:
    from weasyprint import HTML
except ImportError:
    raise ImportError(
        "WeasyPrint dependencies not installed. Please install them first:\n"
        "Windows: Download GTK3 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\n"
        "Mac: brew install cairo pango gdk-pixbuf libffi\n"
        "Linux: sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev"
    )

# Initialize extensions
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # --------------------------
    # Configuration
    # --------------------------
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'change-me-to-a-random-secret'),
        'WTF_CSRF_SECRET_KEY': os.getenv('WTF_CSRF_SECRET_KEY', 'change-me-too'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///donations.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'UPLOAD_FOLDER': os.path.join('static', 'uploads'),
        'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
        'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'ogg'},
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
        'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes'),
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME'),
        'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', 'noreply@dhrubfoundation.org'),
        'SESSION_COOKIE_SECURE': True,
        'REMEMBER_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
    })

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'admin.login'
    
    # Fix proxy headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Register blueprints
    from .routes import main, admin, donations
    app.register_blueprint(main.main_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(donations.donations_bp)
    
    # Create required directories
    with app.app_context():
        create_directories(app)
        initialize_database()
    
    return app

# --------------------------
# Models
# --------------------------
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='viewer')
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    created_at = db.Column(db.DateTime, server_default=func.now())
    reset_token = db.Column(db.String(200))
    reset_token_expires = db.Column(db.DateTime)
    creator = db.relationship('Admin', remote_side=[id])

class AdminActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    activity = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=func.now())
    admin = db.relationship('Admin', backref='activities')

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    provider = db.Column(db.String(50))
    account_number = db.Column(db.String(50))
    ifsc = db.Column(db.String(20))
    transaction_ref = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, server_default=func.now())
    invoice_path = db.Column(db.String(200))
    qr_path = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    verified_at = db.Column(db.DateTime)

# --------------------------
# Forms
# --------------------------
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('master','Master'),('manager','Manager'),('viewer','Viewer')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class UploadForm(FlaskForm):
    files = FileField('Select Images', validators=[
        FileRequired(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!')
    ])
    category = SelectField('Category', choices=[
        ('gallery', 'Gallery'),
        ('events', 'Events'),
        ('team', 'Team'),
        ('projects', 'Projects')
    ])
    visibility = SelectField('Visibility', choices=[
        ('public', 'Public'),
        ('private', 'Private'),
        ('members', 'Members Only')
    ])
    submit = SubmitField('Upload')

# --------------------------
# Utility Functions
# --------------------------
def create_directories(app):
    """Create required directories if they don't exist"""
    dirs = [
        app.config['UPLOAD_FOLDER'],
        os.path.join('static', 'donation_data', 'invoices'),
        os.path.join('static', 'qr'),
        os.path.join('static', 'images', 'members'),
        os.path.dirname(os.path.join('static', 'data', 'members.json')),
        os.path.join('static', 'donation_data')
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

def initialize_database():
    """Initialize database with default admin if needed"""
    db.create_all()
    if not Admin.query.first():
        master = Admin(
            username=os.getenv('DEFAULT_ADMIN_USER', 'admin'),
            email=os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@dhrubfoundation.org'),
            password_hash=generate_password_hash(os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')),
            role='master',
            is_active=True
        )
        db.session.add(master)
        db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def log_admin_activity(activity):
    try:
        if current_user.is_authenticated:
            db.session.add(AdminActivity(
                admin_id=current_user.id,
                activity=activity,
                ip_address=request.remote_addr
            ))
            db.session.commit()
    except Exception:
        app.logger.exception("Failed to log admin activity")

def has_permission(perm):
    permissions = {
        'master': ['view_dashboard', 'manage_donations', 'manage_admins', 'system_settings'],
        'manager': ['view_dashboard', 'manage_donations'],
        'viewer': ['view_dashboard']
    }
    return current_user.is_authenticated and (
        current_user.role == 'master' or perm in permissions.get(current_user.role, [])
    )

def get_members_data():
    try:
        with open(os.path.join('static', 'data', 'members.json')) as f:
            return json.load(f)
    except Exception:
        return {'founders': [], 'admin': []}

def generate_qr(amount):
    qr_dir = os.path.join('static', 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    uri = f"upi://pay?pa=dhrub@upi&pn=Dhrub Foundation&am={amount}&cu=INR"
    img = qrcode.make(uri)
    fn = f"{uuid.uuid4().hex}_qr.png"
    qr_path = os.path.join(qr_dir, fn)
    img.save(qr_path)
    return fn

def generate_invoice_pdf(data):
    invoice_dir = os.path.join('static', 'donation_data', 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)
    html = render_template('includes/invoice_template.html', donation=data)
    fn = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(invoice_dir, fn)
    with redirect_stderr(io.StringIO()):
        HTML(string=html).write_pdf(path)
    return fn

# --------------------------
# Application Factory
# --------------------------
app = create_app()

# --------------------------
# Error Handlers
# --------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# --------------------------
# Context Processors
# --------------------------
@app.context_processor
def inject_utilities():
    return dict(
        get_members_data=get_members_data,
        has_permission=has_permission
    )

# --------------------------
# CLI Commands
# --------------------------
@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    initialize_database()
    print('Initialized the database.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)