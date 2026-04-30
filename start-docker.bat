@echo off
REM Simple Docker Start Script for Umukozi

echo 🐳 Starting Umukozi with Docker...
echo ==================================

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not available. Please install Docker Desktop.
    echo 💡 For now, you can run the app directly with: python app.py
    pause
    exit /b 1
)

REM Create environment file if needed
if not exist .env (
    echo 📝 Creating .env file...
    echo SECRET_KEY=your-secret-key-change-in-production > .env
    echo FLASK_ENV=production >> .env
    echo DATABASE_URL=sqlite:///umukozi.db >> .env
)

REM Create necessary directories
if not exist instance mkdir instance
if not exist static\uploads mkdir static\uploads

echo 🏗️  Building Docker image...
docker build -f Dockerfile.simple -t umukozi-app .

if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    pause
    exit /b 1
)

echo 🚀 Starting container...
docker run -d --name umukozi-container -p 5000:5000 -v "%cd%\instance":/app/instance -v "%cd%\static\uploads":/app/static/uploads umukozi-app

if %errorlevel% neq 0 (
    echo ❌ Failed to start container!
    pause
    exit /b 1
)

echo ✅ Umukozi is now running in Docker!
echo 🌐 Access the app at: http://localhost:5000
echo 📋 View logs: docker logs umukozi-container
echo 🛑 Stop container: docker stop umukozi-container
echo 🧹 Clean up: docker rm umukozi-container

pause
