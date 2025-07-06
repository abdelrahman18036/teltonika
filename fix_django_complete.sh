#!/bin/bash

# Complete Django setup and fix script
echo "🔧 Complete Django Setup and Fix..."

# Stop the Django service first
systemctl stop teltonika-django

# Check if Django project exists
echo "🔍 Checking Django project structure..."
if [ ! -d "/opt/teltonika/django" ]; then
    echo "📁 Creating Django directory..."
    mkdir -p /opt/teltonika/django
    chown teltonika:teltonika /opt/teltonika/django
fi

cd /opt/teltonika/django

# Check if Django project files exist
if [ ! -f "manage.py" ]; then
    echo "🌐 Creating Django project..."
    sudo -u teltonika /opt/teltonika/venv/bin/django-admin startproject teltonika_gps .
    echo "✅ Django project created"
fi

# Check if gps_data app exists
if [ ! -d "gps_data" ]; then
    echo "📱 Creating gps_data app..."
    sudo -u teltonika /opt/teltonika/venv/bin/python manage.py startapp gps_data
    echo "✅ gps_data app created"
fi

# Create basic Django settings
echo "⚙️  Creating Django settings..."
cat > /opt/teltonika/django/teltonika_gps/settings.py << 'EOF'
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-change-this-in-production-12345'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'gps_data',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'teltonika_gps.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'teltonika_gps.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'teltonika',
        'USER': 'teltonika',
        'PASSWORD': '00oo00oo',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = '/opt/teltonika/static'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Session serializer fix
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/teltonika/django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
EOF

# Create production settings
echo "🔧 Creating production settings..."
cat > /opt/teltonika/django/teltonika_gps/settings_production.py << 'EOF'
from .settings import *

# Production settings
DEBUG = False
SECRET_KEY = 'your-very-secret-key-change-this-in-production'
ALLOWED_HOSTS = ['*']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'teltonika',
        'USER': 'teltonika',
        'PASSWORD': '00oo00oo',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static files
STATIC_ROOT = '/opt/teltonika/static'

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session serializer fix
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
EOF

# Create basic GPS data models
echo "📊 Creating GPS data models..."
cat > /opt/teltonika/django/gps_data/models.py << 'EOF'
from django.db import models
from django.utils import timezone

class Device(models.Model):
    imei = models.CharField(max_length=20, unique=True)
    device_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.imei} - {self.device_name}"

class GPSRecord(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    altitude = models.IntegerField(null=True, blank=True)
    speed = models.IntegerField(null=True, blank=True)
    satellites = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device.imei} - {self.timestamp}"
EOF

# Create basic admin
echo "👤 Creating admin configuration..."
cat > /opt/teltonika/django/gps_data/admin.py << 'EOF'
from django.contrib import admin
from .models import Device, GPSRecord

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['imei', 'device_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['imei', 'device_name']

@admin.register(GPSRecord)
class GPSRecordAdmin(admin.ModelAdmin):
    list_display = ['device', 'latitude', 'longitude', 'speed', 'timestamp']
    list_filter = ['device', 'timestamp']
    search_fields = ['device__imei']
    readonly_fields = ['created_at']
EOF

# Create basic URLs
echo "🌐 Creating URL configuration..."
cat > /opt/teltonika/django/teltonika_gps/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'ok', 'message': 'Django is running'})

def api_root(request):
    return JsonResponse({
        'message': 'Teltonika GPS API',
        'endpoints': {
            'admin': '/admin/',
            'health': '/api/health/',
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health'),
    path('api/', api_root, name='api_root'),
    path('', api_root, name='root'),
]
EOF

# Set proper ownership
chown -R teltonika:teltonika /opt/teltonika/django

# Create static and log directories
mkdir -p /opt/teltonika/static
mkdir -p /var/log/teltonika
chown -R teltonika:teltonika /opt/teltonika/static
chown -R teltonika:teltonika /var/log/teltonika

# Run Django setup
echo "🔄 Running Django migrations..."
cd /opt/teltonika/django
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py makemigrations
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py migrate

# Collect static files
echo "📦 Collecting static files..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py collectstatic --noinput

# Create superuser
echo "👤 Creating superuser..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@teltonika.local', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
"

# Update Django service to use regular settings first
echo "⚙️  Updating Django service..."
cat > /etc/systemd/system/teltonika-django.service << 'EOF'
[Unit]
Description=Teltonika Django GPS Tracking API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=teltonika
Group=teltonika
WorkingDirectory=/opt/teltonika/django
ExecStart=/opt/teltonika/venv/bin/gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile /var/log/teltonika/gunicorn-access.log \
    --error-logfile /var/log/teltonika/gunicorn-error.log \
    --log-level info \
    teltonika_gps.wsgi:application

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload and start Django
echo "🚀 Starting Django service..."
systemctl daemon-reload
systemctl enable teltonika-django
systemctl start teltonika-django

# Wait for service to start
sleep 10

# Check service status
echo "🔍 Checking service status..."
systemctl status teltonika-django --no-pager

# Test connectivity
echo ""
echo "🧪 Testing connectivity..."
echo "Local test:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8000/ || echo "❌ Failed"

echo ""
echo "Health check test:"
curl -s http://127.0.0.1:8000/api/health/ || echo "❌ Failed"

# Check port status
echo ""
echo "🔍 Port status:"
netstat -tlnp | grep :8000 || echo "❌ Port not listening"

echo ""
echo "✅ Django setup completed!"
echo ""
echo "🌐 Access URLs:"
echo "   Main: http://101.46.53.150:8000/"
echo "   Admin: http://101.46.53.150:8000/admin/"
echo "   Health: http://101.46.53.150:8000/api/health/"
echo ""
echo "👤 Admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "🔧 If issues persist:"
echo "   Check logs: journalctl -u teltonika-django -f"
echo "   Manual test: sudo -u teltonika /opt/teltonika/venv/bin/python /opt/teltonika/django/manage.py runserver 0.0.0.0:8000" 