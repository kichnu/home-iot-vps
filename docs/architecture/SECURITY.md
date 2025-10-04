# Security Architecture

Security model and best practices for Home IoT Platform.

## Security Layers

```
┌─────────────────────────────────────┐
│  Internet                           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Layer 1: Network Security          │
│  - Firewall (UFW)                   │
│  - Only ports 22, 80, 443 open      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Layer 2: Transport Security        │
│  - TLS/SSL (Let's Encrypt)          │
│  - HTTPS only, HTTP redirects       │
│  - HSTS headers                     │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Layer 3: Application Security      │
│  - Bearer token auth (API)          │
│  - Session-based auth (Admin)       │
│  - Input validation                 │
│  - SQL injection prevention         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Layer 4: Data Security             │
│  - Encrypted credentials (.env)     │
│  - Secure file permissions (600)    │
│  - Database integrity checks        │
└─────────────────────────────────────┘
```

## Authentication

### API Authentication (ESP32 Devices)

**Method:** Bearer Token

```
Authorization: Bearer <64-character-hex-token>
```

**Token Properties:**
- Length: 64 characters (256 bits entropy)
- Format: Hexadecimal
- Storage: `.env` file (600 permissions)
- Rotation: Recommended every 90 days

**Implementation:**
```python
@require_auth
def receive_water_event():
    # Validates Authorization header
    # Checks token against VALID_TOKEN from .env
    # Returns 401 if invalid
```

**Security Features:**
- ✅ No session management required
- ✅ Stateless authentication
- ✅ Token transmitted over HTTPS only
- ⚠️ Single shared token (per-device tokens recommended for production)

---

### Admin Panel Authentication

**Method:** Session-based with password

**Flow:**
1. User enters password (from `.env`)
2. Server validates against `ADMIN_PASSWORD`
3. Creates session with `secrets.token_urlsafe(32)`
4. Session stored in-memory with metadata
5. Session cookie sent to browser
6. Subsequent requests validated via session cookie

**Session Properties:**
- Session ID: 32 bytes urlsafe random
- Timeout: 30 minutes (configurable)
- Storage: In-memory dictionary (production: use Redis)
- IP tracking: Session tied to IP address

**Security Features:**
- ✅ Automatic session expiration
- ✅ Account lockout after failed attempts
- ✅ Session activity tracking
- ✅ IP-based session validation
- ✅ Secure session cookies (HttpOnly)

**Protection Mechanisms:**

```python
# Failed login tracking
MAX_FAILED_ATTEMPTS = 8  # Default
LOCKOUT_DURATION_HOURS = 1  # Default

# Brute force protection
failed_attempts[client_ip] = {
    'count': 0,
    'last_attempt': timestamp
}

# Account lockout
if failed_attempts >= MAX_FAILED_ATTEMPTS:
    locked_accounts[client_ip] = lock_time
```

## Input Validation

### API Request Validation

All API requests go through `validate_event_data()`:

```python
def validate_event_data(data):
    # 1. Required fields check
    required = ['device_id', 'timestamp', 'unix_time', 
                'event_type', 'volume_ml', 'water_status', 
                'system_status']
    
    # 2. Type validation
    unix_time = int(data['unix_time'])
    volume_ml = int(data['volume_ml'])
    
    # 3. Whitelist validation
    if device_id not in VALID_DEVICE_IDS:
        return False
    
    if event_type not in VALID_EVENT_TYPES:
        return False
    
    if water_status not in VALID_WATER_STATUSES:
        return False
    
    # 4. Range validation
    if volume_ml < 0 or volume_ml > 10000:
        return False
    
    return True
```

**Protection against:**
- ✅ Missing required fields
- ✅ Invalid data types
- ✅ Unknown device IDs
- ✅ Invalid event types
- ✅ Out-of-range values

---

### SQL Injection Prevention

Admin SQL queries validated through `validate_sql_query()`:

```python
def validate_sql_query(query):
    # 1. Remove comments
    query = re.sub(r'--.*$', '', query)
    
    # 2. Must start with SELECT
    if not query.startswith('SELECT'):
        return False
    
    # 3. Block dangerous keywords
    blocked = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 
               'CREATE', 'ALTER', 'EXEC']
    
    # 4. Only allow water_events table
    if 'WATER_EVENTS' not in query:
        return False
    
    return True
```

**Protection against:**
- ✅ SQL injection attacks
- ✅ Data modification attempts
- ✅ Schema changes
- ✅ Unauthorized table access

---

## Authorization

### Role-Based Access

**Roles:**
1. **ESP32 Device** - API write access only
   - Can: POST events
   - Cannot: Read data, access admin

2. **Admin User** - Full access
   - Can: View data, run queries, export
   - Cannot: Modify database directly

3. **Anonymous** - Health check only
   - Can: GET /health
   - Cannot: Anything else

### Endpoint Protection

```python
# Public (no auth)
/health

# API auth required (Bearer token)
/api/water-events  (POST)
/api/events        (GET)
/api/stats         (GET)

# Admin auth required (session)
/login             (GET)
/admin             (GET)
/api/admin-query   (POST)
/api/admin-export  (GET)
```

## Network Security

### Firewall Configuration (UFW)

```bash
# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allowed services
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirects to HTTPS)
ufw allow 443/tcp   # HTTPS
```

**Best practices:**
- Change default SSH port (optional but recommended)
- Use SSH key authentication (disable password)
- Consider fail2ban for brute force protection
- Restrict SSH to specific IPs if possible

---

### Nginx Security Headers

```nginx
# Security headers automatically added
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;

# HSTS (enforces HTTPS for 1 year)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

## Data Protection

### Credential Storage

**.env File Security:**
```bash
# Permissions: 600 (owner read/write only)
-rw------- 1 kichnu kichnu 854 .env

# Never commit to git
echo ".env" >> .gitignore

# Template file is safe
-rw-r--r-- 1 kichnu kichnu 1270 .env.example
```

**What's in .env:**
- Admin password (bcrypt hash recommended for future)
- API token (64-char hex)
- Flask secret key (64-char hex)
- Database paths
- Configuration settings

**Protection:**
- ✅ File permissions (600)
- ✅ .gitignore entry
- ✅ Loaded only by application
- ✅ Not visible in process list
- ⚠️ Currently plaintext (encryption planned)

---

### Database Security

**SQLite Security:**
```bash
# File permissions
-rw-r--r-- 1 kichnu kichnu water_events.db

# Should be:
chmod 640 water_events.db  # Owner RW, group R
```

**Query Security:**
- Parameterized queries (prevents SQL injection)
- Read-only queries in admin panel
- Timeout limits (10 seconds)
- Result limits (max 1000 rows)

**Backup Encryption:**
```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup.tar.gz

# Decrypt
gpg --decrypt backup.tar.gz.gpg > backup.tar.gz
```

## Transport Security

### TLS/SSL Configuration

**Let's Encrypt Certificates:**
- Auto-renewal every 60 days
- RSA 2048-bit keys (or better)
- TLS 1.2+ only
- Strong cipher suites

**Nginx SSL Configuration:**
```nginx
ssl_certificate /etc/letsencrypt/live/domain/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

**Verify SSL:**
```bash
# Check certificate
openssl s_client -connect your-domain.com:443

# Test with SSL Labs
# https://www.ssllabs.com/ssltest/
```

## Session Security

### Session Management

**Session Structure:**
```python
active_sessions[session_id] = {
    'client_ip': '192.168.1.100',
    'created_at': 1728043200,
    'last_activity': 1728045000
}
```

**Security Features:**
- 30-minute timeout (configurable)
- IP binding (optional, can cause issues with proxies)
- Automatic cleanup of expired sessions
- Session ID: 32 bytes cryptographically secure random

**Session Expiration:**
```python
SESSION_TIMEOUT_MINUTES = 30

# Auto-cleanup on validation
if now - last_activity > SESSION_TIMEOUT_MINUTES * 60:
    destroy_session()
```

---

### Cookie Security

**Flask Session Cookie:**
```python
app.secret_key = secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(minutes=30)

session['session_id'] = token_urlsafe(32)
session['authenticated'] = True
```

**Cookie attributes:**
- HttpOnly: Yes (prevents XSS access)
- Secure: Yes (HTTPS only) - enforced by nginx
- SameSite: Lax (CSRF protection)

## Account Protection

### Brute Force Protection

**Failed Login Tracking:**
```python
MAX_FAILED_ATTEMPTS = 8
LOCKOUT_DURATION_HOURS = 1

failed_attempts[ip] = {
    'count': 5,
    'last_attempt': timestamp
}

# After 8 failed attempts:
locked_accounts[ip] = lockout_timestamp
```

**Lockout Response:**
- HTTP 429 Too Many Requests
- 1-hour ban from login attempts
- Logged for security monitoring
- Admin notified (future feature)

**Best practices:**
- Use strong passwords (40+ chars)
- Rotate credentials regularly (90 days)
- Monitor failed login attempts
- Consider 2FA for future versions

## Logging & Monitoring

### Security Event Logging

**Logged Events:**
```python
# Failed authentication
logging.warning(f"Invalid token from {client_ip}")

# Account lockout
logging.warning(f"Account locked for IP {client_ip}")

# Successful login
logging.info(f"Successful admin login from {client_ip}")

# Session activity
logging.info(f"Session created for IP: {client_ip}")
```

**Log Locations:**
- Application: `/opt/home-iot/app.log`
- Systemd: `journalctl -u home-iot`
- Nginx access: `/var/log/nginx/home-iot.access.log`
- Nginx errors: `/var/log/nginx/home-iot.error.log`

**Monitoring Commands:**
```bash
# Watch failed logins
sudo journalctl -u home-iot -f | grep -i "failed\|invalid"

# Check lockouts
sudo journalctl -u home-iot | grep "locked"

# Monitor nginx 401/403
tail -f /var/log/nginx/home-iot.access.log | grep " 40[13] "
```

## Security Checklist

### Deployment Security

- [ ] Strong credentials generated (40+ chars)
- [ ] `.env` file permissions = 600
- [ ] Firewall enabled (UFW)
- [ ] SSL/TLS configured (Let's Encrypt)
- [ ] HTTP→HTTPS redirect working
- [ ] Security headers configured (nginx)
- [ ] Default ports changed (optional: SSH)
- [ ] SSH key authentication enabled
- [ ] Regular backups configured
- [ ] Monitoring/alerting setup

### Operational Security

- [ ] Credentials rotated every 90 days
- [ ] Failed login attempts monitored
- [ ] Database backups encrypted
- [ ] Logs reviewed weekly
- [ ] Software updates applied monthly
- [ ] Access logs audited
- [ ] Incident response plan documented

### Code Security

- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] No credentials in code
- [ ] No credentials in git history
- [ ] Environment variables only
- [ ] Parameterized SQL queries
- [ ] Output encoding (XSS prevention)

## Vulnerability Disclosure

### Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Contact:**
- Email: security@your-domain.com
- PGP Key: [key fingerprint]
- Response time: 48 hours

**What to include:**
- Detailed vulnerability description
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Security Update Process

1. Vulnerability reported
2. Issue verified and assessed
3. Patch developed and tested
4. Security advisory published
5. Users notified via:
   - GitHub Security Advisory
   - Email notification
   - Release notes

## Compliance

### Data Protection

**GDPR Considerations:**
- Minimal data collection (device IDs, timestamps)
- IP addresses logged (can be disabled)
- Right to deletion (manual database cleanup)
- Data retention configurable (default 90 days)

**PCI DSS:**
- Not applicable (no payment card data)

**HIPAA:**
- Not applicable (no health data)
- If monitoring health devices: additional measures required

## Future Security Enhancements

### Planned Features

1. **Per-Device API Tokens**
   - Individual tokens per ESP32
   - Token revocation capability
   - Token usage tracking

2. **Two-Factor Authentication (2FA)**
   - TOTP support for admin panel
   - Backup codes
   - Recovery mechanisms

3. **Rate Limiting**
   - Per-device rate limits
   - IP-based rate limiting
   - Adaptive throttling

4. **Enhanced Monitoring**
   - Real-time anomaly detection
   - Automated alerting
   - Security dashboard

5. **Credential Encryption**
   - Encrypted .env storage
   - Hardware security module support
   - Secrets management integration

## Best Practices

### For Developers

1. **Never commit credentials**
2. **Use parameterized queries**
3. **Validate all inputs**
4. **Log security events**
5. **Keep dependencies updated**

### For Administrators

1. **Rotate credentials regularly**
2. **Monitor logs daily**
3. **Keep system patched**
4. **Use strong passwords**
5. **Enable firewall**
6. **Backup regularly**
7. **Test restore procedures**

### For ESP32 Developers

1. **Store tokens securely on device**
2. **Use HTTPS only**
3. **Implement retry logic**
4. **Handle token expiration**
5. **Don't log tokens**

## Related Documentation

- [Credentials Guide](../guides/CREDENTIALS.md) - Credential management
- [Deployment Guide](../DEPLOY.md) - Production setup
- [API Reference](API.md) - Authentication details

---

**Security Contact:** security@your-domain.com  
**Last Security Audit:** 2025-10-04  
**Next Scheduled Review:** 2026-01-04