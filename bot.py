#!/usr/bin/env python3
"""Запуск Telegram бота. Реализация в app.bot."""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs('logs', exist_ok=True)

from app.bot import VPNBot

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    try:
        VPNBot().run()
    except (KeyboardInterrupt, SystemExit):
        pass
