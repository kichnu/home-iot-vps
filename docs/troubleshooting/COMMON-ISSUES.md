Troubleshooting guide for Home IoT Platform.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Service Issues](#service-issues)
- [Network Issues](#network-issues)
- [Database Issues](#database-issues)
- [Authentication Issues](#authentication-issues)
- [ESP32 Integration Issues](#esp32-integration-issues)
- [Performance Issues](#performance-issues)

---

## Installation Issues

### Python Version Too Old

**Symptom:**
```
ERROR: Package requires a different Python: 3.6.x not in '>=3.8'
```

**Solution:**
```bash
# Install Python 3.10
sudo apt install python3.10 python3.10-venv

# Use Python 3.10 explicitly
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### pip install fails

**Symptom:**
```
ERROR: Could not find a version that satisfies the requirement Flask==3.0.0
```

**Solution:**
```bash
# Upgrade pip
pip install --upgrade pip

# Install with --no-cache-dir
pip install --no-cache-dir -r requirements.txt

# If still fails, install individually
pip install Flask==3.0.0
pip install Werkzeug==3.0.1
```

---

### Missing Environment Variables

**Symptom:**
```
❌ BRAK WYMAGANYCH ZMIENNYCH ŚRODOWISKOWYCH:
WATER_SYSTEM_ADMIN_PASSWORD, WATER_SYSTEM_API_TOKEN
```

**Solution:**
```bash
# Generate credentials
python generate_credentials.py --output env

# Verify .env file exists
ls -la .env

# Check permissions (should be 600)
chmod 600 .env

# Verify content
cat .env | grep -E "ADMIN_PASSWORD|API_TOKEN"
```

---

## Service Issues

### Service won't start

**Symptom:**
```bash
sudo systemctl status home-iot
# Shows: failed (Result: exit-code)
```

**Diagnosis:**
```bash
# Check detailed logs
sudo journalctl -u home-iot -n 50 --no-pager

# Look for specific errors
sudo journalctl -u home-iot | grep -i error
```

**Common causes & solutions:**

#### 1. Missing .env file
```bash
ls -la /opt/home-iot/.env
# If missing:
cd /opt/home-iot
source venv/bin/activate
python generate_credentials.py --output env
```

#### 2. Wrong file permissions
```bash
# Fix ownership
sudo chown -R kichnu:kichnu /opt/home-iot

# Fix .env permissions
chmod 600 /opt/home-iot/.env
```

#### 3. Port already in use
```bash
# Check what's using ports
netstat -tln | grep -E ':(5000|5001)'

# If occupied, kill process or change ports in .env
kill <PID>
```

#### 4. Database locked
```bash
# Remove lock file
rm /opt/home-iot/water_events.db-journal

# If database corrupted:
sqlite3 /opt/home-iot/water_events.db "PRAGMA integrity_check;"
```

---

### Service starts but crashes

**Symptom:**
Service shows active briefly, then dies

**Diagnosis:**
```bash
# Watch logs in real-time
sudo journalctl -u home-iot -f

# Check for Python errors
sudo journalctl -u home-iot | grep "Traceback"
```

**Solutions:**
```bash
# Test manually to see full error
cd /opt/home-iot
source venv/bin/activate
python app.py
# Read error message

# Common fixes:
# - Reinstall dependencies: pip install -r requirements.txt
# - Check Python version: python --version
# - Verify imports: python -c "import flask; import sqlite3"
```

---

## Network Issues

### Can't access via domain

**Symptom:**
```
curl: (6) Could not resolve host: your-domain.com
```

**Check DNS:**
```bash
# Verify DNS resolution
nslookup your-domain.com

# Should return your VPS IP
# If not, check domain DNS settings
```

**Check nginx:**
```bash
# Verify nginx is running
sudo systemctl status nginx

# Test nginx config
sudo nginx -t

# Check nginx logs
sudo tail -20 /var/log/nginx/error.log
```

---

### 502 Bad Gateway

**Symptom:**
Browser shows "502 Bad Gateway" error

**Cause:**
Nginx can't connect to Flask backend

**Solutions:**
```bash
# 1. Check if Flask is running
netstat -tln | grep -E ':(5000|5001)'
# Should show LISTEN on both ports

# 2. If not running, start service
sudo systemctl start home-iot

# 3. Check Flask logs
sudo journalctl -u home-iot -n 20 --no-pager

# 4. Test localhost connection
curl http://localhost:5000/health
curl http://localhost:5001/login

# 5. Check nginx config
sudo cat /etc/nginx/sites-enabled/home-iot | grep proxy_pass
# Should be: http://127.0.0.1:5000 and http://127.0.0.1:5001

# 6. Restart both services
sudo systemctl restart home-iot
sudo systemctl restart nginx
```

---

### 504 Gateway Timeout

**Symptom:**
Request times out after 30-60 seconds

**Cause:**
Flask processing too slow or hung

**Solutions:**
```bash
# 1. Check Flask process
ps aux | grep python | grep app.py

# 2. Check database locks
sqlite3 /opt/home-iot/water_events.db \
    "SELECT * FROM sqlite_master LIMIT 1;"

# 3. Increase nginx timeout
sudo nano /etc/nginx/sites-available/home-iot

# Add/increase:
proxy_read_timeout 120s;
proxy_connect_timeout 120s;

# Reload nginx
sudo nginx -t && sudo systemctl reload nginx

# 4. Restart Flask if hung
sudo systemctl restart home-iot
```

---

### SSL Certificate Issues

**Symptom:**
```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

**Check certificate:**
```bash
# View certificate
sudo certbot certificates

# Check expiration
openssl s_client -connect your-domain.com:443 </dev/null 2>/dev/null | \
    openssl x509 -noout -dates

# Renew if expired
sudo certbot renew
sudo systemctl reload nginx
```

**Certificate won't renew:**
```bash
# Check renewal
sudo certbot renew --dry-run

# Common issue: DNS not pointing to server
nslookup your-domain.com  # Should return current IP

# Force renewal
sudo certbot renew --force-renewal

# If fails, delete and recreate
sudo certbot delete --cert-name your-domain.com
sudo certbot --nginx -d your-domain.com
```

---

## Database Issues

### Database corrupted

**Symptom:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Recovery:**
```bash
# 1. Stop service
sudo systemctl stop home-iot

# 2. Backup corrupted database
cp water_events.db water_events.db.corrupted

# 3. Try recovery
sqlite3 water_events.db ".recover" | sqlite3 recovered.db

# 4. If recovery works:
mv water_events.db water_events.db.old
mv recovered.db water_events.db

# 5. If recovery fails, restore from backup
cp /backup/water_events.db water_events.db

# 6. Restart
sudo systemctl start home-iot
```

---

### Database locked

**Symptom:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**
```bash
# 1. Check for other processes
ps aux | grep sqlite

# 2. Remove journal file (safe if no writes happening)
rm water_events.db-journal

# 3. If persistent, increase timeout in code
# Edit app.py, add to database connections:
conn.execute('PRAGMA busy_timeout = 30000')  # 30 seconds
```

---

### Database growing too large

**Symptom:**
Database file > 1GB

**Solutions:**
```bash
# 1. Check size
ls -lh water_events.db
du -h water_events.db

# 2. Check record count
sqlite3 water_events.db "SELECT COUNT(*) FROM water_events;"

# 3. Clean old data (keep last 90 days)
sqlite3 water_events.db << EOF
DELETE FROM water_events 
WHERE received_at < datetime('now', '-90 days');
VACUUM;
ANALYZE;
EOF

# 4. Verify size reduced
ls -lh water_events.db

# 5. Setup automatic cleanup (see db_cleanup.sh)
```

---

## Authentication Issues

### Can't login to admin panel

**Symptom:**
"Invalid password" error

**Solutions:**
```bash
# 1. Check password from .env
grep ADMIN_PASSWORD /opt/home-iot/.env

# 2. Verify .env is being loaded
sudo journalctl -u home-iot -n 20 | grep "Loaded environment"

# 3. Generate new password
cd /opt/home-iot
source venv/bin/activate
python generate_credentials.py --output env

# 4. Restart service
sudo systemctl restart home-iot

# 5. Check for account lockout
sudo journalctl -u home-iot | grep -i "locked"
# If locked, wait 1 hour or restart service
```

---

### Account locked out

**Symptom:**
"Account temporarily locked due to too many failed attempts"

**Solutions:**
```bash
# 1. Check lockout status
sudo journalctl -u home-iot | grep "locked" | tail -5

# 2. Wait for lockout to expire (default: 1 hour)

# 3. Or restart service to clear lockout
sudo systemctl restart home-iot

# 4. Prevent future lockouts:
# - Use correct password from .env
# - Don't let browser autofill wrong password
# - Consider increasing MAX_FAILED_ATTEMPTS in .env
```

---

### API authentication fails

**Symptom:**
ESP32 gets 401 Unauthorized

**Check token:**
```bash
# 1. Get token from .env
TOKEN=$(grep WATER_SYSTEM_API_TOKEN /opt/home-iot/.env | cut -d'=' -f2)
echo $TOKEN

# 2. Test with curl
curl -X POST https://your-domain.com/api/water-events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST",
    "timestamp": "2025-10-04T12:00:00",
    "unix_time": 1728043200,
    "event_type": "AUTO_PUMP",
    "volume_ml": 100,
    "water_status": "OK",
    "system_status": "OK"
  }'

# 3. If 401, check Flask logs
sudo journalctl -u home-iot | grep "Invalid token"

# 4. Regenerate token if needed
python generate_credentials.py --output env
sudo systemctl restart home-iot
```

---

## ESP32 Integration Issues

### ESP32 can't connect to WiFi

**ESP32 Code Debug:**
```cpp
void setup() {
    Serial.begin(115200);
    
    WiFi.begin(ssid, password);
    int attempts = 0;
    
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        Serial.printf(" [%d]\n", WiFi.status());
        attempts++;
    }
    
    if(WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi Connected");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi Failed");
        Serial.printf("Status: %d\n", WiFi.status());
    }
}
```

**WiFi Status Codes:**
- 0 = WL_IDLE_STATUS
- 3 = WL_CONNECTED
- 4 = WL_CONNECT_FAILED
- 6 = WL_DISCONNECTED

---

### ESP32 sends data but gets errors

**Check HTTP response:**
```cpp
int httpCode = http.POST(payload);
Serial.printf("HTTP Code: %d\n", httpCode);

if(httpCode > 0) {
    String response = http.getString();
    Serial.println("Response: " + response);
} else {
    Serial.printf("Error: %s\n", http.errorToString(httpCode).c_str());
}
```

**Common HTTP Codes:**
- 200: Success
- 400: Bad request (check JSON format)
- 401: Unauthorized (check token)
- 500: Server error (check Flask logs)

**Test server from ESP32:**
```cpp
// Test basic connectivity
HTTPClient http;
http.begin("https://your-domain.com/health");
int httpCode = http.GET();
Serial.printf("Health check: %d\n", httpCode);
```

---

## Performance Issues

### Admin panel slow

**Symptoms:**
- Queries take >10 seconds
- Dashboard slow to load

**Solutions:**
```bash
# 1. Check database size
ls -lh /opt/home-iot/water_events.db

# 2. Run ANALYZE
sqlite3 /opt/home-iot/water_events.db "ANALYZE;"

# 3. Check for slow queries in logs
sudo journalctl -u home-iot | grep "slow query"

# 4. Reduce data retention
# Edit db_cleanup.sh to keep fewer days

# 5. Add indexes if querying new columns
sqlite3 /opt/home-iot/water_events.db \
    "CREATE INDEX IF NOT EXISTS idx_custom ON water_events(your_column);"
```

---

### High memory usage

**Symptoms:**
```bash
free -h
# Shows low available memory
```

**Check Flask memory:**
```bash
ps aux | grep python | grep app.py
# Look at RSS column (memory usage)
```

**Solutions:**
```bash
# 1. Restart service
sudo systemctl restart home-iot

# 2. Check for memory leaks in logs
sudo journalctl -u home-iot | grep -i memory

# 3. Limit query result sizes (already limited to 1000)

# 4. Clean up old sessions
# (automatic in code, but restart helps)
```

---

## Getting More Help

### Collect Debug Information

When reporting issues, include:

```bash
# System info
lsb_release -a
free -h
df -h

# Service status
sudo systemctl status home-iot

# Recent logs
sudo journalctl -u home-iot -n 50 --no-pager

# Nginx logs
sudo tail -20 /var/log/nginx/home-iot.error.log

# Database info
ls -lh /opt/home-iot/water_events.db
sqlite3 /opt/home-iot/water_events.db "SELECT COUNT(*) FROM water_events;"

# Network
netstat -tln | grep -E ':(5000|5001|443)'
```

### Support Channels

- 📖 [FAQ](FAQ.md) - Frequently asked questions
- 🐛 [GitHub Issues](https://github.com/your-repo/issues) - Bug reports
- 💬 [Discussions](https://github.com/your-repo/discussions) - Questions
- 📧 Email: support@your-domain.com

---

**Pro tip:** Before asking for help, try turning it off and on again (seriously, `sudo systemctl restart home-iot` fixes many issues!)