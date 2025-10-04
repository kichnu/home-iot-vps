# API Reference Documentation

Complete REST API documentation for Home IoT Platform.

## Base URL

```
https://your-domain.com/api/
```

## Authentication

All API requests require Bearer token authentication:

```
Authorization: Bearer YOUR_API_TOKEN
```

**Get your token from `.env` file:**
```bash
grep WATER_SYSTEM_API_TOKEN .env
```

## Endpoints

### POST /api/water-events

Submit a new IoT event.

**Request:**
```http
POST /api/water-events HTTP/1.1
Host: your-domain.com
Authorization: Bearer YOUR_API_TOKEN
Content-Type: application/json

{
  "device_id": "DOLEWKA",
  "timestamp": "2025-10-04T12:00:00",
  "unix_time": 1728043200,
  "event_type": "AUTO_PUMP",
  "volume_ml": 250,
  "water_status": "OK",
  "system_status": "OK"
}
```

**Response (Success):**
```json
{
  "success": true,
  "event_id": 1,
  "message": "Event recorded successfully"
}
```

**Response (Error):**
```json
{
  "error": "Missing required field: device_id"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/missing token)
- `500` - Server Error

### GET /api/events

Retrieve event history.

**Request:**
```http
GET /api/events?limit=100&device_id=DOLEWKA&event_type=AUTO_PUMP HTTP/1.1
Host: your-domain.com
Authorization: Bearer YOUR_API_TOKEN
```

**Query Parameters:**
- `limit` (int, optional): Max results (1-1000, default: 100)
- `device_id` (string, optional): Filter by device
- `event_type` (string, optional): Filter by event type

**Response:**
```json
{
  "success": true,
  "count": 10,
  "events": [
    {
      "id": 1,
      "device_id": "DOLEWKA",
      "timestamp": "2025-10-04T12:00:00",
      "event_type": "AUTO_PUMP",
      "volume_ml": 250,
      "system_status": "OK",
      "received_at": "2025-10-04 12:00:05"
    }
  ]
}
```

### GET /api/stats

Get platform statistics.

**Request:**
```http
GET /api/stats HTTP/1.1
Host: your-domain.com
Authorization: Bearer YOUR_API_TOKEN
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_events": 1234,
    "unique_devices": 3,
    "event_types": {
      "AUTO_PUMP": 800,
      "MANUAL_NORMAL": 200
    },
    "total_volume_ml": 308500,
    "last_event": {
      "timestamp": "2025-10-04T12:00:00",
      "volume_ml": 250
    }
  }
}
```

### GET /health

Health check endpoint (no authentication required).

**Request:**
```http
GET /health HTTP/1.1
Host: your-domain.com
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-04T12:00:00",
  "database": "connected",
  "nginx_mode": true,
  "http_port": 5000,
  "admin_port": 5001,
  "active_sessions": 1
}
```

## Data Models

### Water System Event

```json
{
  "device_id": "string (required)",
  "timestamp": "string ISO 8601 (required)",
  "unix_time": "integer (required)",
  "event_type": "string (required)",
  "volume_ml": "integer (required)",
  "water_status": "string (required)",
  "system_status": "string (required)",
  
  // Algorithm data (optional)
  "time_gap_1": "integer",
  "time_gap_2": "integer",
  "water_trigger_time": "integer",
  "pump_duration": "integer",
  "pump_attempts": "integer",
  "gap1_fail_sum": "integer",
  "gap2_fail_sum": "integer",
  "water_fail_sum": "integer",
  "algorithm_data": "string (JSON)"
}
```

### Temperature Sensor Event

```json
{
  "device_id": "string (required)",
  "timestamp": "string ISO 8601 (required)",
  "unix_time": "integer (required)",
  "event_type": "string (required)",
  "temperature": "float (required)",
  "humidity": "float (required)",
  "system_status": "string (required)"
}
```

### Security System Event

```json
{
  "device_id": "string (required)",
  "timestamp": "string ISO 8601 (required)",
  "unix_time": "integer (required)",
  "event_type": "string (required)",
  "zone_status": "string (required)",
  "motion_detected": "boolean (required)",
  "system_status": "string (required)"
}
```

## Field Validation

### Required Fields (All Events)

- `device_id`: Must be in VALID_DEVICE_IDS list
- `timestamp`: ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- `unix_time`: Unix timestamp (integer)
- `event_type`: Must be valid for device type
- `system_status`: "OK" or "ERROR"

### Event Types

**Water System:**
- AUTO_PUMP
- MANUAL_NORMAL
- MANUAL_EXTENDED
- AUTO_CYCLE_COMPLETE
- STATISTICS_RESET

**Temperature Sensor:**
- TEMP_READING
- HUMIDITY_READING
- SENSOR_ERROR

**Security System:**
- DOOR_OPEN
- DOOR_CLOSE
- MOTION_DETECTED
- SYSTEM_ARM
- SYSTEM_DISARM

### Water Status Values

- OK
- LOW
- NORMAL
- BOTH_LOW
- SENSOR1_LOW
- SENSOR2_LOW
- PARTIAL
- CHECKING

## Rate Limiting

Currently no rate limiting implemented.

**Recommended client behavior:**
- Max 1 request per second per device
- Implement exponential backoff on errors
- Cache responses when appropriate

## Error Handling

### Error Response Format

```json
{
  "error": "Error message description"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing Authorization header" | No auth header | Add Authorization header |
| "Invalid token" | Wrong API token | Check .env file |
| "Invalid device_id" | Unknown device | Add to VALID_DEVICE_IDS |
| "Invalid event_type" | Wrong event type | Check device type events |
| "Missing required field: X" | Missing field | Add required field |

## Examples

### cURL Examples

```bash
# Send water event
curl -X POST https://your-domain.com/api/water-events \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

# Get recent events
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-domain.com/api/events?limit=10"

# Get stats
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-domain.com/api/stats"

# Health check (no auth)
curl "https://your-domain.com/health"
```

### Python Example

```python
import requests
import time

API_URL = "https://your-domain.com/api/water-events"
API_TOKEN = "YOUR_TOKEN"
DEVICE_ID = "DOLEWKA"

def send_event(event_type, volume_ml):
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "device_id": DEVICE_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "unix_time": int(time.time()),
        "event_type": event_type,
        "volume_ml": volume_ml,
        "water_status": "OK",
        "system_status": "OK"
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    return response.json()

# Send event
result = send_event("AUTO_PUMP", 250)
print(result)
```

## Related Documentation

- [Database Schema](DATABASE.md) - Data structure
- [Multi-Device Guide](../guides/MULTI-DEVICE.md) - Device types
- [ESP32 Setup](../guides/ESP32-SETUP.md) - Hardware integration

---

**API Version:** 2.0 (Multi-device support)
**Last Updated:** 2025-10-04