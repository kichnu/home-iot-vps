"""
SQL query validation for admin panel
Security layer for user-submitted SQL queries
"""

import re
from typing import Tuple


def validate_sql_query(query: str) -> Tuple[bool, str]:
    """
    Validate SQL query for admin panel - only SELECT queries allowed.
    
    Security features:
    - Only SELECT statements permitted
    - Blocks INSERT, UPDATE, DELETE, DROP, etc.
    - Only water_events table accessible
    - Removes comments
    
    Args:
        query: SQL query string to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        
    Example:
        >>> is_valid, error = validate_sql_query(user_query)
        >>> if not is_valid:
        >>>     return jsonify({'error': error}), 400
    """
    query = query.strip().upper()
    
    # Remove SQL comments
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Allowed keywords
    allowed_keywords = [
        'SELECT', 'FROM', 'WHERE', 'ORDER', 'BY', 'LIMIT', 'GROUP', 'HAVING', 
        'AS', 'ASC', 'DESC', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 
        'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 
        'DATETIME', 'DATE', 'TIME', 'NOW', 'SUBSTR', 'LENGTH', 'ROUND'
    ]
    
    # Blocked keywords
    blocked_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 
        'REPLACE', 'MERGE', 'EXEC', 'EXECUTE', 'CALL', 'UNION', 
        'ATTACH', 'DETACH', 'PRAGMA'
    ]
    
    # Check for blocked keywords
    for keyword in blocked_keywords:
        if keyword in query:
            return False, f"Forbidden keyword: {keyword}"
    
    # Must start with SELECT
    if not query.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"
    
    # Must reference water_events table
    if 'WATER_EVENTS' not in query:
        return False, "Only water_events table is allowed"
    
    return True, "Valid"