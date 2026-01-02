#!/bin/bash
# Deployment script for HHHelper on Ubuntu VPS
# Run from the project root directory

set -e

echo "=== HHHelper Deployment ==="

# Configuration
APP_DIR="/opt/hhhelper"
REPO_URL="https://github.com/YOUR_USERNAME/pays.git"  # Update this!

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

echo "1. Installing dependencies..."
apt-get update
apt-get install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# Start and enable docker
systemctl start docker
systemctl enable docker

echo "2. Creating app directory..."
mkdir -p $APP_DIR
cd $APP_DIR

echo "3. Cloning/updating repository..."
if [ -d "$APP_DIR/.git" ]; then
    git pull origin main
else
    git clone $REPO_URL .
fi

echo "4. Setting up environment..."
cd backend
if [ ! -f .env ]; then
    echo -e "${RED}.env file not found!${NC}"
    echo "Create .env file from .env.example and fill in your values:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

echo "5. Building and starting containers..."
docker-compose down || true
docker-compose build --no-cache
docker-compose up -d

echo "6. Waiting for database..."
sleep 5

echo "7. Running migrations..."
docker-compose exec -T api alembic upgrade head

echo "8. Setting up nginx..."
cp ../deploy/nginx/hhhelper.conf /etc/nginx/sites-available/hhhelper
ln -sf /etc/nginx/sites-available/hhhelper /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

echo "9. Getting SSL certificate..."
certbot --nginx -d hhhelper.arsenal0.space --non-interactive --agree-tos --email your@email.com || true

echo "10. Restarting nginx..."
systemctl restart nginx

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Services:"
echo "  - API:  https://hhhelper.arsenal0.space"
echo "  - Bot:  Running in polling mode"
echo ""
echo "Commands:"
echo "  docker-compose logs -f        # View logs"
echo "  docker-compose restart api    # Restart API"
echo "  docker-compose restart bot    # Restart bot"
echo "  docker-compose down           # Stop all"
