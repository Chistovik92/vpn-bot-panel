"""Pytest: добавляет корень проекта в sys.path.

Позволяет запускать тесты как `pytest` из любой директории
(в том числе из CI) без установки пакета.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
