from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Database instance will be set from app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'worker', 'employer', or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # Admin approval required
    is_blocked = db.Column(db.Boolean, default=False)  # Admin can block users
    approved_at = db.Column(db.DateTime, nullable=True)  # When user was approved
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who approved
    blocked_at = db.Column(db.DateTime, nullable=True)  # When user was blocked
    blocked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who blocked
    rejection_reason = db.Column(db.Text, nullable=True)  # Reason for rejection
    
    # Relationships
    worker = db.relationship('Worker', backref='user', uselist=False)
    employer = db.relationship('Employer', backref='user', uselist=False)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender')
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver')

class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    date_of_birth = db.Column(db.Date)
    national_id = db.Column(db.String(20))
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    
    # Location
    province = db.Column(db.String(50))
    district = db.Column(db.String(50))
    sector = db.Column(db.String(50))
    cell = db.Column(db.String(50))
    village = db.Column(db.String(50))
    
    # Professional Information
    experience_years = db.Column(db.Integer)
    hourly_rate = db.Column(db.Float)
    monthly_rate = db.Column(db.Float)
    availability_status = db.Column(db.String(20), default='available')  # available, busy, unavailable
    
    # Skills and Services
    skills = db.Column(db.Text)  # JSON string of skills
    services_offered = db.Column(db.Text)  # JSON string of services
    
    # Profile Completion Requirements
    id_photo = db.Column(db.String(200))  # Path to ID photo
    experience_details = db.Column(db.Text)  # Detailed experience description
    reference_name = db.Column(db.String(100))  # Reference contact name
    reference_phone = db.Column(db.String(20))  # Reference contact phone
    reference_relationship = db.Column(db.String(50))  # How they know the reference
    national_id_number = db.Column(db.String(30))  # Full national ID number
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_documents = db.Column(db.Text)  # JSON string of document paths
    
    # Statistics
    average_rating = db.Column(db.Float, default=0.0)
    total_jobs_completed = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='worker_profile')
    applications = db.relationship('Application', backref='worker')
    reviews_received = db.relationship('Review', foreign_keys='Review.worker_id', backref='worker')

class Employer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Company/Household Information
    company_name = db.Column(db.String(100))
    household_type = db.Column(db.String(50))  # 'family', 'individual', 'company'
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    
    # Location
    province = db.Column(db.String(50))
    district = db.Column(db.String(50))
    sector = db.Column(db.String(50))
    cell = db.Column(db.String(50))
    village = db.Column(db.String(50))
    address_details = db.Column(db.Text)
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_documents = db.Column(db.Text)  # JSON string of document paths
    
    # Statistics
    average_rating = db.Column(db.Float, default=0.0)
    total_jobs_posted = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='employer_profile')
    jobs = db.relationship('Job', backref='employer')
    reviews_given = db.relationship('Review', foreign_keys='Review.employer_id', backref='employer')

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    
    # Job Details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    job_type = db.Column(db.String(50), nullable=False)  # 'full_time', 'part_time', 'temporary', 'live_in'
    
    # Location
    province = db.Column(db.String(50))
    district = db.Column(db.String(50))
    sector = db.Column(db.String(50))
    cell = db.Column(db.String(50))
    village = db.Column(db.String(50))
    address_details = db.Column(db.Text)
    
    # Compensation
    salary_type = db.Column(db.String(20))  # 'hourly', 'daily', 'weekly', 'monthly'
    salary_amount = db.Column(db.Float)
    negotiable = db.Column(db.Boolean, default=True)
    
    # Requirements
    skills_required = db.Column(db.Text)  # JSON string of required skills
    experience_required = db.Column(db.String(50))
    education_required = db.Column(db.String(100))
    languages_required = db.Column(db.Text)  # JSON string of languages
    
    # Schedule
    working_hours = db.Column(db.String(100))
    working_days = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)  # for temporary jobs
    
    # Status
    status = db.Column(db.String(20), default='open')  # 'open', 'closed', 'filled'
    is_urgent = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='job')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    
    # Application Details
    cover_letter = db.Column(db.Text)
    proposed_salary = db.Column(db.Float)
    available_start_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected', 'withdrawn'
    
    # Timestamps
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='application')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    
    # Review Content
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    
    # Review Categories
    punctuality = db.Column(db.Integer)
    quality_of_work = db.Column(db.Integer)
    communication = db.Column(db.Integer)
    reliability = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Message Content
    content = db.Column(db.Text, nullable=False)
    
    # Metadata
    is_read = db.Column(db.Boolean, default=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')

# Admin Message System
class AdminMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for bulk messages
    subject = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='general')  # announcement, notification, warning, etc.
    priority = db.Column(db.String(20), default='normal')  # normal, high, urgent
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

class AdminNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # user_registration, job_application, verification_request, system_alert
    priority = db.Column(db.String(20), default='normal')  # normal, high, critical
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(500))
    action_text = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For system-generated notifications
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    related_job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    
    # Relationships
    related_user = db.relationship('User', backref='related_notifications')
    related_job = db.relationship('Job', backref='related_notifications')

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), nullable=False)
    variables = db.Column(db.Text)  # JSON string of template variables
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotificationPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Email notification preferences
    email_new_user = db.Column(db.Boolean, default=True)
    email_job_applications = db.Column(db.Boolean, default=True)
    email_verifications = db.Column(db.Boolean, default=True)
    email_system_alerts = db.Column(db.Boolean, default=True)
    
    # Push notification preferences
    push_critical = db.Column(db.Boolean, default=True)
    push_high_priority = db.Column(db.Boolean, default=False)
    push_all = db.Column(db.Boolean, default=False)
    
    # Notification frequency
    frequency = db.Column(db.String(20), default='immediate')  # immediate, hourly, daily, weekly
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='notification_preferences')

# Payment System for Worker Contact Access
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    
    # Payment Details
    amount = db.Column(db.Float, nullable=False, default=10000.00)  # 10,000 FRW
    payment_method = db.Column(db.String(50))  # 'momo', 'airtel', 'bank'
    transaction_id = db.Column(db.String(100))  # Transaction reference
    phone_number = db.Column(db.String(20))  # Payer's phone number
    
    # Status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'verified', 'rejected'
    verification_code = db.Column(db.String(10))  # Code for admin verification
    screenshot_path = db.Column(db.String(200))  # Path to payment screenshot
    
    # Verification
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who verified
    
    # Timestamps
    paid_at = db.Column(db.DateTime)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employer = db.relationship('Employer', backref='payments')
    worker = db.relationship('Worker', backref='contact_payments')
    
    def __repr__(self):
        return f'<Payment {self.id}: Employer {self.employer_id} -> Worker {self.worker_id}>'

# Worker Contact Access Tracking
class WorkerContactAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    
    # Access Details
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)
    access_granted = db.Column(db.Boolean, default=False)
    phone_visible = db.Column(db.Boolean, default=False)
    email_visible = db.Column(db.Boolean, default=False)
    whatsapp_accessible = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    payment = db.relationship('Payment', backref='contact_access')
    employer = db.relationship('Employer', backref='contact_access_records')
    worker = db.relationship('Worker', backref='contact_access_records')

    def __repr__(self):
        return f'<WorkerContactAccess {self.id}: Employer {self.employer_id} -> Worker {self.worker_id}>'

# Employment Relationship Tracking
class Employment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)

    # Employment Details
    status = db.Column(db.String(20), default='contacted')  # contacted, interviewing, hired, active, completed, terminated
    job_title = db.Column(db.String(100))
    salary = db.Column(db.Float)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)

    # Status Tracking
    contacted_at = db.Column(db.DateTime, default=datetime.utcnow)
    interviewed_at = db.Column(db.DateTime, nullable=True)
    hired_at = db.Column(db.DateTime, nullable=True)
    terminated_at = db.Column(db.DateTime, nullable=True)
    termination_reason = db.Column(db.Text, nullable=True)

    # Notes
    employer_notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employer = db.relationship('Employer', backref='employment_records')
    worker = db.relationship('Worker', backref='employment_records')

    def __repr__(self):
        return f'<Employment {self.id}: Employer {self.employer_id} -> Worker {self.worker_id} ({self.status})>'

    @property
    def is_active(self):
        return self.status in ['hired', 'active']

    @property
    def duration_days(self):
        if self.start_date:
            end = self.end_date or datetime.utcnow().date()
            return (end - self.start_date).days
        return 0

class EmailConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # SMTP Configuration
    smtp_server = db.Column(db.String(200), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_encryption = db.Column(db.String(10), nullable=False, default='tls')  # 'tls', 'ssl', 'none'
    smtp_username = db.Column(db.String(200), nullable=False)
    smtp_password = db.Column(db.String(200), nullable=False)

    # Email Settings
    from_name = db.Column(db.String(100), nullable=False, default='Umukozi')
    reply_to = db.Column(db.String(200))
    
    # Email Features
    enable_notifications = db.Column(db.Boolean, default=True)
    enable_welcome_emails = db.Column(db.Boolean, default=True)
    enable_job_alerts = db.Column(db.Boolean, default=True)
    enable_verification_emails = db.Column(db.Boolean, default=True)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    creator = db.relationship('User', backref='email_configs_created')
    def __repr__(self):
        return f'<WorkerContactAccess {self.id}: {self.employer_id} -> {self.worker_id}>'
