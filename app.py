import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables (not committed to GitHub)
load_dotenv()

app = Flask(__name__)

# Configuration - sensitive values come from environment variables
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY'),
    'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL'),
    'UPLOAD_FOLDER': os.path.join('static', 'uploads'),
    'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'SERVER_NAME': os.getenv('SERVER_NAME', None),
    # Security settings
    'SESSION_COOKIE_SECURE': True,
    'REMEMBER_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax'
})

# Initialize extensions (import after app creation to avoid circular imports)
from extensions import db, login_manager, mail, csrf

db.init_app(app)
login_manager.init_app(app)
mail.init_app(app)
csrf.init_app(app)

# Import blueprints/routes
from auth.routes import auth_bp
from admin.routes import admin_bp
from main.routes import main_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)

# Create tables
with app.app_context():
    db.create_all()
    from utils.seed import create_initial_admin
    create_initial_admin()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
