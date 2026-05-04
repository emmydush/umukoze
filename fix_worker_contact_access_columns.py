#!/usr/bin/env python3
"""
Fix missing columns in worker_contact_access table
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_worker_contact_access_columns():
    """Add missing columns to worker_contact_access table"""
    
    with app.app_context():
        try:
            # Check current columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('worker_contact_access')]
            
            print('=== Current worker_contact_access columns ===')
            print(f'Columns: {columns}')
            
            # Required columns from model
            required_columns = [
                'id', 'employer_id', 'worker_id', 'payment_id', 
                'access_granted', 'phone_visible', 'email_visible', 
                'whatsapp_accessible', 'created_at', 'granted_at', 'expires_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f'❌ Missing columns: {missing_columns}')
                
                # Add missing columns
                with db.engine.connect() as conn:
                    for column in missing_columns:
                        if column == 'created_at':
                            conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                            print('✅ Added created_at column')
                        elif column == 'expires_at':
                            conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN expires_at DATETIME"))
                            print('✅ Added expires_at column')
                        elif column == 'phone_visible':
                            conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN phone_visible BOOLEAN DEFAULT FALSE"))
                            print('✅ Added phone_visible column')
                        elif column == 'email_visible':
                            conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN email_visible BOOLEAN DEFAULT FALSE"))
                            print('✅ Added email_visible column')
                        elif column == 'whatsapp_accessible':
                            conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN whatsapp_accessible BOOLEAN DEFAULT FALSE"))
                            print('✅ Added whatsapp_accessible column')
                    
                    conn.commit()
                    print('✅ All missing columns added successfully')
            else:
                print('✅ All required columns present')
                
        except Exception as e:
            print(f'❌ Error fixing columns: {e}')
            return False
            
        return True

if __name__ == '__main__':
    success = fix_worker_contact_access_columns()
    if success:
        print('Column fix completed!')
    else:
        print('Column fix failed!')
        sys.exit(1)
