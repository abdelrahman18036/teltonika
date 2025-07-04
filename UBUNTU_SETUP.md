# Teltonika Server - Ubuntu Production Setup

Complete guide to deploy Teltonika GPS tracking server as a production service on Ubuntu with real-time logging and monitoring.

## 🚀 **Quick Installation**

```bash
# Download all files to a directory
sudo bash install.sh
```

The installation script will:

- Create system user and directories
- Install the service
- Configure logging and monitoring
- Start the service automatically
- Set up convenient management commands

## 📋 **Manual Installation Steps**

If you prefer manual installation:

### 1. **System Setup**

```bash
# Create system user
sudo useradd --system --shell /bin/false --home-dir /opt/teltonika --create-home teltonika

# Create directories
sudo mkdir -p /opt/teltonika
sudo mkdir -p /var/log/teltonika
sudo mkdir -p /var/lib/teltonika

# Set permissions
sudo chown -R teltonika:teltonika /opt/teltonika /var/log/teltonika /var/lib/teltonika
sudo chmod 755 /opt/teltonika /var/log/teltonika /var/lib/teltonika
```

### 2. **Install Service Files**

```bash
# Copy service files
sudo cp teltonika_service.py /opt/teltonika/
sudo cp test_data_generator.py /opt/teltonika/
sudo chmod +x /opt/teltonika/*.py
sudo chown teltonika:teltonika /opt/teltonika/*.py
```

### 3. **Configure Systemd Service**

```bash
# Install service file
sudo cp teltonika.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teltonika
sudo systemctl start teltonika
```

### 4. **Configure Firewall**

```bash
# Open port 5000 (if using ufw)
sudo ufw allow 5000/tcp
```

## 🎛️ **Service Management**

### **Basic Commands**

```bash
# Start/Stop/Restart service
teltonika start
teltonika stop
teltonika restart

# Check status
teltonika status

# View real-time logs
teltonika logs

# Monitor dashboard
teltonika monitor

# Run test data generator
teltonika test
```

### **Manual systemctl Commands**

```bash
# Service management
sudo systemctl start teltonika
sudo systemctl stop teltonika
sudo systemctl restart teltonika
sudo systemctl status teltonika

# View logs
sudo journalctl -u teltonika -f
sudo journalctl -u teltonika --since "1 hour ago"
```

## 📁 **Log Files and Data Structure**

### **Log Files Location**

```
/var/log/teltonika/
├── teltonika_service.log    # Main service logs
├── gps_data.log            # GPS tracking data (JSON)
└── device_events.log       # Device connection events
```

### **GPS Data Log Format**

Each line in `gps_data.log` contains JSON data:

```json
{
  "imei": "356307042441013",
  "timestamp": "2024-01-15T14:30:45.123456",
  "latitude": 25.276987,
  "longitude": 55.296249,
  "altitude": 10,
  "angle": 45,
  "satellites": 12,
  "speed": 65,
  "io_data": {
    "1": 1, // Ignition ON
    "21": 4, // GSM Signal
    "66": 12800, // Voltage (12.8V)
    "239": 1 // Ignition Status
  }
}
```

### **Real-time Log Monitoring**

```bash
# Watch GPS data in real-time
tail -f /var/log/teltonika/gps_data.log

# Pretty print JSON logs
tail -f /var/log/teltonika/gps_data.log | jq '.'

# Filter specific IMEI
grep "356307042441013" /var/log/teltonika/gps_data.log | tail -10

# Show only locations
tail -f /var/log/teltonika/gps_data.log | jq -r '"Time: \(.timestamp) | GPS: \(.latitude),\(.longitude) | Speed: \(.speed)km/h"'
```

## 🧪 **Testing the Service**

### **1. Test with Sample Data Generator**

```bash
# Run test data generator
teltonika test

# Or manually
cd /opt/teltonika
python3 test_data_generator.py
```

### **2. Monitor Real-time Data**

```bash
# In one terminal - start monitoring
teltonika logs

# In another terminal - run test data
teltonika test
```

### **3. Expected Output**

When test data is running, you should see:

```
🚗 356307042441013 - 14:30:45 - GPS: 25.276987, 55.296249
   📊 Signal: 4, Voltage: 12.8V, Ignition: ON
🚗 356307042441013 - 14:31:15 - GPS: 25.277123, 55.296456
   📊 Signal: 4, Voltage: 12.7V, Ignition: ON
```

## 📊 **Production Monitoring**

### **Service Health Check**

```bash
# Check if service is running
systemctl is-active teltonika

# Get detailed status
teltonika status

# Monitor resource usage
sudo htop -p $(pgrep -f teltonika_service)
```

### **Log Analysis**

```bash
# Count devices connected today
grep "IMEI_ACCEPTED" /var/log/teltonika/device_events.log | grep $(date +%Y-%m-%d) | wc -l

# Show unique devices
grep "IMEI_ACCEPTED" /var/log/teltonika/device_events.log | jq -r '.imei' | sort | uniq

# GPS data statistics
grep $(date +%Y-%m-%d) /var/log/teltonika/gps_data.log | wc -l
```

### **Performance Monitoring**

```bash
# Network connections
netstat -tlnp | grep :5000

# Disk usage
du -sh /var/log/teltonika/

# Memory usage
ps aux | grep teltonika_service
```

## 🔧 **Configuration**

### **Change Server Port**

Edit `/opt/teltonika/teltonika_service.py`:

```python
CONFIG = {
    'host': '0.0.0.0',
    'port': 8080,  # Change from 5000 to 8080
    # ... rest of config
}
```

Then restart:

```bash
teltonika restart
```

### **Log Rotation**

Logs are automatically rotated daily. Configuration in `/etc/logrotate.d/teltonika`:

```
/var/log/teltonika/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 teltonika teltonika
}
```

## 🚗 **Connecting Your Real Device**

### **Device Configuration**

Configure your Teltonika device:

1. **Server Settings:**

   ```
   Server IP: YOUR_SERVER_IP
   Server Port: 5000
   Protocol: TCP
   ```

2. **Data Settings:**

   ```
   Codec: Codec8
   Data Sending: Enabled
   Period: 30 seconds
   ```

3. **GPRS Settings:**
   ```
   APN: your_carrier_apn
   Username: (if required)
   Password: (if required)
   ```

### **SMS Configuration Commands**

Send these SMS to your device:

```sms
setparam 2003:YOUR_SERVER_IP
setparam 2004:5000
setparam 2001:1
setparam 2002:30
```

### **Verify Connection**

```bash
# Monitor for new connections
teltonika logs

# Check device events
tail -f /var/log/teltonika/device_events.log

# Monitor GPS data
tail -f /var/log/teltonika/gps_data.log | jq '.'
```

## 🚨 **Troubleshooting**

### **Service Won't Start**

```bash
# Check service status
systemctl status teltonika

# Check service logs
journalctl -u teltonika -n 50

# Check if port is available
netstat -tlnp | grep :5000

# Test manually
sudo -u teltonika python3 /opt/teltonika/teltonika_service.py
```

### **Device Won't Connect**

```bash
# Check firewall
sudo ufw status
sudo iptables -L | grep 5000

# Test port connectivity
nc -l 5000  # Listen on port
nc YOUR_SERVER_IP 5000  # Test from another machine

# Check server logs for connection attempts
grep "New connection" /var/log/teltonika/teltonika_service.log
```

### **No GPS Data**

```bash
# Check if IMEI is accepted
grep "IMEI_ACCEPTED" /var/log/teltonika/device_events.log

# Check for parsing errors
grep "Error parsing" /var/log/teltonika/teltonika_service.log

# Verify data format
tail /var/log/teltonika/teltonika_service.log | grep "Received.*bytes"
```

## 📈 **Scaling for Production**

### **Multiple Instances**

For high traffic, run multiple instances:

```bash
# Edit config for different ports
cp /opt/teltonika/teltonika_service.py /opt/teltonika/teltonika_service_8001.py
# Edit port in the new file to 8001

# Create new service file
cp /etc/systemd/system/teltonika.service /etc/systemd/system/teltonika-8001.service
# Edit service file to use new script

# Start additional instance
systemctl enable teltonika-8001
systemctl start teltonika-8001
```

### **Database Integration**

Add database storage by modifying the `log_gps_data()` function:

```python
import sqlite3

def store_in_database(self, record):
    conn = sqlite3.connect('/var/lib/teltonika/tracking.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO gps_data (imei, timestamp, latitude, longitude, speed, io_data)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (record['imei'], record['timestamp'], record['gps']['latitude'],
          record['gps']['longitude'], record['gps']['speed'],
          json.dumps(record['io']['io_data'])))
    conn.commit()
    conn.close()
```

### **Web Dashboard**

Create a simple web interface:

```python
from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route('/api/devices')
def get_devices():
    # Read from log files or database
    return jsonify({'devices': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

## 🔒 **Security Considerations**

### **Firewall Rules**

```bash
# Only allow specific IPs
sudo ufw allow from DEVICE_IP to any port 5000

# Or limit to local network
sudo ufw allow from 192.168.1.0/24 to any port 5000
```

### **SSL/TLS (Optional)**

For encrypted communication, wrap the socket with SSL:

```python
import ssl

# In your server
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="server.crt", keyfile="server.key")
secure_socket = context.wrap_socket(server_socket, server_side=True)
```

### **Access Control**

Restrict log file access:

```bash
sudo chmod 640 /var/log/teltonika/*.log
sudo chown teltonika:adm /var/log/teltonika/*.log
```

## 📞 **Support and Maintenance**

### **Regular Maintenance**

```bash
# Check log sizes weekly
du -sh /var/log/teltonika/

# Verify service health
teltonika status

# Update system
sudo apt update && sudo apt upgrade
```

### **Backup Important Data**

```bash
# Backup GPS data
tar -czf gps_backup_$(date +%Y%m%d).tar.gz /var/log/teltonika/gps_data.log*

# Backup configuration
cp /opt/teltonika/teltonika_service.py ~/teltonika_backup/
```

### **Performance Optimization**

For high-volume deployments:

1. **Increase file limits** in service file
2. **Use SSD storage** for log files
3. **Monitor memory usage** and adjust Python garbage collection
4. **Consider load balancing** for multiple devices

---

**🎉 Your Teltonika server is now ready for production use!**

The service will automatically:

- ✅ Start on boot
- ✅ Log all GPS data to files
- ✅ Rotate logs automatically
- ✅ Handle multiple devices simultaneously
- ✅ Provide real-time monitoring

For questions or issues, check the troubleshooting section or examine the service logs.
