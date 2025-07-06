#!/bin/bash

# Quick fix for PostgreSQL configuration
echo "🔧 Fixing PostgreSQL configuration..."

# Detect PostgreSQL version properly
PG_VERSION=$(ls /etc/postgresql/ | head -1)
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"

echo "📋 Detected PostgreSQL version: $PG_VERSION"
echo "📋 Config file: $PG_CONF"

# Check if config file exists
if [ ! -f "$PG_CONF" ]; then
    echo "🔍 Searching for postgresql.conf..."
    PG_CONF=$(find /etc/postgresql -name "postgresql.conf" -type f | head -1)
    echo "📋 Using config file: $PG_CONF"
fi

if [ ! -f "$PG_CONF" ]; then
    echo "❌ Cannot find PostgreSQL config file"
    echo "🔍 Available PostgreSQL files:"
    find /etc/postgresql -name "*.conf" -type f
    exit 1
fi

# Backup original config
cp "$PG_CONF" "$PG_CONF.backup"
echo "✅ PostgreSQL config backed up"

# Add GPS optimization settings
echo "⚡ Adding PostgreSQL optimizations..."
cat >> "$PG_CONF" << 'EOF'

# Teltonika GPS Optimization
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
max_connections = 200
EOF

echo "✅ PostgreSQL optimizations added"

# Restart PostgreSQL
systemctl restart postgresql
echo "✅ PostgreSQL restarted"

# Continue with the rest of the installation
echo "🐍 Setting up Python virtual environment..."
sudo -u teltonika python3 -m venv /opt/teltonika/venv
sudo -u teltonika /opt/teltonika/venv/bin/pip install --upgrade pip

echo "✅ Python virtual environment created"

# Copy and install service files
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

# Install Python dependencies
echo "📦 Installing Python dependencies..."
sudo -u teltonika /opt/teltonika/venv/bin/pip install \
    django \
    djangorestframework \
    psycopg2-binary \
    django-cors-headers \
    requests \
    python-decouple \
    gunicorn

echo "✅ Python dependencies installed"

# Configure Django settings for production
echo "⚙️  Configuring Django for production..."
cat > /opt/teltonika/django/.env << 'EOF'
DEBUG=False
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=postgresql://teltonika:00oo00oo@localhost:5432/teltonika
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
EOF

chown teltonika:teltonika /opt/teltonika/django/.env

# Run Django migrations
echo "🔄 Running Django migrations..."
cd /opt/teltonika/django
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py migrate
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py collectstatic --noinput

# Create Django superuser
echo "👤 Creating Django superuser..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@teltonika.local', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

echo "✅ Django configured"

# Create systemd services
echo "⚙️  Installing systemd services..."

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
Description=Teltonika Django API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/django
ExecStart=/opt/teltonika/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --timeout 120 teltonika_gps.wsgi:application
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
systemctl enable teltonika
systemctl enable teltonika-django

echo "✅ Systemd services installed"

# Start services
echo "🚀 Starting services..."
systemctl start postgresql
systemctl start teltonika-django
systemctl start teltonika
systemctl start nginx

# Wait for services to start
sleep 5

echo ""
echo "🎉 Installation fix completed!"
echo ""
echo "🔍 Checking service status..."
systemctl status teltonika --no-pager
echo ""
systemctl status teltonika-django --no-pager
echo ""
systemctl status nginx --no-pager
echo ""
echo "🌐 Web Interface: http://$(hostname -I | awk '{print $1}')/admin/"
echo "👤 Admin Login: admin / admin123"
echo "📡 GPS Service: $(hostname -I | awk '{print $1}'):5000"
echo ""
echo "✅ System should now be ready!" 