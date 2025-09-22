"""
Device Type Configuration for Multi-IoT Platform
Central configuration for all supported device types
"""

# Device type mappings: device_id -> device_type
DEVICE_TYPE_MAPPING = {
    'DOLEWKA': 'water_system',
    'ESP32_DEVICE_002': 'temperature_sensor',
    'TEMP_SALON': 'temperature_sensor',
    'TEMP_OUTDOOR': 'temperature_sensor', 
    'SECURITY_01': 'security_system',
    'SECURITY_DOOR': 'security_system',
}

# Device type definitions
DEVICE_TYPES = {
    'water_system': {
        'name': 'Water Management',
        'description': 'Aquarium water level and pump control systems',
        'icon': '🐠',
        'color': '#3498db',
        'columns': [
            'id', 'device_id', 'timestamp', 'event_type', 'volume_ml',
            'pump_duration', 'pump_attempts', 'time_gap_1', 'time_gap_2',
            'water_trigger_time', 'gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum',
            'water_status', 'system_status', 'received_at'
        ],
        'event_types': ['AUTO_PUMP', 'MANUAL_NORMAL', 'MANUAL_EXTENDED', 'AUTO_CYCLE_COMPLETE', 'STATISTICS_RESET']
    },
    
    'temperature_sensor': {
        'name': 'Temperature Monitoring', 
        'description': 'Environmental temperature and humidity sensors',
        'icon': '🌡️',
        'color': '#e74c3c',
        'columns': [
            'id', 'device_id', 'timestamp', 'temperature', 'humidity',
            'system_status', 'received_at'
        ],
        'event_types': ['TEMP_READING', 'HUMIDITY_READING', 'SENSOR_ERROR']
    },
    
    'security_system': {
        'name': 'Security Monitoring',
        'description': 'Door sensors, motion detectors, security cameras', 
        'icon': '🔒',
        'color': '#95a5a6',
        'columns': [
            'id', 'device_id', 'timestamp', 'zone_status', 'motion_detected',
            'system_status', 'received_at'
        ],
        'event_types': ['DOOR_OPEN', 'DOOR_CLOSE', 'MOTION_DETECTED', 'SYSTEM_ARM', 'SYSTEM_DISARM']
    }
}

def get_device_type(device_id):
    """Get device type for given device_id"""
    return DEVICE_TYPE_MAPPING.get(device_id, 'unknown')

def get_device_config(device_type):
    """Get configuration for device type"""
    return DEVICE_TYPES.get(device_type, {})

def get_available_device_types():
    """Get list of device types that have data in database"""
    # This will be implemented to query database
    return list(DEVICE_TYPES.keys())

def get_device_columns(device_type):
    """Get relevant columns for device type"""
    config = get_device_config(device_type)
    return config.get('columns', [])