#!/usr/bin/env python3
"""
Reset admin password
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import generate_password_hash

def reset_admin_password():
    """Reset admin password to a known value"""
    
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(user_type='admin').first()
        
        if admin:
            # Reset password to 'admin123'
            admin.password = generate_password_hash('admin123')
            db.session.commit()
            
            print(f'✅ Admin password reset successfully!')
            print(f'   Email: {admin.email}')
            print(f'   New Password: admin123')
            print(f'   Name: {admin.full_name}')
            print()
            print('You can now login with these credentials.')
        else:
            print('❌ No admin account found!')
            return False
        
        return True

if __name__ == '__main__':
    success = reset_admin_password()
    if success:
        print('Password reset completed!')
    else:
        print('Password reset failed!')
        sys.exit(1)
