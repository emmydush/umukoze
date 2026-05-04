#!/usr/bin/env python3
"""
Check and fix WorkerContactAccess schema
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def check_and_fix_schema():
    """Check and fix WorkerContactAccess table schema"""
    
    with app.app_context():
        try:
            # Check if WorkerContactAccess table exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print('=== Database Schema Check ===')
            print(f'Tables found: {len(tables)}')
            
            if 'worker_contact_access' in tables:
                print('✅ worker_contact_access table exists')
                
                # Check columns
                columns = [col['name'] for col in inspector.get_columns('worker_contact_access')]
                print(f'Columns: {columns}')
                
                # Check for missing columns
                required_columns = ['id', 'employer_id', 'worker_id', 'payment_id', 'access_granted', 'granted_at']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    print(f'❌ Missing columns: {missing_columns}')
                    
                    # Add missing columns
                    with db.engine.connect() as conn:
                        for column in missing_columns:
                            if column == 'granted_at':
                                conn.execute(text("ALTER TABLE worker_contact_access ADD COLUMN granted_at DATETIME"))
                                print('✅ Added granted_at column')
                            # Add other missing columns if needed
                    
                    conn.commit()
                    print('✅ Schema updated successfully')
                else:
                    print('✅ All required columns present')
            else:
                print('❌ worker_contact_access table not found')
                print('Creating table...')
                
                # Create the table
                from models import WorkerContactAccess
                WorkerContactAccess.__table__.create(db.engine, checkfirst=True)
                print('✅ worker_contact_access table created')
                
        except Exception as e:
            print(f'❌ Error checking schema: {e}')
            return False
            
        return True

if __name__ == '__main__':
    success = check_and_fix_schema()
    if success:
        print('Schema check completed!')
    else:
        print('Schema check failed!')
        sys.exit(1)
