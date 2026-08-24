#!/usr/bin/env python3
"""Совместимая точка входа веб-панели.

Реализация находится в app.web (ролевой доступ).
Старые service-файлы, запускавшие web_panel.py, продолжают работать.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import Config


def main():
    from app.web import create_app
    cfg = Config().get_web_config()
    app = create_app()
    app.run(host=cfg['host'], port=cfg['port'], debug=False)


if __name__ == '__main__':
    main()
