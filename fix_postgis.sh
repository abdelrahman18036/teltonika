#!/bin/bash

# Fix PostGIS installation and continue setup
echo "🔧 Fixing PostGIS installation..."

# Install PostGIS
echo "📦 Installing PostGIS..."
apt update
apt install -y postgresql-16-postgis-3 postgresql-16-postgis-3-scripts

echo "✅ PostGIS packages installed"

# Restart PostgreSQL to ensure PostGIS is available
systemctl restart postgresql
sleep 3

# Create PostGIS extension
echo "🗺️  Creating PostGIS extension..."
sudo -u postgres psql -d teltonika -c "CREATE EXTENSION IF NOT EXISTS postgis;" || echo "PostGIS extension creation failed, continuing without it"

echo "✅ PostGIS setup completed"

# Continue with the rest of the installation
echo "🐍 Setting up Python virtual environment..."
sudo -u teltonika python3 -m venv /opt/teltonika/venv
sudo -u teltonika /opt/teltonika/venv/bin/pip install --upgrade pip

echo "✅ Python virtual environment created"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
sudo -u teltonika /opt/teltonika/venv/bin/pip install \
    Django==4.2.* \
    djangorestframework \
    django-cors-headers \
    django-filter \
    django-extensions \
    psycopg2-binary \
    redis \
    django-redis \
    celery \
    gunicorn \
    whitenoise \
    pillow \
    requests \
    python-decouple \
    django-environ \
    pytz \
    python-dateutil

echo "✅ Python dependencies installed"

# Copy service files
echo "📋 Installing Teltonika service..."
if [ -f "teltonika_service.py" ]; then
    cp teltonika_service.py /opt/teltonika/service/
    chmod +x /opt/teltonika/service/teltonika_service.py
    echo "✅ teltonika_service.py installed"
else
    echo "⚠️  teltonika_service.py not found in current directory"
fi

if [ -f "django_integration.py" ]; then
    cp django_integration.py /opt/teltonika/service/
    echo "✅ django_integration.py installed"
else
    echo "⚠️  django_integration.py not found in current directory"
fi

chown -R teltonika:teltonika /opt/teltonika/service/

# Copy Django project
echo "🌐 Installing Django application..."
if [ -d "django" ]; then
    cp -r django/* /opt/teltonika/django/
    chown -R teltonika:teltonika /opt/teltonika/django/
    echo "✅ Django files copied"
else
    echo "⚠️  django directory not found"
fi

# Create production settings
echo "⚙️  Creating production configuration..."
cat > /opt/teltonika/django/.env << 'EOF'
# Django Production Settings
DEBUG=False
SECRET_KEY=your-very-secret-key-change-this-in-production-please
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DATABASE_URL=postgresql://teltonika:00oo00oo@localhost:5432/teltonika

# Redis
REDIS_URL=redis://localhost:6379/0

# Time zone
TIME_ZONE=Africa/Cairo
EOF

chown teltonika:teltonika /opt/teltonika/django/.env
chmod 600 /opt/teltonika/django/.env

# Run Django setup
echo "🔄 Running Django setup..."
cd /opt/teltonika/django

# Run migrations
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py migrate

# Collect static files
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py collectstatic --noinput

# Create superuser
echo "👤 Creating Django superuser..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@teltonika.local', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
"

echo "✅ Django setup completed"

# Create systemd services
echo "⚙️  Creating systemd services..."

# Teltonika service
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

# Django service
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
ExecStart=/opt/teltonika/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
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

# Enable services
systemctl daemon-reload
systemctl enable teltonika
systemctl enable teltonika-django

echo "✅ Systemd services created"

# Configure Nginx
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/teltonika << 'EOF'
upstream teltonika_django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Client settings
    client_max_body_size 100M;
    client_body_timeout 120s;
    client_header_timeout 120s;
    
    # Static files
    location /static/ {
        alias /opt/teltonika/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/teltonika/media/;
        expires 1M;
        add_header Cache-Control "public";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://teltonika_django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
    
    # Admin interface
    location /admin/ {
        proxy_pass http://teltonika_django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
    
    # Health check
    location /health {
        proxy_pass http://teltonika_django/api/health/;
        proxy_set_header Host $host;
        access_log off;
    }
    
    # Default redirect to admin
    location / {
        return 301 /admin/;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/teltonika /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

echo "✅ Nginx configured"

# Create management command
cat > /usr/local/bin/teltonika << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting Teltonika services..."
        sudo systemctl start postgresql
        sudo systemctl start redis-server
        sudo systemctl start teltonika-django
        sudo systemctl start teltonika
        sudo systemctl start nginx
        echo "✅ All services started"
        ;;
    stop)
        echo "🛑 Stopping Teltonika services..."
        sudo systemctl stop teltonika
        sudo systemctl stop teltonika-django
        sudo systemctl stop nginx
        echo "✅ Services stopped"
        ;;
    restart)
        echo "🔄 Restarting Teltonika services..."
        sudo systemctl restart teltonika
        sudo systemctl restart teltonika-django
        sudo systemctl restart nginx
        echo "✅ Services restarted"
        ;;
    status)
        echo "📊 Service Status:"
        sudo systemctl status teltonika --no-pager
        sudo systemctl status teltonika-django --no-pager
        sudo systemctl status nginx --no-pager
        ;;
    monitor)
        echo "📊 Teltonika GPS System Monitor"
        echo "==============================="
        echo "🔍 Service Status:"
        echo "Teltonika Service: $(systemctl is-active teltonika)"
        echo "Django API: $(systemctl is-active teltonika-django)"
        echo "PostgreSQL: $(systemctl is-active postgresql)"
        echo "Redis: $(systemctl is-active redis-server)"
        echo "Nginx: $(systemctl is-active nginx)"
        echo ""
        echo "📈 System Resources:"
        echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
        echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
        echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
        echo ""
        echo "📡 Network Connections:"
        echo "Port 5000 (Teltonika): $(netstat -tlnp | grep :5000 | wc -l) connections"
        echo "Port 8000 (Django): $(netstat -tlnp | grep :8000 | wc -l) connections"
        ;;
    test)
        echo "🧪 Running system tests..."
        curl -s http://localhost/health || echo "❌ Health check failed"
        netstat -tlnp | grep :5000 && echo "✅ Teltonika service port 5000 is open" || echo "❌ Port 5000 not accessible"
        netstat -tlnp | grep :8000 && echo "✅ Django service port 8000 is open" || echo "❌ Port 8000 not accessible"
        ;;
    logs)
        echo "📋 Choose log to view:"
        echo "1) Teltonika service logs"
        echo "2) Django API logs"
        echo "3) Nginx logs"
        echo "4) Live GPS data"
        read -p "Enter choice (1-4): " choice
        case $choice in
            1) sudo journalctl -u teltonika -f ;;
            2) sudo journalctl -u teltonika-django -f ;;
            3) sudo tail -f /var/log/nginx/access.log ;;
            4) sudo tail -f /var/log/teltonika/teltonika_service.log | grep "GPS Coordinates" ;;
        esac
        ;;
    *)
        echo "🚀 Teltonika GPS Tracking System - Complete Edition"
        echo "Usage: teltonika {start|stop|restart|status|monitor|test|logs}"
        echo ""
        echo "🌐 Web Interface: http://$(hostname -I | awk '{print $1}')/admin/"
        echo "📡 GPS Service: $(hostname -I | awk '{print $1}'):5000"
        echo "👤 Admin Login: admin / admin123"
        ;;
esac
EOF

chmod +x /usr/local/bin/teltonika

echo "✅ Management command created"

# Start services
echo "🚀 Starting services..."
systemctl start postgresql
systemctl start redis-server
systemctl start teltonika-django
systemctl start teltonika
systemctl start nginx

# Wait for services to start
sleep 5

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "🚀 Teltonika GPS Tracking System - Complete Edition"
echo "=================================================="
echo ""
echo "🌐 Web Interfaces:"
echo "   Admin Panel: http://$(hostname -I | awk '{print $1}')/admin/"
echo "   API Health:  http://$(hostname -I | awk '{print $1}')/health"
echo ""
echo "👤 Admin Login:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📡 GPS Device Configuration:"
echo "   Server IP: $(hostname -I | awk '{print $1}')"
echo "   Port: 5000"
echo "   Protocol: TCP"
echo ""
echo "🔧 Management Commands:"
echo "   teltonika start    - Start all services"
echo "   teltonika status   - Check system status"
echo "   teltonika monitor  - View system monitor"
echo "   teltonika test     - Run system tests"
echo ""
echo "🔍 Checking service status..."
systemctl status teltonika --no-pager
echo ""
systemctl status teltonika-django --no-pager
echo ""
echo "✅ System is ready for production use!"

# Reminder about kernel upgrade
echo ""
echo "⚠️  IMPORTANT: Kernel upgrade is pending"
echo "   Current: 6.8.0-59-generic"
echo "   Available: 6.8.0-63-generic"
echo "   Consider rebooting after testing the system"
echo "   Command: sudo reboot" 