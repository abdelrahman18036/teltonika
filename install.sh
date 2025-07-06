#!/bin/bash

# Unified Teltonika GPS Tracking System Installation Script
# Installs both GPS tracker service and Django web application
# Run with sudo: sudo bash install.sh

set -e

echo "🚀 Installing Unified Teltonika GPS Tracking System..."
echo "===================================================="
echo "This will install:"
echo "  📡 Teltonika GPS Tracker Service (Port 5000)"
echo "  🌐 Django Web Application (Port 8000)"
echo "  🗄️  PostgreSQL Database"
echo "  📊 Admin Interface & REST API"
echo "===================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script with sudo"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update system
echo "🔄 Updating system packages..."
apt update && apt upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    jq \
    curl \
    wget \
    build-essential \
    libpq-dev \
    software-properties-common

echo "✅ System dependencies installed"

# Create teltonika user and group
echo "👤 Creating teltonika user and group..."
if ! id "teltonika" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir /opt/teltonika --create-home teltonika
    echo "✅ User 'teltonika' created"
else
    echo "ℹ️  User 'teltonika' already exists"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p /opt/teltonika/{gps-service,django-app}
mkdir -p /var/log/teltonika
mkdir -p /var/lib/teltonika

# Set permissions
chown -R teltonika:teltonika /opt/teltonika
chown -R teltonika:teltonika /var/log/teltonika
chown -R teltonika:teltonika /var/lib/teltonika

chmod 755 /opt/teltonika
chmod 755 /var/log/teltonika
chmod 755 /var/lib/teltonika

echo "✅ Directories created with proper permissions"

# Setup PostgreSQL
echo "🗄️  Setting up PostgreSQL database..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE IF NOT EXISTS teltonika;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER teltonika WITH PASSWORD 'teltonika123';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teltonika TO teltonika;" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER teltonika CREATEDB;" 2>/dev/null || true

echo "✅ PostgreSQL database configured"

# Setup Redis
echo "🔴 Setting up Redis..."
systemctl start redis-server
systemctl enable redis-server

echo "✅ Redis configured"

# Install GPS Tracker Service
echo "📡 Installing GPS Tracker Service..."
if [ -f "$SCRIPT_DIR/teltonika-gps-tracker/teltonika_service.py" ]; then
    cp "$SCRIPT_DIR/teltonika-gps-tracker/teltonika_service.py" /opt/teltonika/gps-service/
    chmod +x /opt/teltonika/gps-service/teltonika_service.py
    chown teltonika:teltonika /opt/teltonika/gps-service/teltonika_service.py
    echo "✅ GPS service files installed"
else
    echo "❌ GPS service file not found at $SCRIPT_DIR/teltonika-gps-tracker/teltonika_service.py"
    exit 1
fi

# Install Django Application
echo "🌐 Installing Django Web Application..."
if [ -d "$SCRIPT_DIR/teltonika-django" ]; then
    # Copy Django files
    cp -r "$SCRIPT_DIR/teltonika-django"/* /opt/teltonika/django-app/
    chown -R teltonika:teltonika /opt/teltonika/django-app
    
    # Create Python virtual environment
    echo "🐍 Creating Python virtual environment..."
    sudo -u teltonika python3 -m venv /opt/teltonika/django-app/venv
    
    # Install Python dependencies
    echo "📦 Installing Python dependencies..."
    sudo -u teltonika /opt/teltonika/django-app/venv/bin/pip install --upgrade pip
    sudo -u teltonika /opt/teltonika/django-app/venv/bin/pip install -r /opt/teltonika/django-app/requirements.txt
    
    echo "✅ Django application installed"
else
    echo "❌ Django directory not found at $SCRIPT_DIR/teltonika-django"
    exit 1
fi

# Create Django environment configuration
echo "⚙️  Creating Django environment configuration..."
cat > /opt/teltonika/django-app/.env << 'EOF'
# Django Configuration
SECRET_KEY=teltonika-gps-tracker-secret-key-change-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,*

# Database Configuration
DB_NAME=teltonika
DB_USER=teltonika
DB_PASSWORD=teltonika123
DB_HOST=localhost
DB_PORT=5432

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API Configuration
CORS_ALLOW_ALL_ORIGINS=True
EOF

chown teltonika:teltonika /opt/teltonika/django-app/.env

# Run Django migrations and setup
echo "🗄️  Setting up Django database..."
cd /opt/teltonika/django-app
sudo -u teltonika /opt/teltonika/django-app/venv/bin/python manage.py migrate

# Create Django superuser (non-interactive)
echo "👤 Creating Django superuser..."
sudo -u teltonika /opt/teltonika/django-app/venv/bin/python manage.py shell << 'EOF'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print("Superuser 'admin' created with password 'admin123'")
else:
    print("Superuser 'admin' already exists")
EOF

# Collect static files
echo "📁 Collecting static files..."
sudo -u teltonika /opt/teltonika/django-app/venv/bin/python manage.py collectstatic --noinput

echo "✅ Django setup completed"

# Create systemd service for GPS tracker
echo "⚙️  Installing GPS tracker systemd service..."
cat > /etc/systemd/system/teltonika-gps.service << 'EOF'
[Unit]
Description=Teltonika GPS Tracking Service
After=network.target

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/gps-service
ExecStart=/usr/bin/python3 /opt/teltonika/gps-service/teltonika_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Django
echo "⚙️  Installing Django systemd service..."
cat > /etc/systemd/system/teltonika-django.service << 'EOF'
[Unit]
Description=Teltonika Django Web Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/django-app
ExecStart=/opt/teltonika/django-app/venv/bin/gunicorn --bind 127.0.0.1:8000 teltonika_tracker.wsgi:application
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Create Nginx configuration
echo "🌐 Setting up Nginx reverse proxy..."
cat > /etc/nginx/sites-available/teltonika << 'EOF'
server {
    listen 80;
    server_name _;

    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /opt/teltonika/django-app/staticfiles/;
        expires 1M;
        access_log off;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/teltonika/django-app/media/;
        expires 1M;
        access_log off;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/teltonika /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Enable and start services
echo "🚀 Starting services..."
systemctl daemon-reload
systemctl enable teltonika-gps
systemctl enable teltonika-django
systemctl enable nginx

systemctl start teltonika-gps
systemctl start teltonika-django
systemctl restart nginx

echo "✅ All services started"

# Create log rotation configuration
echo "🔄 Setting up log rotation..."
cat > /etc/logrotate.d/teltonika << 'EOF'
/var/log/teltonika/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 teltonika teltonika
    postrotate
        systemctl reload teltonika-gps
        systemctl reload teltonika-django
    endscript
}
EOF

echo "✅ Log rotation configured"

# Open firewall ports (if ufw is active)
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    echo "🔥 Opening firewall ports..."
    ufw allow 5000/tcp  # GPS tracker service
    ufw allow 80/tcp    # HTTP
    ufw allow 8000/tcp  # Django development (optional)
    echo "✅ Firewall configured"
fi

# Create integrated monitoring script
echo "📊 Creating monitoring script..."
cat > /opt/teltonika/monitor.sh << 'EOF'
#!/bin/bash

# Unified Teltonika System Monitor Script

echo "📊 Teltonika GPS Tracking System Monitor"
echo "========================================"

# Check service statuses
echo "🔍 Service Status:"
echo "GPS Tracker Service:"
systemctl is-active teltonika-gps
echo "Django Web App:"
systemctl is-active teltonika-django
echo "Nginx:"
systemctl is-active nginx
echo "PostgreSQL:"
systemctl is-active postgresql
echo "Redis:"
systemctl is-active redis-server

echo ""
echo "📁 System Information:"
echo "GPS Service Port: 5000"
echo "Web Interface: http://$(hostname -I | awk '{print $1}')"
echo "Admin Panel: http://$(hostname -I | awk '{print $1}')/admin"
echo "API Docs: http://$(hostname -I | awk '{print $1}')/api"

echo ""
echo "📈 Recent GPS Activity (last 10 lines):"
if [ -f "/var/log/teltonika/teltonika_service.log" ]; then
    tail -10 /var/log/teltonika/teltonika_service.log
else
    echo "No GPS activity log found yet"
fi

echo ""
echo "🌐 Django Application Status:"
if systemctl is-active --quiet teltonika-django; then
    echo "✅ Django is running"
    echo "Admin credentials: admin / admin123"
else
    echo "❌ Django is not running"
fi

echo ""
echo "💾 Disk Usage:"
df -h /var/log/teltonika /var/lib/teltonika /opt/teltonika

echo ""
echo "🔗 Network Connections:"
echo "GPS Service (port 5000):"
netstat -tlnp | grep :5000 || echo "No connections on port 5000"
echo "Web Service (port 8000):"
netstat -tlnp | grep :8000 || echo "No connections on port 8000"
echo "HTTP (port 80):"
netstat -tlnp | grep :80 || echo "No connections on port 80"

echo ""
echo "📊 Database Status:"
sudo -u postgres psql -d teltonika -c "SELECT COUNT(*) as total_gps_records FROM gps_tracking_gpsrecord;" 2>/dev/null || echo "Database not accessible"
EOF

chmod +x /opt/teltonika/monitor.sh
chown teltonika:teltonika /opt/teltonika/monitor.sh

echo "✅ Monitoring script created"

# Create convenient management commands
echo "🔗 Creating management commands..."
cat > /usr/local/bin/teltonika << 'EOF'
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start teltonika-gps teltonika-django nginx
        echo "✅ All services started"
        ;;
    stop)
        sudo systemctl stop teltonika-gps teltonika-django
        echo "🛑 Services stopped"
        ;;
    restart)
        sudo systemctl restart teltonika-gps teltonika-django nginx
        echo "🔄 All services restarted"
        ;;
    status)
        echo "📊 Service Status:"
        sudo systemctl status teltonika-gps --no-pager -l
        sudo systemctl status teltonika-django --no-pager -l
        ;;
    logs)
        case "$2" in
            gps)
                sudo journalctl -u teltonika-gps -f
                ;;
            django)
                sudo journalctl -u teltonika-django -f
                ;;
            *)
                echo "🔍 Recent logs from all services:"
                sudo journalctl -u teltonika-gps -u teltonika-django --since "10 minutes ago" --no-pager
                ;;
        esac
        ;;
    monitor)
        sudo /opt/teltonika/monitor.sh
        ;;
    web)
        echo "🌐 Opening web interface..."
        echo "Web Interface: http://$(hostname -I | awk '{print $1}')"
        echo "Admin Panel: http://$(hostname -I | awk '{print $1}')/admin"
        echo "Credentials: admin / admin123"
        ;;
    db)
        echo "🗄️  Connecting to database..."
        sudo -u postgres psql -d teltonika
        ;;
    backup)
        echo "💾 Creating database backup..."
        sudo -u postgres pg_dump teltonika > "/tmp/teltonika_backup_$(date +%Y%m%d_%H%M%S).sql"
        echo "Backup created in /tmp/"
        ;;
    *)
        echo "Unified Teltonika GPS Tracking System"
        echo "Usage: teltonika {start|stop|restart|status|logs|monitor|web|db|backup}"
        echo ""
        echo "Commands:"
        echo "  start      - Start all services"
        echo "  stop       - Stop all services" 
        echo "  restart    - Restart all services"
        echo "  status     - Show detailed service status"
        echo "  logs       - Show logs (add 'gps' or 'django' for specific service)"
        echo "  monitor    - Show monitoring dashboard"
        echo "  web        - Show web interface URLs"
        echo "  db         - Connect to PostgreSQL database"
        echo "  backup     - Create database backup"
        echo ""
        echo "Features:"
        echo "  📡 GPS Tracker Service (Port 5000)"
        echo "  🌐 Django Web Application (Port 80)"
        echo "  🗄️  PostgreSQL Database"
        echo "  📊 REST API & Admin Interface"
        echo "  🔄 Automatic log rotation"
        echo "  💾 Data persistence"
        ;;
esac
EOF

chmod +x /usr/local/bin/teltonika

echo "✅ Management commands created"

# Create integration patch for GPS service
echo "🔗 Creating GPS service integration..."
cat > /opt/teltonika/gps-service/django_integration_patch.py << 'EOF'
"""
Integration patch for connecting GPS service to Django database
Add this to your teltonika_service.py imports and initialization
"""

import sys
import os
sys.path.append('/opt/teltonika/django-app')

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_tracker.settings')
import django
django.setup()

from django.conf import settings
from gps_tracking.models import Device, GPSRecord, DeviceEvent

def store_gps_data_in_db(imei, timestamp, gps_data, io_data):
    """
    Store GPS data directly in Django database
    """
    try:
        # Get or create device
        device, created = Device.objects.get_or_create(
            imei=imei,
            defaults={'name': f'Vehicle {imei}', 'is_active': True}
        )
        
        # Create GPS record
        record_data = {
            'device': device,
            'timestamp': timestamp,
            'latitude': gps_data.get('latitude'),
            'longitude': gps_data.get('longitude'),
            'altitude': gps_data.get('altitude'),
            'speed': gps_data.get('speed'),
            'satellites': gps_data.get('satellites'),
        }
        
        # Add IO parameters
        if io_data:
            io_mapping = {
                239: 'ignition',
                240: 'movement', 
                21: 'gsm_signal',
                66: 'external_voltage',
                67: 'battery_voltage',
                113: 'battery_level',
                16: 'total_odometer',
            }
            
            additional_params = {}
            for io_id, value in io_data.items():
                if io_id in io_mapping:
                    field_name = io_mapping[io_id]
                    if field_name in ['ignition', 'movement']:
                        record_data[field_name] = bool(value)
                    elif field_name in ['external_voltage', 'battery_voltage']:
                        record_data[field_name] = value / 1000.0  # Convert to volts
                    else:
                        record_data[field_name] = value
                else:
                    additional_params[f"IO{io_id}"] = value
            
            if additional_params:
                record_data['additional_parameters'] = additional_params
        
        GPSRecord.objects.create(**record_data)
        return True
        
    except Exception as e:
        print(f"Error storing GPS data in database: {e}")
        return False
EOF

chown teltonika:teltonika /opt/teltonika/gps-service/django_integration_patch.py

# Final status check
echo "🎯 Final system check..."
sleep 5

# Check service statuses
GPS_STATUS=$(systemctl is-active teltonika-gps)
DJANGO_STATUS=$(systemctl is-active teltonika-django)
NGINX_STATUS=$(systemctl is-active nginx)
POSTGRES_STATUS=$(systemctl is-active postgresql)
REDIS_STATUS=$(systemctl is-active redis-server)

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Unified Teltonika GPS Tracking System"
echo "========================================"
echo ""
echo "🔧 Service Status:"
echo "   GPS Tracker:    $GPS_STATUS"
echo "   Django App:     $DJANGO_STATUS"
echo "   Web Server:     $NGINX_STATUS"
echo "   Database:       $POSTGRES_STATUS"
echo "   Redis Cache:    $REDIS_STATUS"
echo ""
echo "🌐 Access URLs:"
echo "   Web Interface:  http://$(hostname -I | awk '{print $1}')"
echo "   Admin Panel:    http://$(hostname -I | awk '{print $1}')/admin"
echo "   API Endpoint:   http://$(hostname -I | awk '{print $1}')/api"
echo ""
echo "🔑 Default Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📡 GPS Service Configuration:"
echo "   Host: 0.0.0.0 (all interfaces)"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo ""
echo "🗄️  Database Information:"
echo "   Database: teltonika"
echo "   User: teltonika"
echo "   Host: localhost:5432"
echo ""
echo "🔧 System Management:"
echo "   teltonika start      - Start all services"
echo "   teltonika stop       - Stop all services"
echo "   teltonika restart    - Restart all services"
echo "   teltonika status     - Check service status"
echo "   teltonika logs       - View logs"
echo "   teltonika monitor    - Show monitoring dashboard"
echo "   teltonika web        - Show web URLs"
echo "   teltonika db         - Access database"
echo "   teltonika backup     - Create database backup"
echo ""
echo "📁 Important Directories:"
echo "   GPS Service:    /opt/teltonika/gps-service/"
echo "   Django App:     /opt/teltonika/django-app/"
echo "   Logs:          /var/log/teltonika/"
echo "   Data:          /var/lib/teltonika/"
echo ""
echo "🚗 Configure your Teltonika device to connect to:"
echo "   IP: $(hostname -I | awk '{print $1}'):5000"
echo ""
echo "🎯 Quick Start:"
echo "   teltonika monitor    - View system status"
echo "   teltonika web        - Get web interface URLs"
echo ""
echo "✅ System is ready for GPS tracking!" 