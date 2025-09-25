#!/bin/bash
LOG_DIR="/home/kichnu/tap_off_water-vps"
LOG_FILE="$LOG_DIR/app.log"

# Usuń logi starsze niż 7 dni
find "$LOG_DIR" -name "app.log*" -type f -mtime +7 -delete

# Opcjonalnie: wyczyść duży plik app.log jeśli > 50MB
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt 52428800 ]; then
    # Zostaw ostatnie 1000 linii
    tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

echo "$(date): Log cleanup completed" >> "$LOG_DIR/cleanup_logs.log"
