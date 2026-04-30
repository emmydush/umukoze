#!/usr/bin/env python3
"""
Database migration script to create admin message and notification tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AdminMessage, AdminNotification, MessageTemplate, NotificationPreference

def create_tables():
    """Create the new admin message and notification tables"""
    
    with app.app_context():
        print("Creating admin message and notification tables...")
        
        try:
            # Create all new tables
            db.create_all()
            
            # Check if tables exist by attempting to query them
            try:
                # Test AdminMessage table
                db.session.query(AdminMessage).limit(1).all()
                print("✓ AdminMessage table exists")
            except:
                print("✗ AdminMessage table creation failed")
                return False
            
            try:
                # Test AdminNotification table
                db.session.query(AdminNotification).limit(1).all()
                print("✓ AdminNotification table exists")
            except:
                print("✗ AdminNotification table creation failed")
                return False
            
            try:
                # Test MessageTemplate table
                db.session.query(MessageTemplate).limit(1).all()
                print("✓ MessageTemplate table exists")
            except:
                print("✗ MessageTemplate table creation failed")
                return False
            
            try:
                # Test NotificationPreference table
                db.session.query(NotificationPreference).limit(1).all()
                print("✓ NotificationPreference table exists")
            except:
                print("✗ NotificationPreference table creation failed")
                return False
            
            print("\n✅ All admin message and notification tables created successfully!")
            
            # Create some default message templates
            create_default_templates()
            
            # Create notification preferences for existing users
            create_default_preferences()
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False

def create_default_templates():
    """Create default message templates"""
    
    templates = [
        {
            'name': 'Welcome New User',
            'subject': 'Welcome to Umukozi!',
            'content': 'Dear {user_name},\n\nWelcome to Umukozi! We\'re excited to have you join our platform. As a {user_type}, you now have access to:\n\n{features}\n\nIf you have any questions, please don\'t hesitate to reach out to our support team.\n\nBest regards,\nThe Umukozi Team',
            'message_type': 'announcement',
            'variables': '["user_name", "user_type", "features"]'
        },
        {
            'name': 'System Maintenance',
            'subject': 'Scheduled System Maintenance',
            'content': 'Dear Users,\n\nWe will be performing scheduled maintenance on our system:\n\nDate: {maintenance_date}\nTime: {maintenance_time}\nDuration: {duration}\n\nDuring this time, the platform may be temporarily unavailable. We apologize for any inconvenience.\n\nThank you for your patience.\n\nUmukozi Team',
            'message_type': 'maintenance',
            'variables': '["maintenance_date", "maintenance_time", "duration"]'
        },
        {
            'name': 'Policy Update',
            'subject': 'Important Policy Update',
            'content': 'Dear Users,\n\nWe have updated our {policy_type} policy. Key changes include:\n\n{changes}\n\nPlease review the updated policy in your account settings. These changes will take effect on {effective_date}.\n\nIf you have any questions, please contact our support team.\n\nBest regards,\nUmukozi Team',
            'message_type': 'policy',
            'variables': '["policy_type", "changes", "effective_date"]'
        },
        {
            'name': 'Account Verification',
            'subject': 'Action Required: Complete Your Profile Verification',
            'content': 'Dear {user_name},\n\nYour account registration is almost complete! To fully access all features and start {action}, please complete your profile verification.\n\nSteps to verify:\n1. Upload a valid ID document\n2. Provide proof of {proof_type}\n3. Wait for admin approval\n\nComplete verification now: {verification_link}\n\nThis helps us maintain a safe and trustworthy platform for all users.\n\nBest regards,\nUmukozi Team',
            'message_type': 'notification',
            'variables': '["user_name", "action", "proof_type", "verification_link"]'
        }
    ]
    
    try:
        for template_data in templates:
            # Check if template already exists
            existing = MessageTemplate.query.filter_by(name=template_data['name']).first()
            if not existing:
                template = MessageTemplate(**template_data)
                db.session.add(template)
        
        db.session.commit()
        print("✓ Default message templates created")
        
    except Exception as e:
        print(f"✗ Error creating default templates: {e}")
        db.session.rollback()

def create_default_preferences():
    """Create default notification preferences for existing users"""
    
    try:
        from models import User
        
        users = User.query.all()
        created_count = 0
        
        for user in users:
            # Check if preferences already exist
            existing = NotificationPreference.query.filter_by(user_id=user.id).first()
            if not existing:
                preferences = NotificationPreference(
                    user_id=user.id,
                    email_new_user=True,
                    email_job_applications=True,
                    email_verifications=True,
                    email_system_alerts=True,
                    push_critical=True,
                    push_high_priority=False,
                    push_all=False,
                    frequency='immediate'
                )
                db.session.add(preferences)
                created_count += 1
        
        db.session.commit()
        print(f"✓ Created default notification preferences for {created_count} users")
        
    except Exception as e:
        print(f"✗ Error creating default preferences: {e}")
        db.session.rollback()

def create_sample_notifications():
    """Create some sample admin notifications for testing"""
    
    try:
        from models import User
        
        # Get admin user
        admin_user = User.query.filter_by(user_type='admin').first()
        if not admin_user:
            print("⚠️ No admin user found - skipping sample notifications")
            return
        
        notifications = [
            {
                'title': 'New User Registration',
                'message': 'John Doe has registered as a worker and is awaiting profile verification.',
                'type': 'user_registration',
                'priority': 'normal',
                'action_url': '/admin/users',
                'action_text': 'Review User'
            },
            {
                'title': 'Verification Request',
                'message': 'Jane Smith has submitted documents for worker verification.',
                'type': 'verification_request',
                'priority': 'high',
                'action_url': '/admin/verification',
                'action_text': 'Review Documents'
            },
            {
                'title': 'System Alert',
                'message': 'Database backup completed successfully. All systems operational.',
                'type': 'system_alert',
                'priority': 'normal'
            },
            {
                'title': 'Critical: Storage Space Low',
                'message': 'Server storage space is running low. Current usage: 85%. Please consider cleanup.',
                'type': 'system_alert',
                'priority': 'critical'
            }
        ]
        
        for notif_data in notifications:
            notification = AdminNotification(**notif_data)
            db.session.add(notification)
        
        db.session.commit()
        print("✓ Sample admin notifications created")
        
    except Exception as e:
        print(f"✗ Error creating sample notifications: {e}")
        db.session.rollback()

if __name__ == '__main__':
    print("🚀 Starting admin message and notification table creation...")
    
    success = create_tables()
    
    if success:
        print("\n📝 Creating sample data...")
        create_sample_notifications()
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the admin messages page at /admin/messages")
        print("2. Test the admin notifications page at /admin/notifications")
        print("3. Verify all functionality works as expected")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
