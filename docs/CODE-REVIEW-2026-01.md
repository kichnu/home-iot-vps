# Przegląd kodu - Styczeń 2026

## Podsumowanie

Przegląd przeprowadzony po reorganizacji aplikacji (usunięcie funkcjonalności logowania danych z ESP32).

---

## Co jest dobrze zrobione

| Obszar | Implementacja |
|--------|---------------|
| Rate limiting | Flask-Limiter z konfiguracją per-endpoint |
| Porównywanie haseł | Timing-safe `hmac.compare_digest` |
| Sesje | Database-backed z timeout i cleanup |
| Brute-force protection | Blokada IP po X nieudanych próbach |
| Reverse proxy | Obsługa X-Real-IP dla Nginx |
| Cookies | HttpOnly, SameSite=Lax, Secure=True |
| Logowanie | Zdarzenia bezpieczeństwa logowane z IP |
| Startup | Weryfikacja wymaganych zmiennych env |
| Database | Fail-safe przy błędach (nie blokuje użytkowników) |

---

## Problemy do naprawy

### PRIORYTET WYSOKI (bezpieczeństwo)

| Problem | Lokalizacja | Ryzyko | Rozwiązanie |
|---------|-------------|--------|-------------|
| Brak CSRF | `templates/*.html` | Atakujący może wykonać akcje w imieniu zalogowanego użytkownika | Dodać Flask-WTF |
| Wyciek informacji | `app.py:/health` | Ujawnia liczbę sesji, zablokowanych kont, ścieżkę do bazy | Ograniczyć dane lub zabezpieczyć endpoint |
| Brak security headers | `app.py` | XSS, clickjacking, content-type sniffing | Dodać middleware z headerami |
| SECRET_KEY auto-gen | `app.py:43` | Restart serwera = wylogowanie wszystkich użytkowników | Wymusić ustawienie w .env |

### PRIORYTET ŚREDNI (niezawodność)

| Problem | Lokalizacja | Ryzyko | Rozwiązanie |
|---------|-------------|--------|-------------|
| Brak rotacji logów | `data/logs/app.log` | Dysk się zapełni | logrotate lub RotatingFileHandler |
| requirements.txt niekompletny | `requirements.txt` | Brak `flask-limiter` w pliku | Zaktualizować plik |
| Rate limit GET+POST | `app.py:89-99` | Samo wyświetlenie /login zużywa limit | Rozdzielić limity |
| Health check niepełny | `app.py:/health` | Nie wykryje problemów z zapisem do DB | Dodać test zapisu |

### PRIORYTET NISKI (jakość kodu)

| Problem | Lokalizacja | Rozwiązanie |
|---------|-------------|-------------|
| Martwy kod | `auth/session.py:73-112` | Usunąć `is_account_locked()` |
| Niespójne nazewnictwo | `config.py` | Zmienić `WATER_SYSTEM_` na `IOT_GATEWAY_` |
| Import w funkcjach | `app.py:198,260-261` | Przenieść na początek pliku |
| Hardcoded URL | `app.py:346` | Przenieść do config |
| Brak type hints | Cały projekt | Dodać typowanie |

---

## Rekomendacje dla produkcji

### Bezpieczeństwo

```python
# 1. CSRF Protection (Flask-WTF)
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# 2. Security Headers (middleware)
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

# 3. Wymuszone SECRET_KEY
if not Config.SECRET_KEY:
    logging.critical("FATAL: SECRET_KEY must be set in production")
    sys.exit(1)
```

### Niezawodność

```python
# 1. Rotating logs
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler(
    Config.LOG_PATH,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# 2. Graceful shutdown
import signal
def handle_shutdown(signum, frame):
    logging.info("Shutting down gracefully...")
    # cleanup
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# 3. Deep health check
@app.route('/health')
def health_check():
    # Test DB write
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
    except:
        return jsonify({'status': 'unhealthy', 'db': 'error'}), 503

    return jsonify({'status': 'healthy'}), 200
```

### Operacje

```bash
# /etc/logrotate.d/home-iot
/opt/home-iot/data/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 kichnu kichnu
}
```

```ini
# Systemd hardening - /etc/systemd/system/home-iot.service
[Service]
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/home-iot/data
```

---

## Priorytet wdrożenia

### Faza 1 - Krytyczne (natychmiast)
- [ ] CSRF protection
- [ ] Security headers
- [ ] Wymuszone SECRET_KEY

### Faza 2 - Ważne (wkrótce)
- [ ] Rotacja logów (logrotate)
- [ ] Zaktualizować requirements.txt
- [ ] Usunąć martwy kod
- [ ] Ograniczyć /health endpoint

### Faza 3 - Usprawnienia (później)
- [ ] Refaktoring nazewnictwa env vars
- [ ] Type hints
- [ ] Monitoring (Prometheus)
- [ ] Graceful shutdown
- [ ] Systemd hardening

---

## Pliki do modyfikacji

| Plik | Zmiany |
|------|--------|
| `app.py` | Security headers, CSRF, SECRET_KEY check, health endpoint |
| `requirements.txt` | Dodać flask-limiter, flask-wtf |
| `auth/session.py` | Usunąć `is_account_locked()` |
| `config.py` | Zmiana prefixu env vars (opcjonalnie) |
| `templates/login.html` | CSRF token w formularzu |

---

## Status

- [x] Przegląd przeprowadzony
- [ ] Faza 1 - w trakcie
- [ ] Faza 2
- [ ] Faza 3
