"""
Event data validation for ESP32 devices
Validates incoming IoT device payloads
"""

import logging
from typing import Tuple
from config import Config


def validate_event_data(data: dict) -> Tuple[bool, str]:
    """
    Validate event data from ESP32 devices.
    
    Args:
        data: Dictionary containing event data from device
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        
    Example:
        >>> is_valid, error = validate_event_data(payload)
        >>> if not is_valid:
        >>>     return jsonify({'error': error}), 400
    """
    # Timestamp is now OPTIONAL (backwards compatibility)
    required_fields = [
        'device_id', 'unix_time',
        'event_type', 'volume_ml', 'water_status', 'system_status'
    ]
    
    # Check all required fields are present
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Deprecated timestamp field warning
    if 'timestamp' in data:
        logging.warning(f"⚠️ Deprecated 'timestamp' field received from {data.get('device_id')}")
    
    # Validate data types
    try:
        unix_time = int(data['unix_time'])
        volume_ml = int(data['volume_ml'])
    except (ValueError, TypeError):
        return False, "unix_time and volume_ml must be integers"
    
    # Validate device_id
    if data['device_id'] not in Config.VALID_DEVICE_IDS:
        return False, f"Invalid device_id: {data['device_id']}"
    
    # Validate event_type
    valid_event_types = [
        'AUTO_PUMP', 'MANUAL_NORMAL', 'MANUAL_EXTENDED', 
        'AUTO_CYCLE_COMPLETE', 'STATISTICS_RESET'
    ]
    if data['event_type'] not in valid_event_types:
        return False, f"Invalid event_type: {data['event_type']}"
    
    # Validate water_status
    valid_water_statuses = [
        'OK', 'LOW', 'PARTIAL', 'CHECKING', 'NORMAL', 
        'BOTH_LOW', 'SENSOR1_LOW', 'SENSOR2_LOW'
    ]
    if data['water_status'] not in valid_water_statuses:
        return False, f"Invalid water_status: {data['water_status']}"
    
    # Validate algorithm data for AUTO_CYCLE_COMPLETE events
    if data['event_type'] == 'AUTO_CYCLE_COMPLETE':
        algorithm_fields = [
            'time_gap_1', 'time_gap_2', 'water_trigger_time', 
            'pump_duration', 'pump_attempts', 'gap1_fail_sum', 
            'gap2_fail_sum', 'water_fail_sum'
        ]
        
        for field in algorithm_fields:
            if field in data:
                try:
                    field_value = int(data[field])
                    
                    # Validate sensible ranges
                    if field in ['gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum']:
                        if field_value < 0 or field_value > 65535:
                            return False, f"{field} must be 0-65535"
                    
                    if field in ['time_gap_1', 'time_gap_2', 'water_trigger_time', 'pump_duration']:
                        if int(data[field]) < 0:
                            return False, f"{field} must be >= 0"
                    
                    if field == 'pump_attempts':
                        if int(data[field]) < 1 or int(data[field]) > 10:
                            return False, f"{field} must be between 1-10"
                            
                except (ValueError, TypeError):
                    return False, f"{field} must be an integer"
    
    return True, "Valid"