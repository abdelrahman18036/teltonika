# Teltonika GPS Tracking System

**Complete Edition: Teltonika TCP server + Django REST API + PostgreSQL**

📚 This repository contains everything you need to ingest Teltonika AVL packets on port 5000, persist them in PostgreSQL via a Django REST API, and expose a web admin interface.

---

## 1. Repository layout

| Path                 | Purpose                                                                                                                       |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `install.sh`         | One–shot provisioning script for a fresh Ubuntu host (installs packages, PostgreSQL, virtual-env, systemd units, Nginx, etc.) |
| `teltonika-service/` | Stand-alone TCP server that parses Teltonika AVL packets and forwards them to Django                                          |
| `teltonika-django/`  | Django 5.x project (`gps_data` app) storing devices + GPS records                                                             |

---

## 2. Quick start (production install)

```bash
# ⬇️ Clone & install (run as root)
apt update && apt install -y git
git clone https://github.com/abdelrahman18036/teltonika.git
cd teltonika
sudo bash install.sh
```

The script is **idempotent** – re-running is safe; it skips existing users, DB, etc.

After ~2-3 minutes you will see:

```
🎉 Installation completed successfully!
🌐 Admin Panel: http://<server-ip>/admin/
👤 Admin Login: orange / 00oo00oo
📡 GPS Service Port: 5000/TCP
```

---

## 3. Runtime operations

### 3.1 Unified CLI wrapper

`/usr/local/bin/teltonika <command>`

| Command   | What it does                                                          |
| --------- | --------------------------------------------------------------------- |
| `start`   | Start PostgreSQL → Django (Gunicorn) → Teltonika TCP → Nginx          |
| `stop`    | Stop Teltonika TCP, Django, Nginx                                     |
| `restart` | Restart all services                                                  |
| `status`  | `systemctl status` summary for core services                          |
| `monitor` | Interactive system monitor (CPU, RAM, service states, DB counts)      |
| `test`    | End-to-end performance test (ports 5000 & 8000)                       |
| `logs`    | Interactive log viewer (choose Teltonika / Django / Nginx / live GPS) |
| `scale`   | Show current capacity numbers & run monitor                           |

### 3.2 Systemd units

```
systemctl status teltonika            # TCP server
systemctl status teltonika-django     # Gunicorn API server
systemctl status postgresql
systemctl status nginx
```

Use `start|stop|restart` instead of `status` for lifecycle control.

### 3.3 Django management

Activate the virtual-env first or prefix with full path.

```bash
# Enter venv
source /opt/teltonika/venv/bin/activate
cd /opt/teltonika/django

# Create **extra** superuser interactively
python manage.py createsuperuser

# Apply new migrations
python manage.py migrate

# Collect static assets (if you added new CSS/JS)
python manage.py collectstatic --noinput
```

---

## 4. File & directory map (after install)

| Location                                      | Description                                                                 |
| --------------------------------------------- | --------------------------------------------------------------------------- |
| `/opt/teltonika/service/teltonika_service.py` | Teltonika TCP server (port 5000)                                            |
| `/opt/teltonika/django/`                      | Django project root                                                         |
| `/opt/teltonika/django/staticfiles/`          | Collected static files served by Nginx                                      |
| `/var/log/teltonika/`                         | Rotated logs (`teltonika_service.log`, `gps_data.log`, `device_events.log`) |
| `/usr/local/bin/teltonika`                    | Helper CLI                                                                  |

---

## 5. Default credentials & ports

| Item         | Value                                         |
| ------------ | --------------------------------------------- |
| Superuser    | **orange / 00oo00oo**                         |
| GPS TCP port | **5000**                                      |
| Django API   | **http://<server-ip>:8000/api/**              |
| Admin UI     | **http://<server-ip>/admin/** via Nginx proxy |

> 🔐 **Change the password and set a new `SECRET_KEY` before production!**

---

## 6. Development setup (optional)

```bash
# local dev (Ubuntu / Debian)
python3 -m venv venv && source venv/bin/activate
pip install -r teltonika-django/requirements.txt
cd teltonika-django
python manage.py migrate
env DJANGO_SETTINGS_MODULE=teltonika_gps.settings python manage.py runserver 0.0.0.0:8000
```

Run the TCP server in another shell:

```bash
python teltonika-service/teltonika_service.py
```

---

### 7. Troubleshooting

| Symptom                     | Fix                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------ |
| Nginx 502                   | Check `systemctl status teltonika-django` (Gunicorn crashed?)                        |
| TCP port 5000 not listening | `systemctl restart teltonika` and inspect `/var/log/teltonika/teltonika_service.log` |
| DB auth errors              | `sudo -u postgres psql` → `\du` to verify user `teltonika`                           |

---

## 8. License

MIT © 2025 Abdelrahman El-Sayed
