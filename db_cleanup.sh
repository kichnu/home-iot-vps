#!/bin/bash

# Konfiguracja
DB_PATH="/home/kichnu/tap_off_water-vps/water_events.db"
LOG_FILE="/home/kichnu/tap_off_water-vps/cleanup.log"
RETENTION_DAYS=60

# Sprawdź czy plik bazy istnieje
if [ ! -f "$DB_PATH" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR - Database file not found: $DB_PATH" >> "$LOG_FILE"
    exit 1
fi

# Zapisz rozmiar pliku przed cleanup
SIZE_BEFORE=$(stat -c%s "$DB_PATH")

OLD_RECORDS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM water_events WHERE received_at < datetime('now', '-$RETENTION_DAYS days');")

if [ "$OLD_RECORDS" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): INFO - No records older than $RETENTION_DAYS days found, skipping cleanup" >> "$LOG_FILE"
    exit 0
fi

# Wykonaj cleanup z obsługą błędów
sqlite3 "$DB_PATH" << EOF
.timeout 30000
DELETE FROM water_events WHERE received_at < datetime('now', '-$RETENTION_DAYS days');
VACUUM;
ANALYZE;
EOF

# Sprawdź czy operacja się powiodła
if [ $? -eq 0 ]; then
    SIZE_AFTER=$(stat -c%s "$DB_PATH")
    DELETED_COUNT=$(sqlite3 "$DB_PATH" "SELECT changes();")
    
    echo "$(date '+%Y-%m-%d %H:%M:%S'): SUCCESS - Database cleanup completed" >> "$LOG_FILE"
    echo "  - Records older than $RETENTION_DAYS days removed" >> "$LOG_FILE"
    echo "  - File size: $SIZE_BEFORE -> $SIZE_AFTER bytes" >> "$LOG_FILE"
    echo "  - Space saved: $((SIZE_BEFORE - SIZE_AFTER)) bytes" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR - Database cleanup failed" >> "$LOG_FILE"
    exit 1
fi
