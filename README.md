# Teltonika GPS Tracking System

A production-ready GPS tracking system for Teltonika devices with PostgreSQL database storage and Django REST API.

## 🏗️ Architecture

### Service Components

1. **Teltonika Service** (`teltonika_service.py`)

   - Receives GPS data from Teltonika devices on port 5000
   - Processes Codec 8/8-Extended protocols
   - Stores data in PostgreSQL database
   - Logs to structured files

2. **Django API Service** (`django_api_service.py`)

   - REST API server on port 8000
   - Real-time data access by IMEI
   - Admin interface for data management
   - Live tracking capabilities

3. **PostgreSQL Database**
   - Stores device information and telemetry data
   - Optimized indexes for fast queries
   - Event tracking and system statistics

## 🚀 Quick Installation

### Prerequisites

- Ubuntu 18.04+ or similar Linux distribution
- Root access for installation

### One-Command Installation

```bash
sudo bash install.sh
```

This will:

- Install Python, PostgreSQL, and dependencies
- Create database and user accounts
- Set up Python virtual environment
- Install and configure systemd services
- Configure firewall rules
- Create management commands

## 📊 Database Schema

### Core Models

- **Device**: Device registration and status
- **TelemetryData**: GPS coordinates, speed, IO parameters
- **DeviceEvent**: Significant events (ignition, movement)
- **DataProcessingStatus**: Failed packet retry mechanism

## 🔧 Service Management

### Basic Commands

```bash
# Start both services
teltonika start

# Stop both services
teltonika stop

# Check status
teltonika status

# View logs
teltonika logs data    # Teltonika service logs
teltonika logs api     # Django API logs

# Database operations
teltonika db shell     # PostgreSQL shell
teltonika db migrate   # Run Django migrations
```

### Manual Service Control

```bash
# Individual service control
sudo systemctl start teltonika
sudo systemctl start teltonika-api

sudo systemctl stop teltonika
sudo systemctl stop teltonika-api

# Check logs
sudo journalctl -u teltonika -f
sudo journalctl -u teltonika-api -f
```

## 🌐 API Endpoints

### Base URL: `http://your-server:8000/api/`

### Device Management

```bash
# List all devices
GET /api/devices/

# Get device by IMEI
GET /api/devices/{imei}/

# Device statistics
GET /api/devices/{imei}/stats/
```

### Telemetry Data

```bash
# Get telemetry data by IMEI
GET /api/telemetry/by_imei/?imei=YOUR_IMEI

# Live tracking (all devices)
GET /api/live-tracking/

# Telemetry with filters
GET /api/telemetry/by_imei/?imei=123&start_date=2024-01-01&end_date=2024-01-02
```

### Events

```bash
# Device events
GET /api/events/

# Events by device
GET /api/events/?imei=YOUR_IMEI
```

## 🔧 Configuration

### Environment Variables

- `DJANGO_SETTINGS_MODULE=teltonika_db.settings`
- Database: `teltonika` with user `postgres` password `00oo00oo`

### Key Files

- **Service Config**: `/opt/teltonika/teltonika_service.py`
- **API Config**: `/opt/teltonika/django_api_service.py`
- **Logs**: `/var/log/teltonika/`
- **Data**: `/var/lib/teltonika/`

### Firewall Ports

- **5000**: Teltonika device connections
- **8000**: Django API server
- **22**: SSH access

## 📱 Device Configuration

Configure your Teltonika device to connect to:

- **Server IP**: Your server's IP address
- **Port**: 5000
- **Protocol**: TCP
- **Codec**: Codec8 or Codec8-Extended

## 🔍 Monitoring

### Log Files

```bash
# Service logs
tail -f /var/log/teltonika/teltonika_service.log

# GPS data (JSON format)
tail -f /var/log/teltonika/gps_data.log

# System status
teltonika monitor
```

### Database Monitoring

```bash
# Access PostgreSQL
sudo -u postgres psql teltonika

# Check recent data
SELECT * FROM tracking_telemetrydata ORDER BY timestamp DESC LIMIT 10;

# Device count
SELECT COUNT(*) FROM tracking_device;
```

### Performance Monitoring

```bash
# Check service status
systemctl status teltonika teltonika-api

# Resource usage
top -p $(pgrep -f teltonika)

# Network connections
netstat -tlnp | grep :5000
netstat -tlnp | grep :8000
```

## 🚨 Troubleshooting

### Common Issues

1. **Service won't start**

   ```bash
   # Check logs
   sudo journalctl -u teltonika -n 50

   # Check permissions
   ls -la /opt/teltonika/

   # Check Python environment
   /opt/teltonika/venv/bin/python --version
   ```

2. **Database connection issues**

   ```bash
   # Test database connection
   sudo -u postgres psql teltonika

   # Check PostgreSQL status
   sudo systemctl status postgresql

   # Reset database password
   sudo -u postgres psql -c "ALTER USER postgres PASSWORD '00oo00oo';"
   ```

3. **Devices can't connect**

   ```bash
   # Check firewall
   sudo ufw status

   # Check port binding
   sudo netstat -tlnp | grep :5000

   # Test connectivity
   telnet YOUR_SERVER_IP 5000
   ```

### Log Analysis

```bash
# Find connection issues
grep "IMEI" /var/log/teltonika/teltonika_service.log

# Find parsing errors
grep "ERROR" /var/log/teltonika/teltonika_service.log

# Check recent GPS data
tail -10 /var/log/teltonika/gps_data.log | jq '.'
```

## 📈 Performance Optimization

### Database Optimization

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_usage_count
FROM pg_stat_user_indexes;

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM tracking_telemetrydata WHERE imei = 'YOUR_IMEI';
```

### Service Optimization

- Adjust `max_connections` in teltonika_service.py
- Monitor memory usage with `htop`
- Use log rotation for large deployments

## 🔐 Security

### Firewall Configuration

```bash
# Basic firewall setup
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # Teltonika
sudo ufw allow 8000  # API (restrict to specific IPs in production)
```

### Database Security

- Change default database password
- Restrict database access to localhost
- Regular backups

### API Security

- Add API authentication for production
- Use HTTPS in production
- Rate limiting for API endpoints

## 📦 Backup and Recovery

### Database Backup

```bash
# Create backup
sudo -u postgres pg_dump teltonika > backup_$(date +%Y%m%d).sql

# Restore backup
sudo -u postgres psql teltonika < backup_20240101.sql
```

### Configuration Backup

```bash
# Backup configuration
tar -czf teltonika_config_$(date +%Y%m%d).tar.gz /opt/teltonika/
```

## 🔄 Updates and Maintenance

### Updating the System

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python packages
source /opt/teltonika/venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart services
teltonika restart
```

### Database Maintenance

```bash
# Run migrations
teltonika db migrate

# Vacuum database
sudo -u postgres psql teltonika -c "VACUUM ANALYZE;"
```

## 📞 Support

For issues and support:

1. Check the troubleshooting section above
2. Review log files for error messages
3. Check system resources (CPU, memory, disk space)
4. Verify network connectivity and firewall settings

## 📄 License

This project is designed for production use with Teltonika GPS tracking devices.
