"""
Configuration management for Home IoT Platform
Centralized environment variables and settings
"""

import os
import sys
from datetime import timedelta


class Config:
    """Application configuration from environment variables"""
    
    # Base paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Database configuration
    DATABASE_PATH = os.getenv(
        'WATER_SYSTEM_DATABASE_PATH',
        os.path.join(BASE_DIR, 'data/database/water_events.db')
    )
    
    # Logging configuration
    LOG_PATH = os.getenv(
        'WATER_SYSTEM_LOG_PATH',
        os.path.join(BASE_DIR, 'data/logs/app.log')
    )
    LOG_LEVEL = os.getenv('WATER_SYSTEM_LOG_LEVEL', 'INFO').upper()
    
    # Security credentials (REQUIRED)
    ADMIN_PASSWORD = os.getenv('WATER_SYSTEM_ADMIN_PASSWORD')
    API_TOKEN = os.getenv('WATER_SYSTEM_API_TOKEN')
    SECRET_KEY = os.getenv('WATER_SYSTEM_SECRET_KEY')
    
    # Device configuration
    DEVICE_IDS_STR = os.getenv('WATER_SYSTEM_DEVICE_IDS', 'DOLEWKA')
    VALID_DEVICE_IDS = [dev.strip() for dev in DEVICE_IDS_STR.split(',') if dev.strip()]
    
    # Server ports
    HTTP_PORT = int(os.getenv('WATER_SYSTEM_HTTP_PORT', '5000'))
    ADMIN_PORT = int(os.getenv('WATER_SYSTEM_ADMIN_PORT', '5001'))
    ENABLE_NGINX_MODE = os.getenv('WATER_SYSTEM_NGINX_MODE', 'true').lower() == 'true'
    
    # Session configuration
    SESSION_TIMEOUT_MINUTES = int(os.getenv('WATER_SYSTEM_SESSION_TIMEOUT', '30'))
    SESSION_PERMANENT_LIFETIME = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    
    # Security settings
    MAX_FAILED_ATTEMPTS = int(os.getenv('WATER_SYSTEM_MAX_FAILED_ATTEMPTS', '8'))
    LOCKOUT_DURATION_HOURS = int(os.getenv('WATER_SYSTEM_LOCKOUT_DURATION', '1'))
    
    # Flask configuration
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'water_session'
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def verify_required_vars(cls) -> bool:
        """Verify all required environment variables are set"""
        required_vars = {
            'WATER_SYSTEM_ADMIN_PASSWORD': cls.ADMIN_PASSWORD,
            'WATER_SYSTEM_API_TOKEN': cls.API_TOKEN
        }
        
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        if missing_vars:
            error_msg = f"""
❌ MISSING REQUIRED ENVIRONMENT VARIABLES:
{', '.join(missing_vars)}

🔧 DEVELOPMENT - Create .env file:
   python generate_credentials.py --output env
   
🚀 PRODUCTION - Set system variables:
   export WATER_SYSTEM_ADMIN_PASSWORD='your_secure_password'
   export WATER_SYSTEM_API_TOKEN='your_secure_api_token'

📖 More information in DEPLOY.md
"""
            print(error_msg)
            return False
        
        return True
    
    @classmethod
    def log_startup_info(cls, logger) -> None:
        """Log configuration info at startup (without credentials)"""
        logger.info("=== HOME IOT CONFIGURATION AT STARTUP ===")
        logger.info(f"Base directory: {cls.BASE_DIR}")
        logger.info(f"Database path: {cls.DATABASE_PATH}")
        logger.info(f"Log path: {cls.LOG_PATH}")
        logger.info(f"HTTP port: {cls.HTTP_PORT}")
        logger.info(f"Admin port: {cls.ADMIN_PORT}")
        logger.info(f"Nginx mode: {cls.ENABLE_NGINX_MODE}")
        logger.info(f"Session timeout: {cls.SESSION_TIMEOUT_MINUTES} minutes")
        logger.info(f"Valid device IDs: {cls.VALID_DEVICE_IDS}")
        logger.info(f"Log level: {cls.LOG_LEVEL}")
        logger.info("Environment variables loaded successfully ✅")