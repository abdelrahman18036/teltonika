#!/bin/bash

# Teltonika Django GPS Tracker Installation Script
# This script sets up the complete Django + PostgreSQL GPS tracking system

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
DB_PASSWORD="teltonika"
DJANGO_PORT="8000"
SERVICE_NAME="teltonika-django"

echo -e "${BLUE}=== Teltonika Django GPS Tracker Installation ===${NC}"
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

# Check if running as root and handle user creation
if [[ $EUID -eq 0 ]]; then
    print_status "Running as root. Creating teltonika user and switching to it..."
    
    # Create teltonika user if it doesn't exist
    if ! id "teltonika" &>/dev/null; then
        print_status "Creating teltonika user..."
        useradd -m -s /bin/bash teltonika
        usermod -aG sudo teltonika
        print_status "User 'teltonika' created and added to sudo group"
    else
        print_warning "User 'teltonika' already exists"
    fi
    
    # Copy project files to teltonika user home
    print_status "Setting up project directory for teltonika user..."
    if [[ -d "/home/teltonika/teltonika-django" ]]; then
        print_warning "Project directory already exists, updating files..."
        rm -rf /home/teltonika/teltonika-django
    fi
    
    cp -r "$(pwd)" /home/teltonika/
    chown -R teltonika:teltonika /home/teltonika/teltonika-django
    chmod +x /home/teltonika/teltonika-django/install.sh
    chmod +x /home/teltonika/teltonika-django/reset.sh
    
    print_status "Switching to teltonika user and continuing installation..."
    exec su - teltonika -c "cd teltonika-django && ./install.sh"
fi

USER_HOME="$HOME"
WEB_USER="www-data"
CURRENT_USER=$(whoami)

# Check if we're in the correct directory
if [[ ! -f "manage.py" ]]; then
    print_error "manage.py not found. Please run this script from the teltonika-django directory."
    exit 1
fi

print_status "Starting installation process..."

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt install -y \
    postgresql postgresql-contrib \
    python3 python3-pip python3-venv \
    redis-server \
    nginx \
    supervisor \
    git curl wget \
    build-essential \
    libpq-dev

# Install Python dependencies
print_status "Creating Python virtual environment..."
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
fi

print_status "Activating virtual environment and installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Setup PostgreSQL database
print_status "Setting up PostgreSQL database..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    print_status "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Create database and user
print_status "Creating database and user..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || print_warning "Database $DB_NAME already exists"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || print_warning "User $DB_USER already exists"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Fix PostgreSQL permissions for Django
print_status "Setting up PostgreSQL permissions..."
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT USAGE ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT CREATE ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "ALTER USER $DB_USER CREATEDB;"
sudo -u postgres psql -d $DB_NAME -c "ALTER SCHEMA public OWNER TO $DB_USER;"

# Setup Redis
print_status "Setting up Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Create environment file
print_status "Creating environment configuration..."
if [[ ! -f ".env" ]]; then
    cp env.example .env
    print_status "Created .env file from env.example"
    print_warning "Please review and update .env file if needed"
else
    print_warning ".env file already exists, skipping creation"
fi

# Django setup
print_status "Setting up Django application..."

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
print_status "Running database migrations..."
python manage.py makemigrations gps_tracking
python manage.py migrate

# Check if migrations were successful
if [[ $? -ne 0 ]]; then
    print_error "Database migrations failed. Trying to fix common issues..."
    
    # Try to fix the numeric field overflow issue
    print_status "Applying manual fixes for database schema..."
    python manage.py shell << 'EOF'
import os
import django
from django.db import connection

# Try to drop and recreate problematic tables if they exist
with connection.cursor() as cursor:
    try:
        cursor.execute("DROP TABLE IF EXISTS io_parameters CASCADE;")
        print("Dropped io_parameters table")
    except Exception as e:
        print(f"Could not drop io_parameters table: {e}")
        
    try:
        cursor.execute("DROP TABLE IF EXISTS gps_records CASCADE;")
        print("Dropped gps_records table")
    except Exception as e:
        print(f"Could not drop gps_records table: {e}")
        
print("Manual fixes applied")
EOF

    # Try migrations again
    print_status "Retrying database migrations..."
    python manage.py migrate
fi

# Create superuser
print_status "Creating Django superuser..."
echo "Please create a superuser for Django admin:"
python manage.py createsuperuser

# Load initial data (IO parameters)
print_status "Loading initial IO parameter data..."
python manage.py shell << EOF
from gps_tracking.models import IOParameter

# Create some common IO parameters
io_params = [
    {239: ("Ignition", "boolean", "", 0, 1)},
    {240: ("Movement", "boolean", "", 0, 1)},
    {21: ("GSM Signal", "integer", "scale", 0, 5)},
    {69: ("GNSS Status", "integer", "", 0, 3)},
    {181: ("GNSS PDOP", "decimal", "", 0, 500)},
    {182: ("GNSS HDOP", "decimal", "", 0, 500)},
    {66: ("External Voltage", "decimal", "V", 0, 65535)},
    {67: ("Battery Voltage", "decimal", "V", 0, 65535)},
    {113: ("Battery Level", "integer", "%", 0, 100)},
    {16: ("Total Odometer", "decimal", "km", 0, 999999999)},
    {90: ("Door Status (CAN)", "integer", "", 0, 255)},
    {100: ("Program Number", "integer", "", 0, 65535)},
]

for param_dict in io_params:
    for io_id, (name, data_type, unit, min_val, max_val) in param_dict.items():
        IOParameter.objects.get_or_create(
            io_id=io_id,
            defaults={
                'name': name,
                'data_type': data_type,
                'unit': unit,
                'min_value': min_val,
                'max_value': max_val,
            }
        )

print("Loaded initial IO parameters")
EOF

# Create systemd service file
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Teltonika Django GPS Tracker
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=$(whoami)
Group=www-data
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:$DJANGO_PORT teltonika_tracker.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
print_status "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/teltonika-django > /dev/null << EOF
server {
    listen 80;
    server_name localhost;

    location /static/ {
        alias $(pwd)/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:$DJANGO_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable nginx site
if [[ ! -L "/etc/nginx/sites-enabled/teltonika-django" ]]; then
    sudo ln -s /etc/nginx/sites-available/teltonika-django /etc/nginx/sites-enabled/
fi

# Test nginx configuration
sudo nginx -t

# Create log directories
print_status "Creating log directories..."
mkdir -p logs
sudo mkdir -p /var/log/teltonika-django
sudo chown $(whoami):$(whoami) /var/log/teltonika-django

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME
sudo systemctl reload nginx

# Create integration patch for existing Teltonika service
print_status "Creating integration patch for existing Teltonika service..."
cat > ../teltonika_django_patch.py << 'EOF'
"""
Patch file to add Django PostgreSQL integration to existing Teltonika service.
Copy this code into your existing teltonika_service.py file.
"""

# Add this import at the top of teltonika_service.py
import sys
import os
sys.path.append('/path/to/teltonika-django')  # Update this path
from django_integration import create_db_integration

# Add this to the TeltonikaService.__init__ method
self.db_integration = create_db_integration('http://localhost:8000')

# Add this method to the TeltonikaService class
def store_in_database(self, imei, timestamp, gps_data, io_data, priority=None, event_io_id=None):
    """Store GPS data in PostgreSQL database via Django API"""
    try:
        success = self.db_integration.store_gps_record(
            imei=imei,
            timestamp=timestamp,
            gps_data=gps_data,
            io_data=io_data,
            priority=priority,
            event_io_id=event_io_id
        )
        if success:
            self.logger.debug(f"Successfully stored GPS data for {imei} in database")
        else:
            self.logger.warning(f"Failed to store GPS data for {imei} in database")
    except Exception as e:
        self.logger.error(f"Error storing GPS data in database: {e}")

# Modify the log_gps_data method to also store in database
# Add this line at the end of log_gps_data method:
# self.store_in_database(imei, timestamp, gps_data, io_data, priority, event_io_id)
EOF

# Create management commands
print_status "Creating management commands..."
mkdir -p gps_tracking/management
mkdir -p gps_tracking/management/commands
touch gps_tracking/management/__init__.py
touch gps_tracking/management/commands/__init__.py

cat > gps_tracking/management/commands/monitor_devices.py << 'EOF'
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from gps_tracking.models import Device, DeviceStatus

class Command(BaseCommand):
    help = 'Monitor device connectivity and update online status'

    def handle(self, *args, **options):
        # Mark devices as offline if no data received in last 30 minutes
        offline_threshold = timezone.now() - timedelta(minutes=30)
        
        offline_count = DeviceStatus.objects.filter(
            last_seen__lt=offline_threshold,
            is_online=True
        ).update(is_online=False)
        
        if offline_count > 0:
            self.stdout.write(f'Marked {offline_count} devices as offline')
        
        # Show current status
        total_devices = Device.objects.filter(is_active=True).count()
        online_devices = DeviceStatus.objects.filter(is_online=True).count()
        
        self.stdout.write(f'Total active devices: {total_devices}')
        self.stdout.write(f'Online devices: {online_devices}')
EOF

# Set permissions
print_status "Setting permissions..."
sudo chown -R $(whoami):www-data .
sudo chmod -R 755 .

# Final status check
print_status "Checking service status..."
sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    print_status "✅ Django service is running"
else
    print_error "❌ Django service failed to start"
    echo "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
fi

if systemctl is-active --quiet nginx; then
    print_status "✅ Nginx is running"
else
    print_error "❌ Nginx failed to start"
fi

if systemctl is-active --quiet postgresql; then
    print_status "✅ PostgreSQL is running"
else
    print_error "❌ PostgreSQL is not running"
fi

if systemctl is-active --quiet redis-server; then
    print_status "✅ Redis is running"
else
    print_error "❌ Redis is not running"
fi

# Show useful information
echo ""
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo ""
echo -e "${BLUE}Django Application:${NC} http://localhost/"
echo -e "${BLUE}Django Admin:${NC} http://localhost/admin/"
echo -e "${BLUE}API Root:${NC} http://localhost/api/"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "• View Django logs: sudo journalctl -u $SERVICE_NAME -f"
echo "• Restart Django: sudo systemctl restart $SERVICE_NAME"
echo "• Check status: sudo systemctl status $SERVICE_NAME"
echo "• Monitor devices: python manage.py monitor_devices"
echo "• Django shell: python manage.py shell"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update the existing Teltonika service to use database integration"
echo "2. Copy ../teltonika_django_patch.py content to your teltonika_service.py"
echo "3. Update the path in the patch file to point to this Django directory"
echo "4. Restart the Teltonika GPS service"
echo ""
print_status "Installation completed successfully!" 