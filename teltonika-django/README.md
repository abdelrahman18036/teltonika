# Teltonika Django GPS Tracker

A scalable and fault-tolerant Django application for storing and managing Teltonika GPS tracking data in PostgreSQL database.

## Features

- **PostgreSQL Database Storage** - Reliable, scalable database for GPS data
- **REST API** - Complete API for data access and management
- **Real-time Device Monitoring** - Track device status and connectivity
- **Admin Interface** - Web-based admin panel for data management
- **Multi-device Support** - Handle multiple vehicles simultaneously
- **Event Management** - Track and manage device events
- **Bulk Data Processing** - Optimized for high-frequency GPS data
- **Fault Tolerance** - Robust error handling and recovery

## Database Schema

### Models

1. **Device** - Individual Teltonika devices/vehicles
2. **GPSRecord** - GPS tracking data with all parameters
3. **DeviceEvent** - Device events and alerts
4. **DeviceStatus** - Current status of each device
5. **IOParameter** - IO parameter definitions

### Stored Parameters

All specified parameters are stored with proper data types:

- **Core GPS**: IMEI, Latitude, Longitude, Altitude, Speed, Satellites
- **GNSS Data**: GNSS Status, PDOP (IO181), HDOP (IO182)
- **Vehicle Status**: Ignition (IO239), Movement (IO240)
- **Communication**: GSM Signal (IO021), Active GSM Operator (IO241)
- **Digital I/O**: Digital Inputs/Outputs (IO001, IO179, IO180, IO380)
- **Power**: External Voltage (IO066), Battery Voltage (IO067), Battery Level (IO113), Battery Current (IO068)
- **Vehicle Data**: Total Odometer (IO016), Door Status (IO090), Program Number (IO100)
- **SIM Cards**: ICCID1 (IO011), ICCID2 (IO014)
- **Additional Parameters**: JSON field for any other IO parameters

## Installation

### Prerequisites

- Ubuntu/Debian Linux server
- Python 3.8+
- PostgreSQL 12+
- Redis (for async processing)

### Quick Installation

```bash
cd teltonika-django
chmod +x install.sh
./install.sh
```

The installation script will:

1. Install system dependencies (PostgreSQL, Redis, Python, etc.)
2. Create PostgreSQL database and user
3. Set up Python virtual environment
4. Install Python dependencies
5. Run database migrations
6. Create Django superuser
7. Configure systemd service
8. Set up Nginx reverse proxy
9. Start all services

### Manual Installation Steps

If you prefer manual installation:

```bash
# Install system dependencies
sudo apt update
sudo apt install postgresql postgresql-contrib python3 python3-pip python3-venv redis-server nginx

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE teltonika;"
sudo -u postgres psql -c "CREATE USER teltonika WITH PASSWORD 'teltonika';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teltonika TO teltonika;"

# Django setup
cp env.example .env  # Edit .env file as needed
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# Start services
python manage.py runserver 0.0.0.0:8000
```

## Configuration

### Environment Variables

Create `.env` file (copy from `env.example`):

```bash
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# Database Configuration
DB_NAME=teltonika
DB_USER=teltonika
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Database Configuration

The system uses PostgreSQL with optimized settings:

- Connection pooling for performance
- Proper indexing for GPS queries
- Transaction isolation for data consistency

## API Endpoints

### Authentication

Most endpoints require authentication. Create an API token:

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from rest_framework.authtoken.models import Token
>>> user = User.objects.get(username='your-username')
>>> token = Token.objects.create(user=user)
>>> print(token.key)
```

### Main Endpoints

| Endpoint                                | Method    | Description                                |
| --------------------------------------- | --------- | ------------------------------------------ |
| `/api/devices/`                         | GET, POST | Manage devices                             |
| `/api/gps-records/`                     | GET, POST | GPS records (paginated)                    |
| `/api/gps/create/`                      | POST      | Create single GPS record (unauthenticated) |
| `/api/gps/bulk-create/`                 | POST      | Bulk create GPS records                    |
| `/api/events/`                          | GET, POST | Device events                              |
| `/api/statistics/`                      | GET       | System statistics                          |
| `/api/devices/live-status/`             | GET       | Live device status                         |
| `/api/devices/{imei}/location-history/` | GET       | Location history                           |

### GPS Record Creation

To store GPS data from Teltonika service:

```python
import requests

data = {
    "device_imei": "864636069432371",
    "timestamp": "2025-07-06T19:54:01.570000+00:00",
    "latitude": 25.036705,
    "longitude": 55.201042,
    "altitude": 0,
    "speed": 0,
    "satellites": 0,
    "ignition": False,
    "movement": False,
    "gsm_signal": 5,
    "external_voltage": 12.86,
    "battery_level": 0,
    "total_odometer": 322.9,
    "additional_parameters": {"IO999": "custom_value"}
}

response = requests.post('http://localhost:8000/api/gps/create/', json=data)
```

## Integration with Existing Teltonika Service

### Automatic Integration

The install script creates `../teltonika_django_patch.py` with integration code.

### Manual Integration

1. **Copy the integration module:**

   ```bash
   cp django_integration.py /path/to/your/teltonika-service/
   ```

2. **Modify your existing `teltonika_service.py`:**

   Add imports:

   ```python
   import sys
   sys.path.append('/path/to/teltonika-django')
   from django_integration import create_db_integration
   ```

   In `TeltonikaService.__init__()`:

   ```python
   self.db_integration = create_db_integration('http://localhost:8000')
   ```

   Add method to `TeltonikaService` class:

   ```python
   def store_in_database(self, imei, timestamp, gps_data, io_data, priority=None, event_io_id=None):
       """Store GPS data in PostgreSQL database via Django API"""
       try:
           success = self.db_integration.store_gps_record(
               imei=imei,
               timestamp=timestamp,
               gps_data=gps_data,
               io_data=io_data,
               priority=priority,
               event_io_id=event_io_id
           )
           if success:
               self.logger.debug(f"Successfully stored GPS data for {imei} in database")
       except Exception as e:
           self.logger.error(f"Error storing GPS data in database: {e}")
   ```

   In your `log_gps_data` method, add:

   ```python
   # Store in database
   self.store_in_database(imei, timestamp, gps_data, io_data, priority, event_io_id)
   ```

3. **Restart your Teltonika service:**
   ```bash
   sudo systemctl restart teltonika
   ```

## Administration

### Django Admin

Access the admin interface at: `http://localhost/admin/`

Features:

- View and manage all devices
- Browse GPS records with filtering
- Monitor device events
- View device status
- Manage IO parameters

### Management Commands

```bash
# Monitor device connectivity
python manage.py monitor_devices

# Django shell for custom queries
python manage.py shell

# Database migrations
python manage.py makemigrations
python manage.py migrate
```

### System Management

```bash
# View Django service logs
sudo journalctl -u teltonika-django -f

# Restart services
sudo systemctl restart teltonika-django
sudo systemctl restart nginx

# Check service status
sudo systemctl status teltonika-django
sudo systemctl status postgresql
sudo systemctl status redis-server
```

## Monitoring and Maintenance

### Database Monitoring

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('teltonika'));

-- Check table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor active connections
SELECT count(*) FROM pg_stat_activity WHERE datname='teltonika';
```

### Performance Optimization

1. **Database Indexes** - Already optimized for common queries
2. **Connection Pooling** - Configured for high-frequency inserts
3. **Bulk Operations** - Use bulk create endpoints for multiple records
4. **Pagination** - All list endpoints are paginated

### Log Rotation

Configure log rotation for Django logs:

```bash
sudo nano /etc/logrotate.d/teltonika-django
```

```
/path/to/teltonika-django/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 user group
}
```

## Troubleshooting

### Common Issues

1. **Service won't start:**

   ```bash
   sudo journalctl -u teltonika-django -f
   ```

2. **Database connection errors:**

   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify credentials in `.env` file
   - Test connection: `psql -h localhost -U teltonika -d teltonika`

3. **Permission errors:**

   ```bash
   sudo chown -R user:www-data /path/to/teltonika-django
   sudo chmod -R 755 /path/to/teltonika-django
   ```

4. **High memory usage:**
   - Adjust worker count in systemd service
   - Configure database connection pooling
   - Monitor with `htop` and `free -h`

### Reset System

To completely reset and reinstall:

```bash
chmod +x reset.sh
./reset.sh
./install.sh
```

**⚠️ WARNING:** This will delete ALL GPS data!

## API Examples

### Python Examples

```python
import requests

# Get device statistics
response = requests.get('http://localhost:8000/api/statistics/')
stats = response.json()

# Get recent GPS records for a device
response = requests.get('http://localhost:8000/api/gps-records/?imei=864636069432371&hours=24')
records = response.json()

# Create device event
event_data = {
    "device_imei": "864636069432371",
    "event_type": "ignition_on",
    "timestamp": "2025-07-06T20:00:00Z",
    "description": "Vehicle started"
}
response = requests.post('http://localhost:8000/api/events/', json=event_data)
```

### curl Examples

```bash
# Get live device status
curl -H "Authorization: Token your-token-here" \
     http://localhost:8000/api/devices/live-status/

# Create GPS record
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"device_imei":"864636069432371","latitude":25.0367,"longitude":55.2010}' \
     http://localhost:8000/api/gps/create/
```

## Security

- **Database**: Dedicated user with limited privileges
- **API**: Token-based authentication
- **Network**: Nginx reverse proxy with security headers
- **Secrets**: Environment variables for sensitive data

## Scalability

The system is designed for high-scale GPS tracking:

- **Database**: PostgreSQL with proper indexing and partitioning support
- **API**: Stateless design for horizontal scaling
- **Caching**: Redis for session and data caching
- **Load Balancing**: Nginx configuration ready for multiple workers
- **Async Processing**: Celery ready for background tasks

## Support

For issues and questions:

1. Check the logs: `sudo journalctl -u teltonika-django -f`
2. Review this README
3. Check Django admin for data validation
4. Verify database connectivity and permissions

## License

This project is created for Teltonika GPS tracking integration.
