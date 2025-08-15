#!/usr/bin/env python3
from app import app, db
from models import Admin, Donation

def initialize_db():
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Create initial admin user if none exists
        if not Admin.query.first():
            master_admin = Admin(
                username=app.config['DEFAULT_ADMIN_USER'],
                email=app.config['DEFAULT_ADMIN_EMAIL'],
                password_hash=generate_password_hash(app.config['DEFAULT_ADMIN_PASSWORD']),
                role='master',
                is_active=True
            )
            db.session.add(master_admin)
            db.session.commit()
            print("Initial admin user created")

if __name__ == '__main__':
    initialize_db()