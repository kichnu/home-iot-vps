# Home IoT Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

**Multi-device IoT data logging platform with real-time web dashboard and secure REST API**

Transform your ESP32 devices into a unified monitoring system. Log data from water sensors, temperature monitors, security systems, and custom IoT devices - all managed through a single web interface.

---

## 🎯 What is Home IoT Platform?

A production-ready Flask application that receives data from multiple IoT devices via REST API, stores it in SQLite, and provides a powerful admin dashboard for data analysis and visualization. Perfect for home automation, environmental monitoring, and custom IoT projects.

**Originally designed for aquarium water management** (`DOLEWKA` device), now evolved into a flexible multi-device platform supporting any IoT sensor type.

---

## ✨ Features

### Core Functionality
- 🔌 **Multi-Device Support** - Water systems, temperature sensors, security devices, and custom types
- 📊 **Real-Time Dashboard** - Device-specific admin panels with contextual queries
- 🔐 **Secure REST API** - Bearer token authentication for ESP32 devices
- 💾 **SQLite Database** - Automatic data retention and cleanup
- 📈 **Data Visualization** - Interactive charts and statistics
- 🔍 **SQL Query Interface** - Custom queries with export (CSV/JSON)

### Production Ready
- 🌐 **Nginx Integration** - Reverse proxy with SSL/TLS support
- ⚙️ **Systemd Service** - Automatic startup and monitoring
- 🔒 **Security Features** - Session management, rate limiting, account lockout
- 📝 **Automatic Logging** - Application and nginx logs with rotation
- 🗄️ **Data Management** - Scheduled cleanup and backup support

### Developer Friendly
- 🔧 **Easy Configuration** - Environment variables via `.env` file
- 🔑 **Credential Generator** - Secure password/token generation tool
- 📱 **Device Auto-Discovery** - New devices added through configuration only
- 🎨 **Contextual UI** - Device-specific colors, icons, and queries

---

## 🚀 Quick Start

Get the platform running locally in **5 minutes**:

```bash
# Clone repository
git clone https://github.com/yourusername/home-iot.git
cd home-iot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate secure credentials
python generate_credentials.py --output env

# Run application
python app.py
```

**Access:**
- 🌐 Admin Panel: http://localhost:5001
- 🔌 API Endpoint: http://localhost:5000/api/

**Default login:** Password generated in `.env` file

📖 **Detailed setup guide:** [QUICKSTART.md](docs/QUICKSTART.md)

---

## 📚 Documentation

### Getting Started
- 🚀 **[Quick Start Guide](docs/QUICKSTART.md)** - Development setup (5 minutes)
- 📦 **[Production Deployment](docs/DEPLOY.md)** - VPS deployment with nginx/SSL
- 🔧 **[Troubleshooting](docs/troubleshooting/COMMON-ISSUES.md)** - Common issues and solutions

### Configuration Guides
- 🔑 **[Credentials Management](docs/guides/CREDENTIALS.md)** - Security setup and rotation
- 📱 **[Multi-Device Setup](docs/guides/MULTI-DEVICE.md)** - Adding new device types
- 🔌 **[ESP32 Hardware Setup](docs/guides/ESP32-SETUP.md)** - Device configuration
- 💾 **[Backup & Restore](docs/guides/BACKUP-RESTORE.md)** - Data backup strategies

### Architecture
- 🗄️ **[Database Schema](docs/architecture/DATABASE.md)** - Schema design and migrations
- 🔌 **[API Reference](docs/architecture/API.md)** - REST API documentation
- 🔒 **[Security Model](docs/architecture/SECURITY.md)** - Authentication and authorization

### Reference
- ❓ **[FAQ](docs/troubleshooting/FAQ.md)** - Frequently asked questions
- 📝 **[Examples](examples/)** - ESP32 code examples and API usage

---

## 🏗️ Architecture Overview

```
┌─────────────┐
│   ESP32     │  (Water sensor, Temperature, Security, etc.)
│   Devices   │
└──────┬──────┘
       │ HTTPS POST
       ▼
┌─────────────────────────────────────────┐
│  VPS Server (Ubuntu/Debian)             │
│  ┌─────────────────────────────────┐   │
│  │  Nginx (Port 443)               │   │
│  │  - SSL/TLS Termination          │   │
│  │  - Reverse Proxy                │   │
│  └────────┬────────────────────────┘   │
│           │                              │
│  ┌────────▼────────┐  ┌──────────────┐ │
│  │  Flask API      │  │ Admin Panel  │ │
│  │  Port 5000      │  │ Port 5001    │ │
│  └────────┬────────┘  └──────┬───────┘ │
│           │                    │         │
│  ┌────────▼────────────────────▼──────┐ │
│  │  SQLite Database                   │ │
│  │  - Multi-device tables             │ │
│  │  - Automatic cleanup               │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**→ Detailed architecture:** [Architecture Docs](docs/architecture/)

---

## 📱 Supported Device Types

| Device Type | Icon | Description | Example Use Case |
|-------------|------|-------------|------------------|
| **Water Management** | 🐠 | Aquarium water level, pump control | Automatic aquarium top-off |
| **Temperature Sensors** | 🌡️ | Temperature & humidity monitoring | Room climate control |
| **Security Systems** | 🔒 | Motion detection, door sensors | Home security monitoring |
| **Custom Devices** | 📱 | Add your own device types | Any ESP32 sensor project |

**→ Adding new devices:** [Multi-Device Guide](docs/guides/MULTI-DEVICE.md)

---

## 🔌 API Example

### Send Event from ESP32

```cpp
// ESP32 Arduino Code
#include <HTTPClient.h>

void sendWaterEvent() {
  HTTPClient http;
  http.begin("https://your-domain.com/api/water-events");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer YOUR_API_TOKEN");
  
  String payload = "{\"device_id\":\"DOLEWKA\",\"timestamp\":\"2025-10-04T12:00:00\",\"unix_time\":1728043200,\"event_type\":\"AUTO_PUMP\",\"volume_ml\":250,\"water_status\":\"OK\",\"system_status\":\"OK\"}";
  
  int httpCode = http.POST(payload);
  http.end();
}
```

**→ Complete examples:** [examples/esp32/](examples/esp32/)

---

## 🛠️ Development

### Prerequisites
- Python 3.8+
- SQLite3
- Virtual environment support

### Project Structure

```
├── LICENSE
├── README.md
├── app.py
├── data
│   ├── database
│   │   └── water_events.db
│   └── logs
│       ├── app.log
│       ├── app.log-20251004
│       ├── app_startup.log
│       ├── app_test.log
│       ├── cleanup_logs.log
│       ├── db_cleanup.log
├── device_config.py
├── docs
│   ├── CREDENTIALS.MD
│   ├── DEPLOY.MD
│   ├── MULTI-DEVICE.md
│   ├── QUICKSTART.md
│   ├── architecture
│   │   ├── API.md
│   │   ├── DATABASE.md
│   │   └── SECURITY.md
│   ├── guides
│   │   ├── BACKUP-RESTORE.md
│   │   └── ESP32-SETUP.md
│   └── troubleshooting
│       ├── COMMON-ISSUES.md
│       └── FAQ.md
├── examples
│   ├── api
│   ├── esp32
│   └── queries
├── queries_config.py
├── requirements.txt
├── scripts
│   ├── db_cleanup.sh
│   └── start_home_iot.sh
├── ssl
├── templates
│   ├── admin.html
│   ├── dashboard.html
│   └── login.html
├── tools
│   ├── generate_credentials.py
│   └── manage_credentials.py
├── venv
└── water_events.db
```

### Running Tests

```bash
# Health check
curl http://localhost:5000/health

# API test (requires token)
curl -X POST http://localhost:5000/api/water-events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"TEST","timestamp":"2025-01-01T12:00:00","unix_time":1735732800,"event_type":"AUTO_PUMP","volume_ml":100,"water_status":"OK","system_status":"OK"}'
```

---

## 🔒 Security

### Authentication & Authorization
- **API Authentication:** Bearer token for ESP32 devices
- **Admin Panel:** Session-based authentication with secure cookies
- **Timing Attack Protection:** Constant-time comparison for credentials
- **Session Security:** HttpOnly, SameSite cookies with configurable timeout

### Rate Limiting & Protection
- **Brute-Force Protection:** Login attempts limited to 10/hour
- **API Rate Limiting:** 60 requests/hour per IP for device endpoints
- **Admin Query Limiting:** 30 queries/hour to protect database
- **Health Check Limiting:** 30 requests/minute for monitoring
- **Account Lockout:** Automatic 1-hour ban after 8 failed login attempts
- **Global Limits:** 1000 requests/day, 100/hour per IP as fallback

### Infrastructure Security
- **SSL/TLS:** Production deployment with Let's Encrypt certificates
- **Reverse Proxy:** Nginx with security headers (HSTS, CSP, X-Frame-Options)
- **Input Validation:** All API inputs validated before database storage
- **Secure Storage:** Environment-based credential management

**→ Security details:** [Security Model](docs/architecture/SECURITY.md)

---

## 📊 Database Management

- **Auto-cleanup:** Old records removed automatically (configurable retention)
- **Backup support:** Built-in backup scripts with cron integration
- **Multi-device schema:** Single table supports all device types
- **Performance:** Indexed queries for fast data retrieval

**→ Schema details:** [Database Documentation](docs/architecture/DATABASE.md)

---

## 🌟 Use Cases

### Home Automation
- Aquarium water level monitoring and auto-top-off
- Room temperature and humidity tracking
- Smart watering systems for plants

### Environmental Monitoring
- Multi-room climate monitoring
- Outdoor weather station data logging
- Greenhouse environment control

### Security & Access Control
- Motion detection logging
- Door/window sensor monitoring
- Access event tracking

### Custom Projects
- Energy consumption monitoring
- Soil moisture tracking
- Custom sensor data aggregation

---

## 📈 Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Grafana integration for advanced visualization
- [ ] Mobile app (React Native)
- [ ] MQTT support for IoT protocols
- [ ] Docker containerization
- [ ] Multi-user support with RBAC
- [ ] Data export to cloud storage
- [ ] Alerting and notifications

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/) web framework
- Inspired by real-world aquarium automation needs
- Community contributions and feedback

---

## 📞 Support

- 📖 **Documentation:** [docs/](docs/)
- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/yourusername/home-iot/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/yourusername/home-iot/discussions)
- 📧 **Contact:** your-email@example.com

---

**⭐ If you find this project useful, please consider giving it a star on GitHub!**