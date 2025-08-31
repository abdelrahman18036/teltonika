#!/bin/bash

echo "🔧 Fixing Django systemd service..."

# Backup current service file
sudo cp /etc/systemd/system/teltonika-django.service /etc/systemd/system/teltonika-django.service.backup

# Create correct service file
sudo tee /etc/systemd/system/teltonika-django.service > /dev/null << 'EOF'
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

echo "✅ Service file updated"

# Reload systemd and restart service
echo "🔄 Reloading systemd and restarting Django service..."
sudo systemctl daemon-reload
sudo systemctl restart teltonika-django

# Check service status
echo "📊 Service status:"
sudo systemctl status teltonika-django --no-pager

# Test if Django is responding
echo ""
echo "🧪 Testing Django API..."
sleep 3
if curl -s http://127.0.0.1:8000/admin/ > /dev/null; then
    echo "✅ Django API is responding on port 8000"
else
    echo "❌ Django API is not responding"
    echo "🔍 Checking service logs:"
    sudo journalctl -u teltonika-django --no-pager -n 20
fi

echo ""
echo "🌐 Django should now be accessible at:"
echo "   http://151.106.112.187:8000/admin/"
echo "   http://151.106.112.187:8000/api/devices/"
