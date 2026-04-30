# Umukozi - Connect Household Workers with Employers in Rwanda

A modern web platform that connects trusted household workers with home employers across Rwanda. Built with Flask, SQLite, and responsive HTML/CSS for optimal mobile experience.

## 🌟 Features

### For Workers
- **Profile Creation**: Detailed profiles with skills, experience, and availability
- **Job Search**: Browse and apply for jobs matching your skills
- **Direct Messaging**: Communicate safely with employers
- **Reviews & Ratings**: Build your reputation through reviews
- **Verification System**: Get verified to increase trust and opportunities

### For Employers
- **Job Posting**: Create detailed job postings with requirements
- **Worker Search**: Find verified workers by location, skills, and availability
- **Application Management**: Review and manage applications efficiently
- **Secure Messaging**: Communicate with potential hires
- **Review System**: Rate and review workers after job completion

### Platform Features
- **Mobile-First Design**: Works perfectly on smartphones and tablets
- **Location-Based**: Find workers and jobs in your specific Rwandan district
- **Secure Authentication**: Safe login and registration system
- **Real-Time Notifications**: Stay updated on applications and messages
- **Review System**: Build trust through transparent reviews

## 🛠 Technology Stack

- **Backend**: Python 3.8+, Flask 2.3+
- **Database**: SQLite (for easy deployment and scaling)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Authentication**: Flask-Login with password hashing
- **Styling**: Custom CSS with mobile-first responsive design
- **Deployment**: Supports Heroku, Vercel, or traditional hosting

## 📋 Requirements

- Python 3.8 or higher
- pip package manager
- Git (for cloning)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/umukozi.git
cd umukozi
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Copy the example environment file and update it:
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` file with your settings:
- Change `SECRET_KEY` to a secure random string
- Update email settings for notifications
- Configure other settings as needed

### 5. Initialize Database
```bash
python app.py
```
This will automatically create the SQLite database with all required tables.

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📱 Mobile Optimization

The platform is designed with a mobile-first approach:

- **Responsive Design**: Adapts to any screen size
- **Touch-Friendly**: Large buttons and intuitive navigation
- **Fast Loading**: Optimized for mobile networks
- **Progressive Web App**: Can be installed on mobile devices

## 🏗 Project Structure

```
umukozi/
├── app.py                 # Main Flask application
├── models.py             # Database models
├── requirements.txt      # Python dependencies
├── .env                  # Environment configuration
├── README.md            # This file
├── static/              # Static files
│   ├── css/
│   │   └── style.css    # Main stylesheet
│   ├── js/              # JavaScript files
│   └── images/          # Image assets
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── index.html       # Landing page
    ├── login.html       # Login page
    ├── register.html    # Registration page
    ├── worker_dashboard.html    # Worker dashboard
    └── employer_dashboard.html  # Employer dashboard
```

## 🗄 Database Schema

The application uses SQLite with the following main tables:

- **Users**: Authentication and basic user information
- **Workers**: Worker profiles, skills, and availability
- **Employers**: Employer profiles and company information
- **Jobs**: Job postings with requirements and details
- **Applications**: Job applications and status tracking
- **Reviews**: Worker reviews and ratings
- **Messages**: In-app messaging system

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///umukozi.db
```

### Customization

- **Styling**: Modify `static/css/style.css` for visual changes
- **Content**: Update templates for text and layout changes
- **Features**: Add new routes and functionality in `app.py`

## 🚀 Deployment

### Heroku Deployment

1. Install Heroku CLI and login
2. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
3. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set FLASK_ENV=production
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```

### Vercel Deployment

1. Install Vercel CLI
2. Run:
   ```bash
   vercel
   ```
3. Follow the prompts to deploy

### Traditional Hosting

1. Install dependencies on server
2. Set up WSGI server (Gunicorn recommended)
3. Configure reverse proxy (Nginx recommended)
4. Set up SSL certificate

## 🔒 Security Features

- **Password Hashing**: Secure password storage using bcrypt
- **CSRF Protection**: Built-in Flask CSRF protection
- **Input Validation**: Form validation and sanitization
- **Secure Sessions**: Secure session management
- **SQL Injection Protection**: SQLAlchemy ORM protection

## 🌍 Rwanda-Specific Features

- **Location Support**: All Rwandan provinces and districts
- **Currency**: Rwandan Franc (RWF) support
- **Languages**: Support for English, French, and Kinyarwanda
- **Local Payment Methods**: Ready for Mobile Money integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For support and questions:
- Email: support@umukozi.rw
- Phone: +250 7XX XXX XXX
- Website: www.umukozi.rw

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for the Rwandan community
- Inspired by the need to connect trustworthy household workers with families
- Thanks to all contributors and testers

## 📈 Roadmap

### Phase 1 (Current)
- ✅ Basic platform with authentication
- ✅ Worker and employer profiles
- ✅ Job posting and application system
- ✅ Responsive mobile design

### Phase 2 (Upcoming)
- 🔄 Mobile app (React Native)
- 🔄 Advanced search and filtering
- 🔄 In-app video calling
- 🔄 Payment integration (Mobile Money)

### Phase 3 (Future)
- 📋 AI-powered matching
- 📋 Background check integration
- 📋 Insurance options
- 📋 Training programs

---

**Made with ❤️ in Rwanda**
