from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
import os
import logging
import traceback
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# Import Render configuration
try:
    from render_config import setup_render_environment
    database_url = setup_render_environment()
except ImportError:
    database_url = os.getenv('DATABASE_URL', 'sqlite:///umukozi.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration - support both SQLite (development) and PostgreSQL (production)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Additional production configurations
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB

# Security configurations for production
if os.getenv('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Import models and db
from models import db, User, Worker, Employer, Job, Application, Review, Message, Notification, Payment, WorkerContactAccess

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

# Configure SQLAlchemy logging for database operations
if os.getenv('FLASK_ENV') == 'production':
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)
    
    # Add separate database log file
    db_logger = logging.getLogger('sqlalchemy.engine')
    db_handler = logging.FileHandler('logs/database.log')
    db_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    db_logger.addHandler(db_handler)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logging.error(f"Internal Server Error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    db.session.rollback()
    logging.error(f"Unhandled Exception: {str(e)}")
    logging.error(f"Traceback: {traceback.format_exc()}")
    return render_template('500.html'), 500

def calculate_profile_completion(worker):
    """Calculate worker profile completion percentage"""
    completion = 0
    total_fields = 9  # Total required fields for 100% completion
    
    # Check each required field (10% each)
    if worker.profile_picture:
        completion += 1
    if worker.id_photo:
        completion += 1
    if worker.experience_years is not None:
        completion += 1
    if worker.experience_details:
        completion += 1
    if worker.skills:
        completion += 1
    if worker.reference_name:
        completion += 1
    if worker.reference_phone:
        completion += 1
    if worker.reference_relationship:
        completion += 1
    if worker.national_id_number:
        completion += 1
    
    percentage = (completion / total_fields) * 100
    return round(percentage, 0)

def check_profile_completion(worker):
    """Check if worker profile is complete (100%)"""
    return calculate_profile_completion(worker) >= 100

def require_complete_profile(f):
    """Decorator to require complete worker profile"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.user_type == 'worker':
            worker = Worker.query.filter_by(user_id=current_user.id).first()
            if not check_profile_completion(worker):
                flash('⚠️ Please complete your profile to access this feature.', 'warning')
                return redirect(url_for('worker_complete_profile'))
        return f(*args, **kwargs)
    return decorated_function

def check_payment_status(employer_id, worker_id):
    """Check if employer has paid for access to worker contact"""
    # Check if there's a verified payment for this employer-worker pair
    payment = Payment.query.filter_by(
        employer_id=employer_id, 
        worker_id=worker_id, 
        status='verified'
    ).first()
    
    if payment:
        # Check if access has been granted
        access = WorkerContactAccess.query.filter_by(
            employer_id=employer_id,
            worker_id=worker_id,
            payment_id=payment.id,
            access_granted=True
        ).first()
        return access is not None
    
    return False

def get_worker_contact_info(employer_id, worker_id):
    """Get worker contact info based on payment status"""
    if check_payment_status(employer_id, worker_id):
        # Employer has paid, return actual contact info
        worker = Worker.query.get(worker_id)
        if worker and worker.user:
            return {
                'phone': worker.user.phone,
                'email': worker.user.email,
                'has_access': True
            }
    
    # Employer hasn't paid, return hidden contact info
    return {
        'phone': 'Payment required to view',
        'email': 'Payment required to view',
        'has_access': False
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    """Serve service worker with correct headers"""
    response = app.send_static_file('js/service-worker.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            # Check if user is blocked
            if user.is_blocked:
                flash('❌ Your account has been blocked. Please contact support.', 'error')
                return render_template('login.html')
            
            # Check if user is approved (except admin users)
            if user.user_type != 'admin' and not user.is_approved:
                flash('⏳ Your account is pending approval. Please wait for admin verification.', 'warning')
                return render_template('login.html')
            
            login_user(user)
            # Personalized welcome message
            user_type = "Worker" if user.user_type == 'worker' else "Employer" if user.user_type == 'employer' else "Administrator"
            flash(f'🎉 Welcome back, {user.full_name}! You are logged in as a {user_type}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        user_type = request.form.get('user_type')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            email=email,
            password=hashed_password,
            full_name=full_name,
            phone=phone,
            user_type=user_type
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create profile based on user type
        if user_type == 'worker':
            worker = Worker(user_id=new_user.id)
            db.session.add(worker)
        elif user_type == 'employer':
            employer = Employer(user_id=new_user.id)
            db.session.add(employer)
        
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'worker':
        worker = Worker.query.filter_by(user_id=current_user.id).first()
        # Check if profile is complete
        if not check_profile_completion(worker):
            return redirect(url_for('worker_complete_profile'))
        return render_template('worker_dashboard.html', worker=worker)
    elif current_user.user_type == 'employer':
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        workers = Worker.query.limit(8).all()
        return render_template('employer_dashboard.html', employer=employer, workers=workers)
    elif current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('index'))

# Admin Dashboard Route
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # Get statistics for admin dashboard
    total_workers = Worker.query.count()
    total_employers = Employer.query.count()
    total_jobs = Job.query.count()
    total_applications = Application.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         total_workers=total_workers,
                         total_employers=total_employers,
                         total_jobs=total_jobs,
                         total_applications=total_applications,
                         recent_users=recent_users,
                         recent_jobs=recent_jobs)

# Admin User Management Routes
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    user_type_filter = request.args.get('type', '')
    status_filter = request.args.get('status', '')
    
    query = User.query.filter(User.user_type != 'admin')
    
    if search:
        query = query.filter(
            (User.full_name.contains(search)) | 
            (User.email.contains(search))
        )
    
    if user_type_filter:
        query = query.filter(User.user_type == user_type_filter)
    
    if status_filter == 'pending':
        query = query.filter(User.is_approved == False, User.is_blocked == False)
    elif status_filter == 'approved':
        query = query.filter(User.is_approved == True, User.is_blocked == False)
    elif status_filter == 'blocked':
        query = query.filter(User.is_blocked == True)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Pre-calculate review statistics for each user
    user_stats = {}
    for user in users.items:
        if user.worker:
            # Count applications
            app_count = len(user.worker.applications) if user.worker.applications else 0
            
            # Count reviews and calculate average rating
            reviews = Review.query.filter_by(worker_id=user.worker.id).all()
            review_count = len(reviews)
            avg_rating = None
            if review_count > 0:
                total_rating = sum(r.rating for r in reviews)
                avg_rating = round(total_rating / review_count, 1)
            
            user_stats[user.id] = {
                'applications': app_count,
                'review_count': review_count,
                'avg_rating': avg_rating
            }
        elif user.employer:
            # Count jobs posted
            job_count = len(user.employer.jobs) if user.employer.jobs else 0
            user_stats[user.id] = {
                'jobs': job_count,
                'review_count': 0,
                'avg_rating': None
            }
        else:
            user_stats[user.id] = {
                'applications': 0,
                'review_count': 0,
                'avg_rating': None,
                'jobs': 0
            }
    
    return render_template('admin_users.html', users=users, user_stats=user_stats,
                         search=search, type_filter=user_type_filter, 
                         status_filter=status_filter)

# Admin Workers Management
@app.route('/admin/workers')
@login_required
def admin_workers():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    workers = Worker.query.all()
    verified_workers = Worker.query.filter_by(is_verified=True).all()
    pending_workers = Worker.query.filter_by(is_verified=False).all()
    # Simple suspension check based on user status
    suspended_workers = [w for w in workers if w.user.is_blocked]
    
    # Get other counts for sidebar
    employers = Employer.query.all()
    jobs = Job.query.all()
    pending_verifications = Worker.query.filter_by(is_verified=False).all()
    
    return render_template('admin_workers.html', 
                         workers=workers,
                         verified_workers=verified_workers,
                         pending_workers=pending_workers,
                         suspended_workers=suspended_workers,
                         employers=employers,
                         jobs=jobs,
                         pending_verifications=pending_verifications)

# Admin Employers Management
@app.route('/admin/employers')
@login_required
def admin_employers():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    employers = Employer.query.all()
    verified_employers = Employer.query.filter_by(is_verified=True).all()
    active_jobs = Job.query.filter_by(status='open').all()
    suspended_employers = [e for e in employers if e.user.is_blocked]
    
    # Get other counts for sidebar
    workers = Worker.query.all()
    jobs = Job.query.all()
    pending_verifications = Worker.query.filter_by(is_verified=False).all()
    
    return render_template('admin_employers.html',
                         employers=employers,
                         verified_employers=verified_employers,
                         active_jobs=active_jobs,
                         suspended_employers=suspended_employers,
                         workers=workers,
                         jobs=jobs,
                         pending_verifications=pending_verifications)

# Admin Job Management
@app.route('/admin/jobs')
@login_required
def admin_jobs():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('admin_jobs.html', jobs=jobs)

# Admin Verification Center
@app.route('/admin/verification')
@login_required
def admin_verification():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # Get workers and employers pending verification
    pending_workers = Worker.query.filter_by(is_verified=False).all()
    pending_employers = Employer.query.filter_by(is_verified=False).all()
    
    # Combine them for the verification queue
    pending_verifications = pending_workers + pending_employers
    
    # Stats for the page
    verified_today = Worker.query.filter(Worker.is_verified == True, Worker.updated_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)).all()
    rejected_today = [] # We'd need a separate log for this
    
    total_users = Worker.query.count() + Employer.query.count()
    total_verified = Worker.query.filter_by(is_verified=True).count() + Employer.query.filter_by(is_verified=True).count()
    verification_rate = round((total_verified / total_users * 100), 1) if total_users > 0 else 0
    
    # Sidebar data
    workers = Worker.query.all()
    employers = Employer.query.all()
    jobs = Job.query.all()
    
    return render_template('admin_verification.html',
                         pending_verifications=pending_verifications,
                         verified_today=verified_today,
                         rejected_today=rejected_today,
                         verification_rate=verification_rate,
                         workers=workers,
                         employers=employers,
                         jobs=jobs)

# Admin Verification Actions
@app.route('/admin/verify/<string:user_type>/<int:profile_id>/approve', methods=['POST'])
@login_required
def admin_approve_verification(user_type, profile_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    if user_type == 'worker':
        profile = Worker.query.get_or_404(profile_id)
        profile.is_verified = True
        profile.user.is_approved = True
        profile.user.approved_at = datetime.utcnow()
        profile.user.approved_by = current_user.id
        profile.user.rejection_reason = None
    elif user_type == 'employer':
        profile = Employer.query.get_or_404(profile_id)
        profile.is_verified = True
        profile.user.is_approved = True
        profile.user.approved_at = datetime.utcnow()
        profile.user.approved_by = current_user.id
        profile.user.rejection_reason = None
    
    db.session.commit()
    flash('Verification approved successfully!', 'success')
    return redirect(url_for('admin_verification'))

@app.route('/admin/verify/<string:user_type>/<int:profile_id>/reject', methods=['POST'])
@login_required
def admin_reject_verification(user_type, profile_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    reason = request.form.get('reason', 'Documents did not meet requirements.')
    
    if user_type == 'worker':
        profile = Worker.query.get_or_404(profile_id)
        profile.is_verified = False
        profile.user.is_approved = False
        profile.user.rejection_reason = reason
    elif user_type == 'employer':
        profile = Employer.query.get_or_404(profile_id)
        profile.is_verified = False
        profile.user.is_approved = False
        profile.user.rejection_reason = reason
    
    db.session.commit()
    flash(f'Verification rejected. Reason: {reason}', 'warning')
    return redirect(url_for('admin_verification'))

# Admin Messages
@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # Get sample messages for demonstration
    from datetime import datetime, timedelta
    import random
    
    # Create sample message data
    class MessageSender:
        def __init__(self, id, full_name, email, profile_picture=None):
            self.id = id
            self.full_name = full_name
            self.email = email
            self.profile_picture = profile_picture

    class Message:
        def __init__(self, id, sender, subject, content, message_type, priority, is_read, created_at):
            self.id = id
            self.sender = sender
            self.subject = subject
            self.content = content
            self.type = message_type
            self.priority = priority
            self.is_read = is_read
            self.created_at = created_at

    sample_messages = [
        Message(
            id=1,
            sender=MessageSender(2, 'John Doe', 'john.doe@example.com', None),
            subject='Profile Verification Issue',
            content='Hi Admin, I\'m having trouble uploading my ID document for verification. The system keeps showing an error message saying "Invalid file format" even though I\'m using a JPG file. Can you please help me resolve this issue?',
            message_type='support',
            priority='normal',
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Message(
            id=2,
            sender=MessageSender(3, 'Jane Smith', 'jane.smith@company.com', None),
            subject='Job Posting Approval',
            content='Dear Admin, I have posted a new job for "Senior Software Developer" but it\'s still pending approval. Can you please review and approve it as soon as possible? We need to fill this position urgently.',
            message_type='inquiry',
            priority='high',
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=4)
        ),
        Message(
            id=3,
            sender=MessageSender(4, 'Mike Johnson', 'mike.j@example.com', None),
            subject='Account Suspension Appeal',
            content='My account was suspended without any warning. I believe this is a mistake as I have not violated any terms of service. Please review my account and reactivate it as soon as possible.',
            message_type='appeal',
            priority='urgent',
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=6)
        ),
        Message(
            id=4,
            sender=MessageSender(5, 'Sarah Wilson', 'sarah.w@example.com', None),
            subject='Payment Issue',
            content='Hello, I was charged twice for my monthly subscription. The first charge was on the 1st of the month and another one appeared today. Can you please refund one of the charges?',
            message_type='billing',
            priority='high',
            is_read=True,
            created_at=datetime.utcnow() - timedelta(days=1)
        ),
        Message(
            id=5,
            sender=MessageSender(6, 'Robert Brown', 'robert.b@example.com', None),
            subject='Feature Request',
            content='I would like to suggest adding a feature to allow employers to search for workers based on specific skills and experience levels. This would make the hiring process much more efficient.',
            message_type='feedback',
            priority='normal',
            is_read=True,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
    ]
    
    # Calculate statistics
    total_messages = len(sample_messages)
    unread_messages = len([m for m in sample_messages if not m.is_read])
    urgent_messages = len([m for m in sample_messages if m.priority == 'urgent'])
    sent_today = 3  # Sample data
    
    # Get all users for recipient selection
    all_users = User.query.all()
    
    return render_template('admin_messages.html', 
                         messages=sample_messages,
                         total_messages=total_messages,
                         unread_messages=unread_messages,
                         sent_messages=sent_today,
                         urgent_messages=urgent_messages,
                         all_users=all_users)

@app.route('/admin/messages/send', methods=['POST'])
@login_required
def admin_send_message():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    recipient_type = request.form.get('recipient_type')
    message_type = request.form.get('message_type')
    priority = request.form.get('priority')
    subject = request.form.get('subject')
    content = request.form.get('content')
    send_email = request.form.get('send_email') == 'on'
    
    # In production, this would:
    # 1. Determine recipients based on recipient_type
    # 2. Create message records in database
    # 3. Send email notifications if requested
    # 4. Create notifications for recipients
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('admin_messages'))

# Admin Notifications
@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # Get sample notifications for demonstration
    from datetime import datetime, timedelta
    
    # Create sample notification data
    class Notification:
        def __init__(self, id, title, message, notification_type, priority, is_read, action_url=None, action_text=None, created_at=None):
            self.id = id
            self.title = title
            self.message = message
            self.type = notification_type
            self.priority = priority
            self.is_read = is_read
            self.action_url = action_url
            self.action_text = action_text
            self.created_at = created_at or datetime.utcnow()

    sample_notifications = [
        Notification(
            id=1,
            title='New User Registration',
            message='John Doe has registered as a worker and is awaiting profile verification. The user has completed basic information but needs to upload identification documents.',
            notification_type='user_registration',
            priority='normal',
            is_read=False,
            action_url='/admin/users',
            action_text='Review User',
            created_at=datetime.utcnow() - timedelta(minutes=30)
        ),
        Notification(
            id=2,
            title='Verification Request',
            message='Jane Smith has submitted documents for worker verification including ID card and proof of residence. Documents are ready for review.',
            notification_type='verification_request',
            priority='high',
            is_read=False,
            action_url='/admin/verification',
            action_text='Review Documents',
            created_at=datetime.utcnow() - timedelta(hours=1)
        ),
        Notification(
            id=3,
            title='Job Application Alert',
            message='The position "Senior Software Developer" has received 15 new applications in the last 24 hours. Review applications to find suitable candidates.',
            notification_type='job_application',
            priority='normal',
            is_read=True,
            action_url='/admin/jobs',
            action_text='View Applications',
            created_at=datetime.utcnow() - timedelta(hours=3)
        ),
        Notification(
            id=4,
            title='Critical: Storage Space Low',
            message='Server storage space is running low. Current usage: 85%. Please consider cleanup or upgrade storage plan to avoid service interruption.',
            notification_type='system_alert',
            priority='critical',
            is_read=False,
            action_url='/admin/settings',
            action_text='Manage Storage',
            created_at=datetime.utcnow() - timedelta(hours=6)
        ),
        Notification(
            id=5,
            title='System Maintenance Completed',
            message='Scheduled system maintenance has been completed successfully. All systems are operational and performance has been optimized.',
            notification_type='system_alert',
            priority='normal',
            is_read=True,
            created_at=datetime.utcnow() - timedelta(hours=12)
        ),
        Notification(
            id=6,
            title='Payment Processing Issue',
            message='Multiple payment transactions have failed due to payment gateway issues. Technical team has been notified and working on resolution.',
            notification_type='system_alert',
            priority='high',
            is_read=False,
            action_url='/admin/reports',
            action_text='View Details',
            created_at=datetime.utcnow() - timedelta(days=1)
        ),
        Notification(
            id=7,
            title='New Employer Registration',
            message='TechCorp Inc. has registered as an employer and posted 3 new job positions. Company verification is pending.',
            notification_type='user_registration',
            priority='normal',
            is_read=True,
            action_url='/admin/employers',
            action_text='Review Employer',
            created_at=datetime.utcnow() - timedelta(days=2)
        ),
        Notification(
            id=8,
            title='Database Backup Successful',
            message='Automated database backup has been completed successfully. All data is secured and backup integrity verified.',
            notification_type='system_alert',
            priority='normal',
            is_read=True,
            created_at=datetime.utcnow() - timedelta(days=3)
        )
    ]
    
    # Calculate statistics
    total_notifications = len(sample_notifications)
    unread_count = len([n for n in sample_notifications if not n.is_read])
    critical_count = len([n for n in sample_notifications if n.priority == 'critical'])
    system_count = len([n for n in sample_notifications if n.type == 'system_alert'])
    sent_today = 5  # Sample data
    
    return render_template('admin_notifications.html',
                         notifications=sample_notifications,
                         total_notifications=total_notifications,
                         unread_count=unread_count,
                         sent_today=sent_today,
                         critical_count=critical_count,
                         system_count=system_count)

@app.route('/admin/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def admin_mark_notification_read(notification_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # In production, this would mark the notification as read in database
    return jsonify({'success': True})

@app.route('/admin/notifications/<int:notification_id>/delete', methods=['POST'])
@login_required
def admin_delete_notification(notification_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # In production, this would delete the notification from database
    return jsonify({'success': True})

@app.route('/admin/notifications/mark-all-read', methods=['POST'])
@login_required
def admin_mark_all_notifications_read():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    # In production, this would mark all notifications as read
    return jsonify({'success': True})

# System Management Placeholders
@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('admin_dashboard.html', total_workers=0, total_employers=0, total_jobs=0, total_applications=0, recent_users=[], recent_jobs=[])

@app.route('/admin/settings')
@login_required
def admin_settings():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('admin_settings.html')

@app.route('/admin/logs')
@login_required
def admin_logs():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    return "Activity Logs Placeholder"

@app.route('/admin/moderation')
@login_required
def admin_moderation():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    return "Moderation Placeholder"

@app.route('/admin/user/<int:user_id>/approve', methods=['POST'])
@login_required
def admin_approve_user(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type == 'admin':
        flash('Cannot approve admin users.', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_approved = True
    user.approved_at = datetime.utcnow()
    user.approved_by = current_user.id
    user.rejection_reason = None
    
    db.session.commit()
    flash(f'User {user.full_name} has been approved successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/reject', methods=['POST'])
@login_required
def admin_reject_user(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type == 'admin':
        flash('Cannot reject admin users.', 'error')
        return redirect(url_for('admin_users'))
    
    reason = request.form.get('reason', '')
    user.is_approved = False
    user.rejection_reason = reason
    
    db.session.commit()
    flash(f'User {user.full_name} has been rejected.', 'warning')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/block', methods=['POST'])
@login_required
def admin_block_user(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type == 'admin':
        flash('Cannot block admin users.', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_blocked = True
    user.blocked_at = datetime.utcnow()
    user.blocked_by = current_user.id
    
    db.session.commit()
    flash(f'User {user.full_name} has been blocked.', 'warning')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/unblock', methods=['POST'])
@login_required
def admin_unblock_user(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    user.blocked_at = None
    user.blocked_by = None
    
    db.session.commit()
    flash(f'User {user.full_name} has been unblocked.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type == 'admin':
        flash('Cannot delete admin users.', 'error')
        return redirect(url_for('admin_users'))
    
    # Store name for flash message
    user_name = user.full_name
    
    # Use no_autoflush to prevent premature flushing during deletion
    with db.session.no_autoflush:
        try:
            # Delete reviews related to this user (as worker or employer)
            if user.worker:
                # Delete reviews where this user is the worker
                Review.query.filter_by(worker_id=user.worker.id).delete()
                # Delete worker applications
                Application.query.filter_by(worker_id=user.worker.id).delete()
                db.session.delete(user.worker)
            elif user.employer:
                # Delete reviews where this user is the employer
                Review.query.filter_by(employer_id=user.employer.id).delete()
                # Delete employer jobs and applications
                jobs = Job.query.filter_by(employer_id=user.employer.id).all()
                for job in jobs:
                    # Delete reviews related to this job
                    Review.query.filter_by(application_id=job.id).delete()
                    Application.query.filter_by(job_id=job.id).delete()
                    db.session.delete(job)
                db.session.delete(user.employer)
            
            # Delete messages
            Message.query.filter((Message.sender_id == user_id) | (Message.receiver_id == user_id)).delete()
            
            # Delete notifications
            Notification.query.filter_by(user_id=user_id).delete()
            
            # Delete user
            db.session.delete(user)
            db.session.commit()
            
            flash(f'User {user_name} has been deleted permanently.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'error')
            print(f"Error deleting user {user_id}: {e}")
    
    return redirect(url_for('admin_users'))

# Worker Profile Completion Route
@app.route('/worker/complete-profile', methods=['GET', 'POST'])
@login_required
def worker_complete_profile():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        # Handle file uploads
        profile_picture = request.files.get('profile_picture')
        id_photo = request.files.get('id_photo')
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Save profile picture
        if profile_picture and profile_picture.filename:
            profile_filename = f"profile_{worker.id}_{profile_picture.filename}"
            profile_picture.save(os.path.join(upload_dir, profile_filename))
            worker.profile_picture = profile_filename
        
        # Save ID photo
        if id_photo and id_photo.filename:
            id_filename = f"id_{worker.id}_{id_photo.filename}"
            id_photo.save(os.path.join(upload_dir, id_filename))
            worker.id_photo = id_filename
        
        # Update text fields
        worker.national_id_number = request.form.get('national_id_number')
        worker.experience_years = int(request.form.get('experience_years')) if request.form.get('experience_years') else None
        worker.experience_details = request.form.get('experience_details')
        worker.skills = request.form.get('skills')
        worker.reference_name = request.form.get('reference_name')
        worker.reference_phone = request.form.get('reference_phone')
        worker.reference_relationship = request.form.get('reference_relationship')
        
        db.session.commit()
        
        # Check if profile is now complete
        if check_profile_completion(worker):
            flash('🎉 Congratulations! Your profile is now complete. You can now access all features.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('✅ Profile updated! Please complete all required fields to unlock all features.', 'info')
            return redirect(url_for('worker_complete_profile'))
    
    # Calculate completion percentage
    completion = calculate_profile_completion(worker)
    
    return render_template('worker_complete_profile.html', worker=worker, completion=completion)

# Worker Dashboard Routes
@app.route('/worker/find-jobs')
@login_required
@require_complete_profile
def worker_find_jobs():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    # Get real jobs from database
    jobs = Job.query.filter_by(status='open').order_by(Job.created_at.desc()).all()
    
    return render_template('worker_find_jobs.html', worker=worker, jobs=jobs)

@app.route('/worker/job/<int:job_id>')
@login_required
@require_complete_profile
def worker_job_details(job_id):
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    job = Job.query.get_or_404(job_id)
    
    # Check if worker already applied
    has_applied = Application.query.filter_by(job_id=job_id, worker_id=worker.id).first() is not None or \
                  Application.query.filter_by(job_id=job_id, worker_id=worker.id, status='pending').first() is not None
    
    return render_template('worker_job_details.html', worker=worker, job=job, has_applied=has_applied)

@app.route('/worker/apply/<int:job_id>', methods=['POST', 'GET'])
@login_required
@require_complete_profile
def worker_apply_job(job_id):
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    job = Job.query.get_or_404(job_id)
    
    # Check if worker already applied
    existing_app = Application.query.filter_by(job_id=job_id, worker_id=worker.id).first()
    if existing_app:
        flash('⚠️ You have already applied for this job.', 'warning')
        return redirect(url_for('worker_find_jobs'))
    
    # Create application
    application = Application(
        job_id=job_id,
        worker_id=worker.id,
        status='pending',
        applied_at=datetime.utcnow()
    )
    
    db.session.add(application)
    db.session.commit()
    
    flash('🎉 Application submitted successfully! Good luck.', 'success')
    return redirect(url_for('worker_applications'))

@app.route('/worker/applications')
@login_required
@require_complete_profile
def worker_applications():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    # Get worker's applications
    applications = Application.query.filter_by(worker_id=worker.id).all()
    
    return render_template('worker_applications.html', worker=worker, applications=applications)

@app.route('/worker/activity')
@login_required
@require_complete_profile
def worker_activity():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    # Get real activity data from database
    activities = []
    
    # Add recent applications
    applications = Application.query.filter_by(worker_id=worker.id).order_by(Application.applied_at.desc()).limit(5).all()
    for app in applications:
        activities.append({
            'type': 'application_submitted',
            'message': f'You applied for "{app.job.title}" at {app.job.employer.company_name}',
            'date': app.applied_at.strftime('%Y-%m-%d'),
            'icon': '📋',
            'application_id': app.id
        })
    
    # Add recent messages
    messages = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).limit(3).all()
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        activities.append({
            'type': 'message_received',
            'message': f'New message from {sender.full_name}',
            'date': msg.created_at.strftime('%Y-%m-%d'),
            'icon': '💬',
            'message_id': msg.id
        })
    
    # Add recent reviews
    reviews = Review.query.filter_by(worker_id=worker.id).order_by(Review.created_at.desc()).limit(3).all()
    for review in reviews:
        activities.append({
            'type': 'review_received',
            'message': f'You received a {review.rating}-star review',
            'date': review.created_at.strftime('%Y-%m-%d'),
            'icon': '⭐'
        })
    
    # Sort activities by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Add welcome message if no activities
    if not activities:
        activities.append({
            'type': 'welcome',
            'message': 'Welcome to Umukozi! Start browsing jobs that match your skills',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'icon': '🎉'
        })
    
    return render_template('worker_activity.html', worker=worker, activities=activities)

@app.route('/worker/settings')
@login_required
@require_complete_profile
def worker_settings():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    
    return render_template('worker_settings.html', worker=worker)

# Employer Dashboard Routes
@app.route('/employer/my-jobs')
@login_required
def employer_my_jobs():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get employer's jobs
    jobs = Job.query.filter_by(employer_id=employer.id).order_by(Job.created_at.desc()).all()
    
    return render_template('employer_my_jobs.html', employer=employer, jobs=jobs)

@app.route('/employer/find-workers')
@login_required
def employer_find_workers():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get all workers for now (will add filters later)
    workers = Worker.query.all()
    
    # Check payment status for each worker and hide contact info if not paid
    workers_with_contact_status = []
    for worker in workers:
        contact_info = get_worker_contact_info(employer.id, worker.id)
        workers_with_contact_status.append({
            'worker': worker,
            'has_access': contact_info['has_access'],
            'phone': contact_info['phone'],
            'email': contact_info['email']
        })
    
    return render_template('employer_find_workers.html', employer=employer, workers_with_contact_status=workers_with_contact_status)

@app.route('/employer/applications')
@login_required
def employer_applications():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get all applications for employer's jobs
    applications = []
    for job in employer.jobs:
        applications.extend(job.applications)
    
    # Sort by application date
    applications.sort(key=lambda x: x.applied_at, reverse=True)
    
    # Check payment status for each application's worker
    applications_with_contact_status = []
    for application in applications:
        contact_info = get_worker_contact_info(employer.id, application.worker.id)
        applications_with_contact_status.append({
            'application': application,
            'has_access': contact_info['has_access'],
            'phone': contact_info['phone'],
            'email': contact_info['email']
        })
    
    return render_template('employer_applications.html', employer=employer, applications_with_contact_status=applications_with_contact_status)

@app.route('/employer/activity')
@login_required
def employer_activity():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get real activity data for employer
    activities = []
    
    # Add recent job postings
    jobs = Job.query.filter_by(employer_id=employer.id).order_by(Job.created_at.desc()).limit(5).all()
    for job in jobs:
        activities.append({
            'type': 'job_posted',
            'message': f'You posted a new job: "{job.title}"',
            'date': job.created_at.strftime('%Y-%m-%d'),
            'icon': '📋',
            'job_id': job.id
        })
    
    # Add recent applications received
    applications = []
    for job in employer.jobs:
        applications.extend(job.applications)
    
    applications.sort(key=lambda x: x.applied_at, reverse=True)
    for application in applications[:5]:
        activities.append({
            'type': 'application_received',
            'message': f'New application for "{application.job.title}" from {application.worker.user.full_name}',
            'date': application.applied_at.strftime('%Y-%m-%d'),
            'icon': '📄',
            'application_id': application.id
        })
    
    # Add recent messages sent
    messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.created_at.desc()).limit(3).all()
    for msg in messages:
        receiver = User.query.get(msg.receiver_id)
        activities.append({
            'type': 'message_sent',
            'message': f'You sent a message to {receiver.full_name}',
            'date': msg.created_at.strftime('%Y-%m-%d'),
            'icon': '💬',
            'message_id': msg.id
        })
    
    # Sort activities by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Add welcome message if no activities
    if not activities:
        activities.append({
            'type': 'welcome',
            'message': 'Welcome to Umukozi! Start posting jobs to find the perfect workers.',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'icon': '🎉'
        })
    
    return render_template('employer_activity.html', employer=employer, activities=activities)

@app.route('/employer/settings')
@login_required
def employer_settings():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    return render_template('employer_settings.html', employer=employer)

@app.route('/employer/post-job', methods=['GET', 'POST'])
@login_required
def employer_post_job():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        job_type = request.form.get('job_type')
        
        # Location
        province = request.form.get('province')
        district = request.form.get('district')
        sector = request.form.get('sector')
        cell = request.form.get('cell')
        village = request.form.get('village')
        address_details = request.form.get('address_details')
        
        # Compensation
        salary_type = request.form.get('salary_type')
        salary_amount = request.form.get('salary_amount')
        negotiable = request.form.get('negotiable') == 'on'
        
        # Requirements
        skills_required = request.form.get('skills_required')
        experience_required = request.form.get('experience_required')
        education_required = request.form.get('education_required')
        languages_required = request.form.get('languages_required')
        
        # Schedule
        working_hours = request.form.get('working_hours')
        working_days = request.form.get('working_days')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # Status
        is_urgent = request.form.get('is_urgent') == 'on'
        
        # Validate required fields
        if not title or not description or not job_type:
            flash('Please fill in all required fields (Title, Description, Job Type)', 'error')
            return render_template('employer_post_job.html', employer=employer, form_data=request.form)
        
        # Create new job
        new_job = Job(
            employer_id=employer.id,
            title=title,
            description=description,
            job_type=job_type,
            province=province,
            district=district,
            sector=sector,
            cell=cell,
            village=village,
            address_details=address_details,
            salary_type=salary_type,
            salary_amount=float(salary_amount) if salary_amount else None,
            negotiable=negotiable,
            skills_required=skills_required,
            experience_required=experience_required,
            education_required=education_required,
            languages_required=languages_required,
            working_hours=working_hours,
            working_days=working_days,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
            is_urgent=is_urgent,
            status='open'
        )
        
        # Save to database
        db.session.add(new_job)
        db.session.commit()
        
        flash('🎉 Job posted successfully! Workers will be able to see and apply for your job now.', 'success')
        return redirect(url_for('employer_my_jobs'))
    
    return render_template('employer_post_job.html', employer=employer)

# Profile-specific actions for Workers/Employers templates
@app.route('/admin/worker/<int:worker_id>/<string:action>', methods=['POST'])
@login_required
def admin_worker_action(worker_id, action):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    worker = Worker.query.get_or_404(worker_id)
    user = worker.user
    
    if action == 'verify':
        worker.is_verified = True
        user.is_approved = True
    elif action == 'suspend':
        user.is_blocked = True
    elif action == 'unsuspend':
        user.is_blocked = False
    elif action == 'delete':
        db.session.delete(user)
        db.session.commit()
        flash('Worker deleted successfully.', 'success')
        return redirect(url_for('admin_workers'))
    
    db.session.commit()
    flash(f'Worker action "{action}" completed successfully.', 'success')
    return redirect(url_for('admin_workers'))

@app.route('/admin/employer/<int:employer_id>/<string:action>', methods=['POST'])
@login_required
def admin_employer_action(employer_id, action):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    employer = Employer.query.get_or_404(employer_id)
    user = employer.user
    
    if action == 'verify':
        employer.is_verified = True
        user.is_approved = True
    elif action == 'suspend':
        user.is_blocked = True
    elif action == 'unsuspend':
        user.is_blocked = False
    elif action == 'delete':
        db.session.delete(user)
        db.session.commit()
        flash('Employer deleted successfully.', 'success')
        return redirect(url_for('admin_employers'))
    
    db.session.commit()
    flash(f'Employer action "{action}" completed successfully.', 'success')
    return redirect(url_for('admin_employers'))

@app.route('/logout')
@login_required
def logout():
    user_name = current_user.full_name
    logout_user()
    flash(f'👋 Goodbye, {user_name}! You have been successfully logged out. We hope to see you again soon!', 'info')
    
    # Check if this is an AJAX request for auto-refresh
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'Goodbye, {user_name}! You have been successfully logged out.',
            'redirect': url_for('index')
        })
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
