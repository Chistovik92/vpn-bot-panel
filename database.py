"""Совместимость: реализация переехала в app.database."""
from app.database import Database, UserRole, test_database  # noqa: F401

if __name__ == '__main__':
    test_database()
