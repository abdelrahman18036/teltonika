#!/bin/bash

# Teltonika Django GPS Tracker Reset Script
# This script completely removes and reinstalls the Django + PostgreSQL GPS tracking system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="teltonika"
DB_USER="teltonika"
SERVICE_NAME="teltonika-django"

echo -e "${RED}=== Teltonika Django GPS Tracker RESET Script ===${NC}"
echo -e "${YELLOW}⚠️  WARNING: This will completely remove all data and reinstall the system!${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Confirmation prompt
read -p "Are you sure you want to reset the entire system? This will delete all GPS data! (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Reset cancelled."
    exit 0
fi

# Additional confirmation for database
read -p "This will also DROP the PostgreSQL database '$DB_NAME'. Continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Reset cancelled."
    exit 0
fi

print_status "Starting system reset..."

# Stop services
print_status "Stopping services..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
sudo systemctl disable $SERVICE_NAME 2>/dev/null || true

# Remove systemd service
print_status "Removing systemd service..."
sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload

# Remove nginx configuration
print_status "Removing nginx configuration..."
sudo rm -f /etc/nginx/sites-enabled/teltonika-django
sudo rm -f /etc/nginx/sites-available/teltonika-django
sudo systemctl reload nginx 2>/dev/null || true

# Drop PostgreSQL database and user
print_status "Dropping PostgreSQL database and user..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" 2>/dev/null || true

# Remove log directories
print_status "Removing log directories..."
sudo rm -rf /var/log/teltonika-django
rm -rf logs

# Remove virtual environment
print_status "Removing Python virtual environment..."
rm -rf venv

# Remove Django generated files
print_status "Removing Django generated files..."
rm -rf staticfiles
rm -rf gps_tracking/migrations
rm -rf gps_tracking/__pycache__
rm -rf teltonika_tracker/__pycache__
rm -rf gps_tracking/management
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove environment file
print_status "Removing environment configuration..."
rm -f .env

# Remove integration patch
print_status "Removing integration files..."
rm -f ../teltonika_django_patch.py

# Clean up any temporary files
print_status "Cleaning up temporary files..."
rm -rf .pytest_cache 2>/dev/null || true
rm -rf .coverage 2>/dev/null || true

print_status "Reset completed! System has been completely removed."
echo ""
echo -e "${BLUE}To reinstall the system, run:${NC}"
echo "  ./install.sh"
echo ""
echo -e "${YELLOW}Services that are still running (if needed):${NC}"
echo "• PostgreSQL (for other applications)"
echo "• Redis (for other applications)" 
echo "• Nginx (for other applications)"
echo ""
echo -e "${YELLOW}To completely remove PostgreSQL (⚠️  affects other applications):${NC}"
echo "  sudo apt remove --purge postgresql postgresql-contrib"
echo ""
echo -e "${YELLOW}To completely remove Redis (⚠️  affects other applications):${NC}"
echo "  sudo apt remove --purge redis-server"
echo ""
print_status "Reset completed successfully!" 