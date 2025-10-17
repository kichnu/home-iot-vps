"""
Authentication decorators for Flask routes
- require_auth: ESP32 device authentication (Bearer token)
- require_admin_auth: Admin panel authentication (session-based)
"""

import logging
from functools import wraps
from flask import request, jsonify, redirect, url_for
from config import Config
from utils.security import secure_compare, get_real_ip
from auth.session import validate_session


def require_auth(f):
    """
    Decorator for ESP32 device authentication.
    
    Validates Bearer token from Authorization header.
    Used for IoT device endpoints (/api/water-events, etc.)
    
    Example:
        >>> @app.route('/api/water-events', methods=['POST'])
        >>> @require_auth
        >>> def receive_water_event():
        >>>     # ... endpoint logic
    """
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
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not secure_compare(token, Config.API_TOKEN):
            logging.warning(f"Invalid token from {client_ip}: {token[:10]}...")
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin_auth(f):
    """
    Decorator for admin panel authentication.
    
    Validates session-based authentication.
    Used for admin endpoints (/admin, /dashboard, /api/admin-*, etc.)
    
    Redirects to login page for browser requests.
    Returns 401 JSON for API requests.
    
    Example:
        >>> @app.route('/admin')
        >>> @require_admin_auth
        >>> def admin_dashboard():
        >>>     # ... endpoint logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Validate session
        if not validate_session():
            # Redirect to login for dashboard/admin pages
            if request.endpoint == 'admin_dashboard' or request.endpoint == 'device_dashboard':
                return redirect(url_for('login_page'))
            # Return JSON error for API endpoints
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function