#!/usr/bin/env python3
"""
IoT VPS Gateway - Proxy to IoT devices through WireGuard
Simplified version without database logging functionality
"""

import os
import sys
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import logging
from datetime import datetime
import secrets
from flask_limiter import Limiter
from config import Config
from utils.security import secure_compare, get_real_ip
from database import get_db_connection, init_database_path, init_database
from auth import (
    cleanup_expired_sessions,
    get_failed_attempts_info,
    record_failed_attempt,
    reset_failed_attempts,
    create_session,
    validate_session,
    destroy_session,
    require_admin_auth
)

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    print("python-dotenv not installed, using system environment variables only")

# Verify configuration on startup
if not Config.verify_required_vars():
    sys.exit(1)

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

app.jinja_env.auto_reload = True

# ============================================
# RATE LIMITING CONFIGURATION
# ============================================

def get_real_ip_for_limiter():
    """Get real client IP for rate limiting (Nginx-aware)."""
    return get_real_ip()

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

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/login')
@limiter.limit("15 per 15 minutes")
def login_page():
    """Login page"""
    if validate_session():
        return redirect(url_for('device_dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
@limiter.limit("15 per 15 minutes")
def login_submit():
    """Handle login with centralized error handling."""
    client_ip = get_real_ip()

    try:
        # Check if account is locked
        attempt_info = get_failed_attempts_info(client_ip)

        if attempt_info.get('is_locked'):
            time_left_seconds = attempt_info.get('time_until_unlock', 0)
            time_left_minutes = max(1, time_left_seconds // 60)

            flash(
                f'Account temporarily locked due to too many failed attempts. '
                f'Try again in {time_left_minutes} minutes.',
                'error'
            )
            logging.warning(
                f"Blocked login attempt from locked IP: {client_ip} "
                f"(unlocks in {time_left_minutes} minutes)"
            )
            return render_template('login.html'), 429

        # Validate password
        password = request.form.get('password', '')

        if not password:
            flash('Password is required.', 'error')
            return render_template('login.html'), 400

        if secure_compare(password, Config.ADMIN_PASSWORD):
            # Successful login
            reset_failed_attempts(client_ip)
            create_session(client_ip)
            logging.info(f"Successful admin login from IP: {client_ip}")
            return redirect(url_for('device_dashboard'))

        # Failed login - record attempt
        result = record_failed_attempt(client_ip)

        if result.get('is_locked'):
            flash(
                f'Too many failed attempts. Account locked for '
                f'{result["lockout_duration_hours"]} hour(s).',
                'error'
            )
            logging.warning(
                f"Failed admin login from IP: {client_ip} "
                f"(attempt {result['attempt_count']}/{Config.MAX_FAILED_ATTEMPTS}) - ACCOUNT LOCKED"
            )
            return render_template('login.html'), 429
        else:
            remaining = result.get('remaining_attempts', 0)
            flash(f'Invalid password. {remaining} attempts remaining.', 'error')
            logging.warning(
                f"Failed admin login from IP: {client_ip} "
                f"(attempt {result['attempt_count']}/{Config.MAX_FAILED_ATTEMPTS}, {remaining} remaining)"
            )
            return render_template('login.html'), 401

    except Exception as e:
        logging.error(f"Login error for IP {client_ip}: {e}", exc_info=True)
        flash(
            'An error occurred during login. Please try again or contact administrator.',
            'error'
        )
        return render_template('login.html'), 500


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """User logout"""
    client_ip = get_real_ip()
    destroy_session()
    logging.info(f"Admin logout from IP: {client_ip}")
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login_page'))


# ============================================
# DASHBOARD ROUTES
# ============================================

@app.route('/')
@app.route('/admin')
@require_admin_auth
def admin_dashboard():
    """Redirect to dashboard"""
    return redirect(url_for('device_dashboard'))


@app.route('/dashboard')
@require_admin_auth
def device_dashboard():
    """Multi-device dashboard"""
    client_ip = get_real_ip()

    try:
        from device_config import DEVICE_NETWORK_CONFIG, get_device_config, get_device_network_config

        # Build device list from network config (devices with dashboards)
        discovered_types = []
        for device_type, network_config in DEVICE_NETWORK_CONFIG.items():
            if network_config.get('has_local_dashboard'):
                config = get_device_config(device_type)
                discovered_types.append({
                    'type': device_type,
                    'name': config.get('name', device_type.title()),
                    'icon': config.get('icon', ''),
                    'color': config.get('color', '#95a5a6'),
                    'description': config.get('description', ''),
                    'proxy_path': network_config.get('proxy_path', ''),
                    'has_local_dashboard': True
                })

        logging.info(f"Dashboard accessed from {client_ip} - {len(discovered_types)} devices")

        return render_template('dashboard.html',
                             device_types=discovered_types,
                             recent_activity=[])

    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        return jsonify({'error': 'Dashboard error'}), 500


# ============================================
# API ROUTES
# ============================================

@app.route('/api/auth-check')
@limiter.exempt
def auth_check():
    """
    Internal endpoint for Nginx auth_request.
    Returns 200 if session valid, 401 if not.
    Used to protect /device/* proxy routes.
    """
    if validate_session():
        return '', 200
    return '', 401


@app.route('/api/session-info')
@require_admin_auth
def session_info():
    """Session information for frontend"""
    session_data = {
        'authenticated': True,
        'login_time': session.get('login_time'),
        'timeout_minutes': Config.SESSION_TIMEOUT_MINUTES,
        'client_ip': get_real_ip()
    }
    return jsonify(session_data)


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


@app.route('/health', methods=['GET'])
@limiter.limit("30 per minute")
def health_check():
    """Application health check endpoint"""
    cleanup_expired_sessions()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM admin_sessions')
            active_sessions_count = cursor.fetchone()[0]

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
        'admin_port': Config.ADMIN_PORT,
        'session_management': 'database',
        'active_sessions': active_sessions_count,
        'locked_accounts': locked_accounts_count
    }), 200


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405


# ============================================
# SERVER STARTUP
# ============================================

def run_admin_server():
    """Run HTTP server for Admin Panel (Nginx handles SSL)"""
    logging.info(f"Starting Admin server on port {Config.ADMIN_PORT} (HTTP - Nginx handles SSL)")
    app.run(host='0.0.0.0', port=Config.ADMIN_PORT, debug=False, threaded=True)


if __name__ == '__main__':
    # Initialize database on startup - MUST succeed before starting server
    if not init_database():
        logging.critical("FATAL: Cannot start server without working database")
        logging.critical(f"Check path and permissions: {Config.DATABASE_PATH}")
        sys.exit(1)

    logging.info("IoT VPS Gateway started (Nginx Mode)")
    logging.info(f"Database: {Config.DATABASE_PATH}")
    logging.info(f"Session timeout: {Config.SESSION_TIMEOUT_MINUTES} minutes")
    logging.info(f"Account lockout: {Config.MAX_FAILED_ATTEMPTS} attempts, {Config.LOCKOUT_DURATION_HOURS}h ban")
    logging.info(f"Nginx reverse proxy mode: {Config.ENABLE_NGINX_MODE}")

    logging.info(f"Starting server on http://0.0.0.0:{Config.ADMIN_PORT}")
    logging.info("External access via Nginx: https://app.krzysztoforlinski.pl/")

    run_admin_server()
