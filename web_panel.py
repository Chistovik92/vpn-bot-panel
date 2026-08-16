#!/usr/bin/env python3
"""Compatibility entry point for the web admin panel.

The project uses the SQLite/Flask implementation in admin_panel.py.
This module intentionally re-exports the same Flask app so old service
files that start web_panel.py keep working.
"""
from admin_panel import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
