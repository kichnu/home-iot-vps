"""
Data export utilities for Home IoT Platform
Exports query results to CSV and JSON formats
"""

import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
from flask import Response


def generate_filename(
    query_type: str, 
    device_type: Optional[str] = None, 
    extension: str = 'csv'
) -> str:
    """
    Generate timestamped filename for exports.
    
    Args:
        query_type: Type of query being exported
        device_type: Optional device type context
        extension: File extension (csv or json)
        
    Returns:
        Formatted filename string
        
    Example:
        >>> generate_filename('last24h', 'water_system', 'csv')
        'water_system_last24h_20231016_143022.csv'
    """
    filename_parts = []
    if device_type:
        filename_parts.append(device_type)
    filename_parts.append(query_type)
    filename_parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    return f"{'_'.join(filename_parts)}.{extension}"


def export_to_csv(
    data: List[Dict], 
    filename: Optional[str] = None
) -> Response:
    """
    Export query results to CSV format.
    
    Args:
        data: List of dictionaries (query results)
        filename: Optional custom filename
        
    Returns:
        Flask Response object with CSV data
        
    Example:
        >>> results = execute_query("SELECT * FROM water_events LIMIT 10")
        >>> return export_to_csv(results, 'events.csv')
    """
    if filename is None:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output = io.StringIO()
    
    if data:
        # Write CSV with headers
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
    
    return response


def export_to_json(
    data: List[Dict], 
    filename: Optional[str] = None
) -> Response:
    """
    Export query results to JSON format.
    
    Args:
        data: List of dictionaries (query results)
        filename: Optional custom filename
        
    Returns:
        Flask Response object with JSON data
        
    Example:
        >>> results = execute_query("SELECT * FROM water_events LIMIT 10")
        >>> return export_to_json(results, 'events.json')
    """
    if filename is None:
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    response = Response(
        json.dumps(data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
    
    return response