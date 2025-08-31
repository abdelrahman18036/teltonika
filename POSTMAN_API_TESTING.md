# Teltonika GPS API Testing Guide - Postman Collection

Complete API testing guide for Teltonika GPS Tracking System with device IMEI: `864275070621324`

## 🚀 Base Configuration

**Base URL:** `http://151.106.112.187:8000`  
**Device IMEI:** `864275070621324`  
**Content-Type:** `application/json`

---

## 📋 Postman Environment Setup

Create these environment variables in Postman:

| Variable | Value |
|----------|-------|
| `base_url` | `http://151.106.112.187:8000` |
| `device_imei` | `864275070621324` |

---

## 🔍 1. Health Check & System Status

### Test Django Admin (Health Check)
```http
GET {{base_url}}/admin/
```

**Expected Response:** HTTP 200 or 302 (redirect to login)

### Test API Root
```http
GET {{base_url}}/api/
```

---

## 📱 2. Device Management

### Get All Devices
```http
GET {{base_url}}/api/devices/
```

### Get Specific Device
```http
GET {{base_url}}/api/devices/{{device_imei}}/
```

### Get Device GPS Records
```http
GET {{base_url}}/api/devices/{{device_imei}}/records/
```

### Get Device Commands History
```http
GET {{base_url}}/api/devices/{{device_imei}}/commands/
```

---

## 🔐 3. Digital Output Commands

### Lock Vehicle (DOUT1 HIGH)
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "digital_output",
  "command_name": "lock"
}
```

### Unlock Vehicle (DOUT2 HIGH)
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "digital_output",
  "command_name": "unlock"
}
```

### Mobilize Engine (DOUT3 HIGH)
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "digital_output",
  "command_name": "mobilize"
}
```

### Immobilize Engine (DOUT3 LOW)
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "digital_output",
  "command_name": "immobilize"
}
```

---

## 🚗 4. CAN Control Commands

### CAN Lock All Doors
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "can_control",
  "command_name": "lock"
}
```

### CAN Unlock All Doors
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "can_control",
  "command_name": "unlock"
}
```

### CAN Block Engine
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "can_control",
  "command_name": "immobilize"
}
```

### CAN Unblock Engine
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "can_control",
  "command_name": "mobilize"
}
```

---

## ⚙️ 5. Custom Commands

### Get Device Status
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getstatus",
  "custom_command": "getstatus"
}
```

### Get Device Version
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getver",
  "custom_command": "getver"
}
```

### Get Device Information
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getinfo",
  "custom_command": "getinfo"
}
```

### Custom Digital Output Pattern
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "custom_setdigout",
  "custom_command": "setdigout 123"
}
```

### Get GSM Info
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getgsminfo",
  "custom_command": "getgsminfo"
}
```

### Get GPS Info
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getgpsinfo",
  "custom_command": "getgpsinfo"
}
```

---

## 📊 6. Advanced Testing Commands

### Custom IO Control
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "iocontrol",
  "custom_command": "setio 11 1"
}
```

### Set Device Parameters
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "setparam",
  "custom_command": "setparam 1001:30"
}
```

### Get Configuration
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "getparam",
  "custom_command": "getparam 1001"
}
```

---

## 🔧 7. Terminal/Command Line Testing

### Quick Health Check
```bash
curl -I http://151.106.112.187:8000/admin/
```

### Test Device API
```bash
curl http://151.106.112.187:8000/api/devices/864275070621324/
```

### Send Lock Command
```bash
curl -X POST http://151.106.112.187:8000/api/devices/864275070621324/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command_type": "digital_output", "command_name": "lock"}'
```

### Send Custom Command
```bash
curl -X POST http://151.106.112.187:8000/api/devices/864275070621324/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command_type": "custom", "command_name": "getstatus", "custom_command": "getstatus"}'
```

### Check Command History
```bash
curl http://151.106.112.187:8000/api/devices/864275070621324/commands/
```

---

## 📋 8. Expected Response Formats

### Successful Command Response
```json
{
  "id": 123,
  "command_type": "digital_output",
  "command_name": "lock",
  "status": "pending",
  "created_at": "2025-08-31T10:30:00Z",
  "sent_at": null,
  "response_at": null,
  "response_data": null
}
```

### Device Information Response
```json
{
  "imei": "864275070621324",
  "last_seen": "2025-08-31T10:25:00Z",
  "is_online": true,
  "total_records": 15420,
  "last_location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timestamp": "2025-08-31T10:25:00Z"
  }
}
```

### Command History Response
```json
{
  "count": 25,
  "results": [
    {
      "id": 123,
      "command_type": "custom",
      "command_name": "getstatus",
      "status": "completed",
      "created_at": "2025-08-31T10:30:00Z",
      "sent_at": "2025-08-31T10:30:01Z",
      "response_at": "2025-08-31T10:30:03Z",
      "response_data": "Status: OK"
    }
  ]
}
```

---

## 🚨 9. Error Testing

### Invalid Device IMEI
```http
GET {{base_url}}/api/devices/invalid_imei/
```

### Invalid Command Type
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "invalid_type",
  "command_name": "test"
}
```

### Missing Required Fields
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_name": "lock"
}
```

---

## 📈 10. Performance Testing

### Load Test - Multiple Commands
```http
POST {{base_url}}/api/devices/{{device_imei}}/commands/
Content-Type: application/json

{
  "command_type": "custom",
  "command_name": "test_{{$randomInt}}",
  "custom_command": "getstatus"
}
```

### Stress Test Device Endpoint
```http
GET {{base_url}}/api/devices/{{device_imei}}/
```

---

## 🔍 11. Monitoring & Debugging

### Check Service Status
```bash
# On server
teltonika status
```

### View Django Logs
```bash
# On server
sudo journalctl -u teltonika-django -f
```

### Monitor API Calls
```bash
# On server
sudo tail -f /var/log/nginx/access.log
```

---

## 📚 12. Postman Collection Import

To import this as a Postman collection:

1. Copy the requests above into Postman
2. Set up the environment variables
3. Organize into folders:
   - Health Checks
   - Device Management
   - Digital Output Commands
   - CAN Control Commands
   - Custom Commands
   - Error Testing

---

## 🏷️ Tags for Organization

- `health` - Health check endpoints
- `device` - Device management
- `digital_output` - Digital output commands
- `can_control` - CAN bus commands
- `custom` - Custom Teltonika commands
- `monitoring` - System monitoring
- `error` - Error testing

---

## 🔗 Quick Links

- **Django Admin:** http://151.106.112.187/admin/
- **API Root:** http://151.106.112.187:8000/api/
- **Device Commands:** http://151.106.112.187:8000/api/devices/864275070621324/commands/

---

## 📝 Notes

- All POST requests require `Content-Type: application/json` header
- Commands are queued and executed asynchronously
- Check command status using the commands history endpoint
- Custom commands support any valid Teltonika command syntax
- Response times may vary based on device connectivity

---

**🚀 Happy Testing!**
