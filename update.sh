#!/bin/bash

# Teltonika GPS Tracker Update Script
# This script updates the production deployment with new code changes
# Usage: ./update.sh

set -e  # Exit on any error

echo "=== Teltonika GPS Tracker Update Script ==="
echo "Starting update process..."

# Configuration
REPO_DIR="/root/teltonika"
DJANGO_DIR="/opt/teltonika-django"
SERVICE_DIR="/opt/teltonika-service"
DJANGO_SERVICE="teltonika-django"
TELTONIKA_SERVICE="teltonika"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
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

# Step 2: Backup current installations (optional)
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
    # Create directory if it doesn't exist
    mkdir -p $DJANGO_DIR
    
    # Copy Django files
    cp -r $REPO_DIR/teltonika-django/* $DJANGO_DIR/
    
    # Set proper ownership
    chown -R root:root $DJANGO_DIR
    
    # Set execute permissions on manage.py
    chmod +x $DJANGO_DIR/manage.py
    
    print_status "Django application updated"
else
    print_error "Django source directory not found in repository"
    exit 1
fi

# Step 4: Copy Teltonika service
print_status "Updating Teltonika service..."
if [ -d "$REPO_DIR/teltonika-service" ]; then
    # Create directory if it doesn't exist
    mkdir -p $SERVICE_DIR
    
    # Copy service files
    cp -r $REPO_DIR/teltonika-service/* $SERVICE_DIR/
    
    # Set proper ownership
    chown -R root:root $SERVICE_DIR
    
    # Set execute permissions on Python files
    chmod +x $SERVICE_DIR/*.py
    
    print_status "Teltonika service updated"
else
    print_error "Teltonika service source directory not found in repository"
    exit 1
fi

# Step 5: Update systemd service files
print_status "Updating systemd service files..."

# Copy Django service file
if [ -f "$DJANGO_DIR/teltonika-django.service" ]; then
    cp $DJANGO_DIR/teltonika-django.service /etc/systemd/system/
    print_status "Django service file updated"
fi

# Copy Teltonika service file
if [ -f "$SERVICE_DIR/teltonika.service" ]; then
    cp $SERVICE_DIR/teltonika.service /etc/systemd/system/
    print_status "Teltonika service file updated"
fi

# Reload systemd
systemctl daemon-reload

# Step 6: Install/Update Python dependencies
print_status "Installing Python dependencies..."

# Install Django dependencies
if [ -f "$DJANGO_DIR/requirements.txt" ]; then
    print_status "Installing Django requirements..."
    cd $DJANGO_DIR
    pip3 install -r requirements.txt
    print_status "Django dependencies installed"
fi

# Install service dependencies (if requirements file exists)
if [ -f "$SERVICE_DIR/requirements.txt" ]; then
    print_status "Installing service requirements..."
    cd $SERVICE_DIR
    pip3 install -r requirements.txt
    print_status "Service dependencies installed"
fi

# Step 7: Handle database migrations
print_status "Handling database migrations..."
cd $DJANGO_DIR

# Check if there are new migrations
print_status "Checking for new migrations..."
python3 manage.py showmigrations | grep '\[ \]' && HAS_NEW_MIGRATIONS=true || HAS_NEW_MIGRATIONS=false

if [ "$HAS_NEW_MIGRATIONS" = true ]; then
    print_status "New migrations found. Creating and applying migrations..."
    
    # Make migrations
    python3 manage.py makemigrations
    
    # Apply migrations
    python3 manage.py migrate
    
    print_status "Database migrations completed"
else
    print_status "No new migrations needed"
fi

# Step 8: Collect static files (if needed)
if [ -d "$DJANGO_DIR/static" ] || grep -q "STATIC_" $DJANGO_DIR/*/settings.py 2>/dev/null; then
    print_status "Collecting static files..."
    python3 manage.py collectstatic --noinput
fi

# Step 9: Create necessary directories and set permissions
print_status "Setting up directories and permissions..."

# Create log directories
mkdir -p /var/log/teltonika
mkdir -p /var/lib/teltonika

# Set permissions
chown -R root:root /var/log/teltonika
chown -R root:root /var/lib/teltonika
chmod 755 /var/log/teltonika
chmod 755 /var/lib/teltonika

# Step 10: Enable and start services
print_status "Starting services..."

# Enable services
systemctl enable $DJANGO_SERVICE
systemctl enable $TELTONIKA_SERVICE

# Start Django service
print_status "Starting Django service..."
if systemctl start $DJANGO_SERVICE; then
    print_status "Django service started successfully"
else
    print_error "Failed to start Django service"
    print_status "Checking Django service status..."
    systemctl status $DJANGO_SERVICE --no-pager
fi

# Wait a moment for Django to start
sleep 3

# Start Teltonika service
print_status "Starting Teltonika service..."
if systemctl start $TELTONIKA_SERVICE; then
    print_status "Teltonika service started successfully"
else
    print_error "Failed to start Teltonika service"
    print_status "Checking Teltonika service status..."
    systemctl status $TELTONIKA_SERVICE --no-pager
fi

# Step 11: Verify services are running
print_status "Verifying services..."
sleep 5

# Check Django service
if systemctl is-active --quiet $DJANGO_SERVICE; then
    print_status "✓ Django service is running"
else
    print_error "✗ Django service is not running"
fi

# Check Teltonika service
if systemctl is-active --quiet $TELTONIKA_SERVICE; then
    print_status "✓ Teltonika service is running"
else
    print_error "✗ Teltonika service is not running"
fi

# Step 12: Test connectivity
print_status "Testing service connectivity..."

# Test Django API
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/ | grep -q "200\|404"; then
    print_status "✓ Django API is responding"
else
    print_warning "✗ Django API may not be responding (this might be normal if API endpoints are different)"
fi

# Test Teltonika service ports
if netstat -tuln | grep -q ":5000"; then
    print_status "✓ Teltonika GPS service is listening on port 5000"
else
    print_warning "✗ Teltonika GPS service is not listening on port 5000"
fi

if netstat -tuln | grep -q ":5001"; then
    print_status "✓ Teltonika Command API is listening on port 5001"
else
    print_warning "✗ Teltonika Command API is not listening on port 5001"
fi

# Step 13: Show service status
print_status "=== Final Service Status ==="
echo "Django Service:"
systemctl status $DJANGO_SERVICE --no-pager -l

echo -e "\nTeltonika Service:"
systemctl status $TELTONIKA_SERVICE --no-pager -l

# Step 14: Show logs location
print_status "=== Log Information ==="
echo "Service logs can be viewed with:"
echo "  Django: journalctl -u $DJANGO_SERVICE -f"
echo "  Teltonika: journalctl -u $TELTONIKA_SERVICE -f"
echo "  Application logs: /var/log/teltonika/"

# Step 15: Show backup information
print_status "=== Backup Information ==="
echo "Previous installation backed up to: $BACKUP_DIR"
echo "To restore backup if needed:"
echo "  sudo systemctl stop $DJANGO_SERVICE $TELTONIKA_SERVICE"
echo "  sudo rm -rf $DJANGO_DIR $SERVICE_DIR"
echo "  sudo mv $BACKUP_DIR/teltonika-django-backup $DJANGO_DIR"
echo "  sudo mv $BACKUP_DIR/teltonika-service-backup $SERVICE_DIR"
echo "  sudo systemctl start $DJANGO_SERVICE $TELTONIKA_SERVICE"

print_status "=== Update Complete ==="
echo "Your Teltonika GPS tracker has been updated successfully!"
echo ""
echo "Quick commands for monitoring:"
echo "  Check all services: systemctl status teltonika-django teltonika"
echo "  View logs: journalctl -u teltonika-django -u teltonika -f"
echo "  Test Django: curl http://localhost:8000/api/"
echo "  Test command: teltonika status"
echo ""
echo "If you encounter any issues, check the logs or restore from backup."
