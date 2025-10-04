# Multi-Device IoT Platform Guide

Complete guide to understanding and extending the multi-device architecture.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Supported Device Types](#supported-device-types)
- [Adding a New Device Type](#adding-a-new-device-type)
- [Device Configuration](#device-configuration)
- [Query Configuration](#query-configuration)
- [ESP32 Integration](#esp32-integration)
- [Testing](#testing)
- [Best Practices](#best-practices)

---

## Architecture Overview

### Core Principles

The Home IoT Platform evolved from a single-device water monitoring system into a flexible multi-device platform while maintaining:

1. **Single Service Deployment** - One Flask app, one database, one systemd service
2. **Configuration Over Code** - New devices added through config files, not code changes
3. **Auto-Discovery** - Database-driven device type detection
4. **Contextual Interfaces** - Device-specific admin panels and queries
5. **Backwards Compatibility** - Existing devices continue working unchanged

### Database Architecture

**Single Table Approach** with device-specific columns:

```sql
water_events:
  -- Core columns (all devices)
  id, device_id, device_type, timestamp, unix_time, event_type, 
  system_status, received_at, client_ip
  
  -- Water system specific (NULL for other devices)
  volume_ml, pump_duration, time_gap_1, gap1_fail_sum, algorithm_data
  
  -- Temperature sensor specific (NULL for others)
  temperature, humidity
  
  -- Security system specific (NULL for others)
  zone_status, motion_detected
```

**Benefits:**
- ✅ Simple schema management
- ✅ Single database file
- ✅ Easy backups
- ✅ Flexible column usage

**Trade-offs:**
- ⚠️ Some NULL columns (acceptable for moderate scale)
- ⚠️ Less strict type enforcement

### Application Flow

```
ESP32 Device
    ↓
    POST /api/water-events
    ↓
device_config.py determines device_type from device_id
    ↓
Data stored in water_events table with device_type
    ↓
Admin dashboard shows device types from database
    ↓
Device-specific admin panel loads relevant queries
    ↓
queries_config.py provides contextual SQL queries
```

---

## Supported Device Types

### 1. Water Management Systems 🐠

**Use Cases:**
- Aquarium auto-top-off systems
- Plant watering automation
- Water level monitoring

**Key Metrics:**
- Volume dispensed (ml)
- Pump duration and attempts
- Sensor delays and failures
- Algorithm performance statistics

**Columns Used:**
- `volume_ml`, `pump_duration`, `pump_attempts`
- `time_gap_1`, `time_gap_2`, `water_trigger_time`
- `gap1_fail_sum`, `gap2_fail_sum`, `water_fail_sum`
- `algorithm_data` (JSON), `water_status`

---

### 2. Temperature & Humidity Sensors 🌡️

**Use Cases:**
- Room climate monitoring
- Greenhouse environment control
- HVAC optimization
- Cold storage monitoring

**Key Metrics:**
- Temperature (°C)
- Humidity (%)
- Timestamp and location

**Columns Used:**
- `temperature`, `humidity`
- Basic: `device_id`, `timestamp`, `event_type`, `system_status`

---

### 3. Security Systems 🔒

**Use Cases:**
- Motion detection logging
- Door/window sensor monitoring
- Access control events
- Perimeter security

**Key Metrics:**
- Zone status (armed/disarmed/triggered)
- Motion detection events
- Event timestamps

**Columns Used:**
- `zone_status`, `motion_detected`
- Basic: `device_id`, `timestamp`, `event_type`, `system_status`

---

### 4. Custom Device Types 📱

**The platform is designed to be extended!**

Examples of what you could add:
- Energy consumption monitors
- Soil moisture sensors
- Air quality monitors
- Vehicle GPS trackers
- Smart meter readers

---

## Adding a New Device Type

Let's walk through adding a **Soil Moisture Sensor** device type.

### Step 1: Plan Your Device

**Questions to answer:**
1. What data will it send? (moisture_percent, battery_voltage)
2. What events will it log? (MOISTURE_READING, LOW_BATTERY)
3. What queries will you need? (Daily averages, battery status)
4. What colors/icons for UI? (🌱 green theme)

**Example data structure:**
```json
{
  "device_id": "GARDEN_01",
  "timestamp": "2025-10-04T12:00:00",
  "unix_time": 1728043200,
  "event_type": "MOISTURE_READING",
  "system_status": "OK",
  "moisture_percent": 45,
  "battery_voltage": 3.7
}
```

---

### Step 2: Update Database Schema

Edit `app.py` - `init_database()` function:

```python
# Add to new_columns list:
'moisture_percent INTEGER DEFAULT NULL',
'battery_voltage REAL DEFAULT NULL'
```

**Database migration happens automatically** on next restart!

---

### Step 3: Configure Device Type

Edit `device_config.py`:

```python
# 1. Add device ID mapping
DEVICE_TYPE_MAPPING = {
    'DOLEWKA': 'water_system',
    'GARDEN_01': 'soil_moisture',  # 🆕 NEW
    'GARDEN_02': 'soil_moisture',  # 🆕 NEW
    # ... existing mappings
}

# 2. Define device type
DEVICE_TYPES = {
    'soil_moisture': {  # 🆕 NEW DEVICE TYPE
        'name': 'Soil Moisture Sensors',
        'description': 'Garden and plant soil moisture monitoring',
        'icon': '🌱',
        'color': '#4caf50',  # Green
        'columns': [
            'id', 'device_id', 'timestamp', 'event_type',
            'moisture_percent', 'battery_voltage',
            'system_status', 'received_at'
        ],
        'event_types': [
            'MOISTURE_READING',
            'LOW_BATTERY',
            'SENSOR_ERROR'
        ]
    },
    # ... existing device types
}
```

---

### Step 4: Add Device Queries

Edit `queries_config.py`:

```python
DEVICE_SPECIFIC_QUERIES = {
    'soil_moisture': {  # 🆕 NEW QUERIES
        'recent_readings': {
            'name': 'Recent Moisture Readings',
            'description': 'Last 24 hours of moisture data',
            'sql': """
                SELECT id, device_id, timestamp, moisture_percent,
                       battery_voltage, system_status, received_at
                FROM water_events 
                WHERE moisture_percent IS NOT NULL
                    AND received_at > datetime('now', '-24 hours')
                    {device_filter}
                ORDER BY received_at DESC
            """
        },
        
        'moisture_trends': {
            'name': 'Moisture Trends',
            'description': 'Hourly moisture averages',
            'sql': """
                SELECT 
                    DATE(received_at) as date,
                    HOUR(received_at) as hour,
                    ROUND(AVG(moisture_percent), 1) as avg_moisture,
                    ROUND(AVG(battery_voltage), 2) as avg_battery,
                    COUNT(*) as readings
                FROM water_events 
                WHERE moisture_percent IS NOT NULL 
                    AND received_at > datetime('now', '-7 days')
                    {device_filter}
                GROUP BY DATE(received_at), HOUR(received_at)
                ORDER BY date DESC, hour DESC
            """
        },
        
        'low_battery': {
            'name': 'Low Battery Alerts',
            'description': 'Devices with battery < 3.3V',
            'sql': """
                SELECT device_id, timestamp, battery_voltage,
                       moisture_percent, received_at
                FROM water_events 
                WHERE battery_voltage < 3.3
                    AND battery_voltage IS NOT NULL
                    {device_filter}
                ORDER BY received_at DESC
                LIMIT 50
            """
        }
    },
    # ... existing device queries
}
```

---

### Step 5: Test Configuration

```bash
# Restart application
sudo systemctl restart home-iot

# Check logs for errors
sudo journalctl -u home-iot -n 30 --no-pager

# Test sending data
curl -X POST https://your-domain.com/api/water-events \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "GARDEN_01",
    "timestamp": "2025-10-04T12:00:00",
    "unix_time": 1728043200,
    "event_type": "MOISTURE_READING",
    "moisture_percent": 45,
    "battery_voltage": 3.7,
    "system_status": "OK"
  }'

# Check dashboard
# Visit: https://your-domain.com/dashboard
# You should see "🌱 Soil Moisture Sensors" card
```

---

## Device Configuration Reference

### Complete device_config.py Structure

```python
DEVICE_TYPE_MAPPING = {
    # Maps device_id → device_type
    'DEVICE_ID': 'device_type_name'
}

DEVICE_TYPES = {
    'device_type_name': {
        # Display name in UI
        'name': 'Human Readable Name',
        
        # Short description
        'description': 'What this device does',
        
        # Emoji icon for UI
        'icon': '🔧',
        
        # CSS color (hex) for UI theming
        'color': '#3498db',
        
        # Database columns to display (order matters!)
        'columns': [
            'id',           # Always include
            'device_id',    # Always include
            'timestamp',    # Always include
            # ... device-specific columns
            'received_at'   # Always include
        ],
        
        # Valid event types for validation
        'event_types': [
            'EVENT_TYPE_1',
            'EVENT_TYPE_2'
        ]
    }
}
```

### Helper Functions

```python
# Get device type from device_id
device_type = get_device_type('GARDEN_01')
# Returns: 'soil_moisture'

# Get full device configuration
config = get_device_config('soil_moisture')
# Returns: dict with name, icon, color, etc.

# Get database columns for device
columns = get_device_columns('soil_moisture')
# Returns: ['id', 'device_id', 'timestamp', ...]
```

---

## Query Configuration Reference

### Query Structure

```python
DEVICE_SPECIFIC_QUERIES = {
    'device_type': {
        'query_id': {
            'name': 'Display Name',           # Shown on button
            'description': 'What it does',    # Tooltip text
            'sql': """
                SELECT columns
                FROM water_events 
                WHERE conditions
                    {device_filter}  # Auto-injected filter
                ORDER BY received_at DESC
            """
        }
    }
}
```

### Query Template Variables

Queries support automatic filtering:

```python
# {device_filter} is replaced with:
# - "AND device_type = 'water_system'" when in device context
# - "" (empty) when in general context
```

### Base Queries (Available for All Devices)

```python
# These work for ALL device types:
- last24h          # Events from last 24 hours
- last_100_events  # Last 100 events
- all_events       # All events
- errors           # Events with system_status = 'ERROR'
- today_stats      # Event counts for today
```

---

## ESP32 Integration

### Basic ESP32 Code Template

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "https://your-domain.com/api/water-events";
const char* apiToken = "YOUR_API_TOKEN";
const char* deviceId = "GARDEN_01";

void sendEvent(String eventType, float moisture, float battery) {
    if(WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        
        // Headers
        http.addHeader("Content-Type", "application/json");
        http.addHeader("Authorization", "Bearer " + String(apiToken));
        
        // Build JSON payload
        StaticJsonDocument<256> doc;
        doc["device_id"] = deviceId;
        doc["timestamp"] = getTimestamp();  // Implement your time function
        doc["unix_time"] = getUnixTime();
        doc["event_type"] = eventType;
        doc["moisture_percent"] = (int)moisture;
        doc["battery_voltage"] = battery;
        doc["system_status"] = "OK";
        
        String payload;
        serializeJson(doc, payload);
        
        // Send POST request
        int httpCode = http.POST(payload);
        
        if(httpCode == 200) {
            Serial.println("✅ Event sent successfully");
        } else {
            Serial.printf("❌ HTTP Error: %d\n", httpCode);
        }
        
        http.end();
    }
}

void setup() {
    Serial.begin(115200);
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ WiFi connected");
}

void loop() {
    // Read your sensors
    float moisture = readMoistureSensor();
    float battery = readBatteryVoltage();
    
    // Send event every 10 minutes
    sendEvent("MOISTURE_READING", moisture, battery);
    
    delay(600000);  // 10 minutes
}
```

**→ Complete ESP32 examples:** [../examples/esp32/](../examples/esp32/)

---

## Testing

### Test New Device Type

```bash
# 1. Send test event
curl -X POST https://your-domain.com/api/water-events \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "GARDEN_01",
    "timestamp": "2025-10-04T12:00:00",
    "unix_time": 1728043200,
    "event_type": "MOISTURE_READING",
    "moisture_percent": 45,
    "battery_voltage": 3.7,
    "system_status": "OK"
  }'

# 2. Verify in database
sqlite3 /opt/home-iot/water_events.db \
    "SELECT * FROM water_events WHERE device_id='GARDEN_01';"

# 3. Check dashboard
# Visit: https://your-domain.com/dashboard
# Should show new device type card

# 4. Test admin panel
# Visit: https://your-domain.com/admin/soil_moisture
# Should show device-specific interface

# 5. Test queries
# Click "Recent Moisture Readings" button
# Should display data in table
```

---

## Best Practices

### Device Naming Conventions

```
Good:
- GARDEN_01, GARDEN_02, GARDEN_SHED
- TEMP_LIVING_ROOM, TEMP_BEDROOM
- DOOR_FRONT, DOOR_BACK

Bad:
- garden1 (lowercase, hard to read logs)
- temp-room (hyphens can cause issues)
- My Device (spaces)
```

### Event Type Naming

```
Good:
- MOISTURE_READING
- LOW_BATTERY
- SENSOR_ERROR

Pattern: ACTION_SUBJECT or STATUS_CONDITION
```

### Column Naming

```
Good:
- moisture_percent (descriptive + unit implied)
- battery_voltage
- temperature_celsius

Bad:
- moisture (unit unclear)
- bat (abbreviation)
- temp (ambiguous)
```

### Query Design

```python
# ✅ Good - Clear, documented, efficient
'daily_average': {
    'name': 'Daily Averages',
    'description': 'Average moisture per day for last 30 days',
    'sql': """
        SELECT 
            DATE(received_at) as date,
            ROUND(AVG(moisture_percent), 1) as avg_moisture,
            COUNT(*) as readings
        FROM water_events 
        WHERE moisture_percent IS NOT NULL
            AND received_at > datetime('now', '-30 days')
            {device_filter}
        GROUP BY DATE(received_at)
        ORDER BY date DESC
    """
}

# ❌ Bad - Unclear name, no description, slow query
'query1': {
    'name': 'Query',
    'description': '',
    'sql': "SELECT * FROM water_events"  # Returns all columns, no filter
}
```

### Security Considerations

1. **API Tokens:** Use unique tokens per device
2. **Device IDs:** Use unpredictable IDs (not sequential)
3. **Validation:** Always validate input data
4. **Rate Limiting:** Consider implementing per-device limits

---

## Migration Guide

### Migrating Existing Single-Device Setup

If you have existing DOLEWKA-only installation:

**Good news:** Multi-device architecture is **fully backwards compatible!**

```bash
# 1. Update code (git pull)
git pull origin main

# 2. Restart service
sudo systemctl restart home-iot

# 3. Verify DOLEWKA still works
curl https://your-domain.com/health
```

**What happens:**
- Existing database continues working
- DOLEWKA is auto-assigned device_type='water_system'
- New dashboard shows DOLEWKA as "Water Management"
- Old API requests work unchanged

---

## Troubleshooting

### Device not showing in dashboard

```bash
# Check device_type assignment
sqlite3 /opt/home-iot/water_events.db \
    "SELECT DISTINCT device_id, device_type FROM water_events;"

# If device_type is NULL or wrong:
# 1. Check DEVICE_TYPE_MAPPING in device_config.py
# 2. Restart service
sudo systemctl restart home-iot
```

### Queries not loading

```bash
# Check logs for errors
sudo journalctl -u home-iot -n 50 --no-pager | grep -i error

# Common issue: SQL syntax error
# Verify query in queries_config.py
# Test query directly:
sqlite3 /opt/home-iot/water_events.db "YOUR_QUERY_HERE"
```

### Device shows but no data

```bash
# Check if events are being received
curl -X POST https://your-domain.com/api/water-events \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d @test_payload.json

# Check database
sqlite3 /opt/home-iot/water_events.db \
    "SELECT COUNT(*) FROM water_events WHERE device_id='YOUR_DEVICE';"
```

---

## Advanced Topics

### Custom Validation Rules

Edit `app.py` - `validate_event_data()`:

```python
# Add device-specific validation
if device_type == 'soil_moisture':
    if 'moisture_percent' in data:
        moisture = int(data['moisture_percent'])
        if moisture < 0 or moisture > 100:
            return False, "moisture_percent must be 0-100"
```

### Multi-Language Support

Add translations in templates:

```python
# device_config.py
DEVICE_TYPES = {
    'soil_moisture': {
        'name': {
            'en': 'Soil Moisture Sensors',
            'pl': 'Czujniki Wilgotności Gleby'
        },
        # ...
    }
}
```

### Data Export Customization

Custom export formats for specific device types (future feature).

---

## Related Documentation

- 🔌 [API Reference](../architecture/API.md)
- 🗄️ [Database Schema](../architecture/DATABASE.md)
- 🔧 [ESP32 Hardware Setup](ESP32-SETUP.md)
- 📖 [Examples](../../examples/)

---

## Community Devices

Share your device configurations! Submit a PR with:
- Device type configuration
- Query examples
- ESP32 code example
- Use case description

**Contributors:**
- Water Management (DOLEWKA) - Original author
- Temperature Sensors - Example implementation
- Security Systems - Example implementation

---

**Questions?** Open an issue on GitHub or check the [FAQ](../troubleshooting/FAQ.md)!