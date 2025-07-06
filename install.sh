#!/bin/bash

# Teltonika Server Installation Script for Ubuntu
# Run with sudo: sudo bash install.sh

set -e

echo "🚀 Installing Teltonika GPS Tracking Server with PostgreSQL Database..."
echo "======================================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script with sudo"
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required system packages
echo "📦 Installing system dependencies..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    git \
    curl \
    jq \
    net-tools

echo "✅ System packages installed"

# Create user and group
echo "👤 Creating teltonika user and group..."
if ! id "teltonika" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir /opt/teltonika --create-home teltonika
    echo "✅ User 'teltonika' created"
else
    echo "ℹ️  User 'teltonika' already exists"
fi

# Setup PostgreSQL Database
echo "🗄️  Setting up PostgreSQL database..."

# Start PostgreSQL service
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
-- Create database
CREATE DATABASE teltonika;

-- Create user with password
CREATE USER postgres WITH PASSWORD '00oo00oo';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE teltonika TO postgres;

-- Allow local connections
\q
EOF

echo "✅ PostgreSQL database configured"

# Create directories
echo "📁 Creating directories..."
mkdir -p /opt/teltonika
mkdir -p /var/log/teltonika
mkdir -p /var/lib/teltonika

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv /opt/teltonika/venv
source /opt/teltonika/venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python environment configured"

# Set permissions
chown -R teltonika:teltonika /opt/teltonika
chown -R teltonika:teltonika /var/log/teltonika
chown -R teltonika:teltonika /var/lib/teltonika

chmod 755 /opt/teltonika
chmod 755 /var/log/teltonika
chmod 755 /var/lib/teltonika

echo "✅ Directories created with proper permissions"

# Copy service files and Django project
echo "📋 Installing service files..."
cp teltonika_service.py /opt/teltonika/
cp django_api_service.py /opt/teltonika/
cp requirements.txt /opt/teltonika/
cp fmb920_parameters.csv /opt/teltonika/

# Copy Django project if it exists
if [ -d "teltonika_db" ]; then
    cp -r teltonika_db /opt/teltonika/
    echo "✅ Django project copied"
else
    echo "⚠️  Django project not found - you'll need to copy it manually"
fi

# Set executable permissions
chmod +x /opt/teltonika/teltonika_service.py
chmod +x /opt/teltonika/django_api_service.py

# Set ownership
chown -R teltonika:teltonika /opt/teltonika/

echo "✅ Service files installed"

# Setup Django
echo "⚙️  Setting up Django database..."
cd /opt/teltonika
source venv/bin/activate

if [ -d "teltonika_db" ]; then
    cd teltonika_db
    python manage.py makemigrations
    python manage.py migrate
    echo "✅ Django database initialized"
    
    # Create superuser (optional)
    echo "👤 Creating Django superuser (optional)..."
    echo "You can create a superuser later with: python manage.py createsuperuser"
    cd ..
fi

cd /root

# Install systemd services
echo "⚙️  Installing systemd services..."
cp teltonika.service /etc/systemd/system/

# Create Django API service
cat > /etc/systemd/system/teltonika-api.service << 'EOF'
[Unit]
Description=Teltonika Django API Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika
Environment=PATH=/opt/teltonika/venv/bin
ExecStart=/opt/teltonika/venv/bin/python /opt/teltonika/django_api_service.py --production --port 8000
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=teltonika-api

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/teltonika /var/lib/teltonika

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable teltonika
systemctl enable teltonika-api

echo "✅ Systemd services installed and enabled"

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
        systemctl reload teltonika
    endscript
}
EOF

echo "✅ Log rotation configured"

# Open firewall ports (if ufw is active)
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    echo "🔥 Opening firewall ports..."
    ufw allow 5000/tcp  # Teltonika service
    ufw allow 8000/tcp  # Django API
    ufw allow 22/tcp    # SSH
    echo "✅ Firewall configured for ports 5000, 8000, and 22"
fi

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > /opt/teltonika/monitor.sh << 'EOF'
#!/bin/bash

# Teltonika Server Monitor Script

LOG_FILE="/var/log/teltonika/gps_data.log"
SERVICE_NAME="teltonika"

echo "📊 Teltonika Server Monitor"
echo "=========================="

# Check service status
echo "🔍 Service Status:"
systemctl is-active $SERVICE_NAME
systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo "📁 Log Files:"
echo "Service Log: /var/log/teltonika/teltonika_service.log"
echo "GPS Data: /var/log/teltonika/gps_data.log"
echo "Events: /var/log/teltonika/device_events.log"

echo ""
echo "📈 Recent GPS Data (last 10 entries):"
if [ -f "$LOG_FILE" ]; then
    tail -10 "$LOG_FILE" | while read line; do
        timestamp=$(echo $line | cut -d' ' -f1-2)
        gps_data=$(echo $line | jq -r '. | "\(.imei) - \(.latitude),\(.longitude) - Speed: \(.speed)km/h"' 2>/dev/null || echo "Invalid JSON")
        echo "$timestamp: $gps_data"
    done
else
    echo "No GPS data found yet"
fi

echo ""
echo "💾 Disk Usage:"
df -h /var/log/teltonika /var/lib/teltonika

echo ""
echo "🔗 Network Connections:"
netstat -tlnp | grep :5000 || echo "No connections on port 5000"
EOF

chmod +x /opt/teltonika/monitor.sh
chown teltonika:teltonika /opt/teltonika/monitor.sh

echo "✅ Monitoring script created"

# Create convenient aliases
echo "🔗 Creating convenient commands..."
cat > /usr/local/bin/teltonika << 'EOF'
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start teltonika
        sudo systemctl start teltonika-api
        ;;
    stop)
        sudo systemctl stop teltonika
        sudo systemctl stop teltonika-api
        ;;
    restart)
        sudo systemctl restart teltonika
        sudo systemctl restart teltonika-api
        ;;
    status)
        echo "=== Teltonika Service ==="
        sudo systemctl status teltonika --no-pager
        echo ""
        echo "=== Django API Service ==="
        sudo systemctl status teltonika-api --no-pager
        ;;
    logs)
        case "$2" in
            api)
                sudo journalctl -u teltonika-api -f
                ;;
            data)
                sudo journalctl -u teltonika -f
                ;;
            *)
                echo "Use: teltonika logs {api|data}"
                echo "  api  - Django API logs"
                echo "  data - Teltonika service logs"
                ;;
        esac
        ;;
    monitor)
        sudo /opt/teltonika/monitor.sh
        ;;
    db)
        case "$2" in
            shell)
                sudo -u postgres psql teltonika
                ;;
            migrate)
                cd /opt/teltonika/teltonika_db && sudo -u teltonika /opt/teltonika/venv/bin/python manage.py migrate
                ;;
            *)
                echo "Use: teltonika db {shell|migrate}"
                echo "  shell   - Open database shell"
                echo "  migrate - Run database migrations"
                ;;
        esac
        ;;
    *)
        echo "Usage: teltonika {start|stop|restart|status|logs|monitor|db}"
        echo ""
        echo "Commands:"
        echo "  start           - Start both services"
        echo "  stop            - Stop both services"
        echo "  restart         - Restart both services"
        echo "  status          - Show service status"
        echo "  logs {api|data} - Show real-time logs"
        echo "  monitor         - Show monitoring dashboard"
        echo "  db {shell|migrate} - Database operations"
        ;;
esac
EOF

chmod +x /usr/local/bin/teltonika

echo "✅ Command shortcuts created"

# Final setup
echo "🎯 Final setup..."
systemctl start teltonika
systemctl start teltonika-api

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Quick Start Guide:"
echo "===================="
echo ""
echo "🔧 Service Management:"
echo "   teltonika start           - Start both services"
echo "   teltonika stop            - Stop both services"
echo "   teltonika status          - Check service status"
echo "   teltonika logs data       - View teltonika service logs"
echo "   teltonika logs api        - View Django API logs"
echo "   teltonika monitor         - Show monitoring dashboard"
echo ""
echo "🗄️  Database Operations:"
echo "   teltonika db shell        - Access PostgreSQL shell"
echo "   teltonika db migrate      - Run Django migrations"
echo ""
echo "📁 Log Files:"
echo "   Teltonika Service: /var/log/teltonika/teltonika_service.log"
echo "   Django API: journalctl -u teltonika-api"
echo "   GPS Data: /var/log/teltonika/gps_data.log"
echo "   Events: /var/log/teltonika/device_events.log"
echo ""
echo "🌐 Server Details:"
echo "   Teltonika Service: $(hostname -I | awk '{print $1}'):5000"
echo "   Django API: http://$(hostname -I | awk '{print $1}'):8000/api/"
echo "   Django Admin: http://$(hostname -I | awk '{print $1}'):8000/admin/"
echo ""
echo "🚗 Configure your device to connect to:"
echo "   Server IP: $(hostname -I | awk '{print $1}')"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo "   Codec: Codec8"
echo ""
echo "📊 API Endpoints:"
echo "   Live tracking: /api/live-tracking/"
echo "   Device data: /api/telemetry/by_imei/?imei=YOUR_IMEI"
echo "   All devices: /api/devices/"
echo ""
echo "💡 Next Steps:"
echo "   1. Create Django superuser: cd /opt/teltonika/teltonika_db && python manage.py createsuperuser"
echo "   2. Test API: curl http://$(hostname -I | awk '{print $1}'):8000/api/devices/"
echo "   3. Check logs: teltonika logs data"
echo ""
echo "✅ Both services are now running and ready to receive data!" 