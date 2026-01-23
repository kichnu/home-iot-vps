"""
Database layer for IoT Gateway
- Connection management with context manager
- Database initialization for session management
"""

from .connection import get_db_connection, init_database_path
from .init import init_database

__all__ = [
    'get_db_connection',
    'init_database_path',
    'init_database'
]
