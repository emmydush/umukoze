#!/usr/bin/env python3
"""
Update database schema to add new worker profile fields
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Worker

def update_database_schema():
    """Add new columns to worker table"""
    print("🔄 Updating database schema...")
    
    with app.app_context():
        try:
            # Get the database connection
            connection = db.engine.connect()
            
            # Add new columns if they don't exist
            new_columns = [
                ("id_photo", "VARCHAR(200)"),
                ("experience_details", "TEXT"),
                ("reference_name", "VARCHAR(100)"),
                ("reference_phone", "VARCHAR(20)"),
                ("reference_relationship", "VARCHAR(50)"),
                ("national_id_number", "VARCHAR(30)")
            ]
            
            for column_name, column_type in new_columns:
                try:
                    # Check if column exists using raw SQL
                    result = connection.execute(db.text(f"PRAGMA table_info(worker)"))
                    columns = [row[1] for row in result]
                    
                    if column_name not in columns:
                        print(f"   Adding column: {column_name}")
                        connection.execute(db.text(f"ALTER TABLE worker ADD COLUMN {column_name} {column_type}"))
                        connection.commit()
                        print(f"   ✅ Added {column_name}")
                    else:
                        print(f"   ⏭️  Column {column_name} already exists")
                        
                except Exception as e:
                    print(f"   ❌ Error adding {column_name}: {e}")
            
            connection.close()
            print("\n🎉 Database schema updated successfully!")
            
        except Exception as e:
            print(f"❌ Error updating database: {e}")

if __name__ == '__main__':
    update_database_schema()
