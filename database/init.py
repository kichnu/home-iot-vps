"""
Database initialization and schema management
Creates tables for session management only
"""

import os
import sqlite3
import logging
from config import Config
from .connection import get_db_connection


def init_database() -> bool:
    """
    Initialize SQLite database for session management.

    Creates:
    - admin_sessions table (session management)
    - failed_login_attempts table (security/brute-force protection)

    Called once at application startup.

    Returns:
        True if database initialized successfully, False otherwise
    """
    try:
        # Create directory if needed
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()

        # SESSION TABLES - Database-backed session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                session_id TEXT PRIMARY KEY,
                client_ip TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_activity INTEGER NOT NULL,
                user_agent TEXT
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_activity ON admin_sessions(last_activity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_ip ON admin_sessions(client_ip)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_login_attempts (
                client_ip TEXT PRIMARY KEY,
                attempt_count INTEGER DEFAULT 0,
                last_attempt INTEGER NOT NULL,
                locked_until INTEGER DEFAULT NULL
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_locked_until ON failed_login_attempts(locked_until)')

        conn.commit()
        conn.close()

        # Verify database is readable
        verify_conn = sqlite3.connect(Config.DATABASE_PATH)
        verify_cursor = verify_conn.cursor()
        verify_cursor.execute('SELECT COUNT(*) FROM admin_sessions')
        verify_conn.close()

        logging.info(f"Database initialized: {Config.DATABASE_PATH}")
        return True

    except Exception as e:
        logging.critical(f"FATAL: Database initialization failed: {e}")
        return False
