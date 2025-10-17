"""
Database connection management with context manager pattern
WAL mode enabled for better concurrency
"""

import sqlite3
import logging
from contextlib import contextmanager
from config import Config


# Global database path (set by init_database_path or use Config default)
DATABASE_PATH = None


def init_database_path(path: str) -> None:
    """
    Initialize the global database path.
    
    Args:
        path: Full path to SQLite database file
        
    Example:
        >>> init_database_path('/opt/home-iot/data/database/water_events.db')
    """
    global DATABASE_PATH
    DATABASE_PATH = path
    logging.info(f"Database path initialized: {path}")


@contextmanager
def get_db_connection(row_factory: bool = True):
    """
    Context manager for database connections with WAL mode.
    
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
    
    Yields:
        sqlite3.Connection: Database connection object
        
    Raises:
        RuntimeError: If database path not initialized
    """
    db_path = DATABASE_PATH or Config.DATABASE_PATH
    if db_path is None:
        raise RuntimeError("Database path not initialized.")
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        
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


def execute_query(query: str, params: tuple = None):
    """
    Execute a query and return results (legacy wrapper).
    
    Args:
        query: SQL query string
        params: Optional query parameters
        
    Returns:
        List of Row objects (dict-like)
        
    Note: Prefer using get_db_connection() context manager directly.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()