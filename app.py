#!/usr/bin/env python3
"""
ESP32-C3 Water System VPS Logger
Odbiera i przechowuje zdarzenia z systemu podlewania
+ Admin Panel do zapytań SQL
+ Nginx Reverse Proxy Support
+ Environment Variables Configuration
"""

import os
import sys

# Ładowanie .env file dla developmentu (przed importami Flask)
try:
    from dotenv import load_dotenv
    # Szukaj .env w katalogu aplikacji
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"📄 Loaded environment variables from {env_path}")
    else:
        # Sprawdź czy są ustawione zmienne systemowe
        if not os.getenv('WATER_SYSTEM_ADMIN_PASSWORD'):
            print("⚠️  No .env file found and no environment variables set")
            print("   Create .env file or set environment variables")
            print("   Run: python generate_credentials.py --output env")
except ImportError:
    print("📦 python-dotenv not installed, using system environment variables only")

from flask import Flask, request, jsonify, render_template, send_file, Response, redirect, url_for, session, flash
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import csv
import io
import re
from functools import wraps
import base64
import threading
import secrets
import hashlib
import time

# === KONFIGURACJA Z ZMIENNYCH ŚRODOWISKOWYCH ===

# Ścieżki do plików (automatyczna detekcja lub z env)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.getenv('WATER_SYSTEM_DATABASE_PATH', 
                         os.path.join(BASE_DIR, 'water_events.db'))
LOG_PATH = os.getenv('WATER_SYSTEM_LOG_PATH', 
                    os.path.join(BASE_DIR, 'app.log'))

# Credentials - WYMAGANE zmienne środowiskowe
ADMIN_PASSWORD = os.getenv('WATER_SYSTEM_ADMIN_PASSWORD')
VALID_TOKEN = os.getenv('WATER_SYSTEM_API_TOKEN')

# Lista dozwolonych urządzeń (z fallback)
device_ids_str = os.getenv('WATER_SYSTEM_DEVICE_IDS', 'DOLEWKA')
VALID_DEVICE_IDS = [dev.strip() for dev in device_ids_str.split(',') if dev.strip()]

# Konfiguracja portów
HTTP_PORT = int(os.getenv('WATER_SYSTEM_HTTP_PORT', '5000'))
ADMIN_PORT = int(os.getenv('WATER_SYSTEM_ADMIN_PORT', '5001'))
ENABLE_NGINX_MODE = os.getenv('WATER_SYSTEM_NGINX_MODE', 'true').lower() == 'true'

# Konfiguracja bezpieczeństwa
SESSION_TIMEOUT_MINUTES = int(os.getenv('WATER_SYSTEM_SESSION_TIMEOUT', '30'))
MAX_FAILED_ATTEMPTS = int(os.getenv('WATER_SYSTEM_MAX_FAILED_ATTEMPTS', '8'))
LOCKOUT_DURATION_HOURS = int(os.getenv('WATER_SYSTEM_LOCKOUT_DURATION', '1'))

def verify_required_env_vars():
    """Sprawdź czy wszystkie wymagane zmienne środowiskowe są ustawione"""
    required_vars = {
        'WATER_SYSTEM_ADMIN_PASSWORD': ADMIN_PASSWORD,
        'WATER_SYSTEM_API_TOKEN': VALID_TOKEN
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        error_msg = f"""
❌ BRAK WYMAGANYCH ZMIENNYCH ŚRODOWISKOWYCH:
{', '.join(missing_vars)}

🔧 DEVELOPMENT - Utwórz plik .env:
   python generate_credentials.py --output env
   
🚀 PRODUCTION - Ustaw zmienne systemowe:
   export WATER_SYSTEM_ADMIN_PASSWORD='your_secure_password'
   export WATER_SYSTEM_API_TOKEN='your_secure_api_token'

📖 Więcej informacji w DEPLOY.md
"""
        print(error_msg)
        return False
    
    return True

# Sprawdź zmienne na starcie
if not verify_required_env_vars():
    sys.exit(1)

# Session storage (in production użyj Redis/Database)
active_sessions = {}
failed_attempts = {}
locked_accounts = {}

app = Flask(__name__)
app.secret_key = os.getenv('WATER_SYSTEM_SECRET_KEY', secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Konfiguracja logowania
log_level = os.getenv('WATER_SYSTEM_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# Log konfiguracji na starcie (bez credentials)
logging.info("=== WATER SYSTEM CONFIGURATION ===")
logging.info(f"Base directory: {BASE_DIR}")
logging.info(f"Database path: {DATABASE_PATH}")
logging.info(f"Log path: {LOG_PATH}")
logging.info(f"HTTP port: {HTTP_PORT}")
logging.info(f"Admin port: {ADMIN_PORT}")
logging.info(f"Nginx mode: {ENABLE_NGINX_MODE}")
logging.info(f"Session timeout: {SESSION_TIMEOUT_MINUTES} minutes")
logging.info(f"Valid device IDs: {VALID_DEVICE_IDS}")
logging.info(f"Log level: {log_level}")
logging.info("Environment variables loaded successfully ✅")
def init_database():
    """Inicjalizacja bazy danych SQLite z rozszerzonymi kolumnami algorytmicznymi"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Sprawdź czy tabela istnieje i ma stare kolumny
    cursor.execute("PRAGMA table_info(water_events)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    if not existing_columns:
        # Nowa instalacja - utwórz tabelę z wszystkimi kolumnami
        cursor.execute('''
            CREATE TABLE water_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                unix_time INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                volume_ml INTEGER NOT NULL,
                water_status TEXT NOT NULL,
                system_status TEXT NOT NULL,
                received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                client_ip TEXT,
                
                -- Rozszerzone kolumny algorytmiczne (v2.0)
                time_gap_1 INTEGER DEFAULT NULL,
                time_gap_2 INTEGER DEFAULT NULL,
                water_trigger_time INTEGER DEFAULT NULL,
                pump_duration INTEGER DEFAULT NULL,
                pump_attempts INTEGER DEFAULT NULL,
                gap1_fail_sum INTEGER DEFAULT NULL,
                gap2_fail_sum INTEGER DEFAULT NULL,
                water_fail_sum INTEGER DEFAULT NULL,
                algorithm_data TEXT DEFAULT NULL
            )
        ''')
        logging.info("Created new water_events table with algorithm columns")
        
    else:
        # Istniejąca tabela - dodaj nowe kolumny jeśli nie istnieją
        new_columns = [
            'time_gap_1 INTEGER DEFAULT NULL',
            'time_gap_2 INTEGER DEFAULT NULL', 
            'water_trigger_time INTEGER DEFAULT NULL',
            'pump_duration INTEGER DEFAULT NULL',
            'pump_attempts INTEGER DEFAULT NULL',
            'gap1_fail_sum INTEGER DEFAULT NULL',
            'gap2_fail_sum INTEGER DEFAULT NULL', 
            'water_fail_sum INTEGER DEFAULT NULL',
            'last_reset_timestamp INTEGER DEFAULT NULL',
            'algorithm_data TEXT DEFAULT NULL'
        ]
        
        for column_def in new_columns:
            column_name = column_def.split()[0]
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE water_events ADD COLUMN {column_def}')
                    logging.info(f"Added column: {column_name}")
                except sqlite3.Error as e:
                    logging.warning(f"Could not add column {column_name}: {e}")
    
    # Indeksy dla lepszej wydajności
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON water_events(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON water_events(unix_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON water_events(event_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_algorithm ON water_events(time_gap_1, gap1_fail_sum)')
    
    conn.commit()
    conn.close()
    
    logging.info("Database initialized successfully with algorithm support")



def cleanup_expired_sessions():
    """Czyści wygasłe sesje i lockout"""
    now = time.time()
    
    # Cleanup sessions
    expired_sessions = [sid for sid, data in active_sessions.items() 
                       if now - data['last_activity'] > SESSION_TIMEOUT_MINUTES * 60]
    for sid in expired_sessions:
        del active_sessions[sid]
    
    # Cleanup failed attempts (po 1h)
    expired_attempts = [ip for ip, data in failed_attempts.items() 
                       if now - data['last_attempt'] > 3600]
    for ip in expired_attempts:
        del failed_attempts[ip]
    
    # Cleanup lockouts
    expired_locks = [ip for ip, lock_time in locked_accounts.items() 
                    if now - lock_time > LOCKOUT_DURATION_HOURS * 3600]
    for ip in expired_locks:
        del locked_accounts[ip]
        logging.info(f"Account lockout expired for IP: {ip}")

def is_account_locked(client_ip):
    """Sprawdź czy konto jest zablokowane"""
    cleanup_expired_sessions()
    return client_ip in locked_accounts

def record_failed_attempt(client_ip):
    """Zapisz nieudaną próbę logowania"""
    now = time.time()
    
    if client_ip not in failed_attempts:
        failed_attempts[client_ip] = {'count': 0, 'last_attempt': now}
    
    failed_attempts[client_ip]['count'] += 1
    failed_attempts[client_ip]['last_attempt'] = now
    
    if failed_attempts[client_ip]['count'] >= MAX_FAILED_ATTEMPTS:
        locked_accounts[client_ip] = now
        logging.warning(f"Account locked for IP {client_ip} after {MAX_FAILED_ATTEMPTS} failed attempts")
        return True
    
    return False

def reset_failed_attempts(client_ip):
    """Resetuj licznik nieudanych prób po udanym logowaniu"""
    if client_ip in failed_attempts:
        del failed_attempts[client_ip]

def get_real_ip():
    """Pobierz prawdziwy IP klienta (uwzględniając Nginx proxy)"""
    if ENABLE_NGINX_MODE:
        # Nginx przekazuje prawdziwy IP w X-Real-IP lub X-Forwarded-For
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Pierwszy IP w liście to prawdziwy klient
            return forwarded_for.split(',')[0].strip()
    
    return request.remote_addr

def create_session(client_ip):
    """Utwórz nową sesję"""
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = {
        'client_ip': client_ip,
        'created_at': time.time(),
        'last_activity': time.time()
    }
    
    # Set Flask session
    session.permanent = True
    session['session_id'] = session_id
    session['authenticated'] = True
    session['login_time'] = datetime.now().isoformat()
    
    logging.info(f"New session created for IP: {client_ip}")
    return session_id

def validate_session():
    """Waliduj obecną sesję"""
    cleanup_expired_sessions()
    
    if 'session_id' not in session or 'authenticated' not in session:
        return False
    
    session_id = session['session_id']
    client_ip = get_real_ip()
    
    if session_id not in active_sessions:
        return False
    
    session_data = active_sessions[session_id]
    
    # Sprawdź IP (opcjonalne - może być problemem z proxy)
    if session_data['client_ip'] != client_ip:
        logging.warning(f"Session IP mismatch: {session_data['client_ip']} vs {client_ip}")
        # W trybie Nginx nie blokujemy na IP mismatch (proxy może zmieniać IP)
        if not ENABLE_NGINX_MODE:
            return False
    
    # Update last activity
    session_data['last_activity'] = time.time()
    
    return True

def destroy_session():
    """Zniszcz obecną sesję"""
    if 'session_id' in session:
        session_id = session['session_id']
        if session_id in active_sessions:
            del active_sessions[session_id]
    
    session.clear()

def require_auth(f):
    """Dekorator do sprawdzania autoryzacji ESP32"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        client_ip = get_real_ip()
        
        if not auth_header:
            logging.warning(f"Missing Authorization header from {client_ip}")
            return jsonify({'error': 'Missing Authorization header'}), 401
        
        if not auth_header.startswith('Bearer '):
            logging.warning(f"Invalid Authorization format from {client_ip}")
            return jsonify({'error': 'Invalid Authorization format'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer '
        
        if token != VALID_TOKEN:
            logging.warning(f"Invalid token from {client_ip}: {token}")
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin_auth(f):
    """Dekorator do sprawdzania autoryzacji Admin Panel - Session Based"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # W trybie Nginx nie przekierowujemy HTTP->HTTPS (Nginx to robi)
        
        # Sprawdź sesję
        if not validate_session():
            if request.endpoint == 'admin_dashboard':
                return redirect(url_for('login_page'))
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_sql_query(query):
    """Walidacja zapytania SQL - tylko SELECT"""
    query = query.strip().upper()
    
    # Usuń komentarze
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Dozwolone słowa kluczowe
    allowed_keywords = ['SELECT', 'FROM', 'WHERE', 'ORDER', 'BY', 'LIMIT', 'GROUP', 'HAVING', 'AS', 'ASC', 'DESC', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'DATETIME', 'DATE', 'TIME', 'NOW', 'SUBSTR', 'LENGTH', 'ROUND']
    
    # Zablokowane słowa kluczowe
    blocked_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE', 'CALL', 'UNION', 'ATTACH', 'DETACH', 'PRAGMA']
    
    # Sprawdź zablokowane słowa
    for keyword in blocked_keywords:
        if keyword in query:
            return False, f"Forbidden keyword: {keyword}"
    
    # Musi zaczynać się od SELECT
    if not query.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"
    
    # Sprawdź czy zapytanie ma dozwolone tabele
    if 'WATER_EVENTS' not in query:
        return False, "Only water_events table is allowed"
    
    return True, "Valid"

def execute_safe_query(query, params=None):
    """Bezpiecznie wykonaj zapytanie SQL"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ustaw timeout
        conn.execute('PRAGMA query_timeout = 10000')  # 10 sekund
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        
        # Limit wyników
        if len(results) > 1000:
            results = results[:1000]
        
        conn.close()
        return True, [dict(row) for row in results]
        
    except Exception as e:
        return False, str(e)


def validate_event_data(data):
    """Walidacja danych zdarzenia z obsługą danych algorytmicznych"""
    required_fields = [
        'device_id', 'timestamp', 'unix_time', 
        'event_type', 'volume_ml', 'water_status', 'system_status'
    ]
    
    # Sprawdź czy wszystkie wymagane pola są obecne
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Sprawdź typy danych podstawowych
    try:
        unix_time = int(data['unix_time'])
        volume_ml = int(data['volume_ml'])
    except (ValueError, TypeError):
        return False, "unix_time and volume_ml must be integers"
    
    # Sprawdź czy device_id jest dozwolony
    if data['device_id'] not in VALID_DEVICE_IDS:
        return False, f"Invalid device_id: {data['device_id']}"
    
    # Rozszerzona lista typów zdarzeń
    # valid_event_types = ['AUTO_PUMP', 'MANUAL_NORMAL', 'MANUAL_EXTENDED', 'AUTO_CYCLE_COMPLETE']

    valid_event_types = ['AUTO_PUMP', 'MANUAL_NORMAL', 'MANUAL_EXTENDED', 'AUTO_CYCLE_COMPLETE', 'STATISTICS_RESET']

    if data['event_type'] not in valid_event_types:
        return False, f"Invalid event_type: {data['event_type']}"
    
    # Sprawdź dozwolone statusy wody
    valid_water_statuses = ['OK', 'LOW', 'PARTIAL', 'CHECKING', 'NORMAL', 'BOTH_LOW', 'SENSOR1_LOW', 'SENSOR2_LOW']
    if data['water_status'] not in valid_water_statuses:
        return False, f"Invalid water_status: {data['water_status']}"
    


    if data['event_type'] == 'AUTO_CYCLE_COMPLETE':
        algorithm_fields = ['time_gap_1', 'time_gap_2', 'water_trigger_time', 
                          'pump_duration', 'pump_attempts', 'gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum']
        
        for field in algorithm_fields:
            if field in data:
                try:
                    # Sprawdź czy to liczba
                    field_value = int(data[field])
                    
                    # Sprawdź sensowne zakresy
                    if field in ['gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum']:
                        if field_value < 0 or field_value > 65535:
                            return False, f"{field} must be 0-65535"
                    
                    if field in ['time_gap_1', 'time_gap_2', 'water_trigger_time', 'pump_duration'] and int(data[field]) < 0:
                        return False, f"{field} must be >= 0"
                        
                    if field == 'pump_attempts' and (int(data[field]) < 1 or int(data[field]) > 10):
                        return False, f"{field} must be between 1-10"
                        
                except (ValueError, TypeError):
                    return False, f"{field} must be an integer"
    
    return True, "Valid"



# ===============================
# ESP32 API ENDPOINTS (HTTP ONLY - PORT 5000)
# ===============================

@app.route('/api/water-events', methods=['POST'])
@require_auth


def receive_water_event():
    """Endpoint do odbierania zdarzeń z ESP32-C3"""
    
    client_ip = get_real_ip()
    
    try:
        # Sprawdź Content-Type
        if request.content_type != 'application/json':
            logging.warning(f"Invalid Content-Type from {client_ip}: {request.content_type}")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        # Pobierz dane JSON
        data = request.get_json()
        
        if not data:
            logging.warning(f"No JSON data received from {client_ip}")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Walidacja danych
        is_valid, error_msg = validate_event_data(data)
        if not is_valid:
            logging.warning(f"Invalid data from {client_ip}: {error_msg}")
            return jsonify({'error': error_msg}), 400


        
        # Zapisz do bazy danych z obsługą danych algorytmicznych
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Przygotuj dane algorytmiczne (opcjonalne)
        # Przygotuj dane algorytmiczne (opcjonalne)
        algorithm_values = {}
        algorithm_fields = ['time_gap_1', 'time_gap_2', 'water_trigger_time', 
                          'pump_duration', 'pump_attempts', 'gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum', 
                          'last_reset_timestamp', 'algorithm_data']
        
        for field in algorithm_fields:
            algorithm_values[field] = data.get(field, None)
        
        cursor.execute('''
            INSERT INTO water_events 
            (device_id, timestamp, unix_time, event_type, volume_ml, 
             water_status, system_status, client_ip,
             time_gap_1, time_gap_2, water_trigger_time, pump_duration, pump_attempts,
             gap1_fail_sum, gap2_fail_sum, water_fail_sum, last_reset_timestamp, algorithm_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['device_id'],
            data['timestamp'],
            data['unix_time'],
            data['event_type'],
            data['volume_ml'],
            data['water_status'],
            data['system_status'],
            client_ip,
            algorithm_values['time_gap_1'],
            algorithm_values['time_gap_2'],
            algorithm_values['water_trigger_time'],
            algorithm_values['pump_duration'],
            algorithm_values['pump_attempts'],
            algorithm_values['gap1_fail_sum'],
            algorithm_values['gap2_fail_sum'],
            algorithm_values['water_fail_sum'],
            algorithm_values['last_reset_timestamp'],
            algorithm_values['algorithm_data']
        ))



        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Loguj pomyślne zdarzenie
        logging.info(
            f"Event saved [ID: {event_id}] - Device: {data['device_id']}, "
            f"Type: {data['event_type']}, Volume: {data['volume_ml']}ml, "
            f"Status: {data['water_status']}, IP: {client_ip}"
        )
        
        return jsonify({
            'success': True,
            'event_id': event_id,
            'message': 'Event recorded successfully'
        }), 200
        
    except json.JSONDecodeError:
        logging.error(f"JSON decode error from {client_ip}")
        return jsonify({'error': 'Invalid JSON format'}), 400
    
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500



@app.route('/api/events', methods=['GET'])
@require_auth
def get_events():
    """Endpoint do pobierania historii zdarzeń"""
    
    try:
        # Parametry zapytania
        limit = request.args.get('limit', 100, type=int)
        device_id = request.args.get('device_id')
        event_type = request.args.get('event_type')
        
        # Ograniczenia
        limit = min(limit, 1000)  # Max 1000 rekordów
        
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Zwraca słowniki zamiast tupli
        cursor = conn.cursor()
        
        # Buduj zapytanie SQL
        query = "SELECT * FROM water_events WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY received_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Konwertuj na listę słowników
        events = [dict(row) for row in rows]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(events),
            'events': events
        }), 200
        
    except Exception as e:
        logging.error(f"Error fetching events: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Endpoint do pobierania statystyk"""
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Podstawowe statystyki
        cursor.execute("SELECT COUNT(*) FROM water_events")
        total_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT device_id) FROM water_events")
        unique_devices = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT event_type, COUNT(*) as count 
            FROM water_events 
            GROUP BY event_type
        """)
        event_types = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT SUM(volume_ml) as total_volume 
            FROM water_events
        """)
        total_volume = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT timestamp, volume_ml 
            FROM water_events 
            ORDER BY received_at DESC 
            LIMIT 1
        """)
        last_event = cursor.fetchone()
        
        conn.close()
        
        stats = {
            'total_events': total_events,
            'unique_devices': unique_devices,
            'event_types': event_types,
            'total_volume_ml': total_volume,
            'last_event': {
                'timestamp': last_event[0] if last_event else None,
                'volume_ml': last_event[1] if last_event else None
            } if last_event else None
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ===============================
# ADMIN AUTHENTICATION (SESSION-BASED)
# ===============================

@app.route('/login')
def login_page():
    """Strona logowania"""
    # Jeśli już zalogowany, przekieruj do admin
    if validate_session():
        return redirect(url_for('admin_dashboard'))
    
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_submit():
    """Obsługa logowania"""
    client_ip = get_real_ip()
    
    # Sprawdź czy konto jest zablokowane
    if is_account_locked(client_ip):
        flash('Account temporarily locked due to too many failed attempts. Try again later.', 'error')
        logging.warning(f"Login attempt from locked IP: {client_ip}")
        return render_template('login.html'), 429
    
    password = request.form.get('password', '')
    
    if password == ADMIN_PASSWORD:
        # Udane logowanie
        reset_failed_attempts(client_ip)
        create_session(client_ip)
        logging.info(f"Successful admin login from IP: {client_ip}")
        return redirect(url_for('admin_dashboard'))
    else:
        # Nieudane logowanie
        is_locked = record_failed_attempt(client_ip)
        if is_locked:
            flash(f'Too many failed attempts. Account locked for {LOCKOUT_DURATION_HOURS} hour(s).', 'error')
        else:
            remaining = MAX_FAILED_ATTEMPTS - failed_attempts[client_ip]['count']
            flash(f'Invalid password. {remaining} attempts remaining.', 'error')
        
        logging.warning(f"Failed admin login from IP: {client_ip}")
        return render_template('login.html'), 401

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Wylogowanie"""
    client_ip = get_real_ip()
    destroy_session()
    logging.info(f"Admin logout from IP: {client_ip}")
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login_page'))

# ===============================
# ADMIN PANEL ENDPOINTS (SESSION AUTH)
# ===============================

@app.route('/')
@app.route('/admin')
@require_admin_auth
def admin_dashboard():
    """Admin panel dashboard"""
    client_ip = get_real_ip()
    logging.info(f"Admin panel accessed from {client_ip}")
    return render_template('admin.html')

@app.route('/api/session-info')
@require_admin_auth
def session_info():
    """Informacje o sesji dla frontend"""
    session_data = {
        'authenticated': True,
        'login_time': session.get('login_time'),
        'timeout_minutes': SESSION_TIMEOUT_MINUTES,
        'client_ip': get_real_ip()
    }
    return jsonify(session_data)

@app.route('/api/admin-query', methods=['POST'])
@require_admin_auth
def admin_execute_query():
    """Wykonaj zapytanie SQL z admin panel"""
    
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
        
        query = data['query'].strip()
        
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        # Walidacja SQL
        is_valid, error_msg = validate_sql_query(query)
        if not is_valid:
            logging.warning(f"Invalid SQL query from {get_real_ip()}: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Wykonaj zapytanie
        success, result = execute_safe_query(query)
        
        if not success:
            logging.error(f"SQL query error from {get_real_ip()}: {result}")
            return jsonify({'error': f'Query error: {result}'}), 400
        
        logging.info(f"Admin query executed from {get_real_ip()}: {len(result)} rows returned")
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'limited': len(result) >= 1000
        }), 200
        
    except Exception as e:
        logging.error(f"Admin query exception: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin-quick-query/<query_type>')
@require_admin_auth

def admin_quick_query(query_type):
    """Wykonaj predefiniowane zapytanie"""
    
    quick_queries = {
        'last24h': """
            SELECT id, timestamp, event_type, volume_ml, water_status, client_ip 
            FROM water_events 
            WHERE received_at > datetime('now', '-24 hours') 
            ORDER BY received_at DESC
        """,
        
        'algorithm_cycles': """
            SELECT id, timestamp, time_gap_1, time_gap_2, water_trigger_time, 
                   pump_duration, pump_attempts, gap1_fail_sum, gap2_fail_sum, water_fail_sum,
                   last_reset_timestamp
            FROM water_events 
            WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
            ORDER BY received_at DESC LIMIT 50
        """,
        'algorithm_stats': """
            SELECT 
                COUNT(*) as total_cycles,
                AVG(time_gap_1) as avg_gap1,
                AVG(time_gap_2) as avg_gap2,
                AVG(water_trigger_time) as avg_water_time,
                AVG(pump_duration) as avg_pump_duration,
                MAX(gap1_fail_sum) as max_gap1_sum,
                MAX(gap2_fail_sum) as max_gap2_sum,
                MAX(water_fail_sum) as max_water_sum,
                AVG(pump_attempts) as avg_attempts
            FROM water_events 
            WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
                AND received_at > datetime('now', '-7 days')
        """,
        'algorithm_failures': """
            SELECT id, timestamp, time_gap_1, time_gap_2, water_trigger_time,
                   gap1_fail_sum, gap2_fail_sum, water_fail_sum, pump_attempts, algorithm_data,
                   last_reset_timestamp
            FROM water_events 
            WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
                AND (gap1_fail_sum > 0 OR gap2_fail_sum > 0 OR water_fail_sum > 0 OR pump_attempts > 1)
            ORDER BY received_at DESC
        """,
        'statistics_resets': """
            SELECT id, timestamp, received_at, client_ip
            FROM water_events 
            WHERE event_type = 'STATISTICS_RESET' 
            ORDER BY received_at DESC LIMIT 20
        """,



        'today_stats': """
            SELECT event_type, COUNT(*) as count, SUM(volume_ml) as total_ml 
            FROM water_events 
            WHERE DATE(received_at) = DATE('now') 
            GROUP BY event_type
        """,
        'all_events': """
            SELECT id, timestamp, event_type, volume_ml, water_status 
            FROM water_events 
            ORDER BY received_at DESC 
            LIMIT 100
        """,
        'errors': """
            SELECT id, timestamp, event_type, water_status, system_status, client_ip 
            FROM water_events 
            WHERE water_status != 'OK' OR system_status != 'OK' 
            ORDER BY received_at DESC
        """,
        'monthly': """
            SELECT DATE(received_at) as date, COUNT(*) as events, SUM(volume_ml) as total_ml 
            FROM water_events 
            WHERE received_at > datetime('now', '-30 days') 
            GROUP BY DATE(received_at) 
            ORDER BY date DESC
        """
    }
    
    if query_type not in quick_queries:
        return jsonify({'error': 'Unknown quick query type'}), 400
    
    query = quick_queries[query_type]
    success, result = execute_safe_query(query)
    
    if not success:
        return jsonify({'error': f'Query error: {result}'}), 400
    
    return jsonify({
        'success': True,
        'data': result,
        'count': len(result),
        'query_type': query_type
    }), 200

@app.route('/api/admin-export/<format>')
@require_admin_auth
def admin_export_data(format):
    """Eksport danych w różnych formatach"""
    
    query = request.args.get('query', 'SELECT * FROM water_events ORDER BY received_at DESC LIMIT 1000')
    
    # Walidacja SQL
    is_valid, error_msg = validate_sql_query(query)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    success, result = execute_safe_query(query)
    if not success:
        return jsonify({'error': f'Query error: {result}'}), 400
    
    if format == 'csv':
        # Export CSV
        output = io.StringIO()
        if result:
            writer = csv.DictWriter(output, fieldnames=result[0].keys())
            writer.writeheader()
            writer.writerows(result)
        
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=water_events_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        return response
    
    elif format == 'json':
        # Export JSON
        response = Response(
            json.dumps(result, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=water_events_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
        )
        return response
    
    else:
        return jsonify({'error': 'Unsupported format. Use csv or json'}), 400

# ===============================
# HEALTH CHECK (HTTP)
# ===============================

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint sprawdzania stanu aplikacji"""
    cleanup_expired_sessions()  # Okazja do cleanup
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if os.path.exists(DATABASE_PATH) else 'missing',
        'nginx_mode': ENABLE_NGINX_MODE,
        'http_port': HTTP_PORT,
        'admin_port': ADMIN_PORT,
        'session_management': True,
        'active_sessions': len(active_sessions),
        'locked_accounts': len(locked_accounts)
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

def run_http_server():
    """Uruchom HTTP server dla ESP32 API"""
    logging.info(f"Starting HTTP server on port {HTTP_PORT} for ESP32 API")
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False, threaded=True)

def run_admin_server():
    """Uruchom HTTP server dla Admin Panel (Nginx obsługuje SSL)"""
    logging.info(f"Starting Admin server on port {ADMIN_PORT} (HTTP - Nginx handles SSL)")
    app.run(host='0.0.0.0', port=ADMIN_PORT, debug=False, threaded=True)

if __name__ == '__main__':
    # Inicjalizuj bazę danych przy starcie
    init_database()
    
    logging.info("ESP32-C3 Water System VPS Logger started (Nginx Mode)")
    logging.info(f"Database: {DATABASE_PATH}")
    logging.info(f"Log file: {LOG_PATH}")
    logging.info(f"Session timeout: {SESSION_TIMEOUT_MINUTES} minutes")
    logging.info(f"Account lockout: {MAX_FAILED_ATTEMPTS} attempts, {LOCKOUT_DURATION_HOURS}h ban")
    logging.info(f"Nginx reverse proxy mode: {ENABLE_NGINX_MODE}")
    
    # Dual-server setup bez SSL (Nginx obsługuje SSL)
    logging.info("Starting dual-server setup (HTTP only - Nginx handles SSL):")
    logging.info(f"  - HTTP  (ESP32 API): http://0.0.0.0:{HTTP_PORT}")
    logging.info(f"  - HTTP  (Admin Panel): http://0.0.0.0:{ADMIN_PORT}")
    logging.info("External access via Nginx:")
    logging.info(f"  - ESP32 API: https://app.krzysztoforlinski.pl/api/")
    logging.info(f"  - Admin Panel: https://app.krzysztoforlinski.pl/admin")
    
    # Uruchom HTTP server w osobnym wątku
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Uruchom Admin server w głównym wątku
    run_admin_server()