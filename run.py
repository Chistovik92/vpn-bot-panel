#!/usr/bin/env python3
"""Совместный запуск веб-панели и Telegram бота.

Веб-панель работает в фоновом потоке, бот — в главном
(telegram-bot-polling требует главный поток для обработки сигналов).
"""
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import Config


def setup_logging():
    log_cfg = Config().get_logging_config()
    log_file = log_cfg['file']
    os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
    level = getattr(logging, str(log_cfg['level']).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_web():
    try:
        from app.web import create_app
        web_cfg = Config().get_web_config()
        app = create_app()
        app.run(host=web_cfg['host'], port=web_cfg['port'],
                debug=False, use_reloader=False)
    except Exception as e:
        logging.error('Ошибка веб-панели: %s', e)


def run_bot():
    from app.bot import VPNBot
    VPNBot().run()


def main():
    setup_logging()
    logging.info('🚀 Запуск VPN Bot Panel...')

    config = Config()
    if not config.validate_config():
        logging.error('❌ Токен бота не настроен. Проверьте config.ini')
        sys.exit(1)

    web_thread = threading.Thread(target=run_web, daemon=True,
                                  name='web-panel')
    web_thread.start()

    try:
        run_bot()
    except KeyboardInterrupt:
        logging.info('⏹️ Остановка по запросу пользователя')
    except Exception as e:
        logging.error('❌ Критическая ошибка: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
