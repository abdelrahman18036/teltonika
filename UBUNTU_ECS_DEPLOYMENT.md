# Ubuntu ECS Deployment Guide - Teltonika GPS Tracking System

## 🚀 Complete Deployment Guide for AWS ECS Ubuntu Instance

This guide provides step-by-step instructions for deploying the Teltonika GPS Tracking System on a fresh Ubuntu ECS instance.

---

## 📋 Prerequisites

### AWS ECS Instance Requirements

- **Instance Type**: t3.medium or higher (minimum 4GB RAM)
- **Storage**: 20GB+ EBS volume
- **OS**: Ubuntu 20.04 LTS or 22.04 LTS
- **Security Groups**:
  - SSH (22)
  - HTTP (80)
  - HTTPS (443)
  - Teltonika Service (5000)

### Network Configuration

- Assign an Elastic IP address
- Configure DNS (optional but recommended)
- Ensure internet connectivity

---

## 🔧 Step-by-Step Deployment

### Step 1: Connect to Your ECS Instance

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y
```

### Step 2: Clone the Repository

```bash
# Install git if not present
sudo apt install git -y

# Clone the repository
git clone https://github.com/your-username/teltonika.git
cd teltonika

# Make scripts executable
chmod +x install.sh
chmod +x install_django.sh
```

### Step 3: Run the Complete Installation

```bash
# Run the main installation script
sudo bash install.sh

# Wait for completion (approximately 10-15 minutes)
# The script will automatically:
# - Install all dependencies
# - Configure PostgreSQL
# - Set up Django
# - Configure Nginx
# - Start all services
```

### Step 4: Verify Installation

```bash
# Check service status
teltonika status

# Run system monitor
teltonika monitor

# Test performance
teltonika test

# Check web interface
curl http://localhost/health
```

---

## 🌐 Post-Installation Configuration

### 1. Update Security Settings

```bash
# Change default admin password
teltonika-django shell
# In Django shell:
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.get(username='admin')
admin.set_password('your-secure-password')
admin.save()
exit()
```

### 2. Configure Environment Variables

```bash
# Edit Django environment file
sudo nano /opt/teltonika/django/.env

# Update these critical settings:
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_HOSTS=your-domain.com,your-ec2-ip,localhost,127.0.0.1
DEBUG=False
```

### 3. Configure SSL Certificate (Recommended)

```bash
# Install SSL certificate with Let's Encrypt
sudo certbot --nginx -d your-domain.com

# The certificate will auto-renew
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 4. Configure Firewall

```bash
# Check firewall status
sudo ufw status

# The installation script already configured:
# - SSH (22)
# - HTTP (80)
# - HTTPS (443)
# - Teltonika Service (5000)
```

---

## 📊 System Management

### Service Management Commands

```bash
# Start all services
teltonika start

# Stop all services
teltonika stop

# Restart services
teltonika restart

# Check status
teltonika status

# View system monitor
teltonika monitor

# Run performance tests
teltonika test

# View logs
teltonika logs
```

### Django-Specific Commands

```bash
# Django service management
teltonika-django start
teltonika-django stop
teltonika-django restart
teltonika-django status

# Django utilities
teltonika-django shell        # Open Django shell
teltonika-django migrate      # Run migrations
teltonika-django backup       # Create backup
teltonika-django monitor      # Django monitor
```

---

## 🔍 Monitoring and Maintenance

### 1. System Monitoring

```bash
# Real-time monitoring
teltonika monitor

# View specific logs
teltonika logs
# Choose from:
# 1) Teltonika service logs
# 2) Django API logs
# 3) Nginx logs
# 4) Live GPS data
```

### 2. Performance Monitoring

```bash
# Check system performance
teltonika test

# View scale information
teltonika scale

# Monitor database size
teltonika-django monitor
```

### 3. Backup Management

```bash
# Create manual backup
teltonika-django backup

# Backups are automatically created daily at 2 AM
# Location: /opt/teltonika/backups/
```

---

## 🌐 Web Interface Access

### Admin Panel

- **URL**: `http://your-ec2-ip/admin/`
- **Username**: `admin`
- **Password**: `admin123` (change immediately)

### API Endpoints

- **Health Check**: `http://your-ec2-ip/health`
- **API Base**: `http://your-ec2-ip/api/`
- **Device List**: `http://your-ec2-ip/api/devices/`
- **GPS Records**: `http://your-ec2-ip/api/gps/`

---

## 📡 GPS Device Configuration

### Device Settings

Configure your Teltonika GPS devices with:

- **Server IP**: `your-ec2-ip`
- **Port**: `5000`
- **Protocol**: `TCP`
- **Codec**: `Codec8` or `Codec8 Extended`

### Example Device Configuration

```
Server Settings:
- Primary Server: your-ec2-ip:5000
- Secondary Server: (optional backup)
- Protocol: TCP
- Data Format: Codec8
- Send Period: 30 seconds
- Records to Send: 50
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Services Not Starting

```bash
# Check service status
systemctl status teltonika
systemctl status teltonika-django
systemctl status postgresql
systemctl status nginx

# Check logs
journalctl -u teltonika -f
journalctl -u teltonika-django -f
```

#### 2. Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT version();"

# Check database exists
sudo -u postgres psql -l | grep teltonika
```

#### 3. Web Interface Not Accessible

```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx configuration
sudo nginx -t

# Check firewall
sudo ufw status

# Test local connection
curl http://localhost/health
```

#### 4. GPS Devices Not Connecting

```bash
# Check if port 5000 is open
netstat -tlnp | grep :5000

# Check firewall
sudo ufw status | grep 5000

# Monitor live connections
teltonika logs
# Choose option 4 for live GPS data
```

---

## 📈 Performance Optimization

### System Capacity

- **Concurrent Devices**: 1,000+
- **Records per Second**: 673+
- **Daily Records**: 58+ Million
- **Storage**: Unlimited (PostgreSQL)

### Scaling Recommendations

#### For 100-500 Devices

- Current setup is sufficient
- Monitor CPU and memory usage

#### For 500-1,000 Devices

- Consider upgrading to t3.large
- Increase PostgreSQL shared_buffers to 1GB

#### For 1,000+ Devices

- Upgrade to t3.xlarge or higher
- Consider database clustering
- Implement load balancing

---

## 🔒 Security Best Practices

### 1. Change Default Passwords

```bash
# Change admin password (done via Django shell above)
# Change PostgreSQL password if needed
sudo -u postgres psql -c "ALTER USER teltonika PASSWORD 'new-secure-password';"
```

### 2. Configure SSL

```bash
# Install SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 3. Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
sudo -u teltonika /opt/teltonika/venv/bin/pip install --upgrade pip
```

### 4. Monitor Security

```bash
# Check failed login attempts
sudo grep "Failed password" /var/log/auth.log

# Monitor system access
sudo last -10
```

---

## 📋 Maintenance Schedule

### Daily

- ✅ Automatic backups (2 AM)
- ✅ Log rotation
- ✅ System monitoring

### Weekly

- Check system updates
- Review performance metrics
- Clean old log files

### Monthly

- Review security logs
- Update SSL certificates (automatic)
- Performance optimization review

---

## 🆘 Emergency Procedures

### System Recovery

```bash
# If system becomes unresponsive
sudo systemctl restart teltonika
sudo systemctl restart teltonika-django
sudo systemctl restart nginx

# Database recovery
sudo systemctl restart postgresql
teltonika-django migrate
```

### Backup Restoration

```bash
# Restore from backup
cd /opt/teltonika/backups
# Extract latest backup
tar -xzf teltonika_backup_YYYYMMDD_HHMMSS.tar.gz
# Follow restoration procedures
```

---

## 📞 Support and Resources

### Log Locations

- **Teltonika Service**: `/var/log/teltonika/teltonika_service.log`
- **Django**: `/var/log/teltonika/django.log`
- **Nginx**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`

### Configuration Files

- **Django Settings**: `/opt/teltonika/django/.env`
- **Nginx Config**: `/etc/nginx/sites-available/teltonika`
- **PostgreSQL**: `/etc/postgresql/*/main/postgresql.conf`

### Useful Commands

```bash
# Quick system check
teltonika status && teltonika-django status

# Full system monitor
teltonika monitor && teltonika-django monitor

# Emergency restart
teltonika restart && teltonika-django restart
```

---

## ✅ Deployment Checklist

After deployment, verify:

- [ ] All services are running
- [ ] Web interface is accessible
- [ ] Health check returns 200
- [ ] GPS devices can connect to port 5000
- [ ] Database is storing data
- [ ] Backups are working
- [ ] SSL certificate is installed (if applicable)
- [ ] Firewall is configured
- [ ] Admin password is changed
- [ ] Monitoring is active

---

## 🎯 Quick Start Summary

1. **Launch Ubuntu ECS instance** (t3.medium+, 20GB+)
2. **Connect via SSH** and update system
3. **Clone repository** and run `sudo bash install.sh`
4. **Wait 10-15 minutes** for complete installation
5. **Access admin panel** at `http://your-ip/admin/`
6. **Configure GPS devices** to connect to `your-ip:5000`
7. **Monitor system** with `teltonika monitor`

**That's it! Your Teltonika GPS Tracking System is ready for production use.**
