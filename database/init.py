"""
Database initialization and schema management
Creates tables, adds missing columns, creates indexes
"""

import os
import sqlite3
import logging
from config import Config
from .connection import get_db_connection


def init_database() -> None:
    """
    Initialize SQLite database with multi-device architecture.
    
    Creates:
    - admin_sessions table (session management)
    - failed_login_attempts table (security)
    - water_events table (IoT device data)
    - Appropriate indexes for performance
    
    Handles migrations:
    - Adds missing columns to existing tables
    - Populates device_type for legacy data
    
    Called once at application startup.
    """
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()

    # ==============================================================
    # SESSION TABLES - Database-backed session management
    # ==============================================================
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_sessions (
            session_id TEXT PRIMARY KEY,
            client_ip TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_activity INTEGER NOT NULL,
            user_agent TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_activity ON admin_sessions(last_activity)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_ip ON admin_sessions(client_ip)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS failed_login_attempts (
            client_ip TEXT PRIMARY KEY,
            attempt_count INTEGER DEFAULT 0,
            last_attempt INTEGER NOT NULL,
            locked_until INTEGER DEFAULT NULL
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_locked_until ON failed_login_attempts(locked_until)')
    
    logging.info("✅ Session tables initialized")
    
    # ==============================================================
    # WATER_EVENTS TABLE - Multi-device IoT data
    # ==============================================================
    
    # Check if table exists and get existing columns
    cursor.execute("PRAGMA table_info(water_events)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # Add daily_volume_ml if missing (migration)
    if existing_columns and 'daily_volume_ml' not in existing_columns:
        try:
            cursor.execute('''
                ALTER TABLE water_events 
                ADD COLUMN daily_volume_ml REAL DEFAULT NULL
            ''')
            logging.info("Added daily_volume_ml column to water_events table")
        except sqlite3.Error as e:
            logging.warning(f"Could not add daily_volume_ml column: {e}")
    
    if not existing_columns:
        # New installation - create table with all columns (multi-device ready)
        cursor.execute('''
            CREATE TABLE water_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_type TEXT DEFAULT NULL,
                timestamp TEXT NOT NULL,
                unix_time INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                volume_ml INTEGER DEFAULT NULL,
                water_status TEXT DEFAULT NULL,
                system_status TEXT NOT NULL,
                received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                client_ip TEXT,
                
                -- Water system specific columns
                time_gap_1 INTEGER DEFAULT NULL,
                time_gap_2 INTEGER DEFAULT NULL,
                water_trigger_time INTEGER DEFAULT NULL,
                pump_duration INTEGER DEFAULT NULL,
                pump_attempts INTEGER DEFAULT NULL,
                gap1_fail_sum INTEGER DEFAULT NULL,
                gap2_fail_sum INTEGER DEFAULT NULL,
                water_fail_sum INTEGER DEFAULT NULL,
                algorithm_data TEXT DEFAULT NULL,
                daily_volume_ml INTEGER DEFAULT NULL,
                last_reset_timestamp INTEGER DEFAULT NULL,
                
                -- Temperature sensor specific columns  
                temperature REAL DEFAULT NULL,
                humidity REAL DEFAULT NULL,
                
                -- Security system specific columns
                zone_status TEXT DEFAULT NULL,
                motion_detected BOOLEAN DEFAULT NULL
            )
        ''')
        logging.info("Created new multi-device water_events table")
        
    else:
        # Existing table - add new columns if missing
        new_columns = [
            # Multi-device core
            'device_type TEXT DEFAULT NULL',
            
            # Algorithm columns
            'time_gap_1 INTEGER DEFAULT NULL',
            'time_gap_2 INTEGER DEFAULT NULL', 
            'water_trigger_time INTEGER DEFAULT NULL',
            'pump_duration INTEGER DEFAULT NULL',
            'pump_attempts INTEGER DEFAULT NULL',
            'gap1_fail_sum INTEGER DEFAULT NULL',
            'gap2_fail_sum INTEGER DEFAULT NULL', 
            'water_fail_sum INTEGER DEFAULT NULL',
            'last_reset_timestamp INTEGER DEFAULT NULL',
            'algorithm_data TEXT DEFAULT NULL',
            
            # Temperature sensor columns
            'temperature REAL DEFAULT NULL',
            'humidity REAL DEFAULT NULL',
            
            # Security system columns  
            'zone_status TEXT DEFAULT NULL',
            'motion_detected BOOLEAN DEFAULT NULL'
        ]
        
        for column_def in new_columns:
            column_name = column_def.split()[0]
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE water_events ADD COLUMN {column_def}')
                    logging.info(f"Added column: {column_name}")
                except sqlite3.Error as e:
                    logging.warning(f"Could not add column {column_name}: {e}")
        
        # Populate device_type for existing data (one-time migration)
        cursor.execute("SELECT COUNT(*) FROM water_events WHERE device_type IS NULL")
        untyped_records = cursor.fetchone()[0]
        
        if untyped_records > 0:
            logging.info(f"Populating device_type for {untyped_records} existing records...")
            
            # Import device mapping
            try:
                from device_config import get_device_type
                
                # Update existing records based on device_id
                cursor.execute("SELECT DISTINCT device_id FROM water_events WHERE device_type IS NULL")
                device_ids = [row[0] for row in cursor.fetchall()]
                
                for device_id in device_ids:
                    device_type = get_device_type(device_id)
                    cursor.execute(
                        "UPDATE water_events SET device_type = ? WHERE device_id = ? AND device_type IS NULL",
                        (device_type, device_id)
                    )
                    updated = cursor.rowcount
                    logging.info(f"Updated {updated} records: {device_id} → {device_type}")
                    
            except ImportError:
                logging.warning("device_config not available, setting device_type to device_id")
                cursor.execute("UPDATE water_events SET device_type = device_id WHERE device_type IS NULL")
    
    # ==============================================================
    # INDEXES for multi-device performance
    # ==============================================================
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON water_events(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_type ON water_events(device_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id_type ON water_events(device_id, device_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON water_events(unix_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON water_events(event_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_received_at ON water_events(received_at)')
    
    conn.commit()
    conn.close()
    
    logging.info("Database initialized successfully with multi-device architecture")