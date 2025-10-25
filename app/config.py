import os
import configparser
from typing import Dict, Any

class Config:
    """Класс для работы с конфигурацией"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self) -> configparser.ConfigParser:
        """Загрузка конфигурации из файла"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self.create_default_config()
        return self.config
    
    def create_default_config(self):
        """Создание конфигурации по умолчанию"""
        self.config['DATABASE'] = {
            'path': 'data/vpn_bot.db',
            'backup_path': 'backups/'
        }
        
        self.config['BOT'] = {
            'token': 'YOUR_BOT_TOKEN_HERE',
            'admin_telegram_id': 'YOUR_ADMIN_TELEGRAM_ID'
        }
        
        self.config['WEB'] = {
            'secret_key': os.urandom(24).hex(),
            'host': '0.0.0.0',
            'port': '5000',
            'debug': 'False'
        }
        
        self.config['PAYMENTS'] = {
            'yoomoney_shop_id': 'YOUR_YOOMONEY_SHOP_ID',
            'yoomoney_secret_key': 'YOUR_YOOMONEY_SECRET_KEY',
            'cryptobot_token': 'YOUR_CRYPTOBOT_TOKEN',
            'cryptobot_shop_id': 'YOUR_CRYPTOBOT_SHOP_ID'
        }
        
        self.config['SECURITY'] = {
            'auto_unban_interval_hours': '6',
            'max_login_attempts': '5',
            'session_timeout_minutes': '60',
            'backup_retention_days': '7'
        }
        
        self.config['LOGGING'] = {
            'level': 'INFO',
            'file': 'logs/vpn_bot.log',
            'max_size_mb': '10',
            'backup_count': '5'
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_database_path(self) -> str:
        """Получение пути к базе данных"""
        return self.config.get('DATABASE', 'path', fallback='data/vpn_bot.db')
    
    def get_bot_token(self) -> str:
        """Получение токена бота"""
        return self.config.get('BOT', 'token', fallback='YOUR_BOT_TOKEN_HERE')
    
    def get_payment_config(self) -> Dict[str, Any]:
        """Получение конфигурации платежей"""
        return {
            'yoomoney_shop_id': self.config.get('PAYMENTS', 'yoomoney_shop_id', fallback=''),
            'yoomoney_secret_key': self.config.get('PAYMENTS', 'yoomoney_secret_key', fallback=''),
            'cryptobot_token': self.config.get('PAYMENTS', 'cryptobot_token', fallback=''),
            'cryptobot_shop_id': self.config.get('PAYMENTS', 'cryptobot_shop_id', fallback='')
        }
    
    def validate_config(self) -> bool:
        """Проверка корректности конфигурации"""
        token = self.get_bot_token()
        if not token or token == 'YOUR_BOT_TOKEN_HERE':
            return False
        return True
    
    def get_web_config(self) -> Dict[str, Any]:
        """Получение конфигурации веб-панели"""
        return {
            'secret_key': self.config.get('WEB', 'secret_key'),
            'host': self.config.get('WEB', 'host', fallback='0.0.0.0'),
            'port': self.config.getint('WEB', 'port', fallback=5000),
            'debug': self.config.getboolean('WEB', 'debug', fallback=False)
        }