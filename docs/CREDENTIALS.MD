# Credentials Management Guide

Kompletny przewodnik zarządzania credentials dla ESP32 Water System Logger.

## Spis treści

- [Generowanie credentials](#generowanie-credentials)
- [Rotacja credentials](#rotacja-credentials)
- [Środowiska deployment](#środowiska-deployment)
- [Backup i recovery](#backup-i-recovery)
- [Security audit](#security-audit)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)

## Generowanie credentials

### Generowanie nowych credentials

Użyj dedykowanego generatora dla bezpiecznych credentials:

```bash
# Podstawowe generowanie
python generate_credentials.py --output display

# Generowanie dla development (.env file)
python generate_credentials.py --output env

# Generowanie dla production (systemd)
python generate_credentials.py --output systemd

# Generowanie z custom parametrami
python generate_credentials.py \
    --output both \
    --password-length 40 \
    --token-format sha256 \
    --no-symbols
```

### Typy credentials

#### Admin Password
- **Długość**: 32-64 znaki
- **Format**: Alphanumeric + symbole (opcjonalnie)
- **Użycie**: Logowanie do admin panel
- **Zmienna**: `WATER_SYSTEM_ADMIN_PASSWORD`

```bash
# Silne hasło (z symbolami)
python generate_credentials.py --password-length 40

# Hasło bez symboli (łatwiejsze w deployment)
python generate_credentials.py --no-symbols
```

#### API Token
- **Długość**: 64 znaki (hex) lub 32 bytes
- **Format**: hex, base64, sha256, uuid
- **Użycie**: Autoryzacja ESP32 API calls
- **Zmienna**: `WATER_SYSTEM_API_TOKEN`

```bash
# Różne formaty tokenów
python generate_credentials.py --token-format hex      # Default
python generate_credentials.py --token-format base64
python generate_credentials.py --token-format sha256
python generate_credentials.py --token-format uuid
```

#### Flask Secret Key
- **Długość**: 64 znaki hex
- **Użycie**: Sesje Flask, CSRF protection
- **Zmienna**: `WATER_SYSTEM_SECRET_KEY`

### Manual generation (dla advanced users)

```bash
# Admin password (32 chars)
openssl rand -base64 32 | tr -d '=' | head -c 32

# API token (64 chars hex)
openssl rand -hex 32

# UUID token
uuidgen

# SHA256 token
echo "salt$(date +%s)$(openssl rand -hex 32)" | sha256sum | cut -d' ' -f1
```

## Rotacja credentials

### Development environment

```bash
# 1. Backup obecnych credentials
cp .env .env.backup.$(date +%s)

# 2. Wygeneruj nowe credentials
python generate_credentials.py --output env

# 3. Restart aplikacji
python app.py
```

### Production environment

#### Metoda 1: Zero-downtime rotation

```bash
# 1. Backup obecnej konfiguracji
sudo cp /etc/systemd/system/water-system.service.d/override.conf \
       /etc/systemd/system/water-system.service.d/override.conf.backup.$(date +%s)

# 2. Wygeneruj nowe credentials
python generate_credentials.py --output systemd

# 3. Aktualizuj systemd override
sudo cp systemd-override.conf /etc/systemd/system/water-system.service.d/override.conf
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf

# 4. Reload i restart
sudo systemctl daemon-reload
sudo systemctl restart water-system

# 5. Weryfikuj
sudo systemctl status water-system
curl -s https://your-domain.com/health
```

#### Metoda 2: Staged rotation (dla większych deploymentów)

```bash
# 1. Przygotuj nowe credentials w tymczasowym pliku
python generate_credentials.py --output systemd
mv systemd-override.conf systemd-override.new

# 2. Zaplanuj deployment window
echo "Planning credential rotation for $(date)"

# 3. W maintenance window:
sudo systemctl stop water-system
sudo cp systemd-override.new /etc/systemd/system/water-system.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl start water-system

# 4. Verify
sudo journalctl -u water-system --lines=10
```

### Rotacja w czasie scheduled maintenance

Utwórz skrypt rotacji credentials:

```bash
#!/bin/bash
# rotate_credentials.sh

set -e

BACKUP_DIR="/home/$(whoami)/credential-backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== Credential Rotation Started: $DATE ==="

# Backup
mkdir -p "$BACKUP_DIR"
sudo cp /etc/systemd/system/water-system.service.d/override.conf \
        "$BACKUP_DIR/override.conf.$DATE"

# Generate new credentials
cd /home/$(whoami)/water-system-logger
source venv/bin/activate
python generate_credentials.py --output systemd --no-symbols

# Deploy
sudo cp systemd-override.conf /etc/systemd/system/water-system.service.d/override.conf
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart water-system

# Verify
sleep 5
if curl -s https://your-domain.com/health > /dev/null; then
    echo "✅ Credential rotation successful"
    # Cleanup old backups (keep last 10)
    ls -t "$BACKUP_DIR"/override.conf.* | tail -n +11 | xargs rm -f
else
    echo "❌ Health check failed - rolling back"
    sudo cp "$BACKUP_DIR/override.conf.$DATE" \
            /etc/systemd/system/water-system.service.d/override.conf
    sudo systemctl daemon-reload
    sudo systemctl restart water-system
    exit 1
fi

echo "=== Credential Rotation Completed: $(date) ==="
```

## Środowiska deployment

### Development (.env file)

```bash
# Setup
python generate_credentials.py --output env

# Struktura
ls -la .env*
# -rw------- 1 user user  874 .env          # Real credentials (git ignored)
# -rw-r--r-- 1 user user 1270 .env.example  # Template (committed)

# Test
source venv/bin/activate
python app.py
```

### Staging (systemd environment)

```bash
# Generate staging credentials (different from prod!)
python generate_credentials.py --output systemd

# Deploy to staging systemd
sudo mkdir -p /etc/systemd/system/water-system-staging.service.d/
sudo cp systemd-override.conf /etc/systemd/system/water-system-staging.service.d/override.conf
```

### Production (systemd environment + secrets management)

```bash
# Production-grade deployment
sudo mkdir -p /etc/water-system/
sudo chmod 750 /etc/water-system/

# Generate strong production credentials
python generate_credentials.py \
    --output systemd \
    --password-length 48 \
    --token-format sha256 \
    --no-symbols

# Deploy with proper permissions
sudo cp systemd-override.conf /etc/systemd/system/water-system.service.d/override.conf
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf
sudo chown root:root /etc/systemd/system/water-system.service.d/override.conf
```

### Multi-environment configuration

Dla organizacji z wieloma środowiskami:

```bash
# Directory structure
/etc/water-system/
├── environments/
│   ├── dev.env
│   ├── staging.env
│   └── prod.env
└── scripts/
    ├── deploy-env.sh
    └── rotate-credentials.sh

# Environment-specific deployment
sudo ./deploy-env.sh prod
```

## Backup i recovery

### Backup credentials

```bash
#!/bin/bash
# backup_credentials.sh

BACKUP_DIR="/secure/backups/water-system"
DATE=$(date +%Y%m%d_%H%M%S)
HOSTNAME=$(hostname)

mkdir -p "$BACKUP_DIR"

# Backup systemd environment
if [ -f "/etc/systemd/system/water-system.service.d/override.conf" ]; then
    sudo cp /etc/systemd/system/water-system.service.d/override.conf \
            "$BACKUP_DIR/override.conf.$HOSTNAME.$DATE"
fi

# Backup .env (for development)
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env.$HOSTNAME.$DATE"
fi

# Encrypt backups
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/override.conf.$HOSTNAME.$DATE"
rm "$BACKUP_DIR/override.conf.$HOSTNAME.$DATE"

echo "✅ Credentials backed up to: $BACKUP_DIR"
echo "🔐 Encrypted file: override.conf.$HOSTNAME.$DATE.gpg"
```

### Recovery procedures

```bash
# Recovery from backup
BACKUP_FILE="override.conf.server01.20250906_120000.gpg"

# Decrypt
gpg --decrypt "$BACKUP_FILE" > override.conf.recovered

# Restore
sudo cp override.conf.recovered /etc/systemd/system/water-system.service.d/override.conf
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart water-system

# Verify
sudo systemctl status water-system
```

### Emergency credential reset

```bash
#!/bin/bash
# emergency_reset.sh

echo "🚨 EMERGENCY CREDENTIAL RESET"
echo "This will generate new credentials and restart the service"
read -p "Continue? (yes/NO): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

# Generate emergency credentials
python generate_credentials.py --output both --password-length 32

# Deploy immediately
sudo cp systemd-override.conf /etc/systemd/system/water-system.service.d/override.conf
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart water-system

# Show new credentials for immediate use
echo ""
echo "🔑 NEW CREDENTIALS GENERATED:"
echo "Check .env file for development access"
echo "Production credentials deployed to systemd"

# Health check
sleep 5
if curl -s https://your-domain.com/health > /dev/null; then
    echo "✅ Emergency reset successful"
else
    echo "❌ Health check failed - manual intervention required"
fi
```

## Security audit

### Credential strength audit

```bash
#!/bin/bash
# audit_credentials.sh

echo "=== CREDENTIAL STRENGTH AUDIT ==="

# Check .env file (development)
if [ -f ".env" ]; then
    echo "Development environment (.env):"
    
    ADMIN_PASS=$(grep "ADMIN_PASSWORD" .env | cut -d'=' -f2)
    API_TOKEN=$(grep "API_TOKEN" .env | cut -d'=' -f2)
    
    echo "  Admin password length: ${#ADMIN_PASS}"
    echo "  API token length: ${#API_TOKEN}"
    
    # Check password complexity
    if [[ $ADMIN_PASS =~ [A-Z] ]] && [[ $ADMIN_PASS =~ [a-z] ]] && [[ $ADMIN_PASS =~ [0-9] ]]; then
        echo "  ✅ Admin password has good complexity"
    else
        echo "  ⚠️ Admin password could be stronger"
    fi
fi

# Check production environment
echo ""
echo "Production environment (systemd):"
if sudo test -f "/etc/systemd/system/water-system.service.d/override.conf"; then
    echo "  ✅ Systemd override file exists"
    echo "  Permissions: $(sudo stat -c %a /etc/systemd/system/water-system.service.d/override.conf)"
    
    if [ "$(sudo stat -c %a /etc/systemd/system/water-system.service.d/override.conf)" = "600" ]; then
        echo "  ✅ Proper file permissions"
    else
        echo "  ⚠️ File permissions should be 600"
    fi
else
    echo "  ❌ No systemd override file found"
fi

# Check for credential leaks in git
echo ""
echo "Git repository audit:"
if git log --all -S "admin" --source --all | grep -q "admin"; then
    echo "  ⚠️ Found 'admin' in git history - review needed"
else
    echo "  ✅ No obvious credential leaks in git history"
fi
```

### Access audit

```bash
# Who has access to credentials?
echo "=== ACCESS AUDIT ==="

# .env file access
if [ -f ".env" ]; then
    echo ".env file access:"
    ls -la .env
fi

# systemd file access
echo ""
echo "systemd override file access:"
sudo ls -la /etc/systemd/system/water-system.service.d/override.conf

# Process environment (check if credentials are visible in process list)
echo ""
echo "Process environment check:"
if ps aux | grep water-system | grep -q "PASSWORD\|TOKEN"; then
    echo "⚠️ Credentials visible in process list"
else
    echo "✅ Credentials not visible in process list"
fi
```

## Troubleshooting

### Common issues

#### Missing environment variables

```bash
# Symptom: Application fails to start with environment variable error
# Solution:
python generate_credentials.py --output env  # Development
# or
sudo systemctl edit water-system  # Production - add Environment= lines
```

#### Credential mismatch

```bash
# Symptom: 401 Unauthorized errors
# Debug:
sudo journalctl -u water-system | grep -i "password\|token\|unauthorized"

# Solution: Regenerate credentials
python generate_credentials.py --output both
sudo systemctl restart water-system
```

#### File permission issues

```bash
# Symptom: systemd can't read credentials
# Solution:
sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf
sudo chown root:root /etc/systemd/system/water-system.service.d/override.conf
sudo systemctl daemon-reload
```

#### Development vs Production mismatch

```bash
# Ensure environments use different credentials
# Development (.env):
WATER_SYSTEM_ADMIN_PASSWORD=dev_password_here

# Production (systemd):
Environment=WATER_SYSTEM_ADMIN_PASSWORD=prod_password_here
```

### Debug commands

```bash
# Check environment variables in systemd
sudo systemctl show water-system --property=Environment

# Check if application can read credentials
sudo -u kichnu bash -c "cd /home/kichnu/water-system-logger && source venv/bin/activate && python -c 'import os; print(\"Admin:\", bool(os.getenv(\"WATER_SYSTEM_ADMIN_PASSWORD\")))'"

# Test credential validation
curl -X POST https://your-domain.com/api/water-events \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Best practices

### Development

1. **Używaj .env files**: Nigdy nie commituj do git
2. **Różne credentials**: Dev != staging != production
3. **Regular rotation**: Co najmniej co 90 dni
4. **Monitor logs**: Sprawdzaj nieudane próby logowania

### Production

1. **systemd environment**: Bezpieczniejsze niż pliki
2. **Strong credentials**: Min. 32 znaki, mix chars
3. **File permissions**: 600 dla credential files
4. **Regular audits**: Miesięczne sprawdzenia dostępu
5. **Backup strategy**: Zaszyfrowane backupy credentials

### Security

1. **Principle of least privilege**: Tylko potrzebny dostęp
2. **No hardcoded values**: Zawsze environment variables
3. **Credential rotation**: Regularna zmiana
4. **Audit trails**: Log credential access
5. **Incident response**: Plan na compromise

### Monitoring

```bash
# Monitor failed authentication attempts
sudo journalctl -u water-system | grep -i "failed\|unauthorized" | tail -20

# Check credential age
stat /etc/systemd/system/water-system.service.d/override.conf

# Monitor unusual access patterns
sudo tail -f /var/log/nginx/water-system.access.log | grep -E "(401|403)"
```

### Automation

Ustaw cron job dla regularnej rotacji:

```bash
# Dodaj do crontab (root):
# Credential rotation - first Sunday of every month at 2 AM
0 2 * * 0 [ $(date +\%d) -le 7 ] && /home/kichnu/water-system-logger/rotate_credentials.sh >> /var/log/water-system-rotation.log 2>&1
```

## Compliance i dokumentacja

### Tracking credentials

Prowadź log zmian credentials:

```bash
# /var/log/water-system-credentials.log
2025-09-06 12:00:00 - GENERATED - Initial credentials - user:kichnu
2025-10-01 02:00:00 - ROTATED   - Scheduled rotation - auto
2025-10-15 14:30:00 - EMERGENCY - Security incident response - user:admin
```

### Documentation requirements

Dla environments produkcyjnych dokumentuj:
- Kto ma dostęp do credentials
- Kiedy były ostatnio zmieniane
- Backup procedures
- Incident response contacts
- Compliance requirements (GDPR, ISO, etc.)

---

**Note**: Ten guide zakłada standardowy deployment. Dla enterprise environments rozważ integrację z dedicated secret management systems (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault).