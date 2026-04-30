#!/usr/bin/env python3
"""
Database migration script to add admin control fields to User model
"""

from app import app, db
from models import User
from datetime import datetime

def migrate_admin_fields():
    """Add new admin control fields to the database"""
    
    with app.app_context():
        try:
            # Add new columns to the user table using raw SQL
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN is_approved BOOLEAN DEFAULT 0'))
                    print("✅ Added is_approved column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding is_approved column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT 0'))
                    print("✅ Added is_blocked column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding is_blocked column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN approved_at DATETIME'))
                    print("✅ Added approved_at column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding approved_at column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN approved_by INTEGER'))
                    print("✅ Added approved_by column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding approved_by column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN blocked_at DATETIME'))
                    print("✅ Added blocked_at column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding blocked_at column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN blocked_by INTEGER'))
                    print("✅ Added blocked_by column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding blocked_by column: {e}")
                
                try:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN rejection_reason TEXT'))
                    print("✅ Added rejection_reason column")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Error adding rejection_reason column: {e}")
                
                conn.commit()
        except Exception as e:
            print(f"⚠️  Database connection error: {e}")
        
        # Update existing admin user to be approved
        admin = User.query.filter_by(email='admin@umukozi.rw').first()
        if admin:
            admin.is_approved = True
            admin.approved_at = datetime.utcnow()
            admin.approved_by = admin.id  # Self-approved
            db.session.commit()
            print('✅ Admin user updated to be approved by default')
        else:
            print('❌ Admin user not found')
        
        # Set all existing non-admin users to pending approval
        other_users = User.query.filter(User.user_type != 'admin').all()
        updated_count = 0
        for user in other_users:
            if not hasattr(user, 'is_approved') or user.is_approved is None:
                user.is_approved = False
                updated_count += 1
        
        db.session.commit()
        print(f'✅ Updated {updated_count} existing users to pending approval')
        
        print("\n🎉 Database migration completed successfully!")

if __name__ == "__main__":
    migrate_admin_fields()
