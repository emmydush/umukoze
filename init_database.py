#!/usr/bin/env python3
"""
Database initialization script for Umukozi deployment
This script creates all database tables and sets up initial data
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Worker, Employer, Job, Application, Review, Message, Notification, Payment, WorkerContactAccess, AdminMessage, AdminNotification, MessageTemplate, NotificationPreference

def init_database():
    """Initialize database with all tables"""
    print("🔧 Initializing database...")
    
    with app.app_context():
        try:
            # Create all tables
            print("📊 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Check if admin user exists
            admin_user = User.query.filter_by(user_type='admin').first()
            if not admin_user:
                print("👤 Creating default admin user...")
                from werkzeug.security import generate_password_hash
                
                admin = User(
                    email='admin@umukozi.rw',
                    password=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    full_name='System Administrator',
                    phone='+250000000000',
                    user_type='admin',
                    is_approved=True,
                    is_active=True
                )
                db.session.add(admin)
                db.session.commit()
                print("✅ Default admin user created!")
                print("   Email: admin@umukozi.rw")
                print("   Password: admin123")
                print("   ⚠️  Please change this password after first login!")
            else:
                print("✅ Admin user already exists")
            
            print("🎉 Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            return False
    
    return True

def check_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    with app.app_context():
        try:
            # Test connection by executing a simple query
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful!")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Umukozi Database Initialization")
    print("=" * 50)
    
    # Check environment
    database_url = os.getenv('DATABASE_URL', 'sqlite:///umukozi.db')
    print(f"📡 Database URL: {database_url}")
    
    # Test connection first
    if check_database_connection():
        # Initialize database
        if init_database():
            print("\n✨ Ready to start the application!")
        else:
            print("\n❌ Database initialization failed!")
            sys.exit(1)
    else:
        print("\n❌ Cannot connect to database!")
        sys.exit(1)
