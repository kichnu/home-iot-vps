"""
Database layer for Home IoT Platform
- Connection management with context manager
- Database initialization and migrations
- Safe query execution
"""

from .connection import get_db_connection, init_database_path
from .init import init_database
from .queries import execute_safe_query

__all__ = [
    'get_db_connection',
    'init_database_path',
    'init_database',
    'execute_safe_query'
]