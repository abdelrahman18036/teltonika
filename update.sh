#!/bin/bash

# Teltonika GPS Tracker Update Script (Fixed Version)
# This script updates the production deployment with new code changes
# Usage: bash update_fixed.sh

set -e  # Exit on any error

echo "=== Teltonika GPS Tracker Update Script ==="
echo "Starting update process..."

# Configuration
REPO_DIR="/root/teltonika"
DJANGO_DIR="/opt/teltonika-django"
SERVICE_DIR="/opt/teltonika-service"
DJANGO_SERVICE="teltonika-django"
TELTONIKA_SERVICE="teltonika"

# Simple color codes that work in sh
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}[WARNING]${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Check if repo directory exists
if [ ! -d "$REPO_DIR" ]; then
    print_error "Repository directory $REPO_DIR not found!"
    print_error "Please ensure you have cloned the repository to /root/teltonika"
    exit 1
fi

print_status "Repository found at $REPO_DIR"

# Step 1: Stop services
print_status "Stopping services..."
systemctl stop $DJANGO_SERVICE 2>/dev/null || print_warning "Django service was not running"
systemctl stop $TELTONIKA_SERVICE 2>/dev/null || print_warning "Teltonika service was not running"

# Step 2: Backup current installations
print_status "Creating backup of current installation..."
BACKUP_DIR="/opt/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR
if [ -d "$DJANGO_DIR" ]; then
    cp -r $DJANGO_DIR $BACKUP_DIR/teltonika-django-backup
fi
if [ -d "$SERVICE_DIR" ]; then
    cp -r $SERVICE_DIR $BACKUP_DIR/teltonika-service-backup
fi
print_status "Backup created at $BACKUP_DIR"

# Step 3: Copy Django application
print_status "Updating Django application..."
if [ -d "$REPO_DIR/teltonika-django" ]; then
    mkdir -p $DJANGO_DIR
    cp -r $REPO_DIR/teltonika-django/* $DJANGO_DIR/
    chown -R root:root $DJANGO_DIR
    chmod +x $DJANGO_DIR/manage.py
    print_status "Django application updated"
else
    print_error "Django source directory not found in repository"
    exit 1
fi

# Step 4: Copy Teltonika service
print_status "Updating Teltonika service..."
if [ -d "$REPO_DIR/teltonika-service" ]; then
    mkdir -p $SERVICE_DIR
    cp -r $REPO_DIR/teltonika-service/* $SERVICE_DIR/
    chown -R root:root $SERVICE_DIR
    chmod +x $SERVICE_DIR/*.py
    print_status "Teltonika service updated"
else
    print_error "Teltonika service source directory not found in repository"
    exit 1
fi

# Step 5: Update systemd service files
print_status "Updating systemd service files..."
if [ -f "$DJANGO_DIR/teltonika-django.service" ]; then
    cp $DJANGO_DIR/teltonika-django.service /etc/systemd/system/
    print_status "Django service file updated"
fi

if [ -f "$SERVICE_DIR/teltonika.service" ]; then
    cp $SERVICE_DIR/teltonika.service /etc/systemd/system/
    print_status "Teltonika service file updated"
fi

systemctl daemon-reload

# Step 6: Install Python dependencies (with fallback options)
print_status "Installing Python dependencies..."

install_requirements() {
    local req_file="$1"
    local name="$2"
    
    if [ -f "$req_file" ]; then
        print_status "Installing $name requirements..."
        cd "$(dirname "$req_file")"
        
        # Try different methods
        if pip3 install -r "$req_file" --break-system-packages >/dev/null 2>&1; then
            print_status "$name dependencies installed successfully"
        elif pip3 install -r "$req_file" --user >/dev/null 2>&1; then
            print_status "$name dependencies installed to user directory"
        else
            print_warning "Could not install $name dependencies automatically"
            print_warning "You may need to install manually: pip3 install -r $req_file --break-system-packages"
        fi
    fi
}

install_requirements "$DJANGO_DIR/requirements.txt" "Django"
install_requirements "$SERVICE_DIR/requirements.txt" "Service"

# Step 7: Handle database migrations
print_status "Handling database migrations..."
cd $DJANGO_DIR

# Make migrations and migrate
print_status "Creating and applying migrations..."
python3 manage.py makemigrations || print_warning "No new migrations to create"
python3 manage.py migrate || print_warning "Migration failed - check manually"

# Step 8: Collect static files (if needed)
if [ -d "$DJANGO_DIR/static" ] || grep -q "STATIC_" $DJANGO_DIR/*/settings.py 2>/dev/null; then
    print_status "Collecting static files..."
    python3 manage.py collectstatic --noinput || print_warning "Static files collection failed"
fi

# Step 9: Create necessary directories
print_status "Setting up directories and permissions..."
mkdir -p /var/log/teltonika
mkdir -p /var/lib/teltonika
chown -R root:root /var/log/teltonika
chown -R root:root /var/lib/teltonika
chmod 755 /var/log/teltonika
chmod 755 /var/lib/teltonika

# Step 10: Start services
print_status "Starting services..."
systemctl enable $DJANGO_SERVICE
systemctl enable $TELTONIKA_SERVICE

print_status "Starting Django service..."
if systemctl start $DJANGO_SERVICE; then
    print_status "Django service started successfully"
else
    print_error "Failed to start Django service"
    systemctl status $DJANGO_SERVICE --no-pager
fi

sleep 3

print_status "Starting Teltonika service..."
if systemctl start $TELTONIKA_SERVICE; then
    print_status "Teltonika service started successfully"
else
    print_error "Failed to start Teltonika service"
    systemctl status $TELTONIKA_SERVICE --no-pager
fi

# Step 11: Verify services
print_status "Verifying services..."
sleep 5

if systemctl is-active --quiet $DJANGO_SERVICE; then
    print_status "✓ Django service is running"
else
    print_error "✗ Django service is not running"
fi

if systemctl is-active --quiet $TELTONIKA_SERVICE; then
    print_status "✓ Teltonika service is running"
else
    print_error "✗ Teltonika service is not running"
fi

# Step 12: Test connectivity
print_status "Testing connectivity..."

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200\|404\|302"; then
    print_status "✓ Django is responding"
else
    print_warning "✗ Django may not be responding"
fi

if netstat -tuln 2>/dev/null | grep -q ":5000" || ss -tuln 2>/dev/null | grep -q ":5000"; then
    print_status "✓ Teltonika GPS service is listening on port 5000"
else
    print_warning "✗ Teltonika GPS service is not listening on port 5000"
fi

if netstat -tuln 2>/dev/null | grep -q ":5001" || ss -tuln 2>/dev/null | grep -q ":5001"; then
    print_status "✓ Teltonika Command API is listening on port 5001"
else
    print_warning "✗ Teltonika Command API is not listening on port 5001"
fi

# Final status
print_status "=== Update Complete ==="
print_status "Backup location: $BACKUP_DIR"
print_status "Check services with: systemctl status teltonika-django teltonika"
print_status "View logs with: journalctl -u teltonika-django -u teltonika -f"

echo ""
echo "If you encounter issues:"
echo "1. Check logs: journalctl -u teltonika-django -f"
echo "2. Install missing packages: pip3 install package_name --break-system-packages"
echo "3. Restore backup if needed:"
echo "   systemctl stop teltonika-django teltonika"
echo "   rm -rf $DJANGO_DIR $SERVICE_DIR"
echo "   mv $BACKUP_DIR/teltonika-django-backup $DJANGO_DIR"
echo "   mv $BACKUP_DIR/teltonika-service-backup $SERVICE_DIR"
echo "   systemctl start teltonika-django teltonika"
