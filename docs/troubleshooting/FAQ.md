# Frequently Asked Questions (FAQ)

Common questions about Home IoT Platform.

## General Questions

### What is Home IoT Platform?

Home IoT Platform is a self-hosted Flask application that receives data from ESP32 IoT devices, stores it in SQLite, and provides a web-based admin interface for data visualization and analysis.

Originally built for aquarium water management, it now supports multiple device types including temperature sensors, security systems, and custom devices.

---

### Do I need a server to run this?

**For testing/development:** No - runs on your local computer  
**For production IoT:** Yes - requires a VPS with public IP and domain

Minimum VPS specs:
- 512MB RAM (1GB recommended)
- 10GB disk space
- Ubuntu 20.04+ or Debian 11+

---

### How much does it cost to run?

**Software:** Free (MIT License, open source)

**Infrastructure costs:**
- VPS: $5-10/month (DigitalOcean, Vultr, Linode)
- Domain: $10-15/year
- SSL Certificate: Free (Let's Encrypt)

**Total:** ~$60-120/year

---

### Can I use it offline/locally?

Yes! The system works perfectly on a local network:
- Run on Raspberry Pi or local computer
- ESP32 devices connect to local IP
- No internet required for operation
- However, no remote access unless you setup port forwarding/VPN

---

## Technical Questions

### What database does it use?

SQLite - a file-based database that's:
- ✅ Zero-configuration
- ✅ Lightweight
- ✅ No separate database server needed
- ✅ Perfect for IoT workloads
- ✅ Easy to backup (single file)

For very large deployments (>1M events), consider PostgreSQL.

---

### How many devices can it handle?

**Tested:** Up to 10 devices sending data every 5 minutes  
**Theoretical:** 100+ devices

**Bottlenecks:**
1. SQLite write concurrency (~1000 writes/sec)
2. VPS resources
3. Network bandwidth

For high-volume deployments (>100 devices), consider:
- Load balancing
- PostgreSQL instead of SQLite
- Caching layer (Redis)

---

### What ESP32 boards are supported?

**Tested:**
- ESP32-C3
- ESP32-S2
- ESP32 (original)

**Requirements:**
- WiFi capability
- Arduino core support
- HTTPS/SSL support

Most ESP32 variants work out of the box.

---

### Can I use Arduino instead of ESP32?

Arduino boards (Uno, Mega, etc.) lack WiFi - you'd need:
- WiFi shield (ESP8266 module)
- More complex code
- More power consumption

**Recommendation:** Use ESP32 - it's cheaper, more powerful, and has built-in WiFi.

---

### Does it support MQTT?

Not currently. MQTT support is on the roadmap for v3.0.

**Current:** REST API (HTTP POST)  
**Planned:** MQTT, WebSocket, LoRaWAN

**Workaround:** Use MQTT bridge (external tool converts MQTT→HTTP)

---

## Setup Questions

### How long does installation take?

**Development (local):** 5-10 minutes  
**Production (VPS):** 30-45 minutes

**Breakdown:**
- VPS setup: 10 min
- Application install: 5 min
- Nginx config: 5 min
- SSL certificate: 5 min
- Testing: 10 min

---

### Do I need to know Python?

**For basic use:** No - just follow instructions  
**For customization:** Basic Python helps  
**For device types:** Yes - Python experience recommended

**You'll need:**
- Basic Linux command line
- Copy/paste commands
- Text editing skills

---

### Can I run it on Windows?

**Development:** Yes (with WSL or native Python)  
**Production:** Not recommended - Linux is better

**For Windows production:**
- Use Docker (future feature)
- Or use Linux VPS for production, Windows for development

---

### How do I get a domain name?

**Purchase from:**
- Namecheap (~$10/year)
- Google Domains
- GoDaddy

**Free alternatives:**
- FreeDNS (subdomains)
- DuckDNS (dynamic DNS)
- No-IP

**Setup:**
1. Buy domain
2. Add A record pointing to VPS IP
3. Wait for DNS propagation (5-60 min)
4. Use in deployment

---

## Security Questions

### Is it secure?

Yes, when properly configured:
- ✅ HTTPS/SSL encryption
- ✅ Token authentication for devices
- ✅ Session-based admin auth
- ✅ Input validation
- ✅ SQL injection prevention
- ✅ Account lockout protection

**Follow best practices:**
- Strong passwords (40+ chars)
- Regular credential rotation
- Keep software updated
- Monitor failed login attempts
- Regular backups

---

### Can ESP32 devices be hacked?

**Risks:**
- WiFi password sniffing (if not using WPA2)
- API token extraction from device
- Physical access to device

**Mitigation:**
- Use HTTPS (encrypted communication)
- Store tokens in secure storage (not hardcoded)
- Use WPA2/WPA3 WiFi
- Physical security for devices

---

### Do I need to open ports on my router?

**For VPS deployment:** No - server has public IP  
**For home server:** Yes - port forwarding required

**Typical setup:**
- Forward external port 443 → internal port 443
- Keep SSH (22) closed to public
- Use VPN for admin access (optional but recommended)

---

## Device Questions

### How do I add a new device type?

See [Multi-Device Guide](../guides/MULTI-DEVICE.md)

**Quick summary:**
1. Define device in `device_config.py`
2. Add queries in `queries_config.py`
3. Update database schema (if new columns)
4. Restart application
5. Configure ESP32 code

**Time:** 15-30 minutes

---

### Can I rename devices?

Currently device IDs are fixed in database.

**Workaround:**
- Device display names can be configured in `device_config.py`
- Database migration script needed to change IDs (manual)

**Future feature:** Device management interface

---

### What sensors can I use?

Any sensor compatible with ESP32:
- Water level sensors (float switches, ultrasonic)
- Temperature/humidity (DHT22, BME280, DS18B20)
- Motion sensors (PIR HC-SR501)
- Door sensors (magnetic reed switches)
- Soil moisture sensors
- Light sensors (LDR, TSL2561)
- Gas sensors (MQ series)
- Distance sensors (HC-SR04)
- And many more!

---

## Data Questions

### How long is data kept?

**Default:** 90 days (configurable)

**Change retention:**
Edit `db_cleanup.sh`:
```bash
RETENTION_DAYS=90  # Change to desired days
```

**No automatic cleanup:**
Comment out cron job or set very high number (999999)

---

### Can I export data?

**Yes! Multiple formats:**
- CSV export (Excel-compatible)
- JSON export (machine-readable)
- Direct SQL queries
- Custom queries via admin panel

**Export methods:**
1. Admin panel → Run query → Export button
2. API: GET /api/events?limit=1000
3. Direct SQLite access
4. Custom Python scripts

---

### Can I import old data?

**Yes:**

```bash
# From CSV
sqlite3 water_events.db << EOF
.mode csv
.import old_data.csv water_events
EOF

# From another database
sqlite3 water_events.db << EOF
ATTACH DATABASE 'old_database.db' AS old;
INSERT INTO water_events SELECT * FROM old.water_events;
EOF
```

---

### What happens if the server goes down?

**During downtime:**
- ESP32 devices fail to send data
- Data is lost (unless device has local storage)
- Admin panel inaccessible

**After recovery:**
- Service resumes normally
- Devices reconnect automatically
- Gap in data from downtime period

**Best practices:**
- Monitor server uptime
- Setup health check alerting
- Consider device-side buffering (advanced)
- Regular backups

---

## Performance Questions

### How much data can it store?

**Practical limits:**
- 1 million events: ~100MB database
- 10 million events: ~1GB database
- SQLite supports databases up to 281 TB

**Recommendations:**
- < 1M events: SQLite is perfect
- 1-10M events: SQLite works, optimize queries
- > 10M events: Consider PostgreSQL

---

### Why is my dashboard slow?

**Common causes:**
1. Large database (>1GB)
2. Complex queries
3. No indexes on custom columns
4. Low VPS resources

**Solutions:**
```bash
# 1. Clean old data
sqlite3 water_events.db "DELETE FROM water_events WHERE received_at < datetime('now', '-90 days'); VACUUM;"

# 2. Optimize database
sqlite3 water_events.db "ANALYZE;"

# 3. Add indexes (if needed)
sqlite3 water_events.db "CREATE INDEX idx_your_column ON water_events(your_column);"

# 4. Upgrade VPS
# More RAM/CPU helps
```

---

### Can I use it with Grafana?

**Not directly** - Grafana requires time-series database (InfluxDB, Prometheus)

**Options:**
1. **Export to Grafana:**
   - Use SQLite data source plugin (experimental)
   - Or export to InfluxDB periodically

2. **Alternative:** Built-in charts (future feature)

---

## Troubleshooting Questions

### "Module not found" error?

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep Flask
```

---

### "Permission denied" errors?

```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/home-iot

# Fix permissions
chmod 600 /opt/home-iot/.env
chmod 755 /opt/home-iot/*.sh
```

---

### "Database is locked" error?

```bash
# Stop service
sudo systemctl stop home-iot

# Remove lock
rm water_events.db-journal

# Start service
sudo systemctl start home-iot
```

---

### ESP32 shows "Connection failed"?

**Check:**
1. WiFi credentials correct?
2. Server accessible from device network?
3. HTTPS certificate valid?
4. API token correct?
5. Firewall allows HTTPS (port 443)?

**Test:**
```cpp
// Add debug output
Serial.println("Connecting to: " + String(serverUrl));
Serial.println("Token: " + String(apiToken).substring(0, 10) + "...");
```

---

## Feature Requests

### Can you add feature X?

**Check roadmap in README.md**

Planned features:
- WebSocket support
- MQTT protocol
- Grafana integration
- Mobile app
- Multi-user support
- Alerting/notifications

**Request a feature:**
- Open GitHub Issue
- Tag as "feature request"
- Describe use case

---

### Why not use existing solutions?

**Existing platforms:**
- ThingSpeak: Requires internet, limited free tier
- Blynk: Paid plans for serious use
- Home Assistant: Heavy, complex setup

**Home IoT Platform advantages:**
- ✅ Self-hosted (full control)
- ✅ Lightweight (runs on cheap VPS)
- ✅ Open source (modify as needed)
- ✅ Simple architecture (easy to understand)
- ✅ No cloud dependencies

---

## Community Questions

### How can I contribute?

**Ways to contribute:**
1. Report bugs (GitHub Issues)
2. Submit pull requests
3. Write documentation
4. Share device configurations
5. Help others in Discussions
6. Star the repository ⭐

**Contribution guide:**
See CONTRIBUTING.md (if exists) or open PR

---

### Where can I get help?

**Resources:**
1. 📖 [Documentation](../) - Comprehensive guides
2. 🔧 [Troubleshooting](COMMON-ISSUES.md) - Common problems
3. 🐛 [GitHub Issues](https://github.com/your-repo/issues) - Bug reports
4. 💬 [Discussions](https://github.com/your-repo/discussions) - Questions
5. 📧 Email: support@your-domain.com

**Before asking:**
- Check docs
- Search existing issues
- Try troubleshooting guide
- Collect debug information

---

### Is commercial use allowed?

**Yes!** MIT License permits:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

**Requirements:**
- Include original license
- Include copyright notice

**You can:**
- Use in your business
- Sell as a product
- Integrate into services
- Modify and rebrand

---

## Still Have Questions?

**Didn't find your answer?**

1. Check [Troubleshooting Guide](COMMON-ISSUES.md)
2. Search [GitHub Issues](https://github.com/your-repo/issues)
3. Ask in [Discussions](https://github.com/your-repo/discussions)
4. Email: support@your-domain.com

**When asking for help, include:**
- What you're trying to do
- What you've tried
- Error messages (full text)
- System info (OS, Python version)
- Relevant logs

**We're here to help!** 🚀
EOF
```

---

## 9. Examples Structure (Placeholders)

```bash
# Create examples directory structure
mkdir -p examples/esp32
mkdir -p examples/api
mkdir -p examples/queries

# Create placeholder README files
cat > examples/README.md << 'EOF'
# Examples

Code examples for Home IoT Platform.

## Directory Structure

```
examples/
├── esp32/           # ESP32 Arduino code
│   ├── README.md
│   └── [Device-specific examples]
├── api/             # API usage examples
│   ├── README.md
│   └── [Language-specific examples]
└── queries/         # SQL query examples
    ├── README.md
    └── [Use-case specific queries]
```

## ESP32 Examples

See [esp32/README.md](esp32/README.md) for complete Arduino examples for different device types.

**Available examples:**
- Water management system
- Temperature/humidity sensor
- Security/motion detector
- Custom device template

## API Examples

See [api/README.md](api/README.md) for API integration examples in different languages.

**Available examples:**
- Python (requests)
- cURL (command line)
- JavaScript (Node.js)
- Arduino (ESP32)

## SQL Query Examples

See [queries/README.md](queries/README.md) for useful SQL queries for data analysis.

**Example queries:**
- Daily/weekly statistics
- Anomaly detection
- Performance analysis
- Data export queries

---

**Contributing Examples:**

Have a useful example? Submit a PR!
1. Follow existing structure
2. Add comments explaining code
3. Include required libraries/dependencies
4. Test before submitting
EOF

cat > examples/esp32/README.md << 'EOF'
# ESP32 Arduino Examples

Complete Arduino code examples for different device types.

## Prerequisites

- Arduino IDE 1.8+ or PlatformIO
- ESP32 board support installed
- Required libraries (see each example)

## Available Examples

### 🐠 Water Management System
**File:** `water_system_example.ino` (TO BE ADDED)
- Auto-fill system with dual sensors
- Pump control
- Algorithm data tracking

### 🌡️ Temperature/Humidity Sensor
**File:** `temperature_sensor_example.ino` (TO BE ADDED)
- DHT22/BME280 sensor support
- Periodic readings
- Battery monitoring

### 🔒 Security/Motion Detector
**File:** `security_system_example.ino` (TO BE ADDED)
- PIR motion sensor
- Door/window sensors
- Zone monitoring

### 📱 Custom Device Template
**File:** `custom_device_template.ino` (TO BE ADDED)
- Basic structure for any sensor
- HTTP POST implementation
- Error handling

## Usage

1. Open example in Arduino IDE
2. Configure WiFi credentials
3. Set API endpoint and token
4. Upload to ESP32
5. Monitor Serial output

## See Also

- [ESP32 Setup Guide](../../docs/guides/ESP32-SETUP.md)
- [Multi-Device Guide](../../docs/guides/MULTI-DEVICE.md)

---

**📝 Note:** Example code will be added in future commits. See documentation for current code snippets.
EOF

cat > examples/api/README.md << 'EOF'
# API Usage Examples

Examples of integrating with Home IoT Platform API in different languages.

## Available Examples

### Python
**File:** `python_client.py` (TO BE ADDED)
- Using `requests` library
- Error handling
- Batch operations

### cURL
**File:** `curl_examples.sh` (TO BE ADDED)
- Command-line API testing
- Useful for debugging
- Shell script automation

### JavaScript/Node.js
**File:** `nodejs_client.js` (TO BE ADDED)
- Using `axios` library
- Async/await pattern
- Web application integration

### Arduino/ESP32
See [../esp32/](../esp32/) for ESP32-specific examples.

## API Reference

See [API Documentation](../../docs/architecture/API.md) for complete API reference.