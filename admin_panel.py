#!/usr/bin/env python3
"""Совместимый модуль: веб-приложение панели переехало в app.web.

Старый код, делавший `from admin_panel import app`, продолжает работать.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.web import create_app  # noqa: E402,F401

app = create_app()

if __name__ == '__main__':
    host = os.getenv('VPN_PANEL_HOST', '127.0.0.1')
    port = int(os.getenv('VPN_PANEL_PORT', '8080'))
    app.run(host=host, port=port, debug=False)
