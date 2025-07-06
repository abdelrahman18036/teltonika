#!/bin/bash

# Teltonika GPS Tracking Server Installation Script for Ubuntu
# Features: Clean logging with IMEI and vehicle parameters only
# Run with sudo: sudo bash install.sh

set -e

echo "🚀 Installing Teltonika GPS Tracking Server with Fast API Integration..."
echo "======================================================================="

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
chmod +x /opt/teltonika/teltonika_service.py
chown teltonika:teltonika /opt/teltonika/teltonika_service.py

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
echo "Main Log: /var/log/teltonika/teltonika_service.log"
echo "GPS Data: /var/log/teltonika/gps_data.log"
echo "Events: /var/log/teltonika/device_events.log"

echo ""
echo "📈 Recent Activity (last 20 lines):"
if [ -f "/var/log/teltonika/teltonika_service.log" ]; then
    echo "--- Clean Log Output ---"
    tail -20 /var/log/teltonika/teltonika_service.log
else
    echo "No activity log found yet"
fi

echo ""
echo "📡 Recent GPS Data (last 5 entries):"
if [ -f "$LOG_FILE" ]; then
    tail -5 "$LOG_FILE" | while read line; do
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

echo ""
echo "📋 Log Format Information:"
echo "The service provides clean output showing:"
echo "  - Device IMEI"
echo "  - GPS coordinates (latitude, longitude)"
echo "  - Vehicle speed, altitude, satellites"
echo "  - All vehicle parameters (ignition, voltage, etc.)"
echo "  - No debug or technical logs"
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
    clean-logs)
        echo "📋 Clean Log Output (last 50 lines):"
        sudo tail -50 /var/log/teltonika/teltonika_service.log
        ;;
    live)
        echo "🔴 Live GPS tracking (press Ctrl+C to stop):"
        sudo tail -f /var/log/teltonika/teltonika_service.log | grep --line-buffered "Device IMEI\|GPS Coordinates\|Vehicle Parameters"
        ;;
    *)
        echo "Teltonika GPS Tracking Server - Clean Logging Edition"
        echo "Usage: teltonika {start|stop|restart|status|logs|monitor|clean-logs|live}"
        echo ""
        echo "Commands:"
        echo "  start      - Start the service"
        echo "  stop       - Stop the service" 
        echo "  restart    - Restart the service"
        echo "  status     - Show service status"
        echo "  logs       - Show real-time system logs"
        echo "  monitor    - Show monitoring dashboard"
        echo "  clean-logs - Show recent clean log output"
        echo "  live       - Live GPS tracking display"
        echo ""
        echo "Features:"
        echo "  ✅ Clean logging (IMEI + GPS + Parameters only)"
        echo "  ✅ No debug noise or technical details"
        echo "  ✅ Human-readable vehicle parameters"
        echo "  ✅ Properly formatted units (V, °C, km/h, etc.)"
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
echo "📋 Teltonika GPS Tracking Server - Fast API Integration Edition"
echo "=============================================================="
echo ""
echo "🔧 Service Management:"
echo "   teltonika start      - Start the service"
echo "   teltonika stop       - Stop the service"
echo "   teltonika status     - Check service status"
echo "   teltonika logs       - View real-time system logs"
echo "   teltonika monitor    - Show monitoring dashboard"
echo "   teltonika clean-logs - Show clean log output"
echo "   teltonika live       - Live GPS tracking display"
echo ""
echo "📁 Log Files:"
echo "   Main Log: /var/log/teltonika/teltonika_service.log"
echo "   GPS Data: /var/log/teltonika/gps_data.log"
echo "   Events: /var/log/teltonika/device_events.log"
echo ""
echo "🌐 Server Details:"
echo "   Host: 0.0.0.0 (all interfaces)"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo "   🔗 API Integration: Sends data to Django backend via HTTP API"
echo ""
echo "📊 What You'll See in Logs:"
echo "   ✅ Device IMEI identification"
echo "   ✅ GPS coordinates (lat, lon)"
echo "   ✅ Vehicle speed, altitude, satellites"
echo "   ✅ All vehicle parameters with proper units:"
echo "      • Ignition status (ON/OFF)"
echo "      • Digital inputs/outputs (HIGH/LOW)"
echo "      • Voltages (13.85V format)"
echo "      • Temperatures (25.5°C format)"
echo "      • Fuel levels, engine RPM, etc."
echo "   ✅ Fast API storage confirmation"
echo "   ❌ No debug logs or technical noise"
echo ""
echo "🚗 Configure your device to connect to:"
echo "   IP: $(hostname -I | awk '{print $1}'):5000"
echo ""
echo "🔴 Start live tracking: teltonika live"
echo "📊 View dashboard: teltonika monitor"
echo ""
echo "🔧 Django Backend Integration:"
echo "============================================"
echo "This service now includes FAST API integration for high-performance data storage."
echo ""
echo "📋 To set up the Django backend:"
echo "   1. cd ../teltonika_django"
echo "   2. bash install_django.sh"
echo "   3. Start Django: ./django_manage.sh start"
echo ""
echo "⚡ Performance Features:"
echo "   • Bulk data batching (up to 500 records/batch)"
echo "   • Background processing (non-blocking)"
echo "   • Automatic retry with exponential backoff"
echo "   • No data loss guarantee with local queuing"
echo "   • Real-time performance monitoring"
echo ""
echo "🌐 API Endpoints (when Django backend is running):"
echo "   • Admin Interface: http://localhost/admin/"
echo "   • Performance Stats: http://localhost:8000/api/gps/performance/"
echo "   • Device Latest: http://localhost:8000/api/gps/device/{imei}/latest/"
echo ""
echo "⚠️  Note: The Teltonika service will work without Django backend,"
echo "   but GPS data will only be stored in log files." 