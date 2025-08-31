#!/bin/bash

# Teltonika GPS Tracker Update Script (Fixed to match install.sh)
# This script updates the production deployment with new code changes
# Usage: bash update_fixed_v2.sh

set -e  # Exit on any error

echo "=== Teltonika GPS Tracker Update Script ==="
echo "Starting update process..."

# Configuration - MATCHING install.sh exactly
REPO_DIR="/root/teltonika"
DJANGO_DIR="/opt/teltonika/django"
SERVICE_DIR="/opt/teltonika/service"
DJANGO_SERVICE="teltonika-django"
TELTONIKA_SERVICE="teltonika"
TELTONIKA_USER="teltonika"

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

# Check if teltonika user exists
if ! getent passwd "$TELTONIKA_USER" >/dev/null 2>&1; then
    print_warning "User '$TELTONIKA_USER' may not exist, attempting to create..."
    if ! useradd --system --shell /bin/bash --home-dir /opt/teltonika --create-home teltonika 2>/dev/null; then
        print_status "User '$TELTONIKA_USER' already exists or was created successfully"
    fi
fi

# Verify user exists now
if getent passwd "$TELTONIKA_USER" >/dev/null 2>&1; then
    print_status "User '$TELTONIKA_USER' verified"
else
    print_error "Failed to verify user '$TELTONIKA_USER'"
    exit 1
fi

# Ensure all required directories exist
print_status "Ensuring required directories exist..."
mkdir -p /opt/teltonika/service
mkdir -p /opt/teltonika/django
mkdir -p /opt/teltonika/logs
mkdir -p /opt/teltonika/data
mkdir -p /var/log/teltonika
mkdir -p /var/lib/teltonika

# Check if virtual environment exists, create if needed
if [ ! -d "/opt/teltonika/venv" ]; then
    print_status "Creating Python virtual environment..."
    sudo -u $TELTONIKA_USER python3 -m venv /opt/teltonika/venv
    sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/pip install --upgrade pip
    print_status "Virtual environment created"
fi

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
    # Remove old files and copy new ones
    rm -rf $DJANGO_DIR/*
    cp -r $REPO_DIR/teltonika-django/* $DJANGO_DIR/
    chown -R $TELTONIKA_USER:$TELTONIKA_USER $DJANGO_DIR
    chmod +x $DJANGO_DIR/manage.py
    print_status "Django application updated"
else
    print_error "Django source directory not found in repository"
    exit 1
fi

# Step 4: Copy Teltonika service
print_status "Updating Teltonika service..."
if [ -d "$REPO_DIR/teltonika-service" ]; then
    # Remove old files and copy new ones
    rm -rf $SERVICE_DIR/*
    cp -r $REPO_DIR/teltonika-service/* $SERVICE_DIR/
    chown -R $TELTONIKA_USER:$TELTONIKA_USER $SERVICE_DIR
    chmod +x $SERVICE_DIR/*.py
    print_status "Teltonika service updated"
else
    print_error "Teltonika service source directory not found in repository"
    exit 1
fi

# Step 5: Update systemd service files with ORIGINAL paths
print_status "Updating systemd service files..."

# Create the exact systemd service files from install.sh
cat > /etc/systemd/system/teltonika.service << 'EOF'
[Unit]
Description=Teltonika GPS Tracking Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/service
ExecStart=/opt/teltonika/venv/bin/python teltonika_service.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Performance settings
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/teltonika-django.service << 'EOF'
[Unit]
Description=Teltonika Django API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/django
ExecStart=/opt/teltonika/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 teltonika_gps.wsgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Performance settings
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
print_status "Systemd service files updated with original configuration"

# Step 6: Install Python dependencies using the virtual environment
print_status "Installing Python dependencies..."

# Install/update Django dependencies
if [ -f "$DJANGO_DIR/requirements.txt" ]; then
    print_status "Installing Django requirements..."
    cd $DJANGO_DIR
    sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/pip install -r requirements.txt
    print_status "Django dependencies installed"
fi

# Install/update service dependencies (if file exists)
if [ -f "$SERVICE_DIR/requirements.txt" ]; then
    print_status "Installing service requirements..."
    cd $SERVICE_DIR
    sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/pip install -r requirements.txt
    print_status "Service dependencies installed"
fi

# Step 7: Handle database migrations
print_status "Handling database migrations..."
cd $DJANGO_DIR

# Make migrations and migrate
print_status "Creating and applying migrations..."
sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/python manage.py makemigrations || print_warning "No new migrations to create"
sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/python manage.py migrate || print_warning "Migration failed - check manually"

# Step 8: Collect static files
print_status "Collecting static files..."
sudo -u $TELTONIKA_USER /opt/teltonika/venv/bin/python manage.py collectstatic --noinput || print_warning "Static files collection failed"

# Step 9: Ensure proper permissions (like install.sh)
print_status "Setting up directories and permissions..."
chown -R $TELTONIKA_USER:$TELTONIKA_USER /opt/teltonika
chown -R $TELTONIKA_USER:$TELTONIKA_USER /var/log/teltonika
chown -R $TELTONIKA_USER:$TELTONIKA_USER /var/lib/teltonika
chmod 755 /opt/teltonika
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
print_status "System updated to match original installation configuration"
print_status "Backup location: $BACKUP_DIR"
print_status "Check services with: systemctl status teltonika-django teltonika"
print_status "View logs with: journalctl -u teltonika-django -u teltonika -f"
print_status "Monitor system: teltonika monitor"
print_status "Test commands: teltonika command"

echo ""
echo "🎉 Update completed successfully!"
echo ""
echo "📊 Quick Status Check:"
echo "   Django API: http://$(hostname -I | awk '{print $1}'):8000/admin/"
echo "   GPS Service: $(hostname -I | awk '{print $1}'):5000"
echo "   Command API: $(hostname -I | awk '{print $1}'):5001"
echo ""
echo "If you encounter issues:"
echo "1. Check logs: journalctl -u teltonika -f"
echo "2. Check permissions: ls -la /var/log/teltonika/"
echo "3. Restore backup if needed:"
echo "   systemctl stop teltonika-django teltonika"
echo "   rm -rf $DJANGO_DIR $SERVICE_DIR"
echo "   mv $BACKUP_DIR/teltonika-django-backup $DJANGO_DIR"
echo "   mv $BACKUP_DIR/teltonika-service-backup $SERVICE_DIR"
echo "   chown -R teltonika:teltonika /opt/teltonika"
echo "   systemctl start teltonika-django teltonika"
