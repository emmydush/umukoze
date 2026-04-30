#!/usr/bin/env python3
"""
Script to fix database integrity issues with NULL worker_id in reviews table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Review, Application, Worker, Employer, User

def fix_database_integrity():
    """Fix NULL worker_id values in reviews table"""
    
    with app.app_context():
        print("Checking for database integrity issues...")
        
        # Find all reviews with NULL worker_id
        null_worker_reviews = Review.query.filter(Review.worker_id.is_(None)).all()
        
        if null_worker_reviews:
            print(f"Found {len(null_worker_reviews)} reviews with NULL worker_id")
            
            for review in null_worker_reviews:
                print(f"Review ID: {review.id}, Application ID: {review.application_id}")
                
                # Try to find the correct worker from the application
                application = Application.query.get(review.application_id)
                if application and application.worker:
                    review.worker_id = application.worker.id
                    print(f"  Fixed: Set worker_id to {application.worker.id}")
                else:
                    # If we can't find the worker, delete the orphaned review
                    print(f"  Warning: Could not find worker for review {review.id}, deleting...")
                    db.session.delete(review)
            
            try:
                db.session.commit()
                print("✅ Database integrity issues fixed successfully")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error fixing database: {e}")
        else:
            print("✅ No database integrity issues found")
        
        # Check for other potential issues
        print("\nChecking for other potential issues...")
        
        # Check for orphaned applications
        orphaned_apps = Application.query.filter(
            (Application.worker_id.is_(None)) | 
            (Application.job_id.is_(None))
        ).all()
        
        if orphaned_apps:
            print(f"Found {len(orphaned_apps)} potentially orphaned applications")
            for app_item in orphaned_apps:
                print(f"  Application ID: {app_item.id}, Worker: {app_item.worker_id}, Job: {app_item.job_id}")
        
        # Check for reviews with invalid application_id
        invalid_reviews = Review.query.filter(
            ~Review.application_id.in_(
                db.session.query(Application.id).distinct()
            )
        ).all()
        
        if invalid_reviews:
            print(f"Found {len(invalid_reviews)} reviews with invalid application_id")
            for review in invalid_reviews:
                print(f"  Review ID: {review.id}, Invalid Application ID: {review.application_id}")
                db.session.delete(review)
            
            try:
                db.session.commit()
                print("✅ Removed reviews with invalid application_id")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error removing invalid reviews: {e}")
        
        print("\nDatabase integrity check completed!")

if __name__ == "__main__":
    fix_database_integrity()
