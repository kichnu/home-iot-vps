#!/usr/bin/env python3
"""
Professional Credentials Management Tool for Water System Logger
Centralizes all credential operations with safety checks and audit trails
"""

import os
import sys
import argparse
import subprocess
import json
import datetime
import shutil
import secrets
import hashlib
from pathlib import Path

class CredentialsManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.env_file = self.base_dir / '.env'
        self.env_example = self.base_dir / '.env.example'
        self.systemd_override = self.base_dir / 'systemd-override.conf'
        self.log_file = self.base_dir / 'credentials.log'
        self.backup_dir = self.base_dir / 'credential-backups'
        
    def log_action(self, action, details=""):
        """Log credential operations for audit trail"""
        timestamp = datetime.datetime.now().isoformat()
        user = os.getenv('USER', 'unknown')
        log_entry = f"{timestamp} - {action} - {details} - user:{user}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(f"🔍 Logged: {action}")

    def create_backup(self, source_file, backup_name=None):
        """Create timestamped backup of credentials"""
        if not source_file.exists():
            return None
            
        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if backup_name:
            backup_file = self.backup_dir / f"{backup_name}.{timestamp}"
        else:
            backup_file = self.backup_dir / f"{source_file.name}.{timestamp}"
        
        shutil.copy2(source_file, backup_file)
        os.chmod(backup_file, 0o600)
        
        self.log_action("BACKUP_CREATED", f"{source_file} -> {backup_file}")
        return backup_file

    def generate_credentials(self, password_length=32, token_format='hex', no_symbols=False):
        """Generate new credentials using the generator"""
        try:
            cmd = [
                sys.executable, 'generate_credentials.py',
                '--output', 'display',
                '--password-length', str(password_length),
                '--token-format', token_format
            ]
            
            if no_symbols:
                cmd.append('--no-symbols')
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse output to extract credentials
            lines = result.stdout.split('\n')
            credentials = {}
            
            for line in lines:
                if 'Admin Password:' in line:
                    credentials['admin_password'] = line.split(':', 1)[1].strip()
                elif 'API Token:' in line:
                    credentials['api_token'] = line.split(':', 1)[1].strip()
                elif 'Secret Key:' in line:
                    credentials['secret_key'] = line.split(':', 1)[1].strip()
            
            return credentials
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating credentials: {e}")
            return None

    def setup_development(self, force=False, password_length=32, no_symbols=False):
        """Setup development environment with .env file"""
        print("🔧 Setting up development environment...")
        
        # Check if .env exists
        if self.env_file.exists() and not force:
            print(f"⚠️ .env file already exists: {self.env_file}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("❌ Setup cancelled")
                return False
        
        # Backup existing .env
        if self.env_file.exists():
            backup_file = self.create_backup(self.env_file, '.env.backup')
            print(f"✅ Backup created: {backup_file}")
        
        # Generate new credentials
        credentials = self.generate_credentials(password_length=password_length, no_symbols=no_symbols)
        if not credentials:
            return False
        
        # Create .env file
        env_content = f"""# ESP32 Water System Logger - Development Credentials
# Generated: {datetime.datetime.now().isoformat()}
# DO NOT COMMIT THIS FILE TO GIT

# === REQUIRED CREDENTIALS ===
WATER_SYSTEM_ADMIN_PASSWORD={credentials['admin_password']}
WATER_SYSTEM_API_TOKEN={credentials['api_token']}
WATER_SYSTEM_SECRET_KEY={credentials['secret_key']}

# === OPTIONAL CONFIGURATIONS ===
WATER_SYSTEM_DEVICE_IDS=DOLEWKA,ESP32_DEVICE_002
WATER_SYSTEM_SESSION_TIMEOUT=30
WATER_SYSTEM_MAX_FAILED_ATTEMPTS=8
WATER_SYSTEM_LOCKOUT_DURATION=1
WATER_SYSTEM_LOG_LEVEL=INFO
WATER_SYSTEM_NGINX_MODE=true

# === PATHS (auto-detected) ===
WATER_SYSTEM_DATABASE_PATH={self.base_dir}/water_events.db
WATER_SYSTEM_LOG_PATH={self.base_dir}/app.log
WATER_SYSTEM_HTTP_PORT=5000
WATER_SYSTEM_ADMIN_PORT=5001
"""
        
        with open(self.env_file, 'w') as f:
            f.write(env_content)
        
        os.chmod(self.env_file, 0o600)
        
        self.log_action("DEV_SETUP", f"password_length={password_length}, no_symbols={no_symbols}")
        
        print(f"✅ Development environment configured")
        print(f"📁 Credentials file: {self.env_file}")
        print(f"🔒 File permissions: 600 (secure)")
        print(f"🔑 Admin password length: {len(credentials['admin_password'])}")
        print(f"🔑 API token length: {len(credentials['api_token'])}")
        
        return True

    def setup_production(self, password_length=40, no_symbols=True):
        """Setup production environment with systemd override"""
        print("🚀 Setting up production environment...")
        
        # Backup existing systemd override
        systemd_path = Path('/etc/systemd/system/water-system.service.d/override.conf')
        if systemd_path.exists():
            try:
                backup_file = self.create_backup(systemd_path, 'systemd-override.backup')
                print(f"✅ Backup created: {backup_file}")
            except PermissionError:
                print("⚠️ Cannot backup systemd file (need sudo), continuing...")
        
        # Generate strong production credentials
        credentials = self.generate_credentials(
            password_length=password_length, 
            no_symbols=no_symbols
        )
        if not credentials:
            return False
        
        # Create systemd override content
        override_content = f"""[Service]
# === PRODUCTION CREDENTIALS ===
# Generated: {datetime.datetime.now().isoformat()}
Environment=WATER_SYSTEM_ADMIN_PASSWORD={credentials['admin_password']}
Environment=WATER_SYSTEM_API_TOKEN={credentials['api_token']}
Environment=WATER_SYSTEM_SECRET_KEY={credentials['secret_key']}

# === OPTIONAL CONFIGURATIONS ===
Environment=WATER_SYSTEM_DEVICE_IDS=DOLEWKA,ESP32_DEVICE_002
Environment=WATER_SYSTEM_SESSION_TIMEOUT=30
Environment=WATER_SYSTEM_MAX_FAILED_ATTEMPTS=8
Environment=WATER_SYSTEM_LOCKOUT_DURATION=1
Environment=WATER_SYSTEM_LOG_LEVEL=INFO
Environment=WATER_SYSTEM_NGINX_MODE=true

# Security settings
UMask=0077
"""
        
        # Write to local file first
        with open(self.systemd_override, 'w') as f:
            f.write(override_content)
        
        os.chmod(self.systemd_override, 0o600)
        
        self.log_action("PROD_SETUP", f"password_length={password_length}")
        
        print(f"✅ Production systemd override generated")
        print(f"📁 Local file: {self.systemd_override}")
        print(f"🔑 Admin password length: {len(credentials['admin_password'])}")
        print(f"🔑 API token length: {len(credentials['api_token'])}")
        print()
        print("📋 Next steps for production deployment:")
        print("1. sudo mkdir -p /etc/systemd/system/water-system.service.d/")
        print(f"2. sudo cp {self.systemd_override} /etc/systemd/system/water-system.service.d/override.conf")
        print("3. sudo chmod 600 /etc/systemd/system/water-system.service.d/override.conf")
        print("4. sudo systemctl daemon-reload")
        print("5. sudo systemctl restart water-system")
        
        return True

    def rotate_credentials(self, environment='both', password_length=None):
        """Rotate credentials for specified environment"""
        print(f"🔄 Rotating credentials for: {environment}")
        
        if environment in ['dev', 'both'] and self.env_file.exists():
            print("Rotating development credentials...")
            length = password_length or 32
            if not self.setup_development(force=True, password_length=length, no_symbols=True):
                return False
        
        if environment in ['prod', 'both']:
            print("Rotating production credentials...")
            length = password_length or 40
            if not self.setup_production(password_length=length, no_symbols=True):
                return False
        
        self.log_action("ROTATION", f"environment={environment}")
        return True

    def audit_credentials(self):
        """Audit current credential configuration"""
        print("🔍 Credential Security Audit")
        print("=" * 50)
        
        # Check .env file
        if self.env_file.exists():
            stat = os.stat(self.env_file)
            permissions = oct(stat.st_mode)[-3:]
            age_days = (datetime.datetime.now().timestamp() - stat.st_mtime) / 86400
            
            print(f"📄 Development (.env file):")
            print(f"   File: {self.env_file}")
            print(f"   Permissions: {permissions} {'✅' if permissions == '600' else '⚠️'}")
            print(f"   Age: {age_days:.1f} days {'⚠️' if age_days > 90 else '✅'}")
            
            # Check if git ignores .env
            try:
                result = subprocess.run(['git', 'check-ignore', str(self.env_file)], 
                                       capture_output=True, check=True)
                print(f"   Git ignored: ✅")
            except subprocess.CalledProcessError:
                print(f"   Git ignored: ❌ WARNING - .env may be tracked by git!")
        else:
            print("📄 Development: No .env file found")
        
        print()
        
        # Check production systemd
        systemd_path = Path('/etc/systemd/system/water-system.service.d/override.conf')
        if systemd_path.exists():
            try:
                stat = os.stat(systemd_path)
                permissions = oct(stat.st_mode)[-3:]
                age_days = (datetime.datetime.now().timestamp() - stat.st_mtime) / 86400
                
                print(f"🚀 Production (systemd):")
                print(f"   File: {systemd_path}")
                print(f"   Permissions: {permissions} {'✅' if permissions == '600' else '⚠️'}")
                print(f"   Age: {age_days:.1f} days {'⚠️' if age_days > 90 else '✅'}")
                
                # Check systemd service status
                try:
                    result = subprocess.run(['systemctl', 'is-active', 'water-system'], 
                                           capture_output=True, text=True)
                    status = result.stdout.strip()
                    print(f"   Service status: {status} {'✅' if status == 'active' else '⚠️'}")
                except:
                    print(f"   Service status: Unknown")
                    
            except PermissionError:
                print(f"🚀 Production: Cannot access {systemd_path} (need sudo)")
        else:
            print("🚀 Production: No systemd override found")
        
        print()
        
        # Security recommendations
        print("📋 Security Recommendations:")
        if self.env_file.exists():
            env_age = (datetime.datetime.now().timestamp() - os.stat(self.env_file).st_mtime) / 86400
            if env_age > 90:
                print("   ⚠️ Consider rotating development credentials (>90 days old)")
        
        if systemd_path.exists():
            try:
                prod_age = (datetime.datetime.now().timestamp() - os.stat(systemd_path).st_mtime) / 86400
                if prod_age > 90:
                    print("   ⚠️ Consider rotating production credentials (>90 days old)")
            except:
                pass
        
        # Check for credential leaks
        try:
            result = subprocess.run(['git', 'log', '--all', '-S', 'admin', '--oneline'], 
                                   capture_output=True, text=True)
            if 'admin' in result.stdout.lower():
                print("   ⚠️ Potential credential patterns found in git history")
            else:
                print("   ✅ No obvious credential leaks in git history")
        except:
            print("   ⚠️ Cannot check git history")
        
        return True

    def emergency_reset(self):
        """Emergency credential reset with confirmation"""
        print("🚨 EMERGENCY CREDENTIAL RESET")
        print("This will generate new credentials and restart services")
        print("⚠️ This will invalidate all existing credentials!")
        print()
        
        confirm = input("Type 'EMERGENCY RESET' to confirm: ")
        if confirm != 'EMERGENCY RESET':
            print("❌ Reset cancelled")
            return False
        
        print("🔄 Generating emergency credentials...")
        
        # Backup everything first
        if self.env_file.exists():
            self.create_backup(self.env_file, 'emergency-backup')
        
        # Generate new credentials for both environments
        self.setup_development(force=True, password_length=40, no_symbols=True)
        self.setup_production(password_length=48, no_symbols=True)
        
        self.log_action("EMERGENCY_RESET", "Full credential reset performed")
        
        print("✅ Emergency credentials generated")
        print("📋 Next steps:")
        print("1. Deploy production credentials to systemd")
        print("2. Restart water-system service")
        print("3. Update ESP32 device with new API token")
        print("4. Test all endpoints")
        
        return True

    def show_status(self):
        """Show current credential status"""
        print("📊 Credential Status")
        print("=" * 40)
        
        # Development status
        if self.env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(self.env_file)
                admin_pass = os.getenv('WATER_SYSTEM_ADMIN_PASSWORD')
                api_token = os.getenv('WATER_SYSTEM_API_TOKEN')
                
                print(f"🔧 Development:")
                print(f"   Admin password: {'✅ Set' if admin_pass else '❌ Missing'} ({len(admin_pass) if admin_pass else 0} chars)")
                print(f"   API token: {'✅ Set' if api_token else '❌ Missing'} ({len(api_token) if api_token else 0} chars)")
                print(f"   File age: {(datetime.datetime.now().timestamp() - os.stat(self.env_file).st_mtime) / 86400:.1f} days")
            except ImportError:
                print("🔧 Development: Cannot check (python-dotenv not available)")
            except Exception as e:
                print(f"🔧 Development: Error reading .env - {e}")
        else:
            print("🔧 Development: No .env file")
        
        print()
        
        # Production status
        try:
            result = subprocess.run(['systemctl', 'show', 'water-system', '--property=Environment'], 
                                   capture_output=True, text=True)
            env_vars = result.stdout
            
            has_admin = 'WATER_SYSTEM_ADMIN_PASSWORD' in env_vars
            has_token = 'WATER_SYSTEM_API_TOKEN' in env_vars
            
            print(f"🚀 Production:")
            print(f"   Admin password: {'✅ Set' if has_admin else '❌ Missing'}")
            print(f"   API token: {'✅ Set' if has_token else '❌ Missing'}")
            
            # Service status
            result = subprocess.run(['systemctl', 'is-active', 'water-system'], 
                                   capture_output=True, text=True)
            status = result.stdout.strip()
            print(f"   Service: {status} {'✅' if status == 'active' else '❌'}")
            
        except Exception as e:
            print(f"🚀 Production: Cannot check systemd status - {e}")
        
        # Application status
        print()
        try:
            import requests
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("💓 Application: ✅ Healthy (localhost:5000)")
            else:
                print(f"💓 Application: ⚠️ HTTP {response.status_code}")
        except:
            print("💓 Application: ❌ Not responding")

def main():
    parser = argparse.ArgumentParser(description='Professional credentials management for Water System Logger')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup commands
    dev_parser = subparsers.add_parser('setup-dev', help='Setup development environment')
    dev_parser.add_argument('--force', action='store_true', help='Overwrite existing .env')
    dev_parser.add_argument('--length', type=int, default=32, help='Password length')
    dev_parser.add_argument('--no-symbols', action='store_true', help='No special symbols')
    
    prod_parser = subparsers.add_parser('setup-prod', help='Setup production environment')
    prod_parser.add_argument('--length', type=int, default=40, help='Password length')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate credentials')
    rotate_parser.add_argument('environment', choices=['dev', 'prod', 'both'], 
                              help='Environment to rotate')
    rotate_parser.add_argument('--length', type=int, help='Password length')
    
    # Other commands
    subparsers.add_parser('audit', help='Audit credential security')
    subparsers.add_parser('status', help='Show credential status')
    subparsers.add_parser('emergency-reset', help='Emergency credential reset')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = CredentialsManager()
    
    if args.command == 'setup-dev':
        manager.setup_development(
            force=args.force, 
            password_length=args.length,
            no_symbols=args.no_symbols
        )
    
    elif args.command == 'setup-prod':
        manager.setup_production(password_length=args.length)
    
    elif args.command == 'rotate':
        manager.rotate_credentials(args.environment, args.length)
    
    elif args.command == 'audit':
        manager.audit_credentials()
    
    elif args.command == 'status':
        manager.show_status()
    
    elif args.command == 'emergency-reset':
        manager.emergency_reset()

if __name__ == '__main__':
    main()