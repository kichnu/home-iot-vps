# Backup & Restore Guide

Comprehensive backup strategies for Home IoT Platform.

## Backup Strategy

### What to Backup

1. **Database** (`water_events.db`) - Critical data
2. **Configuration** (`.env`) - Credentials and settings
3. **Logs** (`app.log`) - For debugging (optional)
4. **Application code** (Git handles this)

### Backup Frequency

| Data | Frequency | Retention | Priority |
|------|-----------|-----------|----------|
| Database | Daily | 30 days | Critical |
| .env | On change | Forever | Critical |
| Logs | Weekly | 7 days | Low |

## Manual Backup

### Quick Backup
```bash
cd /opt/home-iot

# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup database
cp water_events.db backups/$(date +%Y%m%d)/water_events.db

# Backup .env
cp .env backups/$(date +%Y%m%d)/.env

# Backup logs (optional)
cp app.log backups/$(date +%Y%m%d)/app.log

# Create tarball
tar -czf backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    water_events.db .env app.log

echo "✅ Backup created: backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
Verify Backup
bash# Check backup integrity
tar -tzf backups/backup_YYYYMMDD_HHMMSS.tar.gz

# Check database file
sqlite3 backups/YYYYMMDD/water_events.db "PRAGMA integrity_check;"
Automated Backup
Daily Backup Script
bashcat > /opt/home-iot/backup_daily.sh << 'SCRIPT'
#!/bin/bash

# Configuration
APP_DIR="/opt/home-iot"
BACKUP_DIR="/backup/home-iot"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup filename with timestamp
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"

# Create backup
cd "$APP_DIR"
tar -czf "$BACKUP_FILE" \
    water_events.db \
    .env \
    app.log 2>/dev/null

# Check backup was created
if [ -f "$BACKUP_FILE" ]; then
    echo "$(date): ✅ Backup created: $BACKUP_FILE" >> "$APP_DIR/backup.log"
    
    # Remove old backups
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    echo "$(date): 🧹 Old backups cleaned (>$RETENTION_DAYS days)" >> "$APP_DIR/backup.log"
else
    echo "$(date): ❌ Backup failed!" >> "$APP_DIR/backup.log"
    exit 1
fi

# Report backup size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "$(date): 📊 Backup size: $SIZE" >> "$APP_DIR/backup.log"
SCRIPT

chmod +x /opt/home-iot/backup_daily.sh
Schedule with Cron
bash# Add to crontab
crontab -e

# Add this line (runs daily at 04:00)
0 4 * * * /opt/home-iot/backup_daily.sh
Offsite Backup
Backup to Remote Server (rsync)
bash# Install rsync
sudo apt install -y rsync

# Create backup sync script
cat > /opt/home-iot/backup_remote.sh << 'SCRIPT'
#!/bin/bash

BACKUP_DIR="/backup/home-iot"
REMOTE_USER="user"
REMOTE_HOST="backup-server.com"
REMOTE_DIR="/backups/home-iot/"

# Sync backups to remote server
rsync -avz --delete \
    "$BACKUP_DIR/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

if [ $? -eq 0 ]; then
    echo "$(date): ✅ Remote backup synced" >> /opt/home-iot/backup.log
else
    echo "$(date): ❌ Remote backup failed" >> /opt/home-iot/backup.log
fi
SCRIPT

chmod +x /opt/home-iot/backup_remote.sh

# Schedule (weekly on Sunday at 05:00)
crontab -e
# Add: 0 5 * * 0 /opt/home-iot/backup_remote.sh
Backup to Cloud Storage
Example using AWS S3:
bash# Install AWS CLI
sudo apt install -y awscli

# Configure AWS credentials
aws configure

# Backup to S3
aws s3 sync /backup/home-iot/ s3://your-bucket/home-iot-backups/
Restore Procedures
Restore from Local Backup
bash# 1. Stop service
sudo systemctl stop home-iot

# 2. Backup current state (just in case)
cd /opt/home-iot
cp water_events.db water_events.db.pre-restore

# 3. Extract backup
tar -xzf backups/backup_YYYYMMDD_HHMMSS.tar.gz

# 4. Verify database
sqlite3 water_events.db "PRAGMA integrity_check;"
sqlite3 water_events.db "SELECT COUNT(*) FROM water_events;"

# 5. Restart service
sudo systemctl start home-iot

# 6. Verify
sudo systemctl status home-iot
curl https://your-domain.com/health
Restore Specific Table/Data
bash# Restore only specific events (example: last week)
sqlite3 backup.db << EOF
ATTACH DATABASE 'water_events.db' AS current;
INSERT INTO current.water_events 
SELECT * FROM water_events 
WHERE received_at > datetime('now', '-7 days');
EOF
Emergency Restore
If system is completely broken:
bash# 1. Reinstall application (see DEPLOY.md)

# 2. Restore database only
cd /opt/home-iot
cp /backup/path/to/water_events.db ./

# 3. Recreate .env from backup
cp /backup/path/to/.env ./
chmod 600 .env

# 4. Start service
sudo systemctl start home-iot
Database Management
Compact Database
bash# Vacuum database (reclaim space)
sqlite3 /opt/home-iot/water_events.db "VACUUM;"

# Reindex
sqlite3 /opt/home-iot/water_events.db "REINDEX;"

# Check size before/after
ls -lh water_events.db
Export Data
bash# Export to CSV
sqlite3 -header -csv water_events.db \
    "SELECT * FROM water_events;" > events_export.csv

# Export to JSON
sqlite3 water_events.db << EOF
.mode json
.output events_export.json
SELECT * FROM water_events;
.quit
EOF
Migrate to New Server
bash# On old server:
cd /opt/home-iot
tar -czf migration_backup.tar.gz water_events.db .env

# Transfer to new server:
scp migration_backup.tar.gz user@new-server:/opt/home-iot/

# On new server (after installing app):
cd /opt/home-iot
tar -xzf migration_backup.tar.gz
sudo systemctl start home-iot
Monitoring Backups
Check Backup Status
bash# View backup log
tail -50 /opt/home-iot/backup.log

# List recent backups
ls -lht /backup/home-iot/ | head -10

# Check total backup size
du -sh /backup/home-iot/

# Count backups
ls /backup/home-iot/backup_*.tar.gz | wc -l
Alert on Backup Failures
bash# Add to backup script
if [ $? -ne 0 ]; then
    echo "Backup failed!" | mail -s "Home IoT Backup Failed" admin@example.com
fi
Best Practices

Test Restores Regularly - Verify backups work
Multiple Locations - Local + offsite
Encrypted Backups - For sensitive data
Monitor Backup Size - Detect issues early
Document Recovery - Keep recovery procedures accessible
Version Control Config - Keep .env.example in git

Troubleshooting
Corrupted Database
bash# Try recovery
sqlite3 water_events.db ".recover" | sqlite3 recovered.db

# If that fails, restore from backup
cp backups/YYYYMMDD/water_events.db water_events.db
Large Database
bash# Check size
du -h water_events.db

# Clean old data (keep last 90 days)
sqlite3 water_events.db << EOF
DELETE FROM water_events 
WHERE received_at < datetime('now', '-90 days');
VACUUM;
EOF