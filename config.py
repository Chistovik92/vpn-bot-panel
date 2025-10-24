import os
import configparser
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = "config.ini"
        self.config = configparser.ConfigParser()
        
    def create_config(self):
        """Create default configuration file"""
        
        # Default configuration
        self.config['DATABASE'] = {
            'path': 'data/vpn_bot.db',
            'backup_path': 'data/backups/'
        }
        
        self.config['BOT'] = {
            'token': 'YOUR_BOT_TOKEN_HERE',
            'admin_id': 'YOUR_ADMIN_ID_HERE'
        }
        
        self.config['PAYMENTS'] = {
            'yoo_kassa_token': 'YOUR_YOOKASSA_TOKEN_HERE',
            'crypto_bot_token': 'YOUR_CRYPTO_BOT_TOKEN_HERE'
        }
        
        self.config['VPN'] = {
            'configs_path': 'data/vpn_configs/',
            'default_server': 'vpn.example.com'
        }
        
        # Create directories
        os.makedirs('data/vpn_configs', exist_ok=True)
        os.makedirs('data/backups', exist_ok=True)
        
        # Write configuration file
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
        
        print(f"✅ Configuration file created: {self.config_file}")
    
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
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        return db_path
    
    def get_bot_token(self):
        """Get bot token from configuration"""
        self.load_config()
        return self.config['BOT'].get('token')
    
    def get_admin_id(self):
        """Get admin ID from configuration"""
        self.load_config()
        return self.config['BOT'].get('admin_id')

if __name__ == "__main__":
    config = Config()
    config.create_config()
    print("✅ Config test completed successfully")