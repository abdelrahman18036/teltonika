# Deployment Update Guide

This guide explains how to deploy updates to your Teltonika GPS tracker system.

## Quick Update Process

1. **On your development machine (Windows):**
   ```bash
   # Commit and push your changes
   git add .
   git commit -m "Your update description"
   git push origin main
   ```

2. **On your Ubuntu VPS:**
   ```bash
   # Navigate to repository and pull latest changes
   cd /root/teltonika
   git pull origin main
   
   # Run the update script
   chmod +x update.sh
   ./update.sh
   ```

## What the update script does:

- ✅ Stops running services safely
- ✅ Creates backup of current installation
- ✅ Copies new code to production directories
- ✅ Updates systemd service files
- ✅ Installs/updates Python dependencies
- ✅ Creates and applies database migrations
- ✅ Restarts all services
- ✅ Verifies everything is working
- ✅ Provides rollback instructions if needed

## Manual Update Steps (if needed):

If you prefer to update manually or the script fails:

### 1. Stop Services
```bash
sudo systemctl stop teltonika-django teltonika
```

### 2. Update Code
```bash
cd /root/teltonika
git pull origin main

# Copy Django files
sudo cp -r teltonika-django/* /opt/teltonika-django/

# Copy Service files  
sudo cp -r teltonika-service/* /opt/teltonika-service/
```

### 3. Update Dependencies
```bash
cd /opt/teltonika-django
pip3 install -r requirements.txt
```

### 4. Handle Database
```bash
cd /opt/teltonika-django
python3 manage.py makemigrations
python3 manage.py migrate
```

### 5. Restart Services
```bash
sudo systemctl daemon-reload
sudo systemctl start teltonika-django teltonika
```

## Monitoring

After update, monitor with:
```bash
# Check service status
systemctl status teltonika-django teltonika

# Watch logs
journalctl -u teltonika-django -u teltonika -f

# Test functionality
curl http://localhost:8000/api/
teltonika status
```

## Rollback

If something goes wrong, the update script creates automatic backups:
```bash
# Find your backup
ls /opt/backup-*

# Restore (replace TIMESTAMP with actual backup folder)
sudo systemctl stop teltonika-django teltonika
sudo rm -rf /opt/teltonika-django /opt/teltonika-service
sudo mv /opt/backup-TIMESTAMP/teltonika-django-backup /opt/teltonika-django
sudo mv /opt/backup-TIMESTAMP/teltonika-service-backup /opt/teltonika-service
sudo systemctl start teltonika-django teltonika
```

## Custom Command Testing

After deployment, test your custom command functionality:

```bash
# Test via command line
teltonika command

# Test via API
curl -X POST http://localhost:8000/api/devices/YOUR_IMEI/command/ \
  -H "Content-Type: application/json" \
  -d '{"custom_command": "getstatus"}'
```

## Troubleshooting

### Django Issues
```bash
# Check Django logs
journalctl -u teltonika-django -n 50

# Test Django manually
cd /opt/teltonika-django
python3 manage.py runserver 0.0.0.0:8000
```

### Service Issues
```bash
# Check Teltonika service logs
journalctl -u teltonika -n 50

# Test service manually
cd /opt/teltonika-service
python3 teltonika_service.py
```

### Database Issues
```bash
# Check migration status
cd /opt/teltonika-django
python3 manage.py showmigrations

# Reset migrations (last resort)
python3 manage.py migrate gps_data zero
python3 manage.py migrate
```

## File Locations

- **Repository:** `/root/teltonika/`
- **Django App:** `/opt/teltonika-django/`
- **Service:** `/opt/teltonika-service/`
- **Logs:** `/var/log/teltonika/`
- **Service Files:** `/etc/systemd/system/`
- **Backups:** `/opt/backup-TIMESTAMP/`

## Security Notes

- The update script runs as root (required for systemd operations)
- Backups are created automatically before each update
- Services are stopped gracefully to prevent data loss
- All file permissions are set correctly during update
