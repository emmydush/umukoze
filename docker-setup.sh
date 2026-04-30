#!/bin/bash

# Umukozi Docker Setup Script
# This script sets up the complete Docker environment for Umukozi

set -e

echo "🐳 Setting up Umukozi Docker Environment..."
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env
    echo "✅ .env file created. Please review and modify the settings."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p instance
mkdir -p static/uploads
mkdir -p ssl

# Set proper permissions
echo "🔐 Setting permissions..."
chmod 755 instance
chmod 755 static/uploads
chmod 755 ssl

# Build and start containers
echo "🏗️  Building Docker containers..."
docker-compose build

echo "🚀 Starting containers..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Initialize database
echo "🗄️  Initializing database..."
docker-compose exec web python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"

# Create admin user
echo "👤 Creating admin user..."
docker-compose exec web python create_admin.py

echo "✅ Docker setup complete!"
echo "🌐 Application is running at: http://localhost:5000"
echo "🔍 Check container status with: docker-compose ps"
echo "📋 View logs with: docker-compose logs -f"
echo "🛑 Stop containers with: docker-compose down"

# Display container status
echo ""
echo "📊 Container Status:"
docker-compose ps
