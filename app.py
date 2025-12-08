#!/usr/bin/env python3


import os
import sys
import hashlib
import time
from flask import Flask, request, jsonify, render_template, send_file, Response, redirect, url_for, session, flash
import sqlite3
import json
# from database import get_db_connection, execute_query, init_database_path
from database import get_db_connection, init_database_path, init_database, execute_safe_query
import logging
from datetime import datetime, timedelta
from datetime import timezone as TZ
import re
# from functools import wraps
import base64
import threading
import secrets
import hashlib
import time
import hmac
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from queries_config import get_query_sql, get_all_queries_sql, QUICK_QUERIES
from config import Config
from utils.security import secure_compare, get_real_ip
from validators import validate_event_data, validate_sql_query
from utils.export import export_to_csv, export_to_json, generate_filename
from auth import (
    cleanup_expired_sessions,
    get_failed_attempts_info,
    record_failed_attempt,
    reset_failed_attempts,
    create_session,
    validate_session,
    destroy_session,
    require_auth,
    require_admin_auth
)

try:
    from dotenv import load_dotenv
    # Szukaj .env w katalogu aplikacji
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"📄 Loaded environment variables from {env_path}")
    else:
        # Sprawdź czy są ustawione zmienne systemowe
        if not os.getenv('WATER_SYSTEM_Config.ADMIN_PASSWORD'):
            print("⚠️  No .env file found and no environment variables set")
            print("   Create .env file or set environment variables")
            print("   Run: python generate_credentials.py --output env")
except ImportError:
    print("📦 python-dotenv not installed, using system environment variables only")

# Verify configuration on startup
if not Config.verify_required_vars():
    sys.exit(1)

# # Session storage (in production użyj Redis/Database)
# active_sessions = {}
# failed_attempts = {}
# locked_accounts = {}

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY or secrets.token_hex(32)
app.permanent_session_lifetime = Config.SESSION_PERMANENT_LIFETIME

app.config.update(
    TEMPLATES_AUTO_RELOAD=Config.TEMPLATES_AUTO_RELOAD,
    SESSION_COOKIE_HTTPONLY=Config.SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=Config.SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_NAME=Config.SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
)

# app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# ============================================
# RATE LIMITING CONFIGURATION
# ============================================

def get_real_ip_for_limiter():
    """
    Get real client IP for rate limiting (Nginx-aware).
    Reuses the existing get_real_ip() logic.
    """
    return get_real_ip()

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_real_ip_for_limiter,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
    headers_enabled=True,
)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_PATH),
        logging.StreamHandler()
    ]
)

Config.log_startup_info(logging)

init_database_path(Config.DATABASE_PATH)

@app.route('/api/water-events', methods=['POST'])
@limiter.limit("60 per hour")  
@require_auth
def receive_water_event():
    """
    Receive and store events from IOT.
    
    Validates event data, determines device type, and stores in database.
    """
    client_ip = get_real_ip()
    
    try:
        data = request.get_json()
        
        # Validate event data
        is_valid, error_msg = validate_event_data(data)
        if not is_valid:
            logging.warning(f"Invalid data from {data.get('device_id', 'unknown')}: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Get device type
        from device_config import get_device_type
        device_type = get_device_type(data['device_id'])
        
        # Extract optional fields
        daily_volume_ml = data.get('daily_volume_ml', None)
        
        # Prepare algorithm values
        algorithm_values = {}
        algorithm_fields = [
            'time_gap_1', 'time_gap_2', 'water_trigger_time', 
            'pump_duration', 'pump_attempts', 'gap1_fail_sum', 
            'gap2_fail_sum', 'water_fail_sum', 
            'last_reset_timestamp', 'algorithm_data'
        ]
        
        for field in algorithm_fields:
            algorithm_values[field] = data.get(field, None)
        
        # Prepare timestamp
        from datetime import timezone
        timestamp_value = data.get('timestamp') or datetime.fromtimestamp(
            data['unix_time'], 
            timezone.utc
        ).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Store event in database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO water_events 
                (device_id, device_type, timestamp, unix_time, event_type, volume_ml, 
                 water_status, system_status, client_ip,
                 time_gap_1, time_gap_2, water_trigger_time, pump_duration, pump_attempts,
                 gap1_fail_sum, gap2_fail_sum, water_fail_sum, last_reset_timestamp, algorithm_data,
                 daily_volume_ml)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['device_id'],
                device_type,
                timestamp_value,
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
                algorithm_values['algorithm_data'],
                daily_volume_ml
            ))
            
            # event_id = cursor.lastrowid
        
        logging.info(
            f"Event saved: {data['device_id']} [{device_type}] "
            f"- {data['event_type']} - ID: {event_id}"
        )
        
        return jsonify({'success': True, 'event_id': event_id}), 200
        
    except Exception as e:
        logging.error(f"Error processing event from {client_ip}: {str(e)}", exc_info=True)
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
        
        with get_db_connection() as conn:
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
        with get_db_connection() as conn:
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

@app.route('/login')
@limiter.limit("15 per 15 minutes")
def login_page():
    """Strona logowania"""
    # Jeśli już zalogowany, przekieruj do admin
    if validate_session():
        return redirect(url_for('device_dashboard'))
    
    return render_template('login.html')

@app.route('/')
@app.route('/admin')  
@require_admin_auth
def admin_dashboard():
    """Redirect to dashboard for device type selection"""
    return redirect(url_for('device_dashboard'))

@app.route('/login', methods=['POST'])
@limiter.limit("15 per 15 minutes")
def login_submit():
    """
    Obsługa logowania z centralizowaną obsługą błędów.
    Zawsze zwraca odpowiedź HTTP (nie rzuca wyjątków).
    """
    client_ip = get_real_ip()
    
    try:
        # === KROK 1: Sprawdź czy konto jest zablokowane ===
        attempt_info = get_failed_attempts_info(client_ip)
        
        if attempt_info.get('is_locked'):
            # Konto zablokowane
            time_left_seconds = attempt_info.get('time_until_unlock', 0)
            time_left_minutes = max(1, time_left_seconds // 60)
            
            flash(
                f'Account temporarily locked due to too many failed attempts. '
                f'Try again in {time_left_minutes} minutes.',
                'error'
            )
            logging.warning(
                f"🔒 Blocked login attempt from locked IP: {client_ip} "
                f"(unlocks in {time_left_minutes} minutes)"
            )
            return render_template('login.html'), 429
        
        # === KROK 2: Walidacja hasła ===
        password = request.form.get('password', '')
        
        if not password:
            flash('Password is required.', 'error')
            return render_template('login.html'), 400
        
        if secure_compare(password, Config.ADMIN_PASSWORD):
            # ✅ UDANE LOGOWANIE
            reset_failed_attempts(client_ip)
            create_session(client_ip)
            logging.info(f"✅ Successful admin login from IP: {client_ip}")
            return redirect(url_for('device_dashboard'))
        
        # === KROK 3: Nieudane logowanie - zapisz próbę ===
        result = record_failed_attempt(client_ip)
        
        # Buduj komunikat na podstawie zwróconych danych
        if result.get('is_locked'):
            # Właśnie zablokowaliśmy konto (to była ostatnia próba)
            flash(
                f'Too many failed attempts. Account locked for '
                f'{result["lockout_duration_hours"]} hour(s).',
                'error'
            )
            logging.warning(
                f"❌ Failed admin login from IP: {client_ip} "
                f"(attempt {result['attempt_count']}/{Config.MAX_FAILED_ATTEMPTS}) - ACCOUNT LOCKED"
            )
            return render_template('login.html'), 429
        else:
            # Jeszcze nie zablokowane - pokaż ile prób zostało
            remaining = result.get('remaining_attempts', 0)
            flash(f'Invalid password. {remaining} attempts remaining.', 'error')
            logging.warning(
                f"❌ Failed admin login from IP: {client_ip} "
                f"(attempt {result['attempt_count']}/{Config.MAX_FAILED_ATTEMPTS}, {remaining} remaining)"
            )
            return render_template('login.html'), 401
    
    except Exception as e:
        # === CENTRALIZOWANA OBSŁUGA BŁĘDÓW ===
        # Nigdy nie pozwól na 500 error - zawsze zwróć odpowiedź
        logging.error(f"Login error for IP {client_ip}: {e}", exc_info=True)
        flash(
            'An error occurred during login. Please try again or contact administrator.',
            'error'
        )
        return render_template('login.html'), 500

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Wylogowanie użytkownika"""
    client_ip = get_real_ip()
    destroy_session()
    logging.info(f"Admin logout from IP: {client_ip}")
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login_page'))

     
@app.route('/dashboard')
@require_admin_auth
def device_dashboard():
    """Multi-device dashboard with auto-discovery"""
    client_ip = get_real_ip()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
        
            # Import valid device types
            from device_config import DEVICE_TYPES
            valid_device_types = list(DEVICE_TYPES.keys())
            
            # Placeholders for SQL IN clause
            placeholders = ','.join(['?' for _ in valid_device_types])
            
            # Auto-discover available device types from database (only valid ones)
            cursor.execute(f"""
                SELECT 
                    device_type,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT device_id) as device_count,
                    MAX(received_at) as last_activity,
                    MIN(received_at) as first_activity
                FROM water_events 
                WHERE device_type IN ({placeholders}) 
                GROUP BY device_type 
                ORDER BY event_count DESC
            """, valid_device_types)
        
            discovered_types = []
            for row in cursor.fetchall():
                device_type, event_count, device_count, last_activity, first_activity = row
                
                # Get device type configuration
                from device_config import get_device_config
                config = get_device_config(device_type)
                
                discovered_types.append({
                    'type': device_type,
                    'name': config.get('name', device_type.title()),
                    'icon': config.get('icon', '📱'),
                    'color': config.get('color', '#95a5a6'),
                    'description': config.get('description', f'{device_type} devices'),
                    'event_count': event_count,
                    'device_count': device_count,
                    'last_activity': last_activity,
                    'first_activity': first_activity,
                    'status': 'active' if last_activity else 'inactive'
                })
            
            # Get recent activity across all devices (only valid device types)
            cursor.execute(f"""
                SELECT device_id, device_type, event_type, received_at, volume_ml, system_status
                FROM water_events 
                WHERE device_type IN ({placeholders})
                ORDER BY received_at DESC 
                LIMIT 10
            """, valid_device_types)
            
            recent_activity = []
            for row in cursor.fetchall():
                device_id, device_type, event_type, received_at, volume_ml, system_status = row
                recent_activity.append({
                    'device_id': device_id,
                    'device_type': device_type,
                    'event_type': event_type,
                    'received_at': received_at,
                    'volume_ml': volume_ml,
                    'system_status': system_status
                })
        
        logging.info(f"Dashboard accessed from {client_ip} - {len(discovered_types)} device types discovered")
        
        return render_template('dashboard.html', 
                             device_types=discovered_types, 
                             recent_activity=recent_activity)
        
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        return jsonify({'error': 'Dashboard error'}), 500

 
@app.route('/admin/<device_type>')
@require_admin_auth  
def device_context_admin(device_type):
    """Device-specific admin interface"""
    from device_config import get_device_config, DEVICE_TYPES
    
    # Validate device type
    if device_type not in DEVICE_TYPES:
        return jsonify({'error': f'Unknown device type: {device_type}'}), 404
    
    # Get device configuration
    config = get_device_config(device_type)
    client_ip = get_real_ip()
    
    logging.info(f"Device context admin accessed: {device_type} from {client_ip}")
    
    # Pass device context to template
    return render_template('admin.html', 
                         device_context={
                             'type': device_type,
                             'name': config.get('name', device_type.title()),
                             'icon': config.get('icon', '📱'),
                             'color': config.get('color', '#95a5a6'),
                             'columns': config.get('columns', []),
                             'event_types': config.get('event_types', [])
                         })

@app.route('/api/session-info')
@require_admin_auth
def session_info():
    """Informacje o sesji dla frontend"""
    session_data = {
        'authenticated': True,
        'login_time': session.get('login_time'),
        'timeout_minutes': Config.SESSION_TIMEOUT_MINUTES,
        'client_ip': get_real_ip()
    }
    return jsonify(session_data)

@app.route('/api/admin-query', methods=['POST'])
@limiter.limit("30 per hour")
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

@app.route('/api/admin-device-query/<device_type>/<query_type>')
@require_admin_auth
def admin_device_query(device_type, query_type):
    """Execute device-contextual predefined query"""
    from device_config import DEVICE_TYPES
    from queries_config import get_query_sql
    
    # Validate device type
    if device_type not in DEVICE_TYPES:
        return jsonify({'error': f'Unknown device type: {device_type}'}), 400
    
    try:
        query = get_query_sql(query_type, device_type)
        if not query:
            return jsonify({'error': f'Unknown query type: {query_type} for device: {device_type}'}), 400
        
        success, result = execute_safe_query(query)
        
        if not success:
            return jsonify({'error': f'Query error: {result}'}), 400
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'device_type': device_type,
            'query_type': query_type
        }), 200
        
    except Exception as e:
        logging.error(f"Error in admin_device_query: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/available-queries/<device_type>')
@require_admin_auth  
def get_device_queries(device_type):
    """Get available queries for device type"""
    from device_config import DEVICE_TYPES
    from queries_config import get_available_queries
    
    if device_type not in DEVICE_TYPES:
        return jsonify({'error': f'Unknown device type: {device_type}'}), 400
    
    try:
        queries = get_available_queries(device_type)
        return jsonify({
            'success': True,
            'device_type': device_type,
            'queries': queries
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting device queries: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin-quick-query/<query_type>')
@limiter.limit("60 per hour")
@require_admin_auth
def admin_quick_query(query_type):
    """Wykonaj predefiniowane zapytanie"""
    
    try:
        query = get_query_sql(query_type)
        if not query:
            return jsonify({'error': 'Unknown quick query type'}), 400
        
        success, result = execute_safe_query(query)
        
        if not success:
            return jsonify({'error': f'Query error: {result}'}), 400
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'query_type': query_type
        }), 200
        
    except Exception as e:
        logging.error(f"Error in admin_quick_query: {e}")
        return jsonify({'error': 'Internal server error'}), 500    
    
@app.route('/api/quick-export/<query_type>/<format>')
@app.route('/api/quick-export/<device_type>/<query_type>/<format>')
@require_admin_auth
def quick_export_data(query_type, format, device_type=None):
    """Export predefined query data with optional device context"""
    from queries_config import get_query_sql
    
    query = get_query_sql(query_type, device_type)
    if not query:
        return jsonify({'error': 'Unknown query type'}), 400
    
    success, result = execute_safe_query(query)
    if not success:
        return jsonify({'error': f'Query error: {result}'}), 400
    
    # Generate filename with device context
    filename = generate_filename(query_type, device_type, format)
    
    # Export based on format
    if format == 'csv':
        return export_to_csv(result, filename)
    elif format == 'json':
        return export_to_json(result, filename)
    else:
        return jsonify({'error': 'Unsupported format. Use csv or json'}), 400

@app.route('/api/admin-export/<format>')
@require_admin_auth
def admin_export_data(format):
    """Export query data in CSV or JSON format"""
    
    query = request.args.get('query', 'SELECT * FROM water_events ORDER BY received_at DESC LIMIT 1000')
    
    # Validate SQL
    is_valid, error_msg = validate_sql_query(query)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    success, result = execute_safe_query(query)
    if not success:
        return jsonify({'error': f'Query error: {result}'}), 400
    
    # Generate filename
    filename = f"water_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    # Export based on format
    if format == 'csv':
        return export_to_csv(result, filename)
    elif format == 'json':
        return export_to_json(result, filename)
    else:
        return jsonify({'error': 'Unsupported format. Use csv or json'}), 400

@app.route('/health', methods=['GET'])
@limiter.limit("30 per minute")
def health_check():
    """Endpoint sprawdzania stanu aplikacji"""
    cleanup_expired_sessions()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
        
            # Policz aktywne sesje z bazy
            cursor.execute('SELECT COUNT(*) FROM admin_sessions')
            active_sessions_count = cursor.fetchone()[0]

            # Policz zablokowane konta
            current_time = int(time.time())
            cursor.execute('''
                SELECT COUNT(*) FROM failed_login_attempts 
                WHERE locked_until IS NOT NULL AND locked_until > ?
            ''', (current_time,))
            locked_accounts_count = cursor.fetchone()[0]
        
    except Exception as e:
        logging.error(f"Health check DB error: {e}")
        active_sessions_count = 0
        locked_accounts_count = 0
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if os.path.exists(Config.DATABASE_PATH) else 'missing',
        'nginx_mode': Config.ENABLE_NGINX_MODE,
        'http_port': Config.HTTP_PORT,
        'admin_port': Config.ADMIN_PORT,
        'session_management': 'database',
        'active_sessions': active_sessions_count,
        'locked_accounts': locked_accounts_count
    }), 200


@app.route('/api/device-health/<device_type>')
@require_admin_auth
def device_health_check(device_type):
    """Check if IoT device is reachable through WireGuard"""
    from utils.health_check import check_device_health
    from device_config import DEVICE_NETWORK_CONFIG
    
    if device_type not in DEVICE_NETWORK_CONFIG:
        return jsonify({'error': f'Unknown device type: {device_type}'}), 404
    
    health = check_device_health(device_type)
    
    return jsonify({
        'success': True,
        'device_type': device_type,
        'online': health['online'],
        'latency_ms': health.get('latency_ms'),
        'cached': health.get('cached', False)
    }), 200



@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

def run_http_server():
    """Uruchom HTTP server dla ESP32 API"""
    logging.info(f"Starting HTTP server on port {Config.HTTP_PORT} for ESP32 API")
    app.run(host='0.0.0.0', port=Config.HTTP_PORT, debug=False, threaded=True)

def run_admin_server():
    """Uruchom HTTP server dla Admin Panel (Nginx obsługuje SSL)"""
    logging.info(f"Starting Admin server on port {Config.ADMIN_PORT} (HTTP - Nginx handles SSL)")
    app.run(host='0.0.0.0', port=Config.ADMIN_PORT, debug=False, threaded=True)

if __name__ == '__main__':
    # Inicjalizuj bazę danych przy starcie
    init_database()
    
    logging.info("IOT VPS Logger started (Nginx Mode)")
    logging.info(f"Database: {Config.DATABASE_PATH}")
    # logging.info(f"Log file: {LOG_PATH}")
    logging.info(f"Session timeout: {Config.SESSION_TIMEOUT_MINUTES} minutes")
    logging.info(f"Account lockout: {Config.MAX_FAILED_ATTEMPTS} attempts, {Config.LOCKOUT_DURATION_HOURS}h ban")
    logging.info(f"Nginx reverse proxy mode: {Config.ENABLE_NGINX_MODE}")
    
    # Dual-server setup bez SSL (Nginx obsługuje SSL)
    logging.info("Starting dual-server setup (HTTP only - Nginx handles SSL):")
    logging.info(f"  - HTTP  (ESP32 API): http://0.0.0.0:{Config.HTTP_PORT}")
    logging.info(f"  - HTTP  (Admin Panel): http://0.0.0.0:{Config.ADMIN_PORT}")
    logging.info("External access via Nginx:")
    logging.info(f"  - ESP32 API: https://app.krzysztoforlinski.pl/api/")
    logging.info(f"  - Admin Panel: https://app.krzysztoforlinski.pl/admin")
    
    # Uruchom HTTP server w osobnym wątku
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Uruchom Admin server w głównym wątku
    run_admin_server()






    