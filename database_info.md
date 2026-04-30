# Umukozi Database Structure

## 📊 Database Overview

**Database Type:** SQLite  
**File Location:** `E:\Umukozi\instance\umukozi.db`  
**File Size:** 36,864 bytes (36.8 KB)  
**Status:** ✅ Created and Ready

---

## 🗄 Database Schema

### 1. **Users Table** (Core Authentication)
```sql
- id (INTEGER, Primary Key)
- email (VARCHAR(120), Unique, Not Null)
- password (VARCHAR(200), Not Null, Hashed)
- full_name (VARCHAR(100), Not Null)
- phone (VARCHAR(20), Not Null)
- user_type (VARCHAR(20), Not Null) - 'worker' or 'employer'
- created_at (DATETIME, Default: Current Time)
- is_active (BOOLEAN, Default: True)
```

**Relationships:**
- One-to-One with Workers
- One-to-One with Employers
- One-to-Many with Messages (sent & received)

---

### 2. **Workers Table** (Worker Profiles)
```sql
- id (INTEGER, Primary Key)
- user_id (INTEGER, Foreign Key → Users.id)
  
# Personal Information
- date_of_birth (DATE)
- national_id (VARCHAR(20))
- profile_picture (VARCHAR(200))
- bio (TEXT)

# Location (Rwanda-specific)
- province (VARCHAR(50))
- district (VARCHAR(50))
- sector (VARCHAR(50))
- cell (VARCHAR(50))
- village (VARCHAR(50))

# Professional Information
- experience_years (INTEGER)
- hourly_rate (FLOAT)
- monthly_rate (FLOAT)
- availability_status (VARCHAR(20), Default: 'available')

# Skills & Services
- skills (TEXT) - JSON format
- services_offered (TEXT) - JSON format

# Verification
- is_verified (BOOLEAN, Default: False)
- verification_documents (TEXT) - JSON format

# Statistics
- average_rating (FLOAT, Default: 0.0)
- total_jobs_completed (INTEGER, Default: 0)

# Timestamps
- created_at (DATETIME)
- updated_at (DATETIME)
```

**Relationships:**
- Belongs to User
- Has Many Applications
- Has Many Reviews (received)

---

### 3. **Employers Table** (Employer Profiles)
```sql
- id (INTEGER, Primary Key)
- user_id (INTEGER, Foreign Key → Users.id)

# Company/Household Information
- company_name (VARCHAR(100))
- household_type (VARCHAR(50)) - 'family', 'individual', 'company'
- profile_picture (VARCHAR(200))
- bio (TEXT)

# Location (Rwanda-specific)
- province (VARCHAR(50))
- district (VARCHAR(50))
- sector (VARCHAR(50))
- cell (VARCHAR(50))
- village (VARCHAR(50))
- address_details (TEXT)

# Verification
- is_verified (BOOLEAN, Default: False)
- verification_documents (TEXT) - JSON format

# Statistics
- average_rating (FLOAT, Default: 0.0)
- total_jobs_posted (INTEGER, Default: 0)

# Timestamps
- created_at (DATETIME)
- updated_at (DATETIME)
```

**Relationships:**
- Belongs to User
- Has Many Jobs
- Has Many Reviews (given)

---

### 4. **Jobs Table** (Job Postings)
```sql
- id (INTEGER, Primary Key)
- employer_id (INTEGER, Foreign Key → Employers.id)

# Job Details
- title (VARCHAR(200), Not Null)
- description (TEXT, Not Null)
- job_type (VARCHAR(50), Not Null) - 'full_time', 'part_time', 'temporary', 'live_in'

# Location
- province (VARCHAR(50))
- district (VARCHAR(50))
- sector (VARCHAR(50))
- cell (VARCHAR(50))
- village (VARCHAR(50))
- address_details (TEXT)

# Compensation
- salary_type (VARCHAR(20)) - 'hourly', 'daily', 'weekly', 'monthly'
- salary_amount (FLOAT)
- negotiable (BOOLEAN, Default: True)

# Requirements
- skills_required (TEXT) - JSON format
- experience_required (VARCHAR(50))
- education_required (VARCHAR(100))
- languages_required (TEXT) - JSON format

# Schedule
- working_hours (VARCHAR(100))
- working_days (VARCHAR(100))
- start_date (DATE)
- end_date (DATE) - for temporary jobs

# Status
- status (VARCHAR(20), Default: 'open') - 'open', 'closed', 'filled'
- is_urgent (BOOLEAN, Default: False)

# Timestamps
- created_at (DATETIME)
- updated_at (DATETIME)
```

**Relationships:**
- Belongs to Employer
- Has Many Applications

---

### 5. **Applications Table** (Job Applications)
```sql
- id (INTEGER, Primary Key)
- job_id (INTEGER, Foreign Key → Jobs.id)
- worker_id (INTEGER, Foreign Key → Workers.id)

# Application Details
- cover_letter (TEXT)
- proposed_salary (FLOAT)
- available_start_date (DATE)

# Status
- status (VARCHAR(20), Default: 'pending') - 'pending', 'accepted', 'rejected', 'withdrawn'

# Timestamps
- applied_at (DATETIME)
- updated_at (DATETIME)
```

**Relationships:**
- Belongs to Job
- Belongs to Worker
- Has Many Reviews

---

### 6. **Reviews Table** (Worker Reviews)
```sql
- id (INTEGER, Primary Key)
- application_id (INTEGER, Foreign Key → Applications.id)
- worker_id (INTEGER, Foreign Key → Workers.id)
- employer_id (INTEGER, Foreign Key → Employers.id)

# Review Content
- rating (INTEGER, Not Null) - 1-5 stars
- comment (TEXT)

# Review Categories
- punctuality (INTEGER)
- quality_of_work (INTEGER)
- communication (INTEGER)
- reliability (INTEGER)

# Timestamp
- created_at (DATETIME)
```

**Relationships:**
- Belongs to Application
- Belongs to Worker
- Belongs to Employer

---

### 7. **Messages Table** (In-App Messaging)
```sql
- id (INTEGER, Primary Key)
- sender_id (INTEGER, Foreign Key → Users.id)
- receiver_id (INTEGER, Foreign Key → Users.id)

# Message Content
- content (TEXT, Not Null)

# Metadata
- is_read (BOOLEAN, Default: False)
- job_id (INTEGER, Foreign Key → Jobs.id)
- application_id (INTEGER, Foreign Key → Applications.id)

# Timestamps
- created_at (DATETIME)
- read_at (DATETIME)
```

**Relationships:**
- Belongs to Sender (User)
- Belongs to Receiver (User)
- Optional: Belongs to Job
- Optional: Belongs to Application

---

## 🔗 Relationship Diagram

```
Users (1) ←→ (1) Workers
Users (1) ←→ (1) Employers

Employers (1) → (N) Jobs
Jobs (1) → (N) Applications
Workers (1) → (N) Applications

Applications (1) → (N) Reviews
Workers (N) ←→ (1) Reviews
Employers (N) ←→ (1) Reviews

Users (N) → (N) Messages (as sender/receiver)
Jobs (1) → (N) Messages (optional)
Applications (1) → (N) Messages (optional)
```

---

## 🌍 Rwanda-Specific Features

### Location Hierarchy
- **Province** (4: Kigali, Northern, Southern, Eastern, Western)
- **District** (30 districts)
- **Sector** (416 sectors)
- **Cell** (2,148 cells)
- **Village** (14,837 villages)

### Currency Support
- All monetary values in **Rwandan Francs (RWF)**
- Support for different payment periods (hourly, daily, weekly, monthly)

---

## 📊 Current Database Status

- ✅ **Database Created:** SQLite file exists
- ✅ **Tables Created:** All 7 tables initialized
- ✅ **Relationships Defined:** Foreign keys and constraints set
- ✅ **Ready for Data:** Can accept user registrations immediately
- 📝 **Current Records:** 0 (fresh database)

---

## 🚀 Database Operations

### Creating the Database
```python
# Done automatically when running app.py
with app.app_context():
    db.create_all()
```

### Adding Sample Data
```python
# Example: Create a test user
user = User(
    email="test@example.com",
    password=hashed_password,
    full_name="Test User",
    phone="+250788123456",
    user_type="worker"
)
db.session.add(user)
db.session.commit()
```

### Querying Data
```python
# Get all workers
workers = Worker.query.all()

# Get jobs by district
jobs = Job.query.filter_by(district="Kigali").all()

# Get user's applications
applications = Application.query.filter_by(worker_id=current_user.worker.id).all()
```

---

## 🔒 Security Features

- **Password Hashing:** Using bcrypt for secure password storage
- **SQL Injection Protection:** SQLAlchemy ORM prevents SQL injection
- **Data Validation:** Form validation and sanitization
- **Foreign Key Constraints:** Data integrity maintained
- **Unique Constraints:** Email uniqueness enforced

---

## 📈 Performance Considerations

- **SQLite:** Perfect for small to medium applications
- **Indexes:** Primary keys automatically indexed
- **Relationships:** Optimized with proper foreign keys
- **Scalable:** Can migrate to PostgreSQL if needed

The database is fully set up and ready to handle all user registrations, job postings, and platform operations!
