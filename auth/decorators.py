"""
Authentication decorators for Flask routes
"""

from functools import wraps
from flask import request, jsonify, redirect, url_for
from auth.session import validate_session


def require_admin_auth(f):
    """
    Decorator for admin panel authentication.

    Validates session-based authentication.
    Redirects to login page for browser requests.
    Returns 401 JSON for API requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_session():
            # Redirect to login for dashboard/admin pages
            if request.endpoint in ('admin_dashboard', 'device_dashboard'):
                return redirect(url_for('login_page'))
            # Return JSON error for API endpoints
            return jsonify({'error': 'Authentication required'}), 401

        return f(*args, **kwargs)

    return decorated_function
