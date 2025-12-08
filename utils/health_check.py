"""
Device health check utilities
Checks if IoT devices are reachable through WireGuard
"""

import socket
import time
import logging
from typing import Dict, Optional
from functools import lru_cache
from device_config import get_device_network_config

# Cache health results for 30 seconds
_health_cache: Dict[str, dict] = {}
_cache_timeout = 30  # seconds


def check_device_health(device_type: str) -> dict:
    """
    Check if device is reachable.
    Results are cached for 30 seconds to avoid spamming ESP32.
    
    Returns:
        dict with keys: online, latency_ms, last_check, error
    """
    current_time = time.time()
    
    # Check cache
    if device_type in _health_cache:
        cached = _health_cache[device_type]
        if current_time - cached['timestamp'] < _cache_timeout:
            return {
                'online': cached['online'],
                'latency_ms': cached['latency_ms'],
                'last_check': cached['last_check'],
                'cached': True
            }
    
    # Get device network config
    config = get_device_network_config(device_type)
    if not config:
        return {
            'online': False,
            'latency_ms': None,
            'last_check': current_time,
            'error': 'Unknown device type'
        }
    
    lan_ip = config.get('lan_ip')
    lan_port = config.get('lan_port', 80)
    timeout = config.get('timeout_seconds', 5)
    
    # TCP connection check
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((lan_ip, lan_port))
        sock.close()
        
        latency_ms = int((time.time() - start_time) * 1000)
        online = (result == 0)
        
        if online:
            logging.debug(f"Device {device_type} health check: online ({latency_ms}ms)")
        else:
            logging.warning(f"Device {device_type} health check: offline (error code {result})")
        
    except socket.timeout:
        online = False
        latency_ms = None
        logging.warning(f"Device {device_type} health check: timeout after {timeout}s")
        
    except Exception as e:
        online = False
        latency_ms = None
        logging.error(f"Device {device_type} health check error: {e}")
    
    # Update cache
    health_result = {
        'online': online,
        'latency_ms': latency_ms,
        'last_check': current_time,
        'timestamp': current_time
    }
    _health_cache[device_type] = health_result
    
    return {
        'online': online,
        'latency_ms': latency_ms,
        'last_check': current_time,
        'cached': False
    }


def get_all_devices_health() -> Dict[str, dict]:
    """Check health of all devices with dashboards"""
    from device_config import DEVICE_NETWORK_CONFIG
    
    results = {}
    for device_type in DEVICE_NETWORK_CONFIG.keys():
        results[device_type] = check_device_health(device_type)
    
    return results