"""
Centralna konfiguracja zapytań SQL dla Water System Admin Panel
Single source of truth dla wszystkich predefiniowanych zapytań
"""

QUICK_QUERIES = {
    'last24h': {
        'name': 'Last 24 Hours',
        'description': 'Events from last 24 hours',
        'sql': """
            SELECT id, device_id, timestamp, event_type, pump_duration, pump_attempts, volume_ml, time_gap_1, time_gap_2, 
            water_trigger_time, gap1_fail_sum, gap2_fail_sum, water_fail_sum, system_status
            FROM water_events 
            WHERE received_at > datetime('now', '-24 hours') 
            ORDER BY received_at DESC
        """
    },

    'last_100_events': {
        'name': 'last_100_events',
        'description': 'Last 100 events of all types',
        'sql': """
            SELECT id, device_id, timestamp, event_type, pump_duration, pump_attempts, volume_ml, time_gap_1, time_gap_2, 
            water_trigger_time, gap1_fail_sum, gap2_fail_sum, water_fail_sum, system_status
            FROM water_events 
            ORDER BY received_at DESC 
            LIMIT 100
        """
    },

    'all_events': {
        'name': 'all_events',
        'description': 'All events of all types',
        'sql': """
            SELECT id, device_id, timestamp, event_type, pump_duration, pump_attempts, volume_ml, time_gap_1, time_gap_2, 
            water_trigger_time, gap1_fail_sum, gap2_fail_sum, water_fail_sum, system_status
            FROM water_events 
            ORDER BY received_at DESC 
        """
    },

    'errors': {
        'name': 'System Errors',
        'description': 'Events with error status',
        'sql': """
            SELECT id, device_id, timestamp, event_type, pump_duration, pump_attempts, volume_ml, time_gap_1, time_gap_2, 
            water_trigger_time, gap1_fail_sum, gap2_fail_sum, water_fail_sum, system_status
            FROM water_events 
            WHERE system_status == 'ERROR' 
            ORDER BY received_at DESC
        """
    },

    'other_events': {
        'name': 'other_events',
        'description': 'Other events',
        'sql': """
            SELECT id, device_id, timestamp, event_type, pump_duration, pump_attempts, volume_ml, time_gap_1, time_gap_2, 
            water_trigger_time, gap1_fail_sum, gap2_fail_sum, water_fail_sum, system_status
            FROM water_events 
            WHERE event_type == 'MANUAL_NORMAL' OR event_type == 'MANUAL_EXTENDED' OR event_type == 'STATISTICS_RESET'
            ORDER BY received_at DESC
        """
    },

    'algorithm_stats': {
    'name': 'Algorithm Statistics',
    'description': 'Weekly algorithm performance stats',
    'sql': """
        SELECT 
            COUNT(*) as Total_Cycles,
            ROUND(AVG(time_gap_1), 2) as Avg_Turn_ON_Delay,
            ROUND(AVG(time_gap_2), 2) as Avg_Turn_OFF_Delay,
            ROUND(AVG(water_trigger_time), 2) as Avg_Wter_Fill_Delay,
            ROUND(AVG(pump_duration), 2) as Avg_Pump_Run_Time
        FROM water_events 
        WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
            AND received_at > datetime('now', '-7 days')
    """
},
    
    'algorithm_failures': {
        'name': 'Algorithm Issues',
        'description': 'Cycles with failures or multiple attempts',
        'sql': """
            SELECT id, timestamp, time_gap_1, time_gap_2, water_trigger_time,
                   gap1_fail_sum, gap2_fail_sum, water_fail_sum, pump_attempts, algorithm_data,
                   last_reset_timestamp
            FROM water_events 
            WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
                AND (gap1_fail_sum > 0 OR gap2_fail_sum > 0 OR water_fail_sum > 0 OR pump_attempts > 1)
            ORDER BY received_at DESC
        """
    },
    
    'statistics_resets': {
        'name': 'Statistics Resets',
        'description': 'Recent statistics reset events',
        'sql': """
            SELECT id, timestamp, received_at, client_ip
            FROM water_events 
            WHERE event_type = 'STATISTICS_RESET' 
            ORDER BY received_at DESC LIMIT 20
        """
    },
    
    'today_stats': {
        'name': "Today's Statistics",
        'description': 'Event counts and volumes for today',
        'sql': """
            SELECT event_type, COUNT(*) as count, SUM(volume_ml) as total_ml 
            FROM water_events 
            WHERE DATE(received_at) = DATE('now') 
            GROUP BY event_type
        """
    },
    

}

def get_query_sql(query_type):
    """Pobierz SQL dla danego typu zapytania"""
    if query_type in QUICK_QUERIES:
        return QUICK_QUERIES[query_type]['sql'].strip()
    return None

def get_all_queries_sql():
    """Pobierz wszystkie zapytania SQL jako słownik {query_type: sql}"""
    return {key: query['sql'].strip() for key, query in QUICK_QUERIES.items()}

def get_query_info(query_type):
    """Pobierz pełne informacje o zapytaniu"""
    return QUICK_QUERIES.get(query_type, None)

def get_all_queries_metadata():
    """Pobierz metadane wszystkich zapytań"""
    return {key: {'name': query['name'], 'description': query['description']} 
            for key, query in QUICK_QUERIES.items()}