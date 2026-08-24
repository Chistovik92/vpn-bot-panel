"""Совместимость: конфигурация переехала в app.config."""
from app.config import Config, PROJECT_ROOT  # noqa: F401

if __name__ == '__main__':
    config = Config()
    print(f'✅ Config OK: {config.config_file}')
    print(f'✅ Database path: {config.get_database_path()}')
