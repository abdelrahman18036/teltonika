# Teltonika GPS Tracking System - Django Backend

A high-performance Django backend for receiving and storing GPS data from Teltonika devices. This system provides a robust API for data ingestion and a comprehensive admin interface for managing GPS devices and their data.

## Features

- **Real-time GPS Data Ingestion**: Receives data from `teltonika_service.py` via REST API
- **PostgreSQL Database**: Optimized for high-volume GPS data storage
- **Comprehensive Data Model**: Stores all Teltonika parameters including GPS coordinates, IO data, and vehicle status
- **Admin Interface**: Full-featured Django admin for device and data management
- **API Endpoints**: RESTful API for data access and device management
- **Batch Processing**: Efficient bulk data insertion with queuing
- **Monitoring**: API usage statistics and device status tracking

## Database Schema

### Core Models

1. **Device**: Store device information (IMEI, name, status)
2. **GPSRecord**: Main GPS data with all Teltonika parameters
3. **DeviceStatus**: Track device connection status and statistics
4. **APILog**: Monitor API usage and performance

### Supported Parameters

- **GPS Data**: Latitude, Longitude, Altitude, Speed, Satellites, Angle
- **GNSS Status**: GNSS Status, PDOP, HDOP (IO181, IO182)
- **Vehicle Status**: Ignition (IO239), Movement (IO240)
- **Cellular**: GSM Signal (IO021), Operator (IO241), ICCID1/2 (IO011/IO014)
- **Digital I/O**: Digital Input 1 (IO001), Digital Outputs 1-3 (IO179/IO180/IO380)
- **Power**: External Voltage (IO066), Battery Voltage (IO067), Battery Level (IO113), Current (IO068)
- **Vehicle Info**: Total Odometer (IO016), Program Number (IO100), Door Status (IO090)
- **Additional**: All other IO parameters stored in JSON field

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Django 4.2+

## Database Setup

1. **Create PostgreSQL Database**:

```sql
CREATE DATABASE teltonika;
CREATE USER teltonika WITH PASSWORD '00oo00oo';
GRANT ALL PRIVILEGES ON DATABASE teltonika TO teltonika;
```

2. **Install Dependencies**:

```bash
cd django
pip install -r requirements.txt
```

## Django Setup

1. **Run Migrations**:

```bash
python manage.py makemigrations
python manage.py migrate
```

2. **Create Superuser**:

```bash
python manage.py createsuperuser
```

3. **Start Development Server**:

```bash
python manage.py runserver 0.0.0.0:8000
```

## API Endpoints

### GPS Data Ingestion

- **POST** `/api/gps/` - Bulk GPS data ingestion (main endpoint)
- **POST** `/api/store/` - Single GPS record storage

**Example Request**:

```json
{
  "imei": "123456789012345",
  "timestamp": "2024-01-01T12:00:00Z",
  "priority": 0,
  "gps_data": {
    "latitude": 31.2001,
    "longitude": 29.9187,
    "altitude": 50,
    "speed": 60,
    "angle": 90,
    "satellites": 8
  },
  "io_data": {
    "239": 1, // Ignition ON
    "240": 1, // Moving
    "21": 4, // GSM Signal strength
    "66": 12500 // External voltage (mV)
  },
  "event_io_id": 239
}
```

### Device Management

- **GET** `/api/devices/` - List all devices
- **GET** `/api/devices/{imei}/` - Get device details
- **GET** `/api/devices/{imei}/records/` - Get GPS records for device
- **POST** `/api/devices/{imei}/status/` - Update device status

### Data Access

- **GET** `/api/records/latest/` - Latest GPS records for all devices
- **GET** `/api/status/` - Device status overview
- **GET** `/api/stats/` - API usage statistics
- **GET** `/api/health/` - Health check endpoint

## Integration with Teltonika Service

The Django backend integrates with `teltonika_service.py` through the `django_integration.py` module.

### Integration Features

- **Automatic Queuing**: GPS data is queued for batch processing
- **Error Handling**: Failed requests are logged and retried
- **Statistics**: Track success/failure rates
- **Health Monitoring**: Connection status monitoring

### Configuration

In `teltonika_service.py`, the integration is automatically initialized if available:

```python
# Django API integration
try:
    from django_integration import create_db_integration
    API_INTEGRATION_AVAILABLE = True
except ImportError:
    API_INTEGRATION_AVAILABLE = False
    print("Warning: Django API integration not available")
```

## Admin Interface

Access the Django admin at `http://localhost:8000/admin/` to:

- Manage devices and their settings
- View GPS records with Google Maps integration
- Monitor device connection status
- View API logs and statistics
- Export data for analysis

### Admin Features

- **Device Management**: Add/edit devices, view status indicators
- **GPS Record Browser**: Filter by device, time, location with map links
- **Real-time Status**: Online/offline device indicators
- **Data Export**: Built-in export functionality
- **API Monitoring**: Request logs with performance metrics

## Performance Optimization

### Database Indexes

- Device IMEI (unique)
- GPS timestamp (for time-based queries)
- GPS coordinates (for location queries)
- Device + timestamp (for device-specific time queries)
- Connection status (for monitoring)

### Bulk Processing

- Batch GPS record insertion
- Queued API requests
- Async device status updates
- Connection pooling

## Monitoring and Logging

### Application Logs

- GPS data processing logs
- API request/response logs
- Device connection events
- Error tracking

### Statistics Tracking

- Total devices and records
- API call success rates
- Device online status
- Data ingestion rates

## Production Deployment

### Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://teltonika:password@localhost:5432/teltonika
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
```

### Security Settings

- Enable HTTPS in production
- Configure proper CORS settings
- Use environment variables for secrets
- Set up proper authentication for admin

### Performance Tuning

- Configure PostgreSQL connection pooling
- Enable database query optimization
- Set up Redis for caching (optional)
- Configure proper logging levels

## Development

### Running Tests

```bash
python manage.py test
```

### Database Migrations

When adding new fields:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Custom Commands

Create custom management commands in `gps_data/management/commands/` for:

- Data cleanup
- Bulk data imports
- Performance monitoring
- Device synchronization

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:

   - Check PostgreSQL service status
   - Verify database credentials
   - Ensure database exists

2. **Migration Errors**:

   - Check for missing dependencies
   - Verify model changes
   - Clear migration conflicts

3. **API Integration Issues**:
   - Verify Django server is running
   - Check firewall settings
   - Monitor API logs

### Performance Issues

- Monitor database query performance
- Check for missing indexes
- Optimize bulk insertion queries
- Monitor memory usage

## Support

For issues and questions:

- Check Django admin logs
- Monitor API statistics
- Review device connection status
- Check PostgreSQL performance

## License

This project is part of the Teltonika GPS tracking system.
