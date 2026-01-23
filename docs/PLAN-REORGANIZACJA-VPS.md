# Plan reorganizacji aplikacji VPS

## Cel

Usunięcie funkcjonalności bazy danych i odbierania logów z ESP32.
Pozostawienie tylko proxy do urządzeń IoT przez WireGuard z autentykacją.

---

## 1. PLIKI DO USUNIĘCIA

### 1.1 Katalogi (całe)

```
/opt/home-iot/tools/                    # Zarządzanie credentials dla logów
/opt/home-iot/data/logs/                # Logi db_cleanup
/opt/home-iot/data/database/            # Baza SQLite water_events.db
/opt/home-iot/examples/                 # Przykłady
/opt/home-iot/scripts/                  # Skrypty do czyszczenia logów
/opt/home-iot/validators/               # Walidatory (event, sql)
```

### 1.2 Pliki Python

```
/opt/home-iot/queries_config.py         # Konfiguracja zapytań SQL
/opt/home-iot/utils/export.py           # Eksport CSV/JSON
/opt/home-iot/validators/event_validator.py  # Walidacja zdarzeń z ESP32
```

### 1.3 Templates

```
/opt/home-iot/templates/admin.html      # Panel logów i statystyk (~54KB)
```

---

## 2. PLIKI DO MODYFIKACJI

### 2.1 `app.py` - usunąć endpointy

| Linie (około) | Endpoint | Funkcja |
|---------------|----------|---------|
| 117-209 | `POST /api/water-events` | `receive_water_event()` |
| 211-257 | `GET /api/events` | `get_events()` |
| 259-314 | `GET /api/stats` | `get_stats()` |
| 509-534 | `GET /admin/<device_type>` | `device_context_admin()` |
| 548-589 | `POST /api/admin-query` | `admin_execute_query()` |
| 591-622 | `GET /api/admin-device-query/...` | `admin_device_query()` |
| 624-644 | `GET /api/available-queries/...` | `get_device_queries()` |
| 646-671 | `GET /api/admin-quick-query/...` | `admin_quick_query()` |
| 673-697 | `GET /api/quick-export/...` | `quick_export_data()` |
| 699-724 | `GET /api/admin-export/...` | `admin_export_data()` |

### 2.2 `app.py` - usunąć importy

```python
from utils.export import export_to_csv, export_to_json, generate_filename
from validators import validate_event_data
from queries_config import get_query_sql, get_all_queries_sql, QUICK_QUERIES
```

### 2.3 `app.py` - zmodyfikować `device_dashboard()`

Usunąć zapytania do bazy `water_events`. Dashboard ma pokazywać tylko karty urządzeń z health check, bez statystyk z bazy.

### 2.4 `database/init.py` - usunąć tabelę water_events

Zachować tylko:
- `admin_sessions`
- `failed_login_attempts`

Usunąć:
- `water_events` i wszystkie jej indeksy

### 2.5 `device_config.py` - uprościć

Usunąć z `DEVICE_TYPES`:
- `columns` - niepotrzebne bez bazy
- `event_types` - niepotrzebne bez bazy

---

## 3. PLIKI DO ZACHOWANIA (bez zmian)

```
/opt/home-iot/config.py                 # Konfiguracja aplikacji
/opt/home-iot/auth/session.py           # Zarządzanie sesjami
/opt/home-iot/auth/decorators.py        # Dekoratory autentykacji
/opt/home-iot/auth/__init__.py
/opt/home-iot/utils/health_check.py     # Health check urządzeń
/opt/home-iot/utils/security.py         # Bezpieczeństwo (get_real_ip, secure_compare)
/opt/home-iot/utils/__init__.py
/opt/home-iot/database/connection.py    # Połączenie z bazą (dla sesji)
/opt/home-iot/database/__init__.py
/opt/home-iot/templates/login.html      # Strona logowania
/opt/home-iot/templates/dashboard.html  # Dashboard (modyfikacje później)
```

---

## 5. ENDPOINTY PO REORGANIZACJI

### Zachowane endpointy:

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/` | Redirect do dashboard |
| GET | `/login` | Strona logowania |
| POST | `/login` | Obsługa logowania |
| GET/POST | `/logout` | Wylogowanie |
| GET | `/dashboard` | Dashboard z kartami urządzeń |
| GET | `/health` | Health check aplikacji |
| GET | `/api/auth-check` | Walidacja sesji dla Nginx |
| GET | `/api/session-info` | Info o sesji |
| GET | `/api/device-health/<type>` | Health check urządzenia |

### Usunięte endpointy:

| Metoda | Endpoint |
|--------|----------|
| POST | `/api/water-events` |
| GET | `/api/events` |
| GET | `/api/stats` |
| GET | `/admin/<device_type>` |
| POST | `/api/admin-query` |
| GET | `/api/admin-device-query/...` |
| GET | `/api/available-queries/...` |
| GET | `/api/admin-quick-query/...` |
| GET | `/api/quick-export/...` |
| GET | `/api/admin-export/...` |

---

## 6. ZMIANY W KONFIGURACJI

### 6.1 `config.py` - usunąć zmienne

```python
API_TOKEN              # Token dla ESP32 wysyłających logi - USUNĄĆ
```

### 6.2 `.env` - usunąć zmienne

```
API_TOKEN=...          # USUNĄĆ
```

---

## 7. KOLEJNOŚĆ WDROŻENIA

1. **Backup** - zarchiwizować obecny stan
2. **Usunąć pliki** - katalogi i pliki z sekcji 1
3. **Zmodyfikować app.py** - usunąć endpointy i importy
4. **Zmodyfikować database/init.py** - usunąć water_events
5. **Zmodyfikować device_config.py** - usunąć columns/event_types
6. **Usunąć validators/** - cały katalog
7. **Test** - sprawdzić działanie:
   - Login/logout
   - Dashboard
   - Health check
   - Proxy do urządzeń
8. **Restart** - `sudo systemctl restart home-iot`

---

## 8. SZACOWANE ZMIANY

| Metryka | Przed | Po |
|---------|-------|-----|
| Pliki .py | ~15 | ~10 |
| Linie kodu | ~3400 | ~2000 |
| Templates | 3 | 2 |
| Endpointy | ~20 | ~10 |
| Tabele DB | 3 | 2 |

---

## 9. DECYZJE (UZGODNIONE)

- [x] Baza danych - usunąć BEZ archiwizacji
- [x] API_TOKEN - usunąć z config.py i .env
- [x] Katalog /opt/home-iot/docs/ - ZACHOWAĆ
- [x] Katalog /opt/home-iot/examples/ - USUNĄĆ
- [x] Katalog /opt/home-iot/scripts/ - USUNĄĆ (narzędzia do czyszczenia logów)

---

## Status

- [x] Pliki usunięte (tools/, data/, examples/, scripts/, validators/, queries_config.py, utils/export.py, templates/admin.html)
- [x] app.py zmodyfikowany (z 849 do 349 linii)
- [x] database/init.py zmodyfikowany (usunięta tabela water_events)
- [x] device_config.py zmodyfikowany (usunięte columns/event_types)
- [x] config.py zmodyfikowany (usunięty API_TOKEN)
- [x] .env zaktualizowany
- [x] auth/decorators.py zmodyfikowany (usunięty require_auth)
- [x] database/queries.py usunięty
- [x] utils/__init__.py zaktualizowany
- [x] Testy importów przeszły
- [x] Restart serwisu na VPS

---

## 10. POPRAWKI BEZPIECZEŃSTWA (2026-01-23)

### Problem
Po reorganizacji aplikacja działała, ale przy próbie logowania wyświetlał się błąd:
"Account temporarily locked due to too many failed attempts. Try again in 60 minutes."

### Przyczyna
1. Katalog `data/database/` został usunięty podczas reorganizacji
2. Kod w `auth/session.py` traktował błąd bazy danych jako "konto zablokowane" (DoS vulnerability)

### Naprawione luki bezpieczeństwa

| Plik | Problem | Rozwiązanie |
|------|---------|-------------|
| `auth/session.py` | `get_failed_attempts_info()` - błąd DB = is_locked=True (DoS) | Zmiana na fail-open: is_locked=False + log CRITICAL |
| `auth/session.py` | `record_failed_attempt()` - błąd DB = is_locked=True (DoS) | Zmiana na fail-open: is_locked=False + log CRITICAL |
| `database/init.py` | Brak weryfikacji sukcesu inicjalizacji | Funkcja zwraca bool + weryfikacja odczytu |
| `app.py` | Serwer startował mimo braku bazy | Dodano `sys.exit(1)` gdy `init_database()` zwraca False |

### Logika bezpieczeństwa
- **Odczyt z bazy (sprawdzanie lockout)**: fail-open (pozwól na próbę logowania)
- **Zapis do bazy (tworzenie sesji)**: fail-closed (odmów logowania)
- **Start aplikacji**: fail-closed (nie startuj bez działającej bazy)

---

## 11. PRZEGLĄD KODU - DO POPRAWY

### 11.1 Problemy bezpieczeństwa

| Priorytet | Problem | Lokalizacja | Opis |
|-----------|---------|-------------|------|
| WYSOKI | Brak CSRF | `templates/*.html` | Formularze bez tokenów CSRF |
| WYSOKI | Wyciek informacji | `app.py:/health` | Endpoint zwraca liczbę sesji, zablokowanych kont |
| ŚREDNI | Brak security headers | `app.py` | Brak CSP, X-Frame-Options, X-Content-Type-Options |
| ŚREDNI | SECRET_KEY auto-gen | `app.py:43` | Jeśli nie ustawiony, generuje nowy przy każdym restarcie (invaliduje sesje) |
| NISKI | Rate limit GET+POST | `app.py:89-99` | GET /login i POST /login dzielą limit (samo wyświetlenie strony zużywa limit) |

### 11.2 Problemy jakości kodu

| Problem | Lokalizacja | Opis |
|---------|-------------|------|
| Martwy kod | `auth/session.py:73-112` | Funkcja `is_account_locked()` nigdy nie używana |
| Niespójne nazewnictwo | `config.py` | Prefix `WATER_SYSTEM_` dla IoT Gateway |
| Import w funkcjach | `app.py:198,260-261` | `device_config` importowany wewnątrz route handlers |
| Hardcoded URL | `app.py:346` | Domena w logu startowym |
| requirements.txt | `requirements.txt` | Brak `flask-limiter` (jest zainstalowany, ale nie w pliku) |

### 11.3 Problemy niezawodności

| Problem | Opis |
|---------|------|
| Brak rotacji logów | `data/logs/app.log` będzie rosnąć bez ograniczeń |
| Brak graceful shutdown | Brak obsługi SIGTERM/SIGINT |
| Health check niepełny | Nie sprawdza możliwości zapisu do bazy |
| Brak backup DB | Sesje SQLite bez mechanizmu backup |

### 11.4 Rekomendacje dla produkcji

**Bezpieczeństwo:**
- [ ] Dodać Flask-WTF dla CSRF protection
- [ ] Dodać security headers (middleware)
- [ ] Wymusić ustawienie SECRET_KEY w .env
- [ ] Ograniczyć informacje w /health (lub zabezpieczyć endpoint)
- [ ] Rozdzielić rate limit dla GET i POST /login

**Niezawodność:**
- [ ] Skonfigurować logrotate dla app.log
- [ ] Dodać obsługę sygnałów (graceful shutdown)
- [ ] Health check z weryfikacją zapisu do DB
- [ ] Monitoring (Prometheus metrics lub similar)

**Kod:**
- [ ] Usunąć martwy kod (`is_account_locked`)
- [ ] Zmienić prefix env vars na `IOT_GATEWAY_` lub `HOME_IOT_`
- [ ] Przenieść importy na początek pliku
- [ ] Zaktualizować requirements.txt
- [ ] Dodać type hints

### 11.5 Priorytet wdrożenia

1. **Natychmiast**: CSRF protection, security headers
2. **Wkrótce**: logrotate, requirements.txt, usunięcie martwego kodu
3. **Później**: refaktoring nazewnictwa, monitoring
