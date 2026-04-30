#!/usr/bin/env python3
"""
Debug script to check login issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import check_password_hash

def debug_users():
    """Debug all users in database"""
    print("🔍 Debugging Login Issue...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            print(f"Total users in database: {len(users)}")
            
            for user in users:
                print(f"\n👤 User ID: {user.id}")
                print(f"   Email: '{user.email}'")
                print(f"   Full Name: '{user.full_name}'")
                print(f"   User Type: '{user.user_type}'")
                print(f"   Phone: '{user.phone}'")
                print(f"   Password Hash: '{user.password[:50]}...'")
                print(f"   Created At: {user.created_at}")
                print(f"   Is Active: {user.is_active}")
                
                # Test password verification
                test_passwords = ['testpassword123', 'password', '123456']
                for pwd in test_passwords:
                    if check_password_hash(user.password, pwd):
                        print(f"   ✅ Password '{pwd}' WORKS")
                        break
                else:
                    print(f"   ❌ No common passwords work")
            
            # Test specific emails
            test_emails = [
                'testworker@umukozi.rw',
                'testemployer@umukozi.rw',
                'Testworker@umukozi.rw',  # Case variation
                'testworker@umukozi.rw '  # Space variation
            ]
            
            print(f"\n🔍 Testing specific email lookups:")
            for email in test_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    print(f"   ✅ Found: '{email}' -> ID {user.id}")
                else:
                    print(f"   ❌ Not found: '{email}'")
            
            # Check for case sensitivity issues
            print(f"\n🔍 Case sensitivity test:")
            user_lower = User.query.filter(User.email.ilike('testworker@umukozi.rw')).all()
            print(f"   Case-insensitive search found: {len(user_lower)} users")
            for u in user_lower:
                print(f"   - '{u.email}' (ID: {u.id})")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def test_login_logic():
    """Test the actual login logic from app.py"""
    print(f"\n🔐 Testing Login Logic...")
    
    with app.app_context():
        try:
            # Simulate login attempt
            email = 'testworker@umukozi.rw'
            password = 'testpassword123'
            
            print(f"Testing login with:")
            print(f"   Email: '{email}'")
            print(f"   Password: '{password}'")
            
            # This is the exact logic from app.py
            user = User.query.filter_by(email=email).first()
            
            if user:
                print(f"✅ User found: ID {user.id}")
                if check_password_hash(user.password, password):
                    print(f"✅ Password match - LOGIN SHOULD SUCCEED")
                else:
                    print(f"❌ Password mismatch - LOGIN WILL FAIL")
                    print(f"   Stored hash: {user.password}")
            else:
                print(f"❌ User not found - LOGIN WILL FAIL")
                
                # Try case-insensitive
                user_ci = User.query.filter(User.email.ilike(email)).first()
                if user_ci:
                    print(f"⚠️  Found with case-insensitive search: '{user_ci.email}'")
                
        except Exception as e:
            print(f"❌ Error testing login logic: {e}")

if __name__ == '__main__':
    debug_users()
    test_login_logic()
