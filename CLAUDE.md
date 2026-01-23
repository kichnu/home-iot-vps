# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IoT VPS Gateway - a Flask-based authentication proxy for IoT devices accessible through WireGuard VPN. The application runs behind Nginx (which handles SSL termination and device proxying) and provides session-based authentication to protect access to IoT device dashboards.

## Commands

```bash
# Run the application (development)
python app.py

# Run with gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5001 app:app

# Restart the systemd service (production)
sudo systemctl restart home-iot
```

## Architecture

### Request Flow
1. Client -> Nginx (SSL termination) -> Flask app (authentication)
2. Nginx uses `/api/auth-check` endpoint to validate sessions before proxying to IoT devices
3. Device proxy paths (e.g., `/device/top_off_water`) are handled by Nginx, not Flask

### Key Modules

**`app.py`** - Main Flask application with routes:
- Authentication: `/login`, `/logout`
- Dashboard: `/dashboard` (protected, shows device cards)
- API: `/api/auth-check` (Nginx auth_request), `/api/device-health/<device_type>`

**`auth/`** - Session management module:
- `session.py` - Database-backed sessions with IP tracking, failed login tracking, account lockout
- `decorators.py` - `@require_admin_auth` decorator for protected routes

**`database/`** - SQLite layer (WAL mode enabled):
- `connection.py` - Context manager `get_db_connection()` with auto-commit
- `init.py` - Schema for `admin_sessions` and `failed_login_attempts` tables only

**`device_config.py`** - Device definitions:
- `DEVICE_TYPES` - Display info (name, icon, color)
- `DEVICE_NETWORK_CONFIG` - Network info (WireGuard IPs, ports, proxy paths)

**`utils/`**:
- `security.py` - `secure_compare()` (timing-safe), `get_real_ip()` (Nginx-aware)
- `health_check.py` - TCP connectivity check to devices with 30s caching

### Configuration

Environment variables (prefix `WATER_SYSTEM_`):
- `ADMIN_PASSWORD` (required) - Single admin password
- `SECRET_KEY` - Flask session key (auto-generated if empty)
- `ADMIN_PORT` - Default 5001
- `NGINX_MODE` - Default true (affects IP detection)
- `SESSION_TIMEOUT` - Minutes, default 30
- `MAX_FAILED_ATTEMPTS` / `LOCKOUT_DURATION` - Brute-force protection

### Database

SQLite at `data/database/sessions.db` with two tables:
- `admin_sessions` - Session tokens, IP, timestamps
- `failed_login_attempts` - IP-based lockout tracking

No event logging or data storage - this is purely an auth gateway.

### Documentation

- `docs/CODE-REVIEW-2026-01.md` - Security audit, code quality issues, TODOs
- `docs/PLAN-REORGANIZACJA-VPS.md` - Reorganization history and security fixes
