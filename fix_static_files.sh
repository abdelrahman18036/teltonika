#!/bin/bash

echo "🔧 Fixing Django static files serving..."

# Stop Django service
systemctl stop teltonika-django

# Update Django settings to properly serve static files
echo "⚙️  Updating Django settings for static files..."
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# WhiteNoise configuration for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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

# Install whitenoise for serving static files
echo "📦 Installing whitenoise for static files..."
/opt/teltonika/venv/bin/pip install whitenoise

# Collect static files again
echo "📦 Collecting static files..."
cd /opt/teltonika/django
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py collectstatic --noinput

# Set proper permissions
chown -R teltonika:teltonika /opt/teltonika/static

# Create GPS API endpoints
echo "🌐 Creating GPS API endpoints..."
cat > /opt/teltonika/django/gps_data/views.py << 'EOF'
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from .models import Device, GPSRecord
from .serializers import DeviceSerializer, GPSRecordSerializer

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

class GPSRecordViewSet(viewsets.ModelViewSet):
    queryset = GPSRecord.objects.all()
    serializer_class = GPSRecordSerializer

@api_view(['POST'])
def receive_gps_data(request):
    """Endpoint for receiving GPS data from Teltonika devices"""
    try:
        data = request.data
        
        # Get or create device
        device, created = Device.objects.get_or_create(
            imei=data.get('imei'),
            defaults={'device_name': f"Device {data.get('imei')}"}
        )
        
        # Create GPS record
        gps_record = GPSRecord.objects.create(
            device=device,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            altitude=data.get('altitude'),
            speed=data.get('speed'),
            satellites=data.get('satellites'),
            timestamp=data.get('timestamp')
        )
        
        return Response({
            'status': 'success',
            'message': 'GPS data received',
            'record_id': gps_record.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

def api_info(request):
    """API information endpoint"""
    return JsonResponse({
        'message': 'Teltonika GPS Tracking API',
        'version': '1.0',
        'endpoints': {
            'devices': '/api/devices/',
            'gps_records': '/api/gps/',
            'receive_gps': '/api/gps/receive/',
            'admin': '/admin/',
            'health': '/api/health/',
        }
    })
EOF

# Create serializers
echo "📝 Creating serializers..."
cat > /opt/teltonika/django/gps_data/serializers.py << 'EOF'
from rest_framework import serializers
from .models import Device, GPSRecord

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

class GPSRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSRecord
        fields = '__all__'
EOF

# Update URLs to include API endpoints
echo "🔗 Updating URL configuration..."
cat > /opt/teltonika/django/teltonika_gps/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from gps_data.views import DeviceViewSet, GPSRecordViewSet, receive_gps_data, api_info

def health_check(request):
    return JsonResponse({'status': 'ok', 'message': 'Django is running'})

# Create router for API endpoints
router = DefaultRouter()
router.register(r'devices', DeviceViewSet)
router.register(r'gps', GPSRecordViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/gps/receive/', receive_gps_data, name='receive_gps'),
    path('api/health/', health_check, name='health'),
    path('api/info/', api_info, name='api_info'),
    path('', api_info, name='root'),
]
EOF

# Set proper ownership
chown -R teltonika:teltonika /opt/teltonika/django

# Start Django service
echo "🚀 Starting Django service..."
systemctl start teltonika-django

# Wait for service to start
sleep 5

# Check service status
echo "🔍 Checking service status..."
systemctl status teltonika-django --no-pager

# Test connectivity
echo ""
echo "🧪 Testing connectivity..."
echo "Main API:"
curl -s http://127.0.0.1:8000/ | head -3

echo ""
echo "Health check:"
curl -s http://127.0.0.1:8000/api/health/

echo ""
echo "API Info:"
curl -s http://127.0.0.1:8000/api/info/ | head -5

echo ""
echo "✅ Static files fix completed!"
echo ""
echo "🌐 Access URLs:"
echo "   Main API: http://101.46.53.150:8000/"
echo "   Admin: http://101.46.53.150:8000/admin/"
echo "   API Endpoints: http://101.46.53.150:8000/api/"
echo "   GPS Data: http://101.46.53.150:8000/api/gps/"
echo "   Devices: http://101.46.53.150:8000/api/devices/"
echo "   Health: http://101.46.53.150:8000/api/health/"
echo ""
echo "👤 Admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📝 The admin interface should now load properly with CSS/JS files!" 