"""
Centralna konfiguracja zapytań SQL dla Multi-Device IoT Platform
Device-specific queries with contextual filtering
"""

# Base queries applicable to all device types
BASE_QUERIES = {
    'last24h': {
        'name': 'Last 24 Hours',
        'description': 'Events from last 24 hours',
        'sql': """
            SELECT {columns}
            FROM water_events 
            WHERE received_at > datetime('now', '-24 hours') 
            {device_filter}
            ORDER BY received_at DESC
        """
    },
    
    'last_100_events': {
        'name': 'Last 100 Events',
        'description': 'Last 100 events',
        'sql': """
            SELECT {columns}
            FROM water_events 
            WHERE 1=1 {device_filter}
            ORDER BY received_at DESC 
            LIMIT 100
        """
    },
    
    'all_events': {
        'name': 'All Events',
        'description': 'All events',
        'sql': """
            SELECT {columns}
            FROM water_events 
            WHERE 1=1 {device_filter}
            ORDER BY received_at DESC
        """
    },
    
    'errors': {
        'name': 'System Errors',
        'description': 'Events with error status',
        'sql': """
            SELECT {columns}
            FROM water_events 
            WHERE system_status = 'ERROR' {device_filter}
            ORDER BY received_at DESC
        """
    },
    
    'today_stats': {
        'name': "Today's Statistics",
        'description': 'Event counts and volumes for today',
        'sql': """
            SELECT event_type, COUNT(*) as count, 
                   COALESCE(SUM(volume_ml), 0) as total_ml 
            FROM water_events 
            WHERE DATE(received_at) = DATE('now') {device_filter}
            GROUP BY event_type
        """
    }
}

# Device-specific queries
DEVICE_SPECIFIC_QUERIES = {
    'water_system': {
        'algorithm_stats': {
            'name': 'Algorithm Statistics',
            'description': 'Weekly algorithm performance stats',
            'sql': """
                SELECT 
                    COUNT(*) as Total_Cycles,
                    ROUND(AVG(time_gap_1), 2) as Avg_Turn_ON_Delay,
                    ROUND(AVG(time_gap_2), 2) as Avg_Turn_OFF_Delay,
                    ROUND(AVG(water_trigger_time), 2) as Avg_Water_Fill_Delay,
                    ROUND(AVG(pump_duration), 2) as Avg_Pump_Run_Time,
                    SUM(gap1_fail_sum) as Total_Turn_ON_Failures,
                    SUM(gap2_fail_sum) as Total_Turn_OFF_Failures,
                    SUM(water_fail_sum) as Total_Water_Fill_Failures
                FROM water_events 
                WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
                    AND received_at > datetime('now', '-7 days')
                    {device_filter}
            """
        },
        
        'algorithm_failures': {
            'name': 'Algorithm Issues',
            'description': 'Cycles with failures or multiple attempts',
            'sql': """
                SELECT id, timestamp, device_id, time_gap_1, time_gap_2, water_trigger_time,
                       gap1_fail_sum, gap2_fail_sum, water_fail_sum, pump_attempts, 
                       pump_duration, volume_ml, algorithm_data, received_at
                FROM water_events 
                WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
                    AND (gap1_fail_sum > 0 OR gap2_fail_sum > 0 OR water_fail_sum > 0 OR pump_attempts > 1)
                    {device_filter}
                ORDER BY received_at DESC
            """
        },
        
        'pump_operations': {
            'name': 'Pump Operations',
            'description': 'All pump-related events',
            'sql': """
                SELECT id, device_id, timestamp, event_type, volume_ml, 
                       pump_duration, pump_attempts, water_status, system_status, received_at
                FROM water_events 
                WHERE event_type IN ('AUTO_PUMP', 'MANUAL_NORMAL', 'MANUAL_EXTENDED', 'AUTO_CYCLE_COMPLETE')
                    {device_filter}
                ORDER BY received_at DESC
            """
        },
        
        'statistics_resets': {
            'name': 'Statistics Resets',
            'description': 'Recent statistics reset events',
            'sql': """
                SELECT id, device_id, timestamp, received_at, client_ip
                FROM water_events 
                WHERE event_type = 'STATISTICS_RESET' {device_filter}
                ORDER BY received_at DESC LIMIT 20
            """
        }
    },
    
    'temperature_sensor': {
        'temperature_readings': {
            'name': 'Temperature Readings',
            'description': 'Recent temperature measurements',
            'sql': """
                SELECT id, device_id, timestamp, temperature, humidity, 
                       system_status, received_at
                FROM water_events 
                WHERE temperature IS NOT NULL {device_filter}
                ORDER BY received_at DESC
            """
        },
        
        'temperature_trends': {
            'name': 'Temperature Trends',
            'description': 'Hourly temperature averages',
            'sql': """
                SELECT 
                    DATE(received_at) as date,
                    HOUR(received_at) as hour,
                    ROUND(AVG(temperature), 1) as avg_temp,
                    ROUND(AVG(humidity), 1) as avg_humidity,
                    COUNT(*) as readings
                FROM water_events 
                WHERE temperature IS NOT NULL 
                    AND received_at > datetime('now', '-24 hours')
                    {device_filter}
                GROUP BY DATE(received_at), HOUR(received_at)
                ORDER BY received_at DESC
            """
        }
    },
    
    'security_system': {
        'security_events': {
            'name': 'Security Events',
            'description': 'Recent security events',
            'sql': """
                SELECT id, device_id, timestamp, zone_status, motion_detected,
                       system_status, received_at
                FROM water_events 
                WHERE zone_status IS NOT NULL OR motion_detected IS NOT NULL
                    {device_filter}
                ORDER BY received_at DESC
            """
        },
        
        'security_alerts': {
            'name': 'Security Alerts',
            'description': 'Motion detection and alerts',
            'sql': """
                SELECT id, device_id, timestamp, event_type, zone_status, 
                       motion_detected, system_status, received_at
                FROM water_events 
                WHERE motion_detected = 1 OR event_type LIKE '%MOTION%'
                    {device_filter}
                ORDER BY received_at DESC
            """
        }
    }
}

def get_query_sql(query_type, device_type=None):
    """Get SQL for given query type with optional device filtering"""
    from device_config import get_device_columns
    
    # Check base queries first
    if query_type in BASE_QUERIES:
        query_config = BASE_QUERIES[query_type]
        sql = query_config['sql']
        
        # Get appropriate columns for device type
        if device_type:
            columns = ', '.join(get_device_columns(device_type))
            device_filter = f"AND device_type = '{device_type}'"
        else:
            columns = '*'
            device_filter = ''
        
        return sql.format(columns=columns, device_filter=device_filter).strip()
    
    # Check device-specific queries
    if device_type and device_type in DEVICE_SPECIFIC_QUERIES:
        device_queries = DEVICE_SPECIFIC_QUERIES[device_type]
        if query_type in device_queries:
            query_config = device_queries[query_type]
            sql = query_config['sql']
            device_filter = f"AND device_type = '{device_type}'"
            return sql.format(device_filter=device_filter).strip()
    
    return None

def get_available_queries(device_type=None):
    """Get available queries for device type"""
    queries = {}
    
    # Add base queries (available for all device types)
    for query_id, config in BASE_QUERIES.items():
        queries[query_id] = {
            'name': config['name'],
            'description': config['description'],
            'category': 'general'
        }
    
    # Add device-specific queries
    if device_type and device_type in DEVICE_SPECIFIC_QUERIES:
        for query_id, config in DEVICE_SPECIFIC_QUERIES[device_type].items():
            queries[query_id] = {
                'name': config['name'], 
                'description': config['description'],
                'category': device_type
            }
    
    return queries

def get_query_info(query_type, device_type=None):
    """Get full query information"""
    # Check base queries
    if query_type in BASE_QUERIES:
        return BASE_QUERIES[query_type]
    
    # Check device-specific queries
    if device_type and device_type in DEVICE_SPECIFIC_QUERIES:
        device_queries = DEVICE_SPECIFIC_QUERIES[device_type]
        if query_type in device_queries:
            return device_queries[query_type]
    
    return None

# Legacy support for existing QUICK_QUERIES
QUICK_QUERIES = BASE_QUERIES.copy()

if 'water_system' in DEVICE_SPECIFIC_QUERIES:
    QUICK_QUERIES.update(DEVICE_SPECIFIC_QUERIES['water_system'])

def get_all_queries_sql():
    """Legacy function - get all queries as dict"""
    return {key: query['sql'].strip() for key, query in QUICK_QUERIES.items()}

def get_all_queries_metadata():
    """Legacy function - get metadata for all queries"""
    return {key: {'name': query['name'], 'description': query['description']} 
            for key, query in QUICK_QUERIES.items()}




