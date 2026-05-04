#!/usr/bin/env python3
"""
Create or check admin accounts
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import generate_password_hash

def check_and_create_admin():
    """Check existing admins and create one if needed"""
    
    with app.app_context():
        # Check existing admin accounts
        admins = User.query.filter_by(user_type='admin').all()
        
        print('=== Admin Account Check ===')
        if admins:
            print(f'Found {len(admins)} existing admin account(s):')
            for admin in admins:
                print(f'  - Name: {admin.full_name}')
                print(f'    Email: {admin.email}')
                print(f'    Active: {admin.is_active}')
                print(f'    Approved: {admin.is_approved}')
                print(f'    Created: {admin.created_at}')
                print()
        else:
            print('No admin accounts found.')
        
        # Create admin if none exist
        if not admins:
            print('Creating default admin account...')
            
            admin_email = input('Enter admin email (default: admin@umukozi.com): ').strip() or 'admin@umukozi.com'
            admin_password = input('Enter admin password (default: admin123): ').strip() or 'admin123'
            admin_name = input('Enter admin name (default: Admin User): ').strip() or 'Admin User'
            admin_phone = input('Enter admin phone (default: 0780000000): ').strip() or '0780000000'
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=admin_email).first()
            if existing_user:
                print(f'Error: User with email {admin_email} already exists!')
                return False
            
            # Create admin user
            admin_user = User(
                email=admin_email,
                password=generate_password_hash(admin_password),
                full_name=admin_name,
                phone=admin_phone,
                user_type='admin',
                is_active=True,
                is_approved=True,
                approved_at=db.func.current_timestamp()
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f'✅ Admin account created successfully!')
            print(f'   Email: {admin_email}')
            print(f'   Password: {admin_password}')
            print(f'   Name: {admin_name}')
            print()
            print('You can now login with these credentials.')
        
        return True

if __name__ == '__main__':
    success = check_and_create_admin()
    if success:
        print('Admin account setup completed!')
    else:
        print('Admin account setup failed!')
        sys.exit(1)
