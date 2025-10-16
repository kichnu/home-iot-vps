"""
Database connection management with context manager
Centralized database operations for Home IoT Platform
"""

import sqlite3
import logging
from contextlib import contextmanager
import os

# Import from app.py (będzie dostępne po imporcie)
DATABASE_PATH = None

def init_database_path(path):
    """Initialize database path from main app"""
    global DATABASE_PATH
    DATABASE_PATH = path

@contextmanager
def get_db_connection(row_factory=True):
    """
    Context manager for database connections.
    
    Args:
        row_factory: If True, returns dict-like rows. If False, returns tuples.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM water_events")
            results = cursor.fetchall()
        # Connection auto-commits and closes
    
    Example with manual control:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT ...")
                conn.commit()
            except:
                conn.rollback()
                raise
    """
    if DATABASE_PATH is None:
        raise RuntimeError("Database path not initialized. Call init_database_path() first.")
    
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        
        if row_factory:
            conn.row_factory = sqlite3.Row
        
        # Set pragmas for better performance
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA mmap_size=30000000000')
        
        yield conn
        
        # Auto-commit if no exception
        conn.commit()
        
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        raise
        
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None, fetch=True):
    """
    Execute a single query with automatic connection management.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: If True, returns results. If False, returns rowcount.
    
    Returns:
        List of dicts (if fetch=True) or rowcount (if fetch=False)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch:
            return [dict(row) for row in cursor.fetchall()]
        else:
            return cursor.rowcount