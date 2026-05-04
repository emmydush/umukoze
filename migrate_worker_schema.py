#!/usr/bin/env python3
"""
Migration script to add missing columns to the Worker table
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate_worker_schema():
    """Add missing columns to Worker table"""
    
    with app.app_context():
        try:
            # Check for missing columns in 'worker' table
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('worker')]
            
            missing_columns = [
                ('age', 'INTEGER'),
                ('date_of_birth', 'DATE'),
                ('id_photo', 'VARCHAR(200)'),
                ('experience_details', 'TEXT'),
                ('reference_name', 'VARCHAR(100)'),
                ('reference_phone', 'VARCHAR(20)'),
                ('reference_relationship', 'VARCHAR(50)'),
                ('national_id_number', 'VARCHAR(30)')
            ]
            
            for column_name, column_type in missing_columns:
                if column_name not in columns:
                    print(f"Adding {column_name} column to worker table...")
                    
                    # Add the column
                    with db.engine.connect() as conn:
                        try:
                            conn.execute(text(f"ALTER TABLE worker ADD COLUMN {column_name} {column_type}"))
                            conn.commit()
                            print(f"✅ {column_name} column added successfully!")
                        except Exception as e:
                            print(f"❌ Error adding {column_name}: {e}")
                else:
                    print(f"✅ {column_name} column already exists!")
                    
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            return False
            
        return True

if __name__ == '__main__':
    print("🚀 Starting Worker table migration...")
    success = migrate_worker_schema()
    if success:
        print("\n✨ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
