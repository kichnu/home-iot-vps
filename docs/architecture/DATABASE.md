Complete database schema and design decisions for Home IoT Platform.

## Overview

Home IoT Platform uses **SQLite** with a single-table approach for multi-device support.

**Rationale:**
- ✅ Simple schema management
- ✅ Easy backups (single file)
- ✅ No server required
- ✅ Flexible for IoT workloads
- ✅ Sufficient for 100K+ events

## Schema

### Main Table: `water_events`

```sql
CREATE TABLE water_events (
    -- Core columns (all devices)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    device_type TEXT DEFAULT NULL,
    timestamp TEXT NOT NULL,
    unix_time INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    system_status TEXT NOT NULL,
    received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    client_ip TEXT,
    
    -- Water system specific
    volume_ml INTEGER DEFAULT NULL,
    time_gap_1 INTEGER DEFAULT NULL,
    time_gap_2 INTEGER DEFAULT NULL,
    water_trigger_time INTEGER DEFAULT NULL,
    pump_duration INTEGER DEFAULT NULL,
    pump_attempts INTEGER DEFAULT NULL,
    gap1_fail_sum INTEGER DEFAULT NULL,
    gap2_fail_sum INTEGER DEFAULT NULL,
    water_fail_sum INTEGER DEFAULT NULL,
    algorithm_data TEXT DEFAULT NULL,
    last_reset_timestamp INTEGER DEFAULT NULL,
    water_status TEXT DEFAULT NULL,
    
    -- Temperature sensor specific
    temperature REAL DEFAULT NULL,
    humidity REAL DEFAULT NULL,
    
    -- Security system specific
    zone_status TEXT DEFAULT NULL,
    motion_detected BOOLEAN DEFAULT NULL
);
```

### Indexes

```sql
CREATE INDEX idx_device_id ON water_events(device_id);
CREATE INDEX idx_device_type ON water_events(device_type);
CREATE INDEX idx_device_id_type ON water_events(device_id, device_type);
CREATE INDEX idx_timestamp ON water_events(unix_time);
CREATE INDEX idx_event_type ON water_events(event_type);
CREATE INDEX idx_received_at ON water_events(received_at);
```

## Column Reference

### Core Columns (All Devices)

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| `id` | INTEGER | Auto-increment primary key | Yes |
| `device_id` | TEXT | Unique device identifier | Yes |
| `device_type` | TEXT | Device category (e.g., 'water_system') | Auto |
| `timestamp` | TEXT | ISO 8601 timestamp from device | Yes |
| `unix_time` | INTEGER | Unix timestamp for queries | Yes |
| `event_type` | TEXT | Event category | Yes |
| `system_status` | TEXT | OK or ERROR | Yes |
| `received_at` | DATETIME | Server receipt time | Auto |
| `client_ip` | TEXT | Request IP address | Auto |

### Water System Columns

| Column | Type | Description |
|--------|------|-------------|
| `volume_ml` | INTEGER | Water volume dispensed (ml) |
| `pump_duration` | INTEGER | Pump run time (ms) |
| `pump_attempts` | INTEGER | Number of pump attempts |
| `time_gap_1` | INTEGER | Sensor 1 delay (ms) |
| `time_gap_2` | INTEGER | Sensor 2 delay (ms) |
| `water_trigger_time` | INTEGER | Water detection delay (ms) |
| `gap1_fail_sum` | INTEGER | Sensor 1 failure count |
| `gap2_fail_sum` | INTEGER | Sensor 2 failure count |
| `water_fail_sum` | INTEGER | Water detection failure count |
| `algorithm_data` | TEXT | JSON with detailed algorithm data |
| `last_reset_timestamp` | INTEGER | Statistics reset timestamp |
| `water_status` | TEXT | OK, LOW, BOTH_LOW, etc. |

### Temperature Sensor Columns

| Column | Type | Description |
|--------|------|-------------|
| `temperature` | REAL | Temperature (°C) |
| `humidity` | REAL | Humidity (%) |

### Security System Columns

| Column | Type | Description |
|--------|------|-------------|
| `zone_status` | TEXT | ARMED, DISARMED, TRIGGERED, etc. |
| `motion_detected` | BOOLEAN | 1 if motion detected, 0 otherwise |

## Queries

### Common Queries

```sql
-- Count events per device
SELECT device_id, COUNT(*) as events
FROM water_events
GROUP BY device_id;

-- Events in last 24 hours
SELECT *
FROM water_events
WHERE received_at > datetime('now', '-24 hours')
ORDER BY received_at DESC;

-- Average temperature by device
SELECT device_id, AVG(temperature) as avg_temp
FROM water_events
WHERE temperature IS NOT NULL
GROUP BY device_id;

-- System errors
SELECT *
FROM water_events
WHERE system_status = 'ERROR'
ORDER BY received_at DESC;
```

### Performance Tips

```sql
-- Use indexes
EXPLAIN QUERY PLAN
SELECT * FROM water_events WHERE device_id = 'DOLEWKA';
-- Should show "USING INDEX idx_device_id"

-- Limit results
SELECT * FROM water_events
ORDER BY received_at DESC
LIMIT 100;  -- Always use LIMIT

-- Use unix_time for date ranges (faster than text timestamp)
SELECT * FROM water_events
WHERE unix_time BETWEEN 1728000000 AND 1728086400;
```

## Maintenance

### Cleanup Old Data

```sql
-- Delete events older than 90 days
DELETE FROM water_events
WHERE received_at < datetime('now', '-90 days');

-- Reclaim space
VACUUM;
```

### Optimize Database

```sql
-- Rebuild indexes
REINDEX;

-- Update statistics
ANALYZE;

-- Check integrity
PRAGMA integrity_check;
```

## Migrations

### Adding New Device Type

1. Add columns to schema (in `app.py - init_database()`)
2. Restart application (auto-migration runs)
3. Update `device_config.py`
4. Update `queries_config.py`

Example migration:
```python
# In init_database():
new_columns = [
    'soil_moisture INTEGER DEFAULT NULL',
    'battery_level REAL DEFAULT NULL'
]
```

### Schema Versioning

Currently no formal migration system. Changes are additive:
- ✅ Adding columns: Safe (DEFAULT NULL)
- ⚠️ Renaming columns: Requires manual migration
- ❌ Deleting columns: Requires rebuild

## Backup Considerations

### Backup Strategies

```bash
# Hot backup (while running)
sqlite3 water_events.db ".backup /backup/hot_backup.db"

# Cold backup (service stopped)
cp water_events.db /backup/cold_backup.db
```

### Database Size Management

Expected growth:
- 100 events/day = ~50KB/day
- 1 year = ~18MB
- 10 years = ~180MB

With cleanup (90 day retention):
- Stable at ~15MB

## Related Documentation

- [Multi-Device Guide](../guides/MULTI-DEVICE.md) - Adding device types
- [API Reference](API.md) - Data input validation
- [Backup Guide](../guides/BACKUP-RESTORE.md) - Database backups

---

**Schema version:** 2.0 (Multi-device architecture)
**Last updated:** 2025-10-04