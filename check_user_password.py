#!/usr/bin/env python3
"""
Check the registered user's password
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def check_registered_user():
    """Check the user you registered"""
    print("🔍 Checking Your Registered Account...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Find your registered account
            user = User.query.filter_by(email='emmychris915@gmil.com').first()
            
            if user:
                print(f"✅ Found your account:")
                print(f"   Email: {user.email}")
                print(f"   Name: {user.full_name}")
                print(f"   Type: {user.user_type}")
                print(f"   Phone: {user.phone}")
                print(f"   Created: {user.created_at}")
                
                # Since we can't decrypt the password, let's reset it to a known one
                print(f"\n🔧 Resetting password to 'password123' for testing...")
                from werkzeug.security import generate_password_hash
                user.password = generate_password_hash('password123', method='pbkdf2:sha256')
                db.session.commit()
                
                print(f"✅ Password reset successful!")
                print(f"\n🔑 You can now login with:")
                print(f"   Email: emmychris915@gmil.com")
                print(f"   Password: password123")
                
            else:
                print(f"❌ Account not found with email: emmychris915@gmil.com")
                
                # Show all users for reference
                all_users = User.query.all()
                print(f"\n📋 All registered users:")
                for u in all_users:
                    print(f"   - {u.email} ({u.full_name})")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_registered_user()
