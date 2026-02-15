"""
Authentication and session management for IoT Gateway
"""

from .session import (
    cleanup_expired_sessions,
    get_failed_attempts_info,
    record_failed_attempt,
    reset_failed_attempts,
    create_session,
    validate_session,
    destroy_session
)
from .decorators import require_admin_auth
from .webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    get_registered_credentials,
    delete_credential,
    has_registered_credentials
)

__all__ = [
    'cleanup_expired_sessions',
    'get_failed_attempts_info',
    'record_failed_attempt',
    'reset_failed_attempts',
    'create_session',
    'validate_session',
    'destroy_session',
    'require_admin_auth',
    'generate_registration_options',
    'verify_registration_response',
    'generate_authentication_options',
    'verify_authentication_response',
    'get_registered_credentials',
    'delete_credential',
    'has_registered_credentials',
]
