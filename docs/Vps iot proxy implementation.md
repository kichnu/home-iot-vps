# VPS IoT Proxy Implementation Guide

## Overview

This document describes the reverse proxy architecture for accessing ESP32 IoT devices through a centralized VPS. The solution provides secure HTTPS access to local IoT devices from any network without requiring VPN clients on end-user devices.

## Architecture Summary

```
[User Device] → HTTPS → [VPS Nginx] → WireGuard → [MikroTik] → LAN → [ESP32]
```

**Key components:**
- VPS: Nginx reverse proxy + Flask admin panel
- WireGuard tunnel: VPS (10.99.0.1) ↔ MikroTik (10.99.0.2)
- ESP32: AsyncWebServer on port 80, trusted IP whitelist for VPS

---

## VPS-Side Changes Implemented

### 1. Nginx Configuration (`/etc/nginx/sites-available/home-iot`)

Added location block for ESP32 proxy:

```nginx
location /device/top_off_water/ {
    proxy_pass http://192.168.10.2/;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-VPS-Proxy "true";
    proxy_connect_timeout 10s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
    proxy_intercept_errors on;
    error_page 502 503 504 = @esp32_offline;
}
```

**Important:** Location block must appear BEFORE `location /` in config file.

### 2. Flask Application

**New file:** `utils/health_check.py`
- TCP socket check to device LAN IP
- 30-second cache to avoid spamming ESP32
- Returns online status and latency

**New endpoint:** `/api/device-health/<device_type>`
- Requires admin authentication
- Used by dashboard for status indicators

**Modified:** `device_config.py`
- Added `DEVICE_NETWORK_CONFIG` dictionary with LAN IPs and proxy paths
- Added `get_device_network_config()` and `get_all_devices_with_dashboard()` functions

**Modified:** `templates/dashboard.html`
- Two buttons per device: "Live Device" (proxy) and "Logs & Database" (admin)
- Real-time online/offline status with health check polling every 30s
- Latency display in milliseconds

---

## ESP32-Side Changes Required

### 1. Trusted IP Whitelist

In `auth_manager.cpp`:
```cpp
const IPAddress TRUSTED_VPS_IP(10, 99, 0, 1);

bool isTrustedProxyIP(IPAddress ip) {
    return (ip == TRUSTED_VPS_IP);
}
```

In `web_server.cpp` → `checkAuthentication()`:
```cpp
if (isTrustedProxyIP(clientIP)) {
    return true;  // Skip authentication for VPS
}
```

### 2. Relative API Paths

All JavaScript fetch calls must use relative paths (no leading slash):
```javascript
// Correct (works for both LAN and proxy)
fetch('api/status')

// Wrong (breaks through proxy)
fetch('/api/status')
```

### 3. Proxy Detection for UI (Optional)

JavaScript to change "Logout" → "Back" when accessed through VPS:
```javascript
const localIPs = ['192.168.10.2', 'localhost', '127.0.0.1'];
const isProxied = !localIPs.includes(window.location.hostname);
if (isProxied) {
    // Change button text and behavior
}
```

---

## Adding New IoT Devices - Checklist

### VPS Configuration

1. **Nginx:** Add new location block
   ```nginx
   location /device/NEW_DEVICE_NAME/ {
       proxy_pass http://192.168.X.X/;
       # ... same headers as above
   }
   ```

2. **device_config.py:** Add to `DEVICE_NETWORK_CONFIG`
   ```python
   'new_device_type': {
       'lan_ip': '192.168.X.X',
       'lan_port': 80,
       'proxy_path': '/device/NEW_DEVICE_NAME',
       'health_endpoint': '/api/status',
       'has_local_dashboard': True,
       'timeout_seconds': 5
   }
   ```

3. **device_config.py:** Add to `DEVICE_TYPE_MAPPING` and `DEVICE_TYPES`

4. **Test:** `curl http://192.168.X.X/` from VPS (must work through WireGuard)

5. **Reload:** `sudo nginx -t && sudo systemctl reload nginx`

### ESP32 Configuration

1. Add VPS WireGuard IP to trusted whitelist: `10.99.0.1`
2. Use relative paths in all JavaScript fetch calls
3. Implement proxy detection if UI changes needed
4. Ensure `/api/status` endpoint exists for health checks

### Network Requirements

- ESP32 must have static IP in LAN
- MikroTik must route VPS subnet (10.99.0.0/24) to LAN
- WireGuard AllowedIPs on VPS must include device's LAN subnet

---

## Fallback Behavior

**When VPS/Internet unavailable:**
- Direct LAN access to ESP32 works unchanged
- Full authentication required (not trusted IP)
- All functionality preserved

**When ESP32 offline:**
- VPS dashboard shows "🔴 Offline" status
- Nginx returns styled error page (@esp32_offline)
- "Back to Dashboard" link provided

---

## Security Notes

- VPS authentication protects all proxy routes
- ESP32 trusts only specific WireGuard IP (10.99.0.1)
- LAN users still require ESP32 authentication
- HTTPS terminates at VPS; internal traffic is HTTP over WireGuard (encrypted tunnel)

---

## File Locations Reference

| Component | Path |
|-----------|------|
| Nginx config | `/etc/nginx/sites-available/home-iot` |
| Flask app | `/home/kichnu/home-iot-vps/app.py` |
| Device config | `/home/kichnu/home-iot-vps/device_config.py` |
| Health check | `/home/kichnu/home-iot-vps/utils/health_check.py` |
| Dashboard template | `/home/kichnu/home-iot-vps/templates/dashboard.html` |
| Systemd service | `/etc/systemd/system/home-iot.service` |
| WireGuard config | `/etc/wireguard/wg0.conf` |