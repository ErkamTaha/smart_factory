#!/bin/bash
# Smart Factory Quick Start Script
# Run this after extracting the project files

echo "🏭 Smart Factory Quick Start"
echo "=========================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first:"
    echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    echo "  macOS: brew install --cask docker"
    echo "  Windows: Download from https://docker.com/products/docker-desktop"
    exit 1
fi

# Detect Docker Compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Docker Compose is not available!"
    echo "Please install Docker Compose or use Docker Desktop which includes it"
    exit 1
fi

echo "✅ Docker is installed"
echo "📋 Using: $DOCKER_COMPOSE"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the smart_factory directory"
    echo "Usage: cd smart_factory && ./quick_start.sh"
    exit 1
fi

echo "📁 Project directory detected"

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating environment file..."
    cp backend/.env.example backend/.env
    echo "✅ Environment file created"
fi

# Check if ports are available
echo "🔍 Checking available ports..."
for port in 3000 8000 5432 1883 8080; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use!"
        echo "Please stop the service using port $port or modify docker-compose.yml"
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
done

echo "✅ Ports are available"

# Start the application
echo ""
echo "🚀 Starting Smart Factory..."
echo "This may take 2-3 minutes on first run (downloading Docker images)"
echo ""

# Use make if available, otherwise use detected docker compose command
if command -v make &> /dev/null; then
    make up-dev
else
    $DOCKER_COMPOSE up -d
fi

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 30

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "✅ Backend is healthy!"
else
    echo "⚠️  Backend might still be starting..."
fi

if curl -f http://localhost:3000 >/dev/null 2>&1; then
    echo "✅ Frontend is healthy!"
else
    echo "⚠️  Frontend might still be starting..."
fi

echo ""
echo "🎉 Smart Factory Started Successfully!"
echo "=================================="
echo ""
echo "📱 Frontend Dashboard:  http://localhost:3000"
echo "🔧 Backend API:         http://localhost:8000"
echo "📚 API Documentation:   http://localhost:8000/docs"
echo "🗄️  Database Admin:      http://localhost:8080"
echo "❤️  Health Check:        http://localhost:8000/api/health"
echo ""
echo "👤 Default Users: alice, bob, charlie, dave, eve, erkam"
echo "🔐 pgAdmin Login: admin@smartfactory.local / admin123"
echo ""
echo "📋 Useful Commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart:       docker-compose restart"
echo ""
echo "🚀 Your Smart Factory is ready for use!"
