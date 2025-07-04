#!/bin/bash

# Teltonika Server Installation Script for Ubuntu
# Run with sudo: sudo bash install.sh

set -e

echo "🚀 Installing Teltonika GPS Tracking Server..."
echo "============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script with sudo"
    exit 1
fi

# Create user and group
echo "👤 Creating teltonika user and group..."
if ! id "teltonika" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir /opt/teltonika --create-home teltonika
    echo "✅ User 'teltonika' created"
else
    echo "ℹ️  User 'teltonika' already exists"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p /opt/teltonika
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

# Copy service files
echo "📋 Installing service files..."
cp teltonika_service.py /opt/teltonika/
cp test_data_generator.py /opt/teltonika/
chmod +x /opt/teltonika/teltonika_service.py
chmod +x /opt/teltonika/test_data_generator.py

chown teltonika:teltonika /opt/teltonika/teltonika_service.py
chown teltonika:teltonika /opt/teltonika/test_data_generator.py

echo "✅ Service files installed"

# Install systemd service
echo "⚙️  Installing systemd service..."
cp teltonika.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable teltonika

echo "✅ Systemd service installed and enabled"

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

# Open firewall port (if ufw is active)
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    echo "🔥 Opening firewall port 5000..."
    ufw allow 5000/tcp
    echo "✅ Firewall configured"
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
        ;;
    stop)
        sudo systemctl stop teltonika
        ;;
    restart)
        sudo systemctl restart teltonika
        ;;
    status)
        sudo systemctl status teltonika
        ;;
    logs)
        sudo journalctl -u teltonika -f
        ;;
    monitor)
        sudo /opt/teltonika/monitor.sh
        ;;
    test)
        cd /opt/teltonika && python3 test_data_generator.py
        ;;
    *)
        echo "Usage: teltonika {start|stop|restart|status|logs|monitor|test}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the service"
        echo "  stop    - Stop the service"
        echo "  restart - Restart the service"
        echo "  status  - Show service status"
        echo "  logs    - Show real-time logs"
        echo "  monitor - Show monitoring dashboard"
        echo "  test    - Run test data generator"
        ;;
esac
EOF

chmod +x /usr/local/bin/teltonika

echo "✅ Command shortcuts created"

# Final setup
echo "🎯 Final setup..."
systemctl start teltonika

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Quick Start Guide:"
echo "===================="
echo ""
echo "🔧 Service Management:"
echo "   teltonika start     - Start the service"
echo "   teltonika stop      - Stop the service"
echo "   teltonika status    - Check service status"
echo "   teltonika logs      - View real-time logs"
echo "   teltonika monitor   - Show monitoring dashboard"
echo ""
echo "🧪 Testing:"
echo "   teltonika test      - Run test data generator"
echo ""
echo "📁 Log Files:"
echo "   Service: /var/log/teltonika/teltonika_service.log"
echo "   GPS Data: /var/log/teltonika/gps_data.log"
echo "   Events: /var/log/teltonika/device_events.log"
echo ""
echo "🌐 Server Details:"
echo "   Host: 0.0.0.0 (all interfaces)"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo ""
echo "🚗 Configure your device to connect to:"
echo "   Server IP: $(hostname -I | awk '{print $1}')"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo "   Codec: Codec8"
echo ""
echo "✅ The service is now running and ready to receive data!" 