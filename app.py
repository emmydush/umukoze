from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

from datetime import datetime
import os
import logging
import traceback
import time
from functools import wraps
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

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
from models import db, User, Worker, Employer, Job, Application, Review, Message, Notification, Payment, WorkerContactAccess, EmailConfig, Employment
from translations import TRANSLATIONS

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Notification Context Processor
@app.context_processor
def inject_globals():
    # Translation helper
    def translate(key, **kwargs):
        lang = session.get('lang', 'en')
        text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    # Notifications helper
    notifs = []
    unread_count = 0
    if current_user.is_authenticated:
        # Get last 5 notifications for the current user
        notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        
    return dict(_=translate, notifs=notifs, unread_count=unread_count)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['en', 'fr', 'rw']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# Notification Routes
@app.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify(success=True)

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return jsonify(success=True)

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

def allowed_file(filename, allowed_extensions):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def check_password_strength(password):
    """
    Validate password strength.
    Requires:
    - Min length 8
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    import re
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[ !@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, "Strong password."

def get_connection_price(employer_id):
    """Determine connection price based on employer's payment history"""
    # Check if employer has any verified payments before
    previous_payments = Payment.query.filter_by(
        employer_id=employer_id,
        status='verified'
    ).count()
    
    if previous_payments == 0:
        # First time connection
        return 10000.00, "first_time"
    else:
        # Subsequent connection
        return 5000.00, "subsequent"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
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
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        # Check password strength
        is_strong, msg = check_password_strength(password)
        if not is_strong:
            flash(f'❌ {msg}', 'error')
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
        
        # Send email notification to admin about new registration
        # send_user_registration_notification(new_user)
        
        # Add welcome notification
        welcome_notif = Notification(
            user_id=new_user.id,
            message=f"Welcome to Umukozi, {full_name}! Complete your profile to start finding jobs." if user_type == 'worker' else f"Welcome to Umukozi, {full_name}! Post your first job to find workers."
        )
        db.session.add(welcome_notif)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'worker':
        worker = Worker.query.filter_by(user_id=current_user.id).first()
        if not worker:
            worker = Worker(user_id=current_user.id)
            db.session.add(worker)
            db.session.commit()
            
        # Check if profile is complete
        if not check_profile_completion(worker):
            return redirect(url_for('worker_complete_profile'))
        return render_template('worker_dashboard.html', worker=worker)
    elif current_user.user_type == 'employer':
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        if not employer:
            employer = Employer(user_id=current_user.id)
            db.session.add(employer)
            db.session.commit()
            
        # Show verified and available workers first, then others
        workers = Worker.query.filter(
            Worker.is_verified == True,
            Worker.availability_status == 'available'
        ).limit(8).all()
        
        # If not enough verified available workers, add more workers
        if len(workers) < 8:
            additional_workers = Worker.query.filter(
                Worker.id.notin_([w.id for w in workers])
            ).limit(8 - len(workers)).all()
            workers.extend(additional_workers)
        
        return render_template('employer_dashboard.html', employer=employer, workers=workers)
    elif current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('index'))

@app.route('/worker/profile/<int:worker_id>')
@login_required
def worker_profile(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    
    # Get contact info if user is employer and has access
    contact_info = None
    if current_user.user_type == 'employer':
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        contact_info = get_worker_contact_info(employer.id, worker.id)
    
    return render_template('worker_profile.html', worker=worker, contact_info=contact_info)

@app.route('/employer/worker-contact/<int:worker_id>')
@login_required
def employer_worker_contact(worker_id):
    if current_user.user_type != 'employer':
        return jsonify({'error': 'Access denied'}), 403
    
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    worker = Worker.query.get_or_404(worker_id)
    
    contact_info = get_worker_contact_info(employer.id, worker.id)
    contact_info['user_id'] = worker.user.id
    return jsonify(contact_info)

@app.route('/employer/payment/<int:worker_id>/pricing')
@login_required
def get_payment_pricing(worker_id):
    """Get pricing information for worker connection"""
    if current_user.user_type != 'employer':
        return jsonify({'error': 'Access denied'}), 403
    
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    if not employer:
        return jsonify({'error': 'Employer profile not found'}), 404
    
    amount, pricing_tier = get_connection_price(employer.id)
    
    return jsonify({
        'amount': amount,
        'pricing_tier': pricing_tier,
        'currency': 'FRW',
        'formatted_amount': f"RWF {int(amount):,}".replace(',', ' ')
    })

@app.route('/employer/payment/<int:worker_id>/submit', methods=['POST'])
@login_required
def submit_payment(worker_id):
    try:
        if current_user.user_type != 'employer':
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        if not employer:
            return jsonify({'success': False, 'error': 'Employer profile not found'}), 404
            
        worker = Worker.query.get_or_404(worker_id)
        
        # Check if payment already exists
        existing_payment = Payment.query.filter_by(
            employer_id=employer.id,
            worker_id=worker.id
        ).first()
        
        if existing_payment and existing_payment.status != 'rejected':
            return jsonify({'success': False, 'error': 'Payment already exists'}), 400
        
        # Ensure upload folder exists
        upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        # Determine pricing based on employer's payment history
        amount, pricing_tier = get_connection_price(employer.id)
        
        # Create new payment record
        payment_method = request.form.get('payment_method', 'momo')
        transaction_id = request.form.get('transaction_id', '')
        phone_number = request.form.get('phone_number', '')
        
        payment = Payment(
            employer_id=employer.id,
            worker_id=worker.id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            phone_number=phone_number,
            status='pending',
            paid_at=datetime.utcnow()
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Handle screenshot upload
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            if file and file.filename and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                try:
                    filename = secure_filename(f"payment_{payment.id}_{int(time.time())}.{file.filename.split('.')[-1]}")
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    
                    payment.screenshot_path = filename
                    db.session.commit()
                except Exception as e:
                    print(f"Error saving screenshot: {e}")
                    # Continue without screenshot - payment is still valid
        
        # Send notification to admin
        try:
            admin_users = User.query.filter_by(user_type='admin', is_active=True).all()
            for admin in admin_users:
                notif = Notification(
                    user_id=admin.id,
                    message=f"New payment submitted: {employer.user.full_name} for {worker.user.full_name}",
                    notification_type='new_payment'
                )
                db.session.add(notif)
            
            db.session.commit()
        except Exception as e:
            print(f"Error sending notifications: {e}")
            # Continue - payment is still saved
        
        return jsonify({
            'success': True,
            'message': 'Payment submitted successfully. Please wait for admin verification.',
            'payment_id': payment.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Payment submission error: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

# Admin Index Route - Redirects to dashboard
@app.route('/admin')
@login_required
def admin_index():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    return redirect(url_for('admin_dashboard'))

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
    
    # Send email notification to user about approval
    # send_user_approval_notification(profile.user)
    
    # Add in-app notification
    approval_notif = Notification(
        user_id=profile.user.id,
        message="Congratulations! Your profile has been verified and approved by the admin."
    )
    db.session.add(approval_notif)
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
    
    # Send email notification to user about rejection
    # send_user_rejection_notification(profile.user, reason)
    
    flash(f'Verification rejected. Reason: {reason}', 'warning')
    return redirect(url_for('admin_verification'))

# User Messages System
@app.route('/messages')
@app.route('/messages/<int:user_id>')
@login_required
def messages(user_id=None):
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_messages'))
    
    from sqlalchemy import or_, desc, and_
    import datetime
    
    # Fetch all users we have messages with
    stmt = db.session.query(Message).filter(
        or_(Message.sender_id == current_user.id, Message.receiver_id == current_user.id)
    ).order_by(desc(Message.created_at))
    all_msgs = stmt.all()

    # Get distinct users
    conversations = []
    seen_users = set()
    
    for msg in all_msgs:
        other_user_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if other_user_id not in seen_users:
            other_user = User.query.get(other_user_id)
            if other_user:
                conversations.append({
                    'other_user': other_user,
                    'latest_msg': msg
                })
            seen_users.add(other_user_id)
            
    active_user = None
    active_messages = []
    
    if user_id:
        active_user = User.query.get_or_404(user_id)
        # Mark read
        unread_msgs = Message.query.filter_by(sender_id=user_id, receiver_id=current_user.id, is_read=False).all()
        for u_msg in unread_msgs:
            u_msg.is_read = True
            u_msg.read_at = datetime.datetime.utcnow()
        if unread_msgs:
            db.session.commit()
            
        active_messages = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.created_at.asc()).all()
    
    # Pass worker / employer side info if needed for sidebars
    employer = None
    worker = None
    if current_user.user_type == 'employer':
        employer = Employer.query.filter_by(user_id=current_user.id).first()
    elif current_user.user_type == 'worker':
        worker = Worker.query.filter_by(user_id=current_user.id).first()
        
    return render_template('user_messages.html', 
                            conversations=conversations, 
                            active_user=active_user, 
                            active_messages=active_messages,
                            current_time=datetime.datetime.utcnow(),
                            employer=employer, worker=worker)

@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form.get('receiver_id', type=int)
    content = request.form.get('content')
    
    if not receiver_id or not content:
        flash('Message cannot be empty.', 'error')
        return redirect(request.referrer or url_for('messages'))
        
    msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    
    notif = Notification(user_id=receiver_id, message=f'New message from {current_user.full_name}')
    db.session.add(notif)
    
    db.session.commit()
    return redirect(url_for('messages', user_id=receiver_id))

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
    
    # Send email notification to user about rejection
    # send_user_rejection_notification(user, reason)
    
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

@app.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.user_type == 'admin' and user.id != current_user.id:
        flash('Cannot reset other admin passwords.', 'error')
        return redirect(url_for('admin_users'))
    
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not new_password:
        flash('Password cannot be empty.', 'error')
        return redirect(url_for('admin_users'))
    
    # Check password strength
    is_strong, msg = check_password_strength(new_password)
    if not is_strong:
        flash(f'❌ {msg}', 'error')
        return redirect(url_for('admin_users'))
    
    if new_password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        # Reset password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash(f'Password for {user.full_name} has been reset successfully.', 'success')
        
        # Log the action
        print(f"Admin {current_user.full_name} reset password for user {user.full_name} (ID: {user.id})")
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
    
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

# Admin Payment Management Routes
@app.route('/admin/payments')
@login_required
def admin_payments():
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Payment.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if search:
        query = query.join(Employer).join(Worker).join(User, Employer.user).join(User, Worker.user, aliased=True).filter(
            User.full_name.contains(search) | User.email.contains(search)
        )
    
    payments = query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin_payments.html', payments=payments, 
                         status_filter=status_filter, search=search)

@app.route('/admin/payment/<int:payment_id>/verify', methods=['POST'])
@login_required
def admin_verify_payment(payment_id):
    try:
        if current_user.user_type != 'admin':
            return redirect(url_for('dashboard'))
        
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'pending':
            flash('Payment has already been processed.', 'warning')
            return redirect(url_for('admin_payments'))
        
        payment.status = 'verified'
        payment.verified_at = datetime.utcnow()
        payment.verified_by = current_user.id
        
        # Grant contact access
        existing_access = WorkerContactAccess.query.filter_by(
            employer_id=payment.employer_id,
            worker_id=payment.worker_id,
            payment_id=payment.id
        ).first()
        
        if not existing_access:
            access = WorkerContactAccess(
                employer_id=payment.employer_id,
                worker_id=payment.worker_id,
                payment_id=payment.id,
                access_granted=True,
                granted_at=datetime.utcnow()
            )
            db.session.add(access)
        
        db.session.commit()
        
        # Send notification to employer
        try:
            employer = Employer.query.get(payment.employer_id)
            if employer and employer.user:
                notif = Notification(
                    user_id=employer.user.id,
                    message=f"Your payment for worker contact has been verified. You can now view their contact information.",
                    notification_type='payment_verified'
                )
                db.session.add(notif)
                db.session.commit()
        except Exception as e:
            print(f"Error sending notification: {e}")
            # Continue - payment is still verified
        
        flash('Payment verified successfully. Contact access granted.', 'success')
        return redirect(url_for('admin_payments'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Payment verification error: {e}")
        flash(f'Error verifying payment: {str(e)}', 'error')
        return redirect(url_for('admin_payments'))

@app.route('/admin/payment/<int:payment_id>/reject', methods=['POST'])
@login_required
def admin_reject_payment(payment_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    payment = Payment.query.get_or_404(payment_id)
    reason = request.form.get('reason', 'Payment could not be verified')
    
    if payment.status != 'pending':
        flash('Payment has already been processed.', 'warning')
        return redirect(url_for('admin_payments'))
    
    payment.status = 'rejected'
    payment.verified_at = datetime.utcnow()
    payment.verified_by = current_user.id
    
    db.session.commit()
    
    # Send notification to employer
    employer = Employer.query.get(payment.employer_id)
    if employer and employer.user:
        notif = Notification(
            user_id=employer.user.id,
            message=f"Your payment was rejected: {reason}",
            notification_type='payment_rejected'
        )
        db.session.add(notif)
        db.session.commit()
    
    flash('Payment rejected.', 'warning')
    return redirect(url_for('admin_payments'))

@app.route('/admin/payment/<int:payment_id>/upload-screenshot', methods=['POST'])
@login_required
def admin_upload_payment_screenshot(payment_id):
    if current_user.user_type != 'admin':
        return redirect(url_for('dashboard'))
    
    payment = Payment.query.get_or_404(payment_id)
    
    if 'screenshot' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('admin_payments'))
    
    file = request.files['screenshot']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_payments'))
    
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
        filename = secure_filename(f"payment_{payment.id}_{int(time.time())}.{file.filename.split('.')[-1]}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        payment.screenshot_path = filename
        db.session.commit()
        
        flash('Screenshot uploaded successfully.', 'success')
    else:
        flash('Invalid file type. Please upload PNG, JPG, or GIF.', 'error')
    
    return redirect(url_for('admin_payments'))

# Worker Profile Completion Route
@app.route('/worker/complete-profile', methods=['GET', 'POST'])
@login_required
def worker_complete_profile():
    if current_user.user_type != 'worker':
        return redirect(url_for('dashboard'))
    worker = Worker.query.filter_by(user_id=current_user.id).first()
    if not worker:
        worker = Worker(user_id=current_user.id)
        db.session.add(worker)
        db.session.commit()
    
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
    
    # Send email notification to employer and admin about new job application
    # send_job_application_notification(application)
    
    # Notify employer in-app
    employer_notif = Notification(
        user_id=job.employer.user.id,
        message=f"New Application: {current_user.full_name} applied for your job '{job.title}'."
    )
    db.session.add(employer_notif)
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


@app.route('/employer/hired-workers')
@login_required
def employer_hired_workers():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get all employment records for this employer
    employments = Employment.query.filter_by(employer_id=employer.id).order_by(Employment.created_at.desc()).all()
    
    # Calculate statistics
    total_workers = len(employments)
    active_workers = len([e for e in employments if e.is_active])
    contacted_workers = len([e for e in employments if e.status == 'contacted'])
    interviewing_workers = len([e for e in employments if e.status == 'interviewing'])
    hired_workers = len([e for e in employments if e.status == 'hired'])
    
    return render_template('employer_hired_workers.html', 
                         employer=employer, 
                         employments=employments,
                         total_workers=total_workers,
                         active_workers=active_workers,
                         contacted_workers=contacted_workers,
                         interviewing_workers=interviewing_workers,
                         hired_workers=hired_workers)

@app.route('/employer/employment/<int:employment_id>/details')
@login_required
def employment_details(employment_id):
    if current_user.user_type != 'employer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        employment = Employment.query.get_or_404(employment_id)
        
        # Verify this employment belongs to the employer
        if employment.employer_id != employer.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'id': employment.id,
            'status': employment.status,
            'job_title': employment.job_title,
            'salary': employment.salary,
            'start_date': employment.start_date.isoformat() if employment.start_date else None,
            'end_date': employment.end_date.isoformat() if employment.end_date else None,
            'duration_days': employment.duration_days,
            'employer_notes': employment.employer_notes,
            'contacted_at': employment.contacted_at.isoformat(),
            'interviewed_at': employment.interviewed_at.isoformat() if employment.interviewed_at else None,
            'hired_at': employment.hired_at.isoformat() if employment.hired_at else None,
            'worker': {
                'id': employment.worker.id,
                'name': employment.worker.user.full_name,
                'phone': employment.worker.user.phone,
                'email': employment.worker.user.email,
                'profile_picture': employment.worker.profile_picture,
                'district': employment.worker.district,
                'skills': employment.worker.skills
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/employer/employment/<int:employment_id>/update', methods=['POST'])
@login_required
def update_employment(employment_id):
    if current_user.user_type != 'employer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        employment = Employment.query.get_or_404(employment_id)
        
        # Verify this employment belongs to the employer
        if employment.employer_id != employer.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Update employment details
        old_status = employment.status
        employment.status = request.form.get('status')
        employment.job_title = request.form.get('job_title')
        employment.salary = float(request.form.get('salary')) if request.form.get('salary') else None
        employment.employer_notes = request.form.get('employer_notes')
        
        # Handle start date
        if request.form.get('start_date'):
            employment.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        
        # Update status timestamps
        now = datetime.utcnow()
        if old_status != employment.status:
            if employment.status == 'interviewing' and not employment.interviewed_at:
                employment.interviewed_at = now
            elif employment.status == 'hired' and not employment.hired_at:
                employment.hired_at = now
            elif employment.status == 'terminated' and not employment.terminated_at:
                employment.terminated_at = now
                employment.termination_reason = request.form.get('termination_reason', '')
        
        employment.updated_at = now
        
        # Update worker availability based on status
        if employment.status in ['hired', 'active']:
            employment.worker.availability_status = 'busy'
        elif employment.status in ['completed', 'terminated']:
            employment.worker.availability_status = 'available'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Employment status updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/employer/worker/<int:worker_id>/hire', methods=['POST'])
@login_required
def hire_worker(worker_id):
    if current_user.user_type != 'employer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        worker = Worker.query.get_or_404(worker_id)
        
        # Check if employment already exists
        existing_employment = Employment.query.filter_by(
            employer_id=employer.id, 
            worker_id=worker.id
        ).first()
        
        if existing_employment:
            return jsonify({'success': False, 'error': 'Worker already in your employment list'}), 400
        
        # Create new employment record
        employment = Employment(
            employer_id=employer.id,
            worker_id=worker.id,
            status='contacted',
            job_title=request.form.get('job_title'),
            salary=float(request.form.get('salary')) if request.form.get('salary') else None,
            employer_notes=request.form.get('notes')
        )
        
        db.session.add(employment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{worker.user.full_name} has been added to your hired workers list'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/employer/application/<int:application_id>/accept', methods=['POST'])
@login_required
def accept_application(application_id):
    if current_user.user_type != 'employer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        application = Application.query.get_or_404(application_id)
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        
        # Verify this application belongs to the employer's job
        if application.job.employer_id != employer.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Update application status
        application.status = 'accepted'
        application.updated_at = datetime.utcnow()
        
        # Notify worker
        worker_notif = Notification(
            user_id=application.worker.user.id,
            message=f"Application Accepted! Your application for '{application.job.title}' has been accepted."
        )
        db.session.add(worker_notif)
        
        # Update worker availability status to 'busy'
        worker = application.worker
        worker.availability_status = 'busy'
        
        # Update job status to 'filled'
        application.job.status = 'filled'
        
        db.session.commit()
        
        # Send email notification to admin
        # send_admin_hiring_notification(application, 'accepted')
        
        return jsonify({
            'success': True, 
            'message': f'Application accepted. {worker.user.full_name} is now marked as busy.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/employer/application/<int:application_id>/reject', methods=['POST'])
@login_required
def reject_application(application_id):
    if current_user.user_type != 'employer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        application = Application.query.get_or_404(application_id)
        employer = Employer.query.filter_by(user_id=current_user.id).first()
        
        # Verify this application belongs to the employer's job
        if application.job.employer_id != employer.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Update application status
        application.status = 'rejected'
        application.updated_at = datetime.utcnow()
        
        # Notify worker
        worker_notif = Notification(
            user_id=application.worker.user.id,
            message=f"Application Status: Your application for '{application.job.title}' was reviewed."
        )
        db.session.add(worker_notif)
        
        db.session.commit()
        
        # Send email notification to admin
        # send_admin_hiring_notification(application, 'rejected')
        
        return jsonify({
            'success': True, 
            'message': 'Application rejected successfully.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

def send_admin_hiring_notification(application, action):
    """Send email notification to admin when a worker is hired/rejected"""
    try:
        # Check if email notifications are enabled
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if not email_config_db or not email_config_db.enable_notifications:
            return
        
        # Get admin users
        admin_users = User.query.filter_by(user_type='admin').all()
        
        if not admin_users:
            return
        
        # Get email configuration from database
        smtp_server = email_config_db.smtp_server
        smtp_port = int(email_config_db.smtp_port)
        smtp_username = email_config_db.smtp_username
        smtp_password = email_config_db.smtp_password
        smtp_encryption = email_config_db.smtp_encryption
        from_name = email_config_db.from_name
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create email content
        worker = application.worker
        employer = application.job.employer
        job = application.job
        
        subject = f"Worker {action.title()}: {worker.user.full_name}"
        
        if action == 'accepted':
            body = f"""
Dear Admin,

A worker has been hired on the Umukozi platform:

Worker Details:
- Name: {worker.user.full_name}
- Email: {worker.user.email}
- Phone: {worker.user.phone}
- District: {worker.district or 'Not specified'}

Employer Details:
- Name: {employer.user.full_name}
- Email: {employer.user.email}
- Company: {employer.company_name}

Job Details:
- Title: {job.title}
- Type: {job.job_type}
- Location: {job.district}

The worker's availability status has been automatically updated to 'busy'.
You can update the worker's status from the admin dashboard if needed.

Best regards,
Umukozi System
            """
        else:  # rejected
            body = f"""
Dear Admin,

A worker application has been rejected on the Umukozi platform:

Worker Details:
- Name: {worker.user.full_name}
- Email: {worker.user.email}
- Phone: {worker.user.phone}

Employer Details:
- Name: {employer.user.full_name}
- Email: {employer.user.email}

Job Details:
- Title: {job.title}
- Type: {job.job_type}

Best regards,
Umukozi System
            """
        
        # Send email to all admin users
        for admin in admin_users:
            try:
                msg = MIMEMultipart()
                msg['From'] = f"{from_name} <{smtp_username}>"
                msg['To'] = admin.email
                msg['Subject'] = subject
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Send email
                if smtp_encryption == 'ssl':
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                else:
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    if smtp_encryption == 'tls':
                        server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                
            except Exception as e:
                print(f"Failed to send email to {admin.email}: {e}")
                continue
        
    except Exception as e:
        print(f"Error sending admin hiring notification: {e}")

def send_user_registration_notification(user):
    """Send email notification to admin when a new user registers"""
    try:
        # Check if email notifications are enabled
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if not email_config_db or not email_config_db.enable_notifications:
            return
        
        # Get admin users
        admin_users = User.query.filter_by(user_type='admin').all()
        
        if not admin_users:
            return
        
        # Get email configuration from database
        smtp_server = email_config_db.smtp_server
        smtp_port = int(email_config_db.smtp_port)
        smtp_username = email_config_db.smtp_username
        smtp_password = email_config_db.smtp_password
        smtp_encryption = email_config_db.smtp_encryption
        from_name = email_config_db.from_name
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create email content
        user_type = user.user_type.title()
        body = f"""
Dear Admin,

A new user has registered on the Umukozi platform:

User Details:
- Name: {user.full_name}
- Email: {user.email}
- Phone: {user.phone}
- User Type: {user_type}
- Registration Date: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Status: {'Approved' if user.is_approved else 'Pending Approval'}

Please review and approve this user's account.

Best regards,
Umukozi System
        """
        
        subject = f"New User Registration: {user.full_name} ({user_type})"
        
        # Send email to all admin users
        for admin in admin_users:
            try:
                msg = MIMEMultipart()
                msg['From'] = f"{from_name} <{smtp_username}>"
                msg['To'] = admin.email
                msg['Subject'] = subject
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Send email
                if smtp_encryption == 'ssl':
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                else:
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    if smtp_encryption == 'tls':
                        server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                
            except Exception as e:
                print(f"Failed to send registration email to {admin.email}: {e}")
                continue
        
    except Exception as e:
        print(f"Error sending user registration notification: {e}")

def send_user_approval_notification(user):
    """Send email notification to user when their account is approved"""
    try:
        # Check if email notifications are enabled
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if not email_config_db or not email_config_db.enable_welcome_emails:
            return
        
        # Get email configuration from database
        smtp_server = email_config_db.smtp_server
        smtp_port = int(email_config_db.smtp_port)
        smtp_username = email_config_db.smtp_username
        smtp_password = email_config_db.smtp_password
        smtp_encryption = email_config_db.smtp_encryption
        from_name = email_config_db.from_name
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create email content
        user_type = user.user_type.title()
        body = f"""
Dear {user.full_name},

Congratulations! Your account has been approved on the Umukozi platform.

Account Details:
- Email: {user.email}
- User Type: {user_type}
- Approval Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

You can now log in to your account and start using the platform:
- Login URL: http://localhost:5000/login

{"As a Worker, you can:" if user.user_type == 'worker' else "As an Employer, you can:"}
{"• Browse and apply for jobs" if user.user_type == 'worker' else "• Post job opportunities"}
{"• Create and manage your profile" if user.user_type == 'worker' else "• Manage job applications"}
{"• Receive job notifications" if user.user_type == 'worker' else "• Find qualified workers"}
{"• Connect with employers" if user.user_type == 'worker' else "• Contact potential candidates"}

If you have any questions or need assistance, please don't hesitate to contact our support team.

Best regards,
Umukozi Team
        """
        
        subject = f"Account Approved - Welcome to Umukozi!"
        
        # Send email to user
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{from_name} <{smtp_username}>"
            msg['To'] = user.email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if smtp_encryption == 'ssl':
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if smtp_encryption == 'tls':
                    server.starttls()
            
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"Failed to send approval email to {user.email}: {e}")
        
    except Exception as e:
        print(f"Error sending user approval notification: {e}")

def send_user_rejection_notification(user, reason):
    """Send email notification to user when their account is rejected"""
    try:
        # Check if email notifications are enabled
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if not email_config_db or not email_config_db.enable_welcome_emails:
            return
        
        # Get email configuration from database
        smtp_server = email_config_db.smtp_server
        smtp_port = int(email_config_db.smtp_port)
        smtp_username = email_config_db.smtp_username
        smtp_password = email_config_db.smtp_password
        smtp_encryption = email_config_db.smtp_encryption
        from_name = email_config_db.from_name
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create email content
        user_type = user.user_type.title()
        body = f"""
Dear {user.full_name},

We regret to inform you that your account registration on the Umukozi platform has been reviewed and could not be approved at this time.

Account Details:
- Email: {user.email}
- User Type: {user_type}
- Registration Date: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Reason for Rejection:
{reason or 'No specific reason provided'}

If you believe this is a mistake or would like to appeal this decision, please:
1. Review our platform requirements and guidelines
2. Ensure all provided information is accurate and complete
3. Contact our support team for further assistance

You may re-register with updated information after addressing the issues mentioned above.

We appreciate your interest in the Umukozi platform and wish you the best in your job search or recruitment efforts.

Best regards,
Umukozi Team
        """
        
        subject = f"Account Registration Update - Umukozi Platform"
        
        # Send email to user
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{from_name} <{smtp_username}>"
            msg['To'] = user.email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if smtp_encryption == 'ssl':
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if smtp_encryption == 'tls':
                    server.starttls()
            
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"Failed to send rejection email to {user.email}: {e}")
        
    except Exception as e:
        print(f"Error sending user rejection notification: {e}")

def send_job_application_notification(application):
    """Send email notification to employer and admin when a worker applies for a job"""
    try:
        # Check if email notifications are enabled
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if not email_config_db or not email_config_db.enable_job_alerts:
            return
        
        # Get email configuration from database
        smtp_server = email_config_db.smtp_server
        smtp_port = int(email_config_db.smtp_port)
        smtp_username = email_config_db.smtp_username
        smtp_password = email_config_db.smtp_password
        smtp_encryption = email_config_db.smtp_encryption
        from_name = email_config_db.from_name
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        worker = application.worker
        job = application.job
        employer = job.employer
        
        # Send email to employer
        employer_body = f"""
Dear {employer.user.full_name},

A new worker has applied for your job posting on the Umukozi platform:

Job Details:
- Title: {job.title}
- Type: {job.job_type}
- Location: {job.district}, {job.province}
- Posted: {job.created_at.strftime('%Y-%m-%d')}

Worker Details:
- Name: {worker.user.full_name}
- Email: {worker.user.email}
- Phone: {worker.user.phone}
- District: {worker.district or 'Not specified'}
- Experience: {worker.experience_years or 'Not specified'} years
- Skills: {worker.skills or 'Not specified'}

Application Details:
- Applied: {application.applied_at.strftime('%Y-%m-%d %H:%M:%S')}
- Status: {application.status.title()}

Log in to your employer dashboard to review this application and contact the worker if interested.

Best regards,
Umukozi Team
        """
        
        employer_subject = f"New Job Application: {worker.user.full_name} applied for {job.title}"
        
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{from_name} <{smtp_username}>"
            msg['To'] = employer.user.email
            msg['Subject'] = employer_subject
            
            msg.attach(MIMEText(employer_body, 'plain'))
            
            # Send email
            if smtp_encryption == 'ssl':
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if smtp_encryption == 'tls':
                    server.starttls()
            
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"Failed to send job application email to employer {employer.user.email}: {e}")
        
        # Send notification to admin if enabled
        if email_config_db.enable_notifications:
            admin_users = User.query.filter_by(user_type='admin').all()
            
            admin_body = f"""
Dear Admin,

A new job application has been submitted on the Umukozi platform:

Job Details:
- Title: {job.title}
- Type: {job.job_type}
- Location: {job.district}, {job.province}
- Employer: {employer.company_name}

Worker Details:
- Name: {worker.user.full_name}
- Email: {worker.user.email}
- Phone: {worker.user.phone}
- District: {worker.district or 'Not specified'}

Application Details:
- Applied: {application.applied_at.strftime('%Y-%m-%d %H:%M:%S')}
- Status: {application.status.title()}

Best regards,
Umukozi System
            """
            
            admin_subject = f"New Job Application: {worker.user.full_name} → {job.title}"
            
            for admin in admin_users:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = f"{from_name} <{smtp_username}>"
                    msg['To'] = admin.email
                    msg['Subject'] = admin_subject
                    
                    msg.attach(MIMEText(admin_body, 'plain'))
                    
                    # Send email
                    if smtp_encryption == 'ssl':
                        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                    else:
                        server = smtplib.SMTP(smtp_server, smtp_port)
                        if smtp_encryption == 'tls':
                            server.starttls()
                    
                    server.login(smtp_username, smtp_password)
                    server.send_message(msg)
                    server.quit()
                    
                except Exception as e:
                    print(f"Failed to send job application email to admin {admin.email}: {e}")
                    continue
        
    except Exception as e:
        print(f"Error sending job application notification: {e}")

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

@app.route('/employer/my-jobs')
@login_required
def employer_my_jobs():
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    
    # Get all jobs for this employer
    jobs = Job.query.filter_by(employer_id=employer.id).order_by(Job.created_at.desc()).all()
    
    return render_template('employer_my_jobs.html', employer=employer, jobs=jobs)

@app.route('/employer/job/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def employer_edit_job(job_id):
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    job = Job.query.get_or_404(job_id)
    
    if job.employer_id != employer.id:
        flash('Unauthorized to edit this job.', 'error')
        return redirect(url_for('employer_my_jobs'))
        
    if request.method == 'POST':
        job.title = request.form.get('title')
        job.description = request.form.get('description')
        job.job_type = request.form.get('job_type')
        job.province = request.form.get('province')
        job.district = request.form.get('district')
        job.address_details = request.form.get('address_details')
        job.salary_type = request.form.get('salary_type')
        salary_amount = request.form.get('salary_amount')
        job.salary_amount = float(salary_amount) if salary_amount else None
        job.negotiable = request.form.get('negotiable') == 'on'
        job.skills_required = request.form.get('skills_required')
        job.experience_required = request.form.get('experience_required')
        job.is_urgent = request.form.get('is_urgent') == 'on'
        
        if not job.title or not job.description or not job.job_type or not job.district:
            flash('Please fill in all required fields.', 'error')
            return render_template('employer_edit_job.html', employer=employer, job=job, form_data=request.form)
            
        db.session.commit()
        flash('🎉 Job updated successfully!', 'success')
        return redirect(url_for('employer_my_jobs'))
        
    return render_template('employer_edit_job.html', employer=employer, job=job)

@app.route('/employer/job/<int:job_id>/close', methods=['POST'])
@login_required
def employer_close_job(job_id):
    if current_user.user_type != 'employer':
        return redirect(url_for('dashboard'))
    employer = Employer.query.filter_by(user_id=current_user.id).first()
    job = Job.query.get_or_404(job_id)
    
    if job.employer_id != employer.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    job.status = 'closed'
    db.session.commit()
    return jsonify({'success': True})

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

@app.route('/admin/worker/<int:worker_id>/update-status', methods=['POST'])
@login_required
def admin_update_worker_status(worker_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        worker = Worker.query.get_or_404(worker_id)
        new_status = request.json.get('status')
        
        if new_status not in ['available', 'busy', 'unavailable']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        old_status = worker.availability_status
        worker.availability_status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Worker status updated from {old_status} to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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

# Admin Email Settings
@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
def admin_email_settings():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get active email config from database or create default
    email_config_db = EmailConfig.query.filter_by(is_active=True).first()
    
    if not email_config_db:
        # Create default email config from environment variables
        email_config_db = EmailConfig(
            smtp_server=os.getenv('SMTP_SERVER', ''),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_encryption=os.getenv('SMTP_ENCRYPTION', 'tls'),
            smtp_username=os.getenv('SMTP_USERNAME', ''),
            smtp_password=os.getenv('SMTP_PASSWORD', ''),
            from_name=os.getenv('EMAIL_FROM_NAME', 'Umukozi'),
            reply_to=os.getenv('EMAIL_REPLY_TO', ''),
            enable_notifications=os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() == 'true',
            enable_welcome_emails=os.getenv('ENABLE_WELCOME_EMAILS', 'true').lower() == 'true',
            enable_job_alerts=os.getenv('ENABLE_JOB_ALERTS', 'true').lower() == 'true',
            enable_verification_emails=os.getenv('ENABLE_VERIFICATION_EMAILS', 'true').lower() == 'true',
            created_by=current_user.id
        )
        db.session.add(email_config_db)
        db.session.commit()
    
    # Convert database object to dictionary for template
    email_config = {
        'smtp_server': email_config_db.smtp_server,
        'smtp_port': str(email_config_db.smtp_port),
        'smtp_encryption': email_config_db.smtp_encryption,
        'smtp_username': email_config_db.smtp_username,
        'smtp_password': email_config_db.smtp_password,
        'from_name': email_config_db.from_name,
        'reply_to': email_config_db.reply_to or '',
        'enable_notifications': email_config_db.enable_notifications,
        'enable_welcome_emails': email_config_db.enable_welcome_emails,
        'enable_job_alerts': email_config_db.enable_job_alerts,
        'enable_verification_emails': email_config_db.enable_verification_emails
    }
    
    if request.method == 'POST':
        try:
            # Update database record
            email_config_db.smtp_server = request.form.get('smtp_server', '')
            email_config_db.smtp_port = int(request.form.get('smtp_port', '587'))
            email_config_db.smtp_encryption = request.form.get('smtp_encryption', 'tls')
            email_config_db.smtp_username = request.form.get('smtp_username', '')
            email_config_db.smtp_password = request.form.get('smtp_password', '')
            email_config_db.from_name = request.form.get('from_name', 'Umukozi')
            email_config_db.reply_to = request.form.get('reply_to', '')
            email_config_db.enable_notifications = request.form.get('enable_notifications') == 'on'
            email_config_db.enable_welcome_emails = request.form.get('enable_welcome_emails') == 'on'
            email_config_db.enable_job_alerts = request.form.get('enable_job_alerts') == 'on'
            email_config_db.enable_verification_emails = request.form.get('enable_verification_emails') == 'on'
            email_config_db.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update email_config dict for template
            email_config = {
                'smtp_server': email_config_db.smtp_server,
                'smtp_port': str(email_config_db.smtp_port),
                'smtp_encryption': email_config_db.smtp_encryption,
                'smtp_username': email_config_db.smtp_username,
                'smtp_password': email_config_db.smtp_password,
                'from_name': email_config_db.from_name,
                'reply_to': email_config_db.reply_to or '',
                'enable_notifications': email_config_db.enable_notifications,
                'enable_welcome_emails': email_config_db.enable_welcome_emails,
                'enable_job_alerts': email_config_db.enable_job_alerts,
                'enable_verification_emails': email_config_db.enable_verification_emails
            }
            
            flash('Email settings updated successfully and saved to database!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating email settings: {str(e)}', 'error')
    
    return render_template('admin_email_settings.html', email_config=email_config)

@app.route('/admin/test-email-connection', methods=['POST'])
@login_required
def admin_test_email_connection():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        # Handle empty JSON request
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400
        
        # Get email configuration from database, request, or environment variables
        data = request.get_json() or {}
        
        # Try database first, then request data, then environment variables
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if email_config_db:
            smtp_server = data.get('smtp_server') or email_config_db.smtp_server
            smtp_port = int(data.get('smtp_port') or email_config_db.smtp_port)
            smtp_username = data.get('smtp_username') or email_config_db.smtp_username
            smtp_password = data.get('smtp_password') or email_config_db.smtp_password
            smtp_encryption = data.get('smtp_encryption') or email_config_db.smtp_encryption
        else:
            # Fallback to environment variables
            smtp_server = data.get('smtp_server') or os.getenv('SMTP_SERVER')
            smtp_port = int(data.get('smtp_port') or os.getenv('SMTP_PORT', '587'))
            smtp_username = data.get('smtp_username') or os.getenv('SMTP_USERNAME')
            smtp_password = data.get('smtp_password') or os.getenv('SMTP_PASSWORD')
            smtp_encryption = data.get('smtp_encryption') or os.getenv('SMTP_ENCRYPTION', 'tls')
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return jsonify({'success': False, 'error': 'Missing SMTP configuration'})
        
        # Test connection
        if smtp_encryption == 'ssl':
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_encryption == 'tls':
                server.starttls()
        
        server.login(smtp_username, smtp_password)
        server.quit()
        
        return jsonify({'success': True, 'message': 'SMTP connection successful'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/send-test-email', methods=['POST'])
@login_required
def admin_send_test_email():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        data = request.get_json()
        test_email = data.get('email')
        
        if not test_email:
            return jsonify({'success': False, 'error': 'Email address required'})
        
        # Get email configuration from database or environment variables
        email_config_db = EmailConfig.query.filter_by(is_active=True).first()
        
        if email_config_db:
            smtp_server = email_config_db.smtp_server
            smtp_port = int(email_config_db.smtp_port)
            smtp_username = email_config_db.smtp_username
            smtp_password = email_config_db.smtp_password
            smtp_encryption = email_config_db.smtp_encryption
            from_name = email_config_db.from_name
        else:
            # Fallback to environment variables
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            smtp_encryption = os.getenv('SMTP_ENCRYPTION', 'tls')
            from_name = os.getenv('EMAIL_FROM_NAME', 'Umukozi')
        
        if not all([smtp_server, smtp_username, smtp_password]):
            return jsonify({'success': False, 'error': 'Email not configured'})
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{smtp_username}>"
        msg['To'] = test_email
        msg['Subject'] = 'Umukozi Email Configuration Test'
        
        body = f"""
        This is a test email from Umukozi to verify that your email configuration is working correctly.
        
        If you received this email, your SMTP settings are properly configured.
        
        Best regards,
        Umukozi Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        if smtp_encryption == 'ssl':
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_encryption == 'tls':
                server.starttls()
        
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return jsonify({'success': True, 'message': f'Test email sent to {test_email}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout')
@login_required
def logout():
    user_name = current_user.full_name
    
    # Clear session completely
    from flask import session
    session.clear()
    
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

@app.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    """Route for users to change their own password"""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'error': 'All fields are required.'}), 400
        
    if not check_password_hash(current_user.password, current_password):
        return jsonify({'success': False, 'error': 'Current password is incorrect.'}), 400
        
    if new_password != confirm_password:
        return jsonify({'success': False, 'error': 'New passwords do not match.'}), 400
        
    # Check password strength
    is_strong, msg = check_password_strength(new_password)
    if not is_strong:
        return jsonify({'success': False, 'error': msg}), 400
        
    # Update password
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    # Send notification
    notif = Notification(
        user_id=current_user.id,
        message="Your password was successfully changed. If you didn't do this, please contact support immediately."
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Password updated successfully!'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

