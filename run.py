#!/usr/bin/env python3
"""
VPN Bot Panel - Основной скрипт запуска
"""

import logging
import os
import sys
import threading
from app.bot import VPNBot
from app.config import Config

def setup_logging():
    """Настройка логирования"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'logs/vpn_bot.log')
    
    # Создаем директорию для логов если нет
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_bot():
    """Запуск Telegram бота"""
    try:
        bot = VPNBot()
        bot.run()
    except Exception as e:
        logging.error(f"Ошибка бота: {e}")

def run_web():
    """Запуск веб-панели"""
    try:
        from app.web import create_app
        app = create_app()
        web_config = Config().get_web_config()
        app.run(
            host=web_config['host'],
            port=web_config['port'],
            debug=web_config['debug']
        )
    except Exception as e:
        logging.error(f"Ошибка веб-панели: {e}")

def main():
    """Основная функция запуска"""
    try:
        setup_logging()
        logging.info("🚀 Запуск VPN Bot Panel...")
        
        # Проверка конфигурации
        config = Config()
        if not config.validate_config():
            logging.error("❌ Ошибка конфигурации. Проверьте config.ini")
            sys.exit(1)
        
        # Запуск в отдельных потоках
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        web_thread = threading.Thread(target=run_web, daemon=True)
        
        bot_thread.start()
        web_thread.start()
        
        logging.info("✅ Бот и веб-панель запущены")
        
        # Ожидание завершения
        bot_thread.join()
        web_thread.join()
        
    except KeyboardInterrupt:
        logging.info("⏹️ Остановка по запросу пользователя")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()