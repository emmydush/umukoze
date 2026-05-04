#!/usr/bin/env python3
"""
Add verified_by column to Payment table
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def add_verified_by_column():
    """Add verified_by column to Payment table"""
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('payment')]
            
            if 'verified_by' not in columns:
                print("Adding verified_by column to Payment table...")
                
                # Add the column
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE payment ADD COLUMN verified_by INTEGER REFERENCES user(id)"))
                    conn.commit()
                
                print("✅ verified_by column added successfully!")
            else:
                print("✅ verified_by column already exists!")
                
        except Exception as e:
            print(f"❌ Error adding verified_by column: {e}")
            return False
            
        return True

if __name__ == '__main__':
    success = add_verified_by_column()
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")
        sys.exit(1)
