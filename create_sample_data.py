#!/usr/bin/env python3
"""
Create sample real data in the database for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Worker, Employer, Job, Application, Review, Message
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def create_sample_data():
    """Create sample real data in the database"""
    print("🌱 Creating Sample Real Data...")
    
    with app.app_context():
        try:
            # Create additional sample employers and jobs
            employers_data = [
                {
                    'email': 'employer1@umukozi.rw',
                    'full_name': 'Jean Mugisha',
                    'phone': '+250788111111',
                    'company_name': 'Mugisha Family',
                    'household_type': 'family',
                    'district': 'Kigali',
                    'sector': 'Nyarugenge'
                },
                {
                    'email': 'employer2@umukozi.rw',
                    'full_name': 'Marie Uwimana',
                    'phone': '+250788222222',
                    'company_name': 'Uwimana Household',
                    'household_type': 'family',
                    'district': 'Kigali',
                    'sector': 'Kicukiro'
                },
                {
                    'email': 'employer3@umukozi.rw',
                    'full_name': 'Paul Niyonzima',
                    'phone': '+250788333333',
                    'company_name': 'Niyonzima Home',
                    'household_type': 'family',
                    'district': 'Kigali',
                    'sector': 'Gasabo'
                }
            ]
            
            for emp_data in employers_data:
                # Check if employer already exists
                existing_user = User.query.filter_by(email=emp_data['email']).first()
                if existing_user:
                    print(f"   Employer {emp_data['email']} already exists, skipping...")
                    continue
                
                # Create employer user
                hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')
                employer_user = User(
                    email=emp_data['email'],
                    password=hashed_password,
                    full_name=emp_data['full_name'],
                    phone=emp_data['phone'],
                    user_type='employer'
                )
                
                db.session.add(employer_user)
                db.session.commit()
                
                # Create employer profile
                employer = Employer(
                    user_id=employer_user.id,
                    company_name=emp_data['company_name'],
                    household_type=emp_data['household_type'],
                    bio=f'Looking for reliable domestic helpers for our {emp_data["household_type"]}.',
                    district=emp_data['district'],
                    sector=emp_data['sector'],
                    is_verified=True
                )
                
                db.session.add(employer)
                db.session.commit()
                print(f"   ✅ Created employer: {emp_data['full_name']}")
            
            # Create sample jobs
            jobs_data = [
                {
                    'title': 'House Helper Needed',
                    'description': 'Looking for an experienced house helper for daily cleaning, cooking, and general household management.',
                    'district': 'Kigali',
                    'sector': 'Nyarugenge',
                    'salary_amount': 50000,
                    'salary_type': 'monthly',
                    'job_type': 'full_time',
                    'is_urgent': False,
                    'employer_email': 'employer1@umukozi.rw'
                },
                {
                    'title': 'Childcare Provider',
                    'description': 'Need a caring nanny for 2 children aged 3 and 5 years. Experience with early childhood education preferred.',
                    'district': 'Kigali',
                    'sector': 'Kicukiro',
                    'salary_amount': 60000,
                    'salary_type': 'monthly',
                    'job_type': 'live_in',
                    'is_urgent': True,
                    'employer_email': 'employer2@umukozi.rw'
                },
                {
                    'title': 'Part-time Cleaner',
                    'description': 'Weekend cleaning service for a 3-bedroom house. Must be thorough and reliable.',
                    'district': 'Kigali',
                    'sector': 'Gasabo',
                    'salary_amount': 2000,
                    'salary_type': 'daily',
                    'job_type': 'part_time',
                    'is_urgent': False,
                    'employer_email': 'employer3@umukozi.rw'
                },
                {
                    'title': 'Cook Needed',
                    'description': 'Experienced cook needed for family of 4. Must know both local and international cuisine.',
                    'district': 'Kigali',
                    'sector': 'Nyarugenge',
                    'salary_amount': 45000,
                    'salary_type': 'monthly',
                    'job_type': 'full_time',
                    'is_urgent': False,
                    'employer_email': 'employer1@umukozi.rw'
                },
                {
                    'title': 'Elderly Care Assistant',
                    'description': 'Looking for a compassionate caregiver for elderly person. Medical background a plus.',
                    'district': 'Kigali',
                    'sector': 'Kicukiro',
                    'salary_amount': 55000,
                    'salary_type': 'monthly',
                    'job_type': 'live_in',
                    'is_urgent': True,
                    'employer_email': 'employer2@umukozi.rw'
                }
            ]
            
            for job_data in jobs_data:
                # Find employer
                employer_user = User.query.filter_by(email=job_data['employer_email']).first()
                if not employer_user:
                    print(f"   ⚠️ Employer {job_data['employer_email']} not found, skipping job...")
                    continue
                
                employer = Employer.query.filter_by(user_id=employer_user.id).first()
                
                # Create job
                job = Job(
                    employer_id=employer.id,
                    title=job_data['title'],
                    description=job_data['description'],
                    district=job_data['district'],
                    sector=job_data['sector'],
                    salary_amount=job_data['salary_amount'],
                    salary_type=job_data['salary_type'],
                    job_type=job_data['job_type'],
                    is_urgent=job_data['is_urgent'],
                    status='open',
                    created_at=datetime.now() - timedelta(days=len(jobs_data) - jobs_data.index(job_data))
                )
                
                db.session.add(job)
                db.session.commit()
                print(f"   ✅ Created job: {job_data['title']}")
            
            # Create sample applications for the test worker
            test_worker = Worker.query.filter_by(user_id=1).first()  # Assuming worker ID 1 exists
            if test_worker:
                jobs = Job.query.limit(3).all()  # Get first 3 jobs
                
                for i, job in enumerate(jobs):
                    # Check if application already exists
                    existing_app = Application.query.filter_by(
                        worker_id=test_worker.id, 
                        job_id=job.id
                    ).first()
                    
                    if existing_app:
                        print(f"   Application for job {job.title} already exists, skipping...")
                        continue
                    
                    application = Application(
                        worker_id=test_worker.id,
                        job_id=job.id,
                        cover_letter=f'I am very interested in the {job.title} position. I have relevant experience and believe I would be a great fit for this role.',
                        status='pending' if i == 0 else 'accepted' if i == 1 else 'rejected',
                        applied_at=datetime.now() - timedelta(days=i+1)
                    )
                    
                    db.session.add(application)
                    db.session.commit()
                    print(f"   ✅ Created application for: {job.title}")
            
            # Create sample reviews (linked to applications)
            if test_worker:
                applications = Application.query.filter_by(worker_id=test_worker.id).limit(2).all()
                for i, application in enumerate(applications):
                    review = Review(
                        application_id=application.id,
                        worker_id=test_worker.id,
                        employer_id=application.job.employer_id,
                        rating=5 - i,  # 5, 4 rating
                        comment=f'Excellent work! Very professional and reliable.' if i == 0 else 'Good work, punctual and skilled.',
                        punctuality=5 - i,
                        quality_of_work=5 - i,
                        communication=5 - i,
                        reliability=5 - i,
                        created_at=datetime.now() - timedelta(days=i+5)
                    )
                    
                    db.session.add(review)
                    db.session.commit()
                    print(f"   ✅ Created review for worker (application {application.id})")
            
            # Create sample messages
            if test_worker:
                employers = Employer.query.limit(2).all()
                messages_data = [
                    'Hello, I saw your application and would like to schedule an interview.',
                    'Your profile looks great! Are you available for a part-time position?',
                    'Thank you for your interest. We will review your application and get back to you soon.'
                ]
                
                for i, employer in enumerate(employers):
                    message = Message(
                        sender_id=employer.user_id,
                        receiver_id=test_worker.user_id,
                        content=messages_data[i],
                        created_at=datetime.now() - timedelta(days=i+2)
                    )
                    
                    db.session.add(message)
                    db.session.commit()
                    print(f"   ✅ Created message from {employer.company_name}")
            
            db.session.commit()
            print("\n🎉 Sample data created successfully!")
            
            # Show summary
            print("\n📊 Database Summary:")
            print(f"   Users: {User.query.count()}")
            print(f"   Workers: {Worker.query.count()}")
            print(f"   Employers: {Employer.query.count()}")
            print(f"   Jobs: {Job.query.count()}")
            print(f"   Applications: {Application.query.count()}")
            print(f"   Reviews: {Review.query.count()}")
            print(f"   Messages: {Message.query.count()}")
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_sample_data()
