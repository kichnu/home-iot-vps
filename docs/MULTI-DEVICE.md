# Multi-Device IoT Platform Architecture

Comprehensive guide to the multi-device capabilities of the Water System Logger.

## Architecture Overview

The system evolved from single-device (DOLEWKA) water monitoring to a flexible multi-device IoT platform while maintaining backward compatibility and operational simplicity.

### Core Principles

1. **Single Service Deployment** - One Flask app, one database, one systemd service
2. **Configuration Over Code** - New devices added through config, not code changes  
3. **Auto-Discovery** - Database-driven device type detection
4. **Contextual Interfaces** - Device-specific admin panels and queries
5. **Backwards Compatibility** - Existing DOLEWKA functionality unchanged

### Database Schema Evolution
```sql
-- Single table approach with device-specific columns
water_events:
  -- Core columns (all devices)
  id, device_id, device_type, timestamp, received_at, event_type, system_status
  
  -- Water system columns (NULL for other devices)
  volume_ml, pump_duration, time_gap_1, gap1_fail_sum, algorithm_data
  
  -- Temperature sensor columns (NULL for others)
  temperature, humidity
  
  -- Security system columns (NULL for others)  
  zone_status, motion_detected