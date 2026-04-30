#!/usr/bin/env python3
"""
Script to create admin credentials for Umukozi application
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import sys

def create_admin():
    """Create admin user with credentials"""
    
    # Admin credentials
    admin_email = "admin@umukozi.rw"
    admin_password = "Admin@2024"
    admin_full_name = "System Administrator"
    admin_phone = "+250788123456"
    
    with app.app_context():
        try:
            # Check if admin already exists
            existing_admin = User.query.filter_by(email=admin_email).first()
            if existing_admin:
                print(f"Admin user already exists: {admin_email}")
                print("Deleting existing admin user...")
                db.session.delete(existing_admin)
                db.session.commit()
                print("Existing admin user deleted.")
            
            # Create new admin user
            admin_user = User(
                email=admin_email,
                password=generate_password_hash(admin_password),
                full_name=admin_full_name,
                phone=admin_phone,
                user_type='admin'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("=" * 50)
            print("✅ ADMIN CREDENTIALS CREATED SUCCESSFULLY")
            print("=" * 50)
            print(f"Email:    {admin_email}")
            print(f"Password: {admin_password}")
            print(f"Name:     {admin_full_name}")
            print(f"Phone:    {admin_phone}")
            print(f"User Type: admin")
            print("=" * 50)
            print("📝 Please save these credentials securely!")
            print("🔐 You can now login with these credentials.")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            sys.exit(1)

if __name__ == "__main__":
    create_admin()
