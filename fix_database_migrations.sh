#!/bin/bash

echo "🔧 Fixing database migrations and creating tables..."

# Stop Django service
systemctl stop teltonika-django

cd /opt/teltonika/django

# Check current database state
echo "🔍 Checking current database state..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py showmigrations

# Reset migrations for gps_data app
echo "🔄 Resetting migrations for gps_data app..."
sudo -u teltonika rm -rf gps_data/migrations/
sudo -u teltonika mkdir -p gps_data/migrations/
sudo -u teltonika touch gps_data/migrations/__init__.py

# Create fresh migrations
echo "📝 Creating fresh migrations..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py makemigrations gps_data

# Check if there are any conflicting tables and drop them
echo "🗑️  Cleaning up any existing conflicting tables..."
sudo -u postgres psql -d teltonika -c "
DROP TABLE IF EXISTS gps_data_gpsrecord CASCADE;
DROP TABLE IF EXISTS gps_data_device CASCADE;
DROP TABLE IF EXISTS gps_data_apilog CASCADE;
DROP TABLE IF EXISTS gps_data_devicestatus CASCADE;
" 2>/dev/null || true

# Apply migrations
echo "🚀 Applying migrations..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py migrate

# Verify tables were created
echo "✅ Verifying database tables..."
sudo -u postgres psql -d teltonika -c "\dt" | grep gps_data

# Create some test data
echo "📊 Creating test data..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py shell -c "
from gps_data.models import Device, GPSRecord
from django.utils import timezone
from decimal import Decimal

# Create test device
device, created = Device.objects.get_or_create(
    imei='123456789012345',
    defaults={
        'device_name': 'Test Device 1',
        'is_active': True
    }
)

if created:
    print('✅ Test device created')
else:
    print('ℹ️  Test device already exists')

# Create test GPS record
gps_record, created = GPSRecord.objects.get_or_create(
    device=device,
    latitude=Decimal('30.0444'),
    longitude=Decimal('31.2357'),
    defaults={
        'altitude': 100,
        'speed': 50,
        'satellites': 8,
        'timestamp': timezone.now()
    }
)

if created:
    print('✅ Test GPS record created')
else:
    print('ℹ️  Test GPS record already exists')

print(f'Total devices: {Device.objects.count()}')
print(f'Total GPS records: {GPSRecord.objects.count()}')
"

# Start Django service
echo "🚀 Starting Django service..."
systemctl start teltonika-django

# Wait for service to start
sleep 5

# Check service status
echo "🔍 Checking service status..."
systemctl status teltonika-django --no-pager

# Test the admin interface
echo ""
echo "🧪 Testing admin interface..."
echo "Testing devices endpoint:"
curl -s "http://127.0.0.1:8000/api/devices/" | head -3

echo ""
echo "Testing GPS records endpoint:"
curl -s "http://127.0.0.1:8000/api/gps/" | head -3

# Test database connection
echo ""
echo "🔍 Testing database connection..."
sudo -u teltonika /opt/teltonika/venv/bin/python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM gps_data_device')
device_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM gps_data_gpsrecord')
record_count = cursor.fetchone()[0]
print(f'✅ Database connection OK - Devices: {device_count}, Records: {record_count}')
"

echo ""
echo "✅ Database migrations fix completed!"
echo ""
echo "🌐 Admin interface should now work properly:"
echo "   Admin: http://101.46.53.150:8000/admin/"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📊 API Endpoints:"
echo "   Devices: http://101.46.53.150:8000/api/devices/"
echo "   GPS Records: http://101.46.53.150:8000/api/gps/"
echo "   Receive GPS: http://101.46.53.150:8000/api/gps/receive/"
echo ""
echo "🔧 If you still see errors, try:"
echo "   1. Check logs: journalctl -u teltonika-django -f"
echo "   2. Manual migration: sudo -u teltonika /opt/teltonika/venv/bin/python /opt/teltonika/django/manage.py migrate --run-syncdb" 