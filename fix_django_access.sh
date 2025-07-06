#!/bin/bash

# Fix Django external access and import issues
echo "🔧 Fixing Django external access issues..."

# Stop the current Django service
echo "🛑 Stopping Django service..."
systemctl stop teltonika-django

# Fix the Django service configuration to bind to all interfaces
echo "⚙️  Updating Django service configuration..."
cat > /etc/systemd/system/teltonika-django.service << 'EOF'
[Unit]
Description=Teltonika Django GPS Tracking API
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/django
Environment=DJANGO_SETTINGS_MODULE=teltonika_gps.settings_production
ExecStart=/opt/teltonika/venv/bin/gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --keep-alive 2 \
    --preload \
    --access-logfile /var/log/teltonika/gunicorn-access.log \
    --error-logfile /var/log/teltonika/gunicorn-error.log \
    --log-level info \
    teltonika_gps.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
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

# Fix Django settings to resolve import issues
echo "🐍 Fixing Django settings..."
if [ -f "/opt/teltonika/django/teltonika_gps/settings_production.py" ]; then
    # Add session serializer fix
    cat >> /opt/teltonika/django/teltonika_gps/settings_production.py << 'EOF'

# Fix for Django session serializer
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Allow external access
ALLOWED_HOSTS = ['*']  # Allow all hosts for now, restrict in production

# Disable CORS restrictions for testing
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
EOF
    echo "✅ Django settings updated"
else
    echo "⚠️  Django settings file not found"
fi

# Update firewall to allow port 8000
echo "🔥 Configuring firewall for Django access..."
ufw allow 8000/tcp
echo "✅ Firewall updated to allow port 8000"

# Reload systemd and restart Django
echo "🔄 Reloading systemd and restarting Django..."
systemctl daemon-reload
systemctl enable teltonika-django
systemctl start teltonika-django

# Wait for service to start
sleep 5

# Check service status
echo "🔍 Checking Django service status..."
systemctl status teltonika-django --no-pager

# Test local connectivity
echo ""
echo "🧪 Testing connectivity..."
echo "Local test (127.0.0.1:8000):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8000/ || echo "❌ Local connection failed"

echo ""
echo "External test (0.0.0.0:8000):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://0.0.0.0:8000/ || echo "❌ External connection failed"

# Check if port is listening
echo ""
echo "🔍 Port status:"
netstat -tlnp | grep :8000 || echo "❌ Port 8000 not listening"

# Check firewall status
echo ""
echo "🔥 Firewall status:"
ufw status | grep 8000 || echo "⚠️  Port 8000 not in firewall rules"

echo ""
echo "📋 Django service logs (last 10 lines):"
journalctl -u teltonika-django -n 10 --no-pager

echo ""
echo "✅ Fix completed!"
echo ""
echo "🌐 Django should now be accessible at:"
echo "   http://$(hostname -I | awk '{print $1}'):8000/"
echo "   http://101.46.53.150:8000/"
echo ""
echo "🔧 If still not working, try:"
echo "1. Check logs: journalctl -u teltonika-django -f"
echo "2. Test manual start: sudo -u teltonika /opt/teltonika/venv/bin/python /opt/teltonika/django/manage.py runserver 0.0.0.0:8000"
echo "3. Check Django: cd /opt/teltonika/django && sudo -u teltonika /opt/teltonika/venv/bin/python manage.py check" 