"""
Device Type Configuration for Multi-IoT Platform
Central configuration for all supported device types
"""
# available columns for queries in queries_config.py:
#         'columns': [
#         'id', 'device_id', 'timestamp', 'event_type', 'volume_ml',
#         'pump_duration', 'pump_attempts', 'time_gap_1', 'time_gap_2',
#         'water_trigger_time', 'gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum',
#         'water_status', 'system_status', 'received_at','daily_volume_ml'
#     ],

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
        'name': 'Auto Top Off',
        'description': 'Auto Top Off Aquarium Water System',
        'icon': '🐠',
        'color': '#3498db',
        'columns': [
            'id', 'device_id', 'timestamp', 'event_type', 'volume_ml',
            'pump_duration', 'pump_attempts', 'time_gap_1', 'time_gap_2',
            'water_trigger_time', 'gap1_fail_sum', 'gap2_fail_sum', 'water_fail_sum',
            'water_status', 'system_status', 'daily_volume_ml'
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


# ============================================
# NETWORK CONFIGURATION FOR DEVICE PROXY
# Used by health check and dashboard
# ============================================

DEVICE_NETWORK_CONFIG = {
    'water_system': {
        'lan_ip': '192.168.10.2',
        'lan_port': 80,
        'proxy_path': '/device/top_off_water',
        'health_endpoint': '/api/status',
        'has_local_dashboard': True,
        'timeout_seconds': 5
    },
    # Future devices can be added here:
    # 'temperature_sensor': {
    #     'lan_ip': '192.168.10.3',
    #     'lan_port': 80,
    #     'proxy_path': '/device/temp_sensor',
    #     'health_endpoint': '/api/status',
    #     'has_local_dashboard': True,
    #     'timeout_seconds': 3
    # },
}


def get_device_network_config(device_type: str) -> dict:
    """Get network configuration for device type"""
    return DEVICE_NETWORK_CONFIG.get(device_type, {})


def get_all_devices_with_dashboard() -> list:
    """Get all devices that have local dashboards"""
    devices = []
    for device_type, network_config in DEVICE_NETWORK_CONFIG.items():
        if network_config.get('has_local_dashboard'):
            device_config = get_device_config(device_type)
            devices.append({
                'type': device_type,
                'name': device_config.get('name', device_type),
                'icon': device_config.get('icon', '📱'),
                'color': device_config.get('color', '#95a5a6'),
                'description': device_config.get('description', ''),
                'proxy_path': network_config.get('proxy_path', ''),
                'has_local_dashboard': True
            })
    return devices