import os
from datetime import timedelta

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "123456789").split(',')]

# Настройки платежей
YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER", "4100111234567890")
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN", "YOUR_YOOMONEY_TOKEN")

# База данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vpn_bot.db")

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Мониторинг
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "3600"))

# Веб-панель
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "your-secret-key-here")

# Язык по умолчанию
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru")

# Тарифы
TARIFFS = {
    "monthly": {
        "name_ru": "Месячный",
        "name_en": "Monthly", 
        "days": 30,
        "price": 100.00,
        "description_ru": "Доступ на 30 дней",
        "description_en": "Access for 30 days"
    },
    "quarterly": {
        "name_ru": "Квартальный",
        "name_en": "Quarterly",
        "days": 90,
        "price": 250.00,
        "description_ru": "Доступ на 90 дней (экономия 17%)",
        "description_en": "Access for 90 days (17% savings)"
    }
}
