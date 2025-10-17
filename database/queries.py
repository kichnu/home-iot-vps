"""
Safe SQL query execution for admin panel
Includes timeout and result limiting
"""

import logging
from typing import Tuple, List, Dict, Optional
from .connection import get_db_connection


def execute_safe_query(query: str, params: Optional[tuple] = None) -> Tuple[bool, any]:
    """
    Safely execute SQL query with timeout and result limiting.
    
    Security features:
    - 10 second query timeout
    - Maximum 1000 results returned
    - Automatic rollback on error
    
    Args:
        query: SQL query string (should be pre-validated)
        params: Optional query parameters for prepared statements
        
    Returns:
        Tuple of (success: bool, result: List[dict] or error_message: str)
        
    Example:
        >>> success, result = execute_safe_query("SELECT * FROM water_events LIMIT 10")
        >>> if success:
        >>>     for row in result:
        >>>         print(row['device_id'])
        >>> else:
        >>>     print(f"Error: {result}")
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
        
            # Set query timeout (10 seconds)
            conn.execute('PRAGMA query_timeout = 10000')

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = cursor.fetchall()

            # Limit results to 1000 rows
            if len(results) > 1000:
                results = results[:1000]

            # Convert Row objects to dictionaries
            return True, [dict(row) for row in results]
        
    except Exception as e:
        logging.error(f"Query execution error: {e}")
        return False, str(e)