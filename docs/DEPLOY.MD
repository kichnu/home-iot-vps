# Production Deployment Guide

Deploy Home IoT Platform on Ubuntu/Debian VPS with nginx, SSL, and systemd.

## Overview

This guide covers production deployment on a VPS with:
- **Nginx** as reverse proxy with SSL/TLS
- **Systemd** for service management and auto-restart
- **Let's Encrypt** for free SSL certificates
- **UFW** firewall for security

**Estimated time:** 30-45 minutes  
**Downtime:** None (fresh installation)

---

## Prerequisites

### Server Requirements
- **OS:** Ubuntu 20.04+ or Debian 11+
- **RAM:** Minimum 512MB (1GB+ recommended)
- **Disk:** 2GB free space minimum
- **Network:** Public IP address with ports 80/443 accessible

### Before You Begin
- ✅ VPS with root/sudo access
- ✅ Domain name with DNS A record pointing to server IP
- ✅ SSH access configured
- ✅ Basic Linux command line knowledge

### Check Your Setup
```bash
# Check OS version
lsb_release -a

# Check available memory
free -h

# Check disk space
df -h

# Verify domain DNS (from your local machine)
nslookup your-domain.com
```

---

## Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│  Firewall (UFW)                         │
│  Ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)│
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Nginx (Port 443)                       │
│  - SSL Termination (Let's Encrypt)      │
│  - Reverse Proxy                        │
│  - Security Headers                     │
└────────┬───────────────┬────────────────┘
         │               │
         ▼               ▼
┌──────────────┐  ┌──────────────┐
│ Flask API    │  │ Admin Panel  │
│ Port 5000    │  │ Port 5001    │
│ (localhost)  │  │ (localhost)  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌───────────────────────────────┐
│  SQLite Database              │
│  /opt/home-iot/water_events.db│
└───────────────────────────────┘
```

---

## Step 1: System Preparation

### Update System

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    software-properties-common \
    build-essential \
    curl \
    wget \
    git \
    vim
```

### Install Python 3.8+

```bash
# Check Python version
python3 --version

# If Python < 3.8, install Python 3.10
sudo apt install -y python3.10 python3.10-venv python3-pip

# Verify installation
python3 --version  # Should be 3.8+
```

### Install nginx

```bash
# Install nginx
sudo apt install -y nginx

# Start and enable nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Verify nginx is running
sudo systemctl status nginx
```

### Install Certbot (Let's Encrypt)

```bash
# Install Certbot for nginx
sudo apt install -y certbot python3-certbot-nginx

# Verify installation
certbot --version
```

---

## Step 2: Application Setup

### Create Application Directory

```bash
# Create directory in /opt (standard for third-party applications)
sudo mkdir -p /opt/home-iot

# Set ownership to your user
sudo chown $USER:$USER /opt/home-iot

# Navigate to directory
cd /opt/home-iot
```

### Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/yourusername/home-iot.git .

# Verify files
ls -la
# Should see: app.py, requirements.txt, templates/, etc.

# Check Git status
git status
git remote -v
```

### Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify Flask installation
python -c "import flask; print(f'Flask {flask.__version__}')"

# Deactivate for now
deactivate
```

---

## Step 3: Configure Credentials

**⚠️ CRITICAL:** Use strong, unique credentials in production!

### Generate Production Credentials

```bash
cd /opt/home-iot

# Activate virtual environment
source venv/bin/activate

# Generate strong production credentials
python generate_credentials.py \
    --output env \
    --password-length 40 \
    --no-symbols

# This creates /opt/home-iot/.env with:
# - 40-character admin password (no special symbols for CLI ease)
# - 64-character API token
# - 64-character Flask secret key
```

### Verify .env File

```bash
# Check .env exists and has secure permissions
ls -la .env
# Should show: -rw------- (600 permissions)

# View (but don't log!) credentials
cat .env | grep -E "ADMIN_PASSWORD|API_TOKEN"

# IMPORTANT: Save these credentials securely!
# - Copy admin password to password manager
# - Copy API token for ESP32 configuration
```

### Customize Configuration (Optional)

```bash
# Edit .env for production paths
nano .env
```

**Recommended production settings:**
```bash
WATER_SYSTEM_DATABASE_PATH=/opt/home-iot/water_events.db
WATER_SYSTEM_LOG_PATH=/opt/home-iot/app.log
WATER_SYSTEM_HTTP_PORT=5000
WATER_SYSTEM_ADMIN_PORT=5001
WATER_SYSTEM_NGINX_MODE=true
WATER_SYSTEM_LOG_LEVEL=INFO
WATER_SYSTEM_SESSION_TIMEOUT=30
WATER_SYSTEM_MAX_FAILED_ATTEMPTS=8
```

**→ Detailed credential management:** [guides/CREDENTIALS.md](guides/CREDENTIALS.md)

---

## Step 3.5: Install Rate Limiting Dependencies

Rate limiting is **essential for production security** to prevent brute-force attacks and API abuse.

### Install Flask-Limiter
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install Flask-Limiter
pip install Flask-Limiter

# Verify installation
python -c "import flask_limiter; print('✅ Flask-Limiter installed')"

# Update requirements.txt (optional, for future deployments)
pip freeze | grep Flask-Limiter >> requirements.txt

# Deactivate venv
deactivate

---

## Step 4: Systemd Service Configuration

### Create Systemd Service File

```bash
sudo tee /etc/systemd/system/home-iot.service > /dev/null <<'EOF'
[Unit]
Description=Home IoT Multi-Device Platform
After=network.target
Wants=network.target

[Service]
Type=simple
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/opt/home-iot
ExecStart=/opt/home-iot/venv/bin/python /opt/home-iot/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/opt/home-iot

[Install]
WantedBy=multi-user.target
EOF
```

**⚠️ IMPORTANT:** Replace `YOUR_USERNAME` with your actual username:

```bash
# Replace YOUR_USERNAME with current user
sudo sed -i "s/YOUR_USERNAME/$USER/g" /etc/systemd/system/home-iot.service

# Verify replacement
sudo cat /etc/systemd/system/home-iot.service | grep "User="
```

### Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable home-iot

# Start service
sudo systemctl start home-iot

# Check status
sudo systemctl status home-iot
```

**Expected status:** `active (running)` in green

### Verify Application is Running

```bash
# Check logs
sudo journalctl -u home-iot -n 30 --no-pager

# Look for:
# - "Environment variables loaded successfully ✅"
# - "Database initialized successfully"
# - "Running on http://127.0.0.1:5000"
# - "Running on http://127.0.0.1:5001"

# Check ports
netstat -tln | grep -E ':(5000|5001)'
# Should show LISTEN on both ports
```

---

## Step 5: Nginx Configuration

### Create Nginx Configuration

```bash
sudo tee /etc/nginx/sites-available/home-iot > /dev/null <<'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN.com;
    
    # Real IP for Flask (behind proxy)
    real_ip_header X-Real-IP;
    set_real_ip_from 127.0.0.1;

    # ESP32 API (port 5000)
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for IoT devices
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        client_max_body_size 1M;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;  # Don't log health checks
    }

    # Admin Panel (port 5001)
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Longer timeouts for admin panel
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        client_max_body_size 10M;
    }
    
    # Logs
    access_log /var/log/nginx/home-iot.access.log;
    error_log /var/log/nginx/home-iot.error.log;
}
EOF
```

**⚠️ IMPORTANT:** Replace `YOUR_DOMAIN.com` with your actual domain:

```bash
# Edit the file
sudo nano /etc/nginx/sites-available/home-iot

# Or use sed
sudo sed -i 's/YOUR_DOMAIN.com/app.example.com/g' /etc/nginx/sites-available/home-iot
```

### Enable Nginx Site

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Enable home-iot site
sudo ln -s /etc/nginx/sites-available/home-iot \
           /etc/nginx/sites-enabled/home-iot

# Test nginx configuration
sudo nginx -t
# Should show: "syntax is ok" and "test is successful"

# Reload nginx
sudo systemctl reload nginx
```

### Verify HTTP Access

```bash
# Test from server (should return 200 or 302)
curl -I http://localhost/health

# Test from your computer
curl http://YOUR_DOMAIN.com/health
```

---

## Step 6: SSL/TLS Configuration (Let's Encrypt)

### Obtain SSL Certificate

```bash
# Run Certbot for nginx
sudo certbot --nginx \
    -d YOUR_DOMAIN.com \
    --non-interactive \
    --agree-tos \
    --email your-email@example.com \
    --redirect

# This will:
# 1. Verify domain ownership (DNS must be pointing to your server!)
# 2. Obtain SSL certificate
# 3. Automatically configure nginx for HTTPS
# 4. Setup HTTP→HTTPS redirect
```

**Expected output:**
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/YOUR_DOMAIN.com/fullchain.pem
Key is saved at: /etc/letsencrypt/live/YOUR_DOMAIN.com/privkey.pem
```

### Verify SSL Certificate

```bash
# Check certificate
sudo certbot certificates

# Test HTTPS
curl https://YOUR_DOMAIN.com/health

# Test auto-renewal
sudo certbot renew --dry-run
```

### SSL Auto-Renewal

Certbot automatically sets up a systemd timer for renewal:

```bash
# Check renewal timer status
sudo systemctl status certbot.timer

# Manual renewal (if needed)
sudo certbot renew

# View renewal logs
sudo journalctl -u certbot.timer
```

---

## Step 7: Firewall Configuration

### Setup UFW Firewall

```bash
# Install UFW (if not installed)
sudo apt install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: Do this BEFORE enabling!)
sudo ufw allow ssh
# or specific port: sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Verify rules
sudo ufw status verbose
```

**Expected output:**
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

## Step 8: Cron Jobs (Automated Maintenance)

### Setup Database Cleanup

```bash
# Edit crontab
crontab -e

# Add these lines:
# Database cleanup - daily at 03:00
0 3 * * * /opt/home-iot/db_cleanup.sh >> /opt/home-iot/cleanup.log 2>&1

# Log cleanup - daily at 02:00
0 2 * * * /opt/home-iot/cleanup_logs.sh >> /opt/home-iot/cleanup.log 2>&1
```

### Verify Cron Jobs

```bash
# List cron jobs
crontab -l

# Test scripts manually
cd /opt/home-iot
./db_cleanup.sh
./cleanup_logs.sh

# Check logs
tail -20 cleanup.log
```

**→ Backup strategies:** [guides/BACKUP-RESTORE.md](guides/BACKUP-RESTORE.md)

---

## Step 9: Verification & Testing

### Complete System Test

```bash
# 1. Health Check (should return JSON)
curl -s https://YOUR_DOMAIN.com/health | jq

# Expected: {"status": "healthy", "database": "connected", ...}

# 2. Admin Panel (should return 200)
curl -I https://YOUR_DOMAIN.com/login

# 3. API Endpoint (should return 401 without token - this is correct!)
curl -I https://YOUR_DOMAIN.com/api/water-events -X POST

# 4. Check systemd service
sudo systemctl status home-iot

# 5. Check nginx
sudo systemctl status nginx

# 6. Check logs
sudo journalctl -u home-iot -n 20 --no-pager
sudo tail -20 /var/log/nginx/home-iot.access.log
sudo tail -20 /var/log/nginx/home-iot.error.log

# 7. Check database
sqlite3 /opt/home-iot/water_events.db "SELECT COUNT(*) FROM water_events;"
```

### Test ESP32 API

```bash
# Replace YOUR_API_TOKEN with token from .env
curl -X POST https://YOUR_DOMAIN.com/api/water-events \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DOLEWKA",
    "timestamp": "2025-10-04T12:00:00",
    "unix_time": 1728043200,
    "event_type": "AUTO_PUMP",
    "volume_ml": 250,
    "water_status": "OK",
    "system_status": "OK"
  }'

# Expected: {"success": true, "event_id": 1, ...}
```

### Test Admin Panel (Browser)

1. Open: `https://YOUR_DOMAIN.com/login`
2. Enter admin password from `.env`
3. Navigate dashboard
4. Test device-specific admin panels
5. Run SQL queries
6. Export data

---

## Post-Deployment

### Security Checklist

- [ ] Strong, unique credentials generated
- [ ] `.env` file has 600 permissions
- [ ] Firewall (UFW) enabled
- [ ] SSL/TLS working (HTTPS)
- [ ] HTTP redirects to HTTPS
- [ ] Only necessary ports open (22, 80, 443)
- [ ] SSH key authentication enabled (disable password login)
- [ ] Regular backups scheduled
- [ ] Monitoring configured

### Monitoring Setup

```bash
# Monitor application logs
sudo journalctl -u home-iot -f

# Monitor nginx logs
sudo tail -f /var/log/nginx/home-iot.access.log

# Check disk space regularly
df -h

# Monitor database size
ls -lh /opt/home-iot/water_events.db
```

### Regular Maintenance Tasks

**Daily (automated via cron):**
- Database cleanup (old records)
- Log rotation

**Weekly:**
- Check application logs for errors
- Review failed login attempts
- Monitor disk space

**Monthly:**
- Rotate credentials (recommended)
- Review and update dependencies
- Check for security updates
- Test backup restoration

**→ Credential rotation:** [guides/CREDENTIALS.md](guides/CREDENTIALS.md#rotation)

---

## Updating the Application

### Standard Update Process

```bash
# 1. Stop service
sudo systemctl stop home-iot

# 2. Backup database
cd /opt/home-iot
cp water_events.db water_events.db.backup.$(date +%Y%m%d)

# 3. Pull updates
git pull origin main

# 4. Update dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# 5. Restart service
sudo systemctl start home-iot

# 6. Verify
sudo systemctl status home-iot
curl -s https://YOUR_DOMAIN.com/health | jq
```

### Rollback Procedure

```bash
# If update fails:

# 1. Stop service
sudo systemctl stop home-iot

# 2. Restore previous version
git log --oneline  # Find previous commit
git reset --hard PREVIOUS_COMMIT_HASH

# 3. Restore database (if needed)
cp water_events.db.backup.YYYYMMDD water_events.db

# 4. Restart
sudo systemctl start home-iot
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u home-iot -n 50 --no-pager

# Common issues:
# 1. Missing .env file
ls -la /opt/home-iot/.env

# 2. Wrong permissions
sudo chown -R $USER:$USER /opt/home-iot
chmod 600 /opt/home-iot/.env

# 3. Port already in use
netstat -tln | grep -E ':(5000|5001)'
# If ports are occupied, kill process or change ports in .env

# 4. Database lock
rm /opt/home-iot/water_events.db-journal
```

### Nginx 502 Bad Gateway

```bash
# Check if Flask apps are running
netstat -tln | grep -E ':(5000|5001)'

# Check Flask logs
sudo journalctl -u home-iot -n 20 --no-pager

# Restart Flask service
sudo systemctl restart home-iot

# Check nginx error logs
sudo tail -20 /var/log/nginx/home-iot.error.log
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --force-renewal

# Check nginx SSL configuration
sudo nginx -t
```

### Database Issues

```bash
# Check database integrity
sqlite3 /opt/home-iot/water_events.db "PRAGMA integrity_check;"

# Vacuum database (optimize)
sqlite3 /opt/home-iot/water_events.db "VACUUM;"

# Check database size
ls -lh /opt/home-iot/water_events.db
```

**→ More solutions:** [troubleshooting/COMMON-ISSUES.md](troubleshooting/COMMON-ISSUES.md)

---

## Performance Optimization

### Enable Nginx Caching

```bash
# Add to nginx config (inside server block)
sudo nano /etc/nginx/sites-available/home-iot
```

Add before location blocks:
```nginx
# Cache static content
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1M;
    add_header Cache-Control "public, immutable";
}

# Gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
```

### Database Optimization

```bash
# Run ANALYZE to update statistics
sqlite3 /opt/home-iot/water_events.db "ANALYZE;"

# Check query performance
sqlite3 /opt/home-iot/water_events.db "EXPLAIN QUERY PLAN SELECT * FROM water_events WHERE device_id = 'DOLEWKA';"
```

---

## Next Steps

### Configure ESP32 Devices
- Update ESP32 firmware with production domain
- Configure API endpoint: `https://YOUR_DOMAIN.com/api/water-events`
- Add API token from `.env`

**→ Hardware guide:** [guides/ESP32-SETUP.md](guides/ESP32-SETUP.md)

### Add More Device Types
- Configure new device types in `device_config.py`
- Add device-specific queries

**→ Multi-device guide:** [guides/MULTI-DEVICE.md](guides/MULTI-DEVICE.md)

### Setup Monitoring
- Configure uptime monitoring (UptimeRobot, etc.)
- Setup log analysis tools
- Configure alerting for errors

### Backup Strategy
- Automated database backups
- Offsite backup storage
- Backup testing and restoration

**→ Backup guide:** [guides/BACKUP-RESTORE.md](guides/BACKUP-RESTORE.md)

---

## Related Documentation

- 🔑 [Credentials Management](guides/CREDENTIALS.md)
- 📱 [Multi-Device Setup](guides/MULTI-DEVICE.md)
- 💾 [Backup & Restore](guides/BACKUP-RESTORE.md)
- 🔒 [Security Architecture](architecture/SECURITY.md)
- 🗄️ [Database Schema](architecture/DATABASE.md)
- ❓ [FAQ](troubleshooting/FAQ.md)

---

**Deployment complete! Your Home IoT Platform is now running in production.** 🎉