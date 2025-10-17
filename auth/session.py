"""
Session management for admin panel
Database-backed sessions with security features:
- Session expiration and cleanup
- Failed login attempts tracking
- Account lockout mechanism
- IP-based session validation
"""

import time
import secrets
import logging
from datetime import datetime
from typing import Optional
from flask import session, request
from database import get_db_connection
from config import Config
from utils.security import get_real_ip


def cleanup_expired_sessions() -> None:
    """
    Clean up expired sessions and lockouts from database.
    
    Removes:
    - Sessions older than SESSION_TIMEOUT_MINUTES
    - Failed attempts older than 1 hour (if not locked)
    - Expired account lockouts
    
    Called periodically and before session validation.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Timeout in seconds
            session_timeout = Config.SESSION_TIMEOUT_MINUTES * 60
            lockout_duration = Config.LOCKOUT_DURATION_HOURS * 3600
            current_time = int(time.time())
            
            # Delete expired sessions
            cursor.execute('''
                DELETE FROM admin_sessions 
                WHERE last_activity < ?
            ''', (current_time - session_timeout,))
            deleted_sessions = cursor.rowcount
            
            # Delete old failed attempts (after 1 hour if not locked)
            cursor.execute('''
                DELETE FROM failed_login_attempts 
                WHERE last_attempt < ? AND locked_until IS NULL
            ''', (current_time - 3600,))
            
            # Unlock expired lockouts
            cursor.execute('''
                UPDATE failed_login_attempts 
                SET locked_until = NULL, attempt_count = 0
                WHERE locked_until IS NOT NULL AND locked_until < ?
            ''', (current_time,))
            unlocked = cursor.rowcount
            
            # Context manager auto-commits
            
            if deleted_sessions > 0:
                logging.debug(f"Cleaned up {deleted_sessions} expired sessions")
            if unlocked > 0:
                logging.info(f"Unlocked {unlocked} expired account lockouts")
                
    except Exception as e:
        logging.error(f"Session cleanup error: {e}")


def is_account_locked(client_ip: str) -> bool:
    """
    Check if account is locked due to failed login attempts.
    
    Args:
        client_ip: Client IP address to check
        
    Returns:
        True if account is locked, False otherwise
        
    Example:
        >>> if is_account_locked(client_ip):
        >>>     return "Account locked", 429
    """
    cleanup_expired_sessions()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())
            
            cursor.execute('''
                SELECT locked_until 
                FROM failed_login_attempts 
                WHERE client_ip = ? AND locked_until IS NOT NULL
            ''', (client_ip,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                if result[0] > current_time:
                    return True
                else:
                    return False
            
            return False
            
    except Exception as e:
        logging.error(f"Error checking account lock: {e}")
        return False


def record_failed_attempt(client_ip: str) -> bool:
    """
    Record failed login attempt and lock account if threshold exceeded.
    
    Args:
        client_ip: Client IP address
        
    Returns:
        True if account was locked, False otherwise
        
    Example:
        >>> is_locked = record_failed_attempt(client_ip)
        >>> if is_locked:
        >>>     flash(f'Account locked for {LOCKOUT_DURATION_HOURS} hours')
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())
            lockout_until = current_time + (Config.LOCKOUT_DURATION_HOURS * 3600)
            
            # Check current state
            cursor.execute('''
                SELECT attempt_count FROM failed_login_attempts 
                WHERE client_ip = ?
            ''', (client_ip,))
            
            result = cursor.fetchone()
            
            if result:
                # Increment counter
                new_count = result[0] + 1
                
                if new_count >= Config.MAX_FAILED_ATTEMPTS:
                    # LOCK ACCOUNT
                    cursor.execute('''
                        UPDATE failed_login_attempts 
                        SET attempt_count = ?, last_attempt = ?, locked_until = ?
                        WHERE client_ip = ?
                    ''', (new_count, current_time, lockout_until, client_ip))
                    
                    logging.warning(
                        f"🔒 Account locked for IP {client_ip} after "
                        f"{Config.MAX_FAILED_ATTEMPTS} failed attempts"
                    )
                    return True
                else:
                    # Increment counter without locking
                    cursor.execute('''
                        UPDATE failed_login_attempts 
                        SET attempt_count = ?, last_attempt = ?
                        WHERE client_ip = ?
                    ''', (new_count, current_time, client_ip))
            else:
                # First failed attempt
                cursor.execute('''
                    INSERT INTO failed_login_attempts 
                    (client_ip, attempt_count, last_attempt)
                    VALUES (?, 1, ?)
                ''', (client_ip, current_time))
            
            return False
            
    except Exception as e:
        logging.error(f"Error recording failed attempt: {e}")
        return False


def reset_failed_attempts(client_ip: str) -> None:
    """
    Reset failed login attempts counter after successful login.
    
    Args:
        client_ip: Client IP address
        
    Example:
        >>> reset_failed_attempts(client_ip)
        >>> create_session(client_ip)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM failed_login_attempts 
                WHERE client_ip = ?
            ''', (client_ip,))
            
    except Exception as e:
        logging.error(f"Error resetting failed attempts: {e}")


def create_session(client_ip: str) -> Optional[str]:
    """
    Create new admin session in database.
    
    Args:
        client_ip: Client IP address
        
    Returns:
        Session ID if successful, None otherwise
        
    Example:
        >>> session_id = create_session(client_ip)
        >>> if session_id:
        >>>     return redirect('/admin')
    """
    try:
        session_id = secrets.token_urlsafe(32)
        current_time = int(time.time())
        user_agent = request.headers.get('User-Agent', 'Unknown')[:200]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admin_sessions 
                (session_id, client_ip, created_at, last_activity, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, client_ip, current_time, current_time, user_agent))
        
        # Set Flask session
        session.permanent = True
        session['session_id'] = session_id
        session['authenticated'] = True
        session['login_time'] = datetime.now().isoformat()
        
        logging.info(f"✅ New session created for IP: {client_ip}")
        return session_id
        
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        return None


def validate_session() -> bool:
    """
    Validate current admin session.
    
    Checks:
    - Session exists in Flask session
    - Session exists in database
    - Session not expired
    - IP matches (optional in Nginx mode)
    
    Updates last_activity on successful validation.
    
    Returns:
        True if session valid, False otherwise
        
    Example:
        >>> if not validate_session():
        >>>     return redirect('/login')
    """
    cleanup_expired_sessions()
    
    if 'session_id' not in session or 'authenticated' not in session:
        return False
    
    session_id = session['session_id']
    client_ip = get_real_ip()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())
            session_timeout = Config.SESSION_TIMEOUT_MINUTES * 60
            
            cursor.execute('''
                SELECT client_ip, last_activity 
                FROM admin_sessions 
                WHERE session_id = ?
            ''', (session_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return False
            
            stored_ip, last_activity = result
            
            # Check timeout
            if current_time - last_activity > session_timeout:
                cursor.execute('DELETE FROM admin_sessions WHERE session_id = ?', (session_id,))
                logging.info(f"⏱️ Session expired for {client_ip}")
                return False
            
            # Check IP (optional in Nginx mode)
            if stored_ip != client_ip and not Config.ENABLE_NGINX_MODE:
                logging.warning(f"⚠️ Session IP mismatch: {stored_ip} vs {client_ip}")
                return False
            
            # Update last activity
            cursor.execute('''
                UPDATE admin_sessions 
                SET last_activity = ? 
                WHERE session_id = ?
            ''', (current_time, session_id))
            
            return True
            
    except Exception as e:
        logging.error(f"Session validation error: {e}")
        return False


def destroy_session() -> None:
    """
    Destroy current admin session.
    
    Removes session from database and clears Flask session.
    
    Example:
        >>> destroy_session()
        >>> return redirect('/login')
    """
    if 'session_id' in session:
        session_id = session['session_id']
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM admin_sessions 
                    WHERE session_id = ?
                ''', (session_id,))
            
            logging.info(f"🗑️ Session destroyed: {session_id[:8]}...")
            
        except Exception as e:
            logging.error(f"Error destroying session: {e}")
    
    session.clear()