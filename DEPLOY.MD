# Przewodnik Wdrożenia VPS - ESP32 Water System Logger

Kompletny przewodnik wdrożenia aplikacji na serwerze VPS Ubuntu/Debian z nginx, SSL i systemd.

## Wymagania

- **VPS**: Ubuntu 20.04+ lub Debian 11+
- **Domena**: DNS skonfigurowany na IP serwera
- **Porty**: 80 (HTTP), 443 (HTTPS) otwarte
- **Dostęp**: sudo/root na serwerze

## Krok 1: Przygotowanie systemu

### Aktualizacja systemu
```bash
sudo apt update && sudo apt upgrade -y
```

### Instalacja podstawowych narzędzi
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    ufw
```

### Sprawdzenie wersji Python
```bash
python3 --version  # Wymaga 3.8+
```

## Krok 2: Przygotowanie aplikacji

### Sklonowanie repozytorium
```bash
cd /home/$(whoami)
git clone https://github.com/yourusername/water-system-logger.git
cd water-system-logger
```

### Utworzenie środowiska wirtualnego
```bash
python3 -m venv venv
source venv/bin/activate
```

### Instalacja zależności
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Sprawdzenie instalacji
```bash
python -c "import flask; print(f'Flask {flask.__version__}')"
```

## Krok 3: Konfiguracja aplikacji

### Edycja ścieżek w app.py
```bash
# Sprawdź aktualne ścieżki
grep -n "DATABASE_PATH\|LOG_PATH" app.py

# Jeśli potrzeba, dostosuj ścieżki do aktualnego katalogu
# DATABASE_PATH = '/home/yourusername/water-system-logger/water_events.db'
# LOG_PATH = '/home/yourusername/water-system-logger/app.log'
```

### Test aplikacji
```bash
# Test uruchomienia (zatrzyma się po 10 sekund)
timeout 10s python app.py

# Sprawdź czy pliki zostały utworzone
ls -la water_events.db app.log 2>/dev/null || echo "Pliki utworzą się przy pierwszym uruchomieniu"
```

## Krok 4: Konfiguracja nginx

### Utworzenie konfiguracji nginx
```bash
sudo tee /etc/nginx/sites-available/water-system > /dev/null <<'EOF'
server {
    listen 80;
    server_name your-domain.com;  # ZMIEŃ NA SWOJĄ DOMENĘ
    
    # Real IP headers
    real_ip_header X-Real-IP;
    set_real_ip_from 127.0.0.1;

    # ESP32 API (port 5000)
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        client_max_body_size 1M;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # Admin Panel (port 5001)
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        client_max_body_size 10M;
    }
    
    # Logs
    access_log /var/log/nginx/water-system.access.log;
    error_log /var/log/nginx/water-system.error.log;
}
EOF
```

### Aktywacja konfiguracji nginx
```bash
# Wyłącz domyślną konfigurację
sudo rm -f /etc/nginx/sites-enabled/default

# Włącz nową konfigurację
sudo ln -s /etc/nginx/sites-available/water-system /etc/nginx/sites-enabled/

# Sprawdź składnię
sudo nginx -t

# Restart nginx
sudo systemctl reload nginx
```

## Krok 5: Konfiguracja SSL (Let's Encrypt)

### Uzyskanie certyfikatu SSL
```bash
# ZMIEŃ your-domain.com NA SWOJĄ DOMENĘ I EMAIL
sudo certbot --nginx -d your-domain.com \
    --non-interactive \
    --agree-tos \
    --email your-email@example.com \
    --redirect
```

### Sprawdzenie certyfikatu
```bash
sudo certbot certificates
```

### Test auto-renewal
```bash
sudo certbot renew --dry-run
```

## Krok 6: Konfiguracja systemd service

### Utworzenie wrapper script
```bash
cat > start_water_system.sh << 'EOF'
#!/bin/bash
cd /home/$(whoami)/water-system-logger
source venv/bin/activate
exec python app.py
EOF

chmod +x start_water_system.sh
```

### Utworzenie systemd service
```bash
# ZMIEŃ ścieżki na swoje
sudo tee /etc/systemd/system/water-system.service > /dev/null <<EOF
[Unit]
Description=ESP32-C3 Water System VPS Logger
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)/water-system-logger
ExecStart=/home/$(whoami)/water-system-logger/start_water_system.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/home/$(whoami)/water-system-logger

[Install]
WantedBy=multi-user.target
EOF
```

### Aktywacja usługi
```bash
# Przeładuj konfigurację systemd
sudo systemctl daemon-reload

# Włącz automatyczny start
sudo systemctl enable water-system

# Uruchom usługę
sudo systemctl start water-system

# Sprawdź status
sudo systemctl status water-system
```

## Krok 7: Konfiguracja firewall (opcjonalnie)

```bash
# Podstawowa konfiguracja UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Zezwól na SSH, HTTP, HTTPS
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Włącz firewall
sudo ufw --force enable

# Sprawdź status
sudo ufw status
```

## Krok 8: Finalne testy

### Test wszystkich endpointów
```bash
# Test przekierowania HTTP → HTTPS
curl -I http://your-domain.com/health

# Test HTTPS health check
curl https://your-domain.com/health

# Test admin panel
curl -I https://your-domain.com/login

# Test ESP32 API (oczekiwany 401)
curl -I https://your-domain.com/api/water-events -X POST
```

### Sprawdzenie usług
```bash
# Status aplikacji
sudo systemctl status water-system

# Status nginx
sudo systemctl status nginx

# Logi aplikacji
sudo journalctl -u water-system --lines=10

# Logi nginx
sudo tail -5 /var/log/nginx/water-system.error.log
```

## Zarządzanie w trybie produkcyjnym

### Podstawowe komendy
```bash
# Restart aplikacji
sudo systemctl restart water-system

# Sprawdzenie logów na żywo
sudo journalctl -u water-system -f

# Restart nginx
sudo systemctl reload nginx

# Sprawdzenie portów
netstat -tln | grep ':80\|:443\|:5000\|:5001'
```

### Aktualizacja aplikacji
```bash
cd /home/$(whoami)/water-system-logger
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart water-system
```

### Odnowienie certyfikatu SSL
```bash
# Test renewal
sudo certbot renew --dry-run

# Force renewal (jeśli potrzeba)
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

## Backup i monitoring

### Backup bazy danych
```bash
# Utworzenie backup script
cat > backup_database.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/$(whoami)/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /home/$(whoami)/water-system-logger/water_events.db \
   $BACKUP_DIR/water_events_$DATE.db
# Usuń backupy starsze niż 30 dni
find $BACKUP_DIR -name "water_events_*.db" -mtime +30 -delete
EOF

chmod +x backup_database.sh

# Dodaj do crontab (backup co 24h)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/$(whoami)/water-system-logger/backup_database.sh") | crontab -
```

### Monitoring logów
```bash
# Sprawdzenie błędów aplikacji
sudo journalctl -u water-system --since "1 hour ago" | grep -i error

# Sprawdzenie dostępu nginx
sudo tail -100 /var/log/nginx/water-system.access.log | grep -v "200\|301\|302"

# Sprawdzenie wykorzystania zasobów
sudo systemctl show water-system --property=MemoryCurrent
```

## Rozwiązywanie problemów

### Aplikacja nie startuje
```bash
# Sprawdź logi
sudo journalctl -u water-system --lines=20

# Sprawdź ścieżki w service
sudo cat /etc/systemd/system/water-system.service

# Test ręczny
cd /home/$(whoami)/water-system-logger
source venv/bin/activate
python app.py
```

### Nginx 502 Bad Gateway
```bash
# Sprawdź czy aplikacja działa
netstat -tln | grep ':5000\|:5001'

# Restart aplikacji
sudo systemctl restart water-system

# Sprawdź logi nginx
sudo tail -10 /var/log/nginx/water-system.error.log
```

### Problemy z SSL
```bash
# Sprawdź certyfikat
sudo certbot certificates

# Test konfiguracji nginx
sudo nginx -t

# Sprawdź daty certyfikatu
echo | openssl s_client -connect your-domain.com:443 | openssl x509 -noout -dates
```

## Bezpieczeństwo

### Zmiana domyślnych haseł
```bash
# Edytuj app.py i zmień:
# ADMIN_PASSWORD = 'twoje_bezpieczne_haslo'
# VALID_TOKEN = 'twoj_bezpieczny_token_esp32'

# Po zmianie restart aplikacji
sudo systemctl restart water-system
```

### Monitoring bezpieczeństwa
```bash
# Sprawdzenie nieudanych prób logowania
sudo journalctl -u water-system | grep -i "failed\|locked\|invalid"

# Sprawdzenie podejrzanego ruchu
sudo grep "401\|403\|404" /var/log/nginx/water-system.access.log | tail -10
```

## URLs produkcyjne

Po wdrożeniu aplikacja będzie dostępna pod:

- **Admin Panel**: `https://your-domain.com/`
- **ESP32 API**: `https://your-domain.com/api/`
- **Health Check**: `https://your-domain.com/health`

Zmień `your-domain.com` na swoją rzeczywistą domenę w wszystkich plikach konfiguracyjnych.