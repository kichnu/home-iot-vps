"""
Security utilities for Home IoT Platform
- Timing attack protection
- Real IP extraction (Nginx-aware)
"""

import hmac
from flask import request
from config import Config


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    Uses HMAC compare_digest for cryptographic comparison.
    
    Args:
        a: First string to compare
        b: Second string to compare
        
    Returns:
        True if strings match, False otherwise
        
    Example:
        >>> secure_compare(user_token, Config.API_TOKEN)
        True
    """
    if a is None or b is None:
        return False
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def get_real_ip() -> str:
    """
    Extract real client IP address (Nginx reverse proxy aware).
    
    When behind Nginx reverse proxy with proper configuration:
    - Checks X-Real-IP header first
    - Falls back to X-Forwarded-For (takes first IP)
    - Falls back to request.remote_addr
    
    Returns:
        Client IP address as string
        
    Example:
        >>> client_ip = get_real_ip()
        '192.168.1.100'
    """
    if Config.ENABLE_NGINX_MODE:
        # Nginx passes real IP in X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to X-Forwarded-For (first IP is the real client)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
    
    # Direct connection or no proxy headers
    return request.remote_addr