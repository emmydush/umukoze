@echo off
REM Umukozi Docker Setup Script for Windows
REM This script sets up the complete Docker environment for Umukozi

echo 🐳 Setting up Umukozi Docker Environment...
echo ==========================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create environment file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.docker .env
    echo ✅ .env file created. Please review and modify the settings.
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist instance mkdir instance
if not exist static\uploads mkdir static\uploads
if not exist ssl mkdir ssl

REM Build and start containers
echo 🏗️  Building Docker containers...
docker-compose build

if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    pause
    exit /b 1
)

echo 🚀 Starting containers...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ❌ Failed to start containers!
    pause
    exit /b 1
)

REM Wait for database to be ready
echo ⏳ Waiting for database to be ready...
timeout /t 10 /nobreak

REM Initialize database
echo 🗄️  Initializing database...
docker-compose exec web python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database tables created successfully!')"

if %errorlevel% neq 0 (
    echo ⚠️  Database initialization may have failed. Check logs.
)

REM Create admin user
echo 👤 Creating admin user...
docker-compose exec web python create_admin.py

echo ✅ Docker setup complete!
echo 🌐 Application is running at: http://localhost:5000
echo 🔍 Check container status with: docker-compose ps
echo 📋 View logs with: docker-compose logs -f
echo 🛑 Stop containers with: docker-compose down

REM Display container status
echo.
echo 📊 Container Status:
docker-compose ps

pause
