"""
Centralna konfiguracja zapytań SQL dla Water System Admin Panel
Single source of truth dla wszystkich predefiniowanych zapytań
"""

QUICK_QUERIES = {
    'last24h': {
        'name': 'Last 24 Hours',
        'description': 'Events from last 24 hours',
        'sql': """
            SELECT id, timestamp, event_type, volume_ml, water_status, client_ip 
            FROM water_events 
            WHERE received_at > datetime('now', '-24 hours') 
            ORDER BY received_at DESC
        """
    },
    
    'algorithm_cycles': {
        'name': 'Algorithm Cycles',
        'description': 'Recent algorithm cycle completions',
        'sql': """
            SELECT id, timestamp, time_gap_1, time_gap_2, water_trigger_time, 
                   pump_duration, pump_attempts, gap1_fail_sum, gap2_fail_sum, water_fail_sum,
                   last_reset_timestamp
            FROM water_events 
            WHERE event_type = 'AUTO_CYCLE_COMPLETE' 
            ORDER BY received_at DESC LIMIT 50
        """
    },
    
    'algorithm_stats': {
        'name': 'Algorithm Statistics',
        'description': 'Weekly algorithm performance stats',
        'sql': """
            SELECT 
                COUNT(*) as total_cycles,
                AVG(time_gap_1) as avg_gap1,
                AVG(time_gap_2) as avg_gap2,
                AVG(water_trigger_time) as avg_water_time,
                AVG(pump_duration) as avg_pump_duration,
                MAX(gap1_fail_sum) as max_gap1_sum,
                MAX(gap2_fail_sum) as max_gap2_sum,
                MAX(water_fail_sum) as max_water_sum,
                AVG(pump_attempts) as avg_attempts
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
    
    'all_events': {
        'name': 'Recent Events',
        'description': 'Last 100 events of all types',
        'sql': """
            SELECT id, timestamp, event_type, volume_ml, water_status 
            FROM water_events 
            ORDER BY received_at DESC 
            LIMIT 100
        """
    },
    
    'errors': {
        'name': 'System Errors',
        'description': 'Events with error status',
        'sql': """
            SELECT id, timestamp, event_type, water_status, system_status, client_ip 
            FROM water_events 
            WHERE water_status != 'OK' OR system_status != 'OK' 
            ORDER BY received_at DESC
        """
    },
    
    'monthly': {
        'name': 'Daily Summary',
        'description': 'Daily event counts for last 30 days',
        'sql': """
            SELECT DATE(received_at) as date, COUNT(*) as events, SUM(volume_ml) as total_ml 
            FROM water_events 
            WHERE received_at > datetime('now', '-30 days') 
            GROUP BY DATE(received_at) 
            ORDER BY date DESC
        """
    }
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