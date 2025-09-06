#!/usr/bin/env python3
"""
Generator bezpiecznych credentials dla Water System Logger
Generuje silne hasła i tokeny dla ADMIN_PASSWORD i API_TOKEN
"""

import secrets
import string
import base64
import hashlib
import uuid
import argparse
import sys
from datetime import datetime

def generate_password(length=32, use_symbols=True):
    """Generuj bezpieczne hasło administratora"""
    if use_symbols:
        characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    else:
        characters = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_api_token(format_type='hex', length=32):
    """Generuj bezpieczny token API"""
    if format_type == 'hex':
        return secrets.token_hex(length)
    elif format_type == 'base64':
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('ascii').rstrip('=')
    elif format_type == 'uuid':
        return str(uuid.uuid4())
    elif format_type == 'sha256':
        random_data = secrets.token_bytes(64)
        return 'sha256:' + hashlib.sha256(random_data).hexdigest()
    else:
        raise ValueError(f"Unknown format: {format_type}")

def generate_secret_key(length=32):
    """Generuj Flask secret key"""
    return secrets.token_hex(length)

def create_env_file(filename='.env', admin_password=None, api_token=None, secret_key=None):
    """Utwórz plik .env z wygenerowanymi credentials"""
    
    if not admin_password:
        admin_password = generate_password(32, use_symbols=False)  # Bez symboli dla łatwości
    
    if not api_token:
        api_token = generate_api_token('hex', 32)
    
    if not secret_key:
        secret_key = generate_secret_key()
    
    env_content = f"""# ESP32 Water System Logger - Generated Credentials
# Wygenerowano: {datetime.now().isoformat()}

# === WYMAGANE CREDENTIALS ===
WATER_SYSTEM_ADMIN_PASSWORD={admin_password}
WATER_SYSTEM_API_TOKEN={api_token}
WATER_SYSTEM_SECRET_KEY={secret_key}

# === OPCJONALNE KONFIGURACJE ===
WATER_SYSTEM_DEVICE_IDS=DOLEWKA,ESP32_DEVICE_002
WATER_SYSTEM_SESSION_TIMEOUT=30
WATER_SYSTEM_MAX_FAILED_ATTEMPTS=8
WATER_SYSTEM_LOCKOUT_DURATION=1
WATER_SYSTEM_LOG_LEVEL=INFO
WATER_SYSTEM_NGINX_MODE=true

# === ŚCIEŻKI (dostosuj do swojej instalacji) ===
# WATER_SYSTEM_DATABASE_PATH=/home/yourusername/water-system-logger/water_events.db
# WATER_SYSTEM_LOG_PATH=/home/yourusername/water-system-logger/app.log
# WATER_SYSTEM_HTTP_PORT=5000
# WATER_SYSTEM_ADMIN_PORT=5001
"""
    
    with open(filename, 'w') as f:
        f.write(env_content)
    
    # Ustaw bezpieczne uprawnienia
    import os
    os.chmod(filename, 0o600)
    
    return admin_password, api_token, secret_key

def main():
    parser = argparse.ArgumentParser(description='Generator bezpiecznych credentials dla Water System Logger')
    parser.add_argument('--output', '-o', choices=['env', 'systemd', 'both', 'display'], 
                       default='display', help='Format wyjścia')
    parser.add_argument('--env-file', default='.env', help='Nazwa pliku .env')
    parser.add_argument('--password-length', type=int, default=32, help='Długość hasła administratora')
    parser.add_argument('--token-format', choices=['hex', 'base64', 'uuid', 'sha256'], 
                       default='hex', help='Format tokena API')
    parser.add_argument('--no-symbols', action='store_true', help='Bez symboli specjalnych w haśle')
    
    args = parser.parse_args()
    
    print("🔐 Water System Logger - Generator Credentials")
    print("=" * 50)
    
    # Generuj credentials
    admin_password = generate_password(args.password_length, not args.no_symbols)
    api_token = generate_api_token(args.token_format)
    secret_key = generate_secret_key()
    
    if args.output in ['display', 'both']:
        print("\n📋 Wygenerowane Credentials:")
        print(f"Admin Password:  {admin_password}")
        print(f"API Token:       {api_token}")
        print(f"Secret Key:      {secret_key}")
        print(f"\nSiła hasła: {len(admin_password)} znaków")
        print(f"Format tokena: {args.token_format}")
    
    if args.output in ['env', 'both']:
        create_env_file(args.env_file, admin_password, api_token, secret_key)
        print(f"\n✅ Plik {args.env_file} utworzony z credentials")
        print(f"   Uprawnienia: 600 (tylko właściciel)")
    
    print("\n🔒 Instrukcje bezpieczeństwa:")
    print("1. Zachowaj credentials w bezpiecznym miejscu")
    print("2. Nie commituj plików .env do git")
    print("3. Ustaw uprawnienia 600 na plikach z credentials")
    print("4. Używaj różnych credentials na dev/staging/production")
    print("5. Regularnie zmieniaj credentials w produkcji")
    
    if args.output == 'display':
        print("\n💡 Aby utworzyć pliki konfiguracyjne:")
        print("python generate_credentials.py --output env")

if __name__ == '__main__':
    main()
