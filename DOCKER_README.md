# Umukozi Docker Setup Guide

This guide explains how to containerize and deploy the Umukozi application using Docker.

## 🐳 Docker Components

### Services Included:
- **Web**: Flask application with Gunicorn
- **Database**: PostgreSQL 15
- **Cache**: Redis 7 (optional)
- **Proxy**: Nginx (reverse proxy for production)

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- Docker Compose installed
- At least 2GB RAM available

### Windows Setup
```bash
# Run the setup script
docker-setup.bat
```

### Linux/Mac Setup
```bash
# Make script executable
chmod +x docker-setup.sh

# Run the setup script
./docker-setup.sh
```

### Manual Setup
```bash
# 1. Copy environment file
cp .env.docker .env

# 2. Build containers
docker-compose build

# 3. Start services
docker-compose up -d

# 4. Initialize database
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 5. Create admin user
docker-compose exec web python create_admin.py
```

## 📁 File Structure

```
Umukozi/
├── Dockerfile              # Main application container
├── docker-compose.yml      # Multi-container orchestration
├── .dockerignore          # Files to exclude from Docker build
├── nginx.conf             # Nginx configuration
├── init.sql               # PostgreSQL initialization
├── .env.docker            # Environment variables template
├── docker-setup.sh        # Linux/Mac setup script
├── docker-setup.bat       # Windows setup script
└── DOCKER_README.md       # This documentation
```

## ⚙️ Configuration

### Environment Variables
Edit `.env` file to configure:

```bash
# Flask Configuration
SECRET_KEY=your-secure-secret-key
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://umukozi_user:umukozi_password@db:5432/umukozi_db

# Email (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Database Configuration
The setup uses PostgreSQL by default in Docker. For development, you can still use SQLite by setting:
```bash
DATABASE_URL=sqlite:///umukozi.db
```

## 🌐 Access Points

- **Main Application**: http://localhost:5000
- **Database**: localhost:5432
- **Redis**: localhost:6379
- **Nginx (Proxy)**: http://localhost:80

## 🔧 Common Commands

### Container Management
```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web
docker-compose logs -f db

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache

# Restart services
docker-compose restart
```

### Database Management
```bash
# Access PostgreSQL
docker-compose exec db psql -U umukozi_user -d umukozi_db

# Backup database
docker-compose exec db pg_dump -U umukozi_user umukozi_db > backup.sql

# Restore database
docker-compose exec -T db psql -U umukozi_user umukozi_db < backup.sql

# Reset database
docker-compose down -v
docker-compose up -d
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Application Management
```bash
# Access Flask shell
docker-compose exec web python

# Run migrations
docker-compose exec web python update_database_schema.py

# Create admin user
docker-compose exec web python create_admin.py

# View application logs
docker-compose exec web tail -f /dev/stdout
```

## 🔒 Security Considerations

### Production Deployment
1. **Change default passwords** in `.env` file
2. **Use HTTPS** with proper SSL certificates
3. **Set strong SECRET_KEY**
4. **Configure firewall** rules
5. **Regular updates** of Docker images

### SSL Configuration
1. Place SSL certificates in `ssl/` directory:
   - `ssl/cert.pem` - SSL certificate
   - `ssl/key.pem` - SSL private key

2. Uncomment HTTPS section in `nginx.conf`

3. Update `docker-compose.yml` to mount SSL volume

## 🐛 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker-compose logs

# Check resource usage
docker stats

# Rebuild if needed
docker-compose build --no-cache
```

#### Database Connection Errors
```bash
# Check if database is ready
docker-compose exec db pg_isready -U umukozi_user

# Restart database
docker-compose restart db

# Check database logs
docker-compose logs db
```

#### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER instance/
sudo chown -R $USER:$USER static/uploads/

# Or run with elevated permissions (not recommended for production)
sudo docker-compose up -d
```

#### Port Conflicts
```bash
# Check what's using ports
netstat -tulpn | grep :5000
netstat -tulpn | grep :5432

# Change ports in docker-compose.yml if needed
```

### Performance Optimization

#### Database Optimization
```bash
# Connect to database
docker-compose exec db psql -U umukozi_user -d umukozi_db

# Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_jobs_status ON jobs(status);
```

#### Application Scaling
```yaml
# In docker-compose.yml, add:
web:
  # ... existing config
  deploy:
    replicas: 3
```

## 📊 Monitoring

### Health Checks
```bash
# Check application health
curl http://localhost:5000/health

# Check container health
docker-compose ps
```

### Resource Monitoring
```bash
# View resource usage
docker stats

# View disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

## 🔄 Backup and Recovery

### Data Backup
```bash
# Backup database
docker-compose exec db pg_dump -U umukozi_user umukozi_db > backup_$(date +%Y%m%d).sql

# Backup uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz static/uploads/
```

### Data Recovery
```bash
# Restore database
docker-compose exec -T db psql -U umukozi_user umukozi_db < backup_20231201.sql

# Restore uploaded files
tar -xzf uploads_backup_20231201.tar.gz
```

## 🚀 Production Deployment

### Environment Preparation
1. **Server Requirements**:
   - Minimum 4GB RAM
   - 20GB storage
   - Docker and Docker Compose installed

2. **Security Setup**:
   - Configure firewall
   - Set up SSL certificates
   - Update all passwords

3. **Performance Tuning**:
   - Adjust worker processes
   - Configure database connections
   - Set up monitoring

### Deployment Steps
```bash
# 1. Clone repository
git clone <repository-url>
cd Umukozi

# 2. Configure environment
cp .env.docker .env
# Edit .env with production values

# 3. Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Verify deployment
curl https://yourdomain.com/health
```

## 📞 Support

For issues with Docker setup:
1. Check logs: `docker-compose logs`
2. Verify configuration: `.env` file
3. Check resource availability
4. Review this documentation

## 🔄 Updates

To update the application:
```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build

# Restart services
docker-compose up -d
```
