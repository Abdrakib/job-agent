#!/bin/bash
# One-command DigitalOcean deployment script
# Run this on your DigitalOcean droplet after cloning the repo

set -e

echo "🤖 Job Agent — DigitalOcean Setup"
echo "=================================="

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $USER
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Check .env file exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Fill in your .env file before continuing!"
    echo "   nano .env"
    exit 1
fi

# Build and start
echo "Building and starting services..."
docker-compose up -d --build

echo ""
echo "✅ Job Agent is running!"
echo "   Dashboard: http://$(curl -s ifconfig.me):8501"
echo "   Logs: docker-compose logs -f"
echo "   Stop: docker-compose down"
