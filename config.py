import os
import configparser
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = "config.ini"
        self.config = configparser.ConfigParser()
        
    def create_config(self):
        """Create default configuration file with secure settings"""
        
        # Default configuration with security considerations
        self.config['DATABASE'] = {
            'path': 'data/vpn_bot.db',
            'backup_path': 'data/backups/',
            'backup_retention_days': '30'
        }
        
        self.config['BOT'] = {
            'token': 'YOUR_BOT_TOKEN_HERE',
            'admin_id': 'YOUR_ADMIN_ID_HERE',
            'webhook_url': '',
            'webhook_port': '8443'
        }
        
        self.config['PAYMENTS'] = {
            'yookassa_shop_id': 'YOUR_YOOKASSA_SHOP_ID_HERE',
            'yookassa_secret_key': 'YOUR_YOOKASSA_SECRET_KEY_HERE',
            'payment_timeout_minutes': '30'
        }
        
        self.config['VPN'] = {
            'configs_path': 'data/vpn_configs/',
            'default_server': 'vpn.example.com',
            'default_port': '51820',
            'config_expiry_days': '30'
        }
        
        self.config['SECURITY'] = {
            'max_login_attempts': '5',
            'lockout_duration_minutes': '30',
            'session_timeout_minutes': '60',
            'password_min_length': '8'
        }
        
        self.config['LOGGING'] = {
            'level': 'INFO',
            'file': 'logs/vpn_bot.log',
            'max_size_mb': '10',
            'backup_count': '5'
        }
        
        # Create secure directories
        secure_dirs = [
            'data',
            'data/vpn_configs', 
            'data/backups',
            'logs'
        ]
        
        for directory in secure_dirs:
            os.makedirs(directory, exist_ok=True, mode=0o755)
        
        # Write configuration file
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
        
        # Set secure permissions for config file
        os.chmod(self.config_file, 0o600)
        
        print(f"✅ Configuration file created: {self.config_file}")
        print("✅ Secure directories created")
    
    def load_config(self):
        """Load configuration from file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
        
        self.config.read(self.config_file, encoding='utf-8')
        return self.config
    
    def get_database_path(self):
        """Get database path from configuration"""
        if not os.path.exists(self.config_file):
            self.create_config()
        
        self.load_config()
        db_path = self.config['DATABASE'].get('path', 'data/vpn_bot.db')
        
        # Create directory if it doesn't exist with secure permissions
        os.makedirs(os.path.dirname(db_path), exist_ok=True, mode=0o755)
        
        return db_path
    
    def get_bot_token(self):
        """Get bot token from configuration"""
        self.load_config()
        return self.config['BOT'].get('token')
    
    def get_admin_id(self):
        """Get admin ID from configuration"""
        self.load_config()
        return self.config['BOT'].get('admin_id')
    
    def get_security_settings(self):
        """Get security settings"""
        self.load_config()
        return {
            'max_login_attempts': int(self.config['SECURITY'].get('max_login_attempts', '5')),
            'lockout_duration': int(self.config['SECURITY'].get('lockout_duration_minutes', '30')),
            'session_timeout': int(self.config['SECURITY'].get('session_timeout_minutes', '60'))
        }

if __name__ == "__main__":
    config = Config()
    config.create_config()
    print("✅ Config test completed successfully")