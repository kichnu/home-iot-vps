# Quick Start Guide - Development Setup

Get Home IoT Platform running on your local machine in **5 minutes**.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8 or higher** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Terminal/Command Line** access
- **Text Editor** (VS Code, Sublime, vim, etc.)

---

## Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/home-iot.git

# Navigate to project directory
cd home-iot

# Check Python version (should be 3.8+)
python3 --version
```

**Expected output:** `Python 3.8.x` or higher

---

## Step 2: Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Verify activation (prompt should show (venv))
which python  # Should point to venv/bin/python
```

**Expected output:** Your terminal prompt should now show `(venv)` prefix

---

## Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Verify installation
python -c "import flask; print(f'Flask {flask.__version__} installed')"
```

**Expected output:** `Flask 3.0.x installed`

---

## Step 4: Generate Credentials

**⚠️ IMPORTANT:** Never use default passwords in production!

```bash
# Generate secure credentials for development
python generate_credentials.py --output env

# This creates a .env file with:
# - Admin panel password
# - API token for ESP32 devices
# - Flask secret key
```

**Expected output:**
```
🔐 Water System Logger - Generator Credentials
==================================================

📋 Generated Credentials:
Admin Password:  [32-character password]
API Token:       [64-character token]
Secret Key:      [64-character key]

✅ .env file created with credentials
   Permissions: 600 (secure)
```

**View your credentials:**
```bash
# Show admin password (you'll need this to login)
grep ADMIN_PASSWORD .env
```

---

## Step 5: Run Application

```bash
# Start the development server
python app.py
```

**Expected output:**
```
📄 Loaded environment variables from /path/to/.env
=== WATER SYSTEM CONFIGURATION ===
Database path: /path/to/water_events.db
HTTP port: 5000
Admin port: 5001
Environment variables loaded successfully ✅

 * Running on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5001
```

**Application is now running!**

---

## Step 6: Access Application

### Admin Panel
1. Open browser: **http://localhost:5001/login**
2. Enter password from `.env` file (see Step 4)
3. Click Login

**You should see:** Multi-device dashboard with available device types

### API Endpoint
- **ESP32 API:** http://localhost:5000/api/
- **Health Check:** http://localhost:5000/health

**Test health endpoint:**
```bash
curl http://localhost:5000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "active_sessions": 0
}
```

---

## Step 7: Test API (Optional)

Test the API endpoint with a sample event:

```bash
# Get your API token from .env
API_TOKEN=$(grep WATER_SYSTEM_API_TOKEN .env | cut -d'=' -f2)

# Send test event
curl -X POST http://localhost:5000/api/water-events \
  -H "Authorization: Bearer $API_TOKEN" \
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
```

**Expected response:**
```json
{
  "success": true,
  "event_id": 1,
  "message": "Event recorded successfully"
}
```

**View the event in admin panel:**
1. Go to http://localhost:5001
2. Click "Water Management" device
3. Click "Last 100 Events" - you should see your test event

---

## 🎉 Success!

Your Home IoT Platform is now running locally!

### What's Next?

#### Explore the Admin Panel
- 📊 **Dashboard** - View all device types
- 🐠 **Water System** - Example device with test data
- 💻 **SQL Query Interface** - Run custom queries
- 📈 **Quick Queries** - Pre-built data analysis

#### Add Your ESP32 Device
1. Configure ESP32 with your WiFi credentials
2. Set API endpoint: `http://YOUR_LOCAL_IP:5000/api/water-events`
3. Add API token from `.env` file
4. Send test events

**→ Hardware setup guide:** [ESP32-SETUP.md](guides/ESP32-SETUP.md)

#### Deploy to Production
Ready to deploy to a VPS?

**→ Production deployment:** [DEPLOY.md](DEPLOY.md)

---

## 📁 Project Structure

Understanding the key files:

```
home-iot/
├── .env                        # Your credentials (DO NOT COMMIT!)
├── app.py                      # Main Flask application
├── device_config.py            # Device type definitions
├── queries_config.py           # SQL queries configuration
├── water_events.db            # SQLite database (auto-created)
├── app.log                    # Application logs (auto-created)
├── requirements.txt           # Python dependencies
├── templates/
│   ├── admin.html            # Device admin interface
│   ├── dashboard.html        # Multi-device dashboard
│   └── login.html            # Login page
└── docs/                      # Documentation
```

---

## 🔧 Development Configuration

### Environment Variables

The `.env` file controls application behavior:

```bash
# Required
WATER_SYSTEM_ADMIN_PASSWORD=your_password
WATER_SYSTEM_API_TOKEN=your_token
WATER_SYSTEM_SECRET_KEY=your_secret

# Optional (with defaults)
WATER_SYSTEM_DEVICE_IDS=DOLEWKA,ESP32_DEVICE_002
WATER_SYSTEM_SESSION_TIMEOUT=30
WATER_SYSTEM_LOG_LEVEL=INFO
WATER_SYSTEM_HTTP_PORT=5000
WATER_SYSTEM_ADMIN_PORT=5001
```

**Customize:** Edit `.env` and restart `python app.py`

### Adding New Device Types

1. Edit `device_config.py`:
```python
DEVICE_TYPE_MAPPING = {
    'YOUR_DEVICE_ID': 'your_device_type',
}

DEVICE_TYPES = {
    'your_device_type': {
        'name': 'Your Device Name',
        'icon': '🔧',
        'color': '#ff5733',
        # ... other config
    }
}
```

2. Edit `queries_config.py` to add device-specific queries

3. Restart application

**→ Detailed guide:** [MULTI-DEVICE.md](guides/MULTI-DEVICE.md)

---

## 🔍 Troubleshooting

### Application won't start

**Error:** `No module named 'flask'`
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Error:** `Missing environment variables`
```bash
# Generate credentials
python generate_credentials.py --output env

# Verify .env file exists
ls -la .env
```

### Can't access admin panel

**Check ports:**
```bash
# Verify applications are running on correct ports
netstat -tln | grep '5000\|5001'
```

**Reset password:**
```bash
# Generate new credentials
python generate_credentials.py --output env --password-length 32
# Restart application
```

### Database errors

**Reset database:**
```bash
# Stop application (Ctrl+C)
# Remove database
rm water_events.db
# Restart application (will recreate)
python app.py
```

### More issues?

**→ See:** [Troubleshooting Guide](troubleshooting/COMMON-ISSUES.md)

---

## 📊 Development Tips

### View Logs

```bash
# Application logs
tail -f app.log

# Or use journalctl if running as systemd service
journalctl -u home-iot -f
```

### Database Inspection

```bash
# Open SQLite database
sqlite3 water_events.db

# View tables
.tables

# View recent events
SELECT * FROM water_events ORDER BY received_at DESC LIMIT 10;

# Exit
.quit
```

### Test API Without ESP32

Use curl or Postman to test API endpoints:

```bash
# Health check
curl http://localhost:5000/health

# Get events
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/events?limit=10

# Send test event
curl -X POST http://localhost:5000/api/water-events \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d @test_event.json
```

---

## 🚀 Next Steps

### For Developers
- [ ] Explore code structure
- [ ] Add custom device types
- [ ] Customize admin panel queries
- [ ] Implement new features

### For Production Use
- [ ] Deploy to VPS → [DEPLOY.md](DEPLOY.md)
- [ ] Setup SSL/TLS certificates
- [ ] Configure automatic backups
- [ ] Setup monitoring and alerts

### For Hardware Integration
- [ ] Setup ESP32 development environment
- [ ] Flash example code to ESP32
- [ ] Configure WiFi and API credentials
- [ ] Test device-to-server communication

---

## 📚 Related Documentation

- 📦 [Production Deployment](DEPLOY.md) - VPS setup guide
- 🔑 [Credentials Management](guides/CREDENTIALS.md) - Security best practices
- 📱 [Multi-Device Setup](guides/MULTI-DEVICE.md) - Adding device types
- 🔌 [ESP32 Hardware Setup](guides/ESP32-SETUP.md) - Hardware configuration
- 🔒 [Security Model](architecture/SECURITY.md) - Authentication details
- 🗄️ [Database Schema](architecture/DATABASE.md) - Database structure

---

## 💡 Pro Tips

1. **Keep credentials secure:** Never commit `.env` to git (already in `.gitignore`)
2. **Use strong tokens:** In production, use 64+ character tokens
3. **Enable HTTPS:** Even in development, consider using SSL for testing
4. **Monitor logs:** Watch `app.log` for errors and debugging
5. **Backup database:** Regularly backup `water_events.db` during development

---

**Need help?** Check our [FAQ](troubleshooting/FAQ.md) or open an issue on GitHub!