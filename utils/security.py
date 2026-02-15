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


TRUSTED_PROXY_IPS = ('127.0.0.1', '::1')


def get_real_ip() -> str:
    """
    Extract real client IP address (Nginx reverse proxy aware).

    Trust boundary: X-Real-IP / X-Forwarded-For headers are only trusted
    when request.remote_addr is a known proxy (localhost). This prevents
    IP spoofing via forged headers on direct connections to port 5001.

    Returns:
        Client IP address as string
    """
    if Config.ENABLE_NGINX_MODE and request.remote_addr in TRUSTED_PROXY_IPS:
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

    return request.remote_addr