Guide to configuring ESP32 devices for Home IoT Platform.

## Prerequisites

- ESP32 development board (ESP32-C3, ESP32-S2, or ESP32)
- Arduino IDE or PlatformIO
- USB cable for programming
- Sensors (depending on your project)

## Arduino IDE Setup

### Install ESP32 Board Support

1. Open Arduino IDE
2. Go to **File → Preferences**
3. Add to **Additional Board Manager URLs:**
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
4. Go to **Tools → Board → Boards Manager**
5. Search for "ESP32" and install

### Install Required Libraries

**Tools → Manage Libraries**, install:
- `ArduinoJson` by Benoit Blanchon
- `WiFi` (built-in)
- `HTTPClient` (built-in)

## Configuration

### WiFi Credentials
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
API Configuration
cppconst char* serverUrl = "https://your-domain.com/api/water-events";
const char* apiToken = "YOUR_API_TOKEN_FROM_ENV_FILE";
const char* deviceId = "YOUR_DEVICE_ID";  // e.g., "DOLEWKA"
Basic Template
cpp#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// Configuration
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
const char* serverUrl = "https://your-domain.com/api/water-events";
const char* apiToken = "YOUR_TOKEN";
const char* deviceId = "YOUR_DEVICE";

// NTP Time
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 0;
const int   daylightOffset_sec = 3600;

void setup() {
    Serial.begin(115200);
    
    // Connect WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ WiFi Connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    
    // Initialize time
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
}

void sendEvent(String eventType, int value) {
    if(WiFi.status() != WL_CONNECTED) {
        Serial.println("❌ WiFi not connected");
        return;
    }
    
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", "Bearer " + String(apiToken));
    http.setTimeout(10000);
    
    // Get current time
    time_t now;
    struct tm timeinfo;
    time(&now);
    localtime_r(&now, &timeinfo);
    
    // Build JSON
    StaticJsonDocument<512> doc;
    doc["device_id"] = deviceId;
    doc["unix_time"] = (unsigned long)now;
    
    char timestamp[25];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", &timeinfo);
    doc["timestamp"] = timestamp;
    
    doc["event_type"] = eventType;
    doc["volume_ml"] = value;  // or your sensor value
    doc["water_status"] = "OK";
    doc["system_status"] = "OK";
    
    String payload;
    serializeJson(doc, payload);
    
    Serial.println("📤 Sending: " + payload);
    
    int httpCode = http.POST(payload);
    
    if(httpCode > 0) {
        String response = http.getString();
        Serial.printf("✅ Response %d: %s\n", httpCode, response.c_str());
    } else {
        Serial.printf("❌ Error: %s\n", http.errorToString(httpCode).c_str());
    }
    
    http.end();
}

void loop() {
    // Your sensor reading code here
    int sensorValue = analogRead(A0);
    
    // Send event every 10 minutes
    sendEvent("AUTO_PUMP", sensorValue);
    
    delay(600000);  // 10 minutes
}
Testing
Serial Monitor Test

Upload code to ESP32
Open Serial Monitor (115200 baud)
Watch for connection messages
Verify data is being sent

Expected output:
Connecting to WiFi....
✅ WiFi Connected
IP: 192.168.1.100
📤 Sending: {"device_id":"TEST",...}
✅ Response 200: {"success":true,"event_id":1}
Troubleshooting
WiFi Connection Issues
cpp// Add timeout
int attempts = 0;
while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
}
if(WiFi.status() != WL_CONNECTED) {
    Serial.println("\n❌ WiFi connection failed");
    ESP.restart();
}
HTTPS Certificate Issues
For self-signed certificates:
cpp// Add to setup():
#include <WiFiClientSecure.h>
WiFiClientSecure client;
client.setInsecure();  // Skip certificate validation (dev only!)
Time Sync Issues
cpp// Wait for time sync
Serial.print("Syncing time");
int retry = 0;
while(!getLocalTime(&timeinfo) && retry < 10) {
    Serial.print(".");
    delay(1000);
    retry++;
}
Power Optimization
For battery-powered devices:
cpp#include <esp_sleep.h>

void setup() {
    // ... your code ...
    
    // Send data
    sendEvent("MOISTURE_READING", value);
    
    // Deep sleep for 10 minutes
    esp_sleep_enable_timer_wakeup(10 * 60 * 1000000ULL);
    esp_deep_sleep_start();
}
Related Documentation

Multi-Device Guide - Device type configuration
API Reference - API endpoint details
Examples - Complete code examples