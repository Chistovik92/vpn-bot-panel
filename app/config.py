"""Единая конфигурация VPN Bot Panel.

Все модули проекта используют только этот класс.
Схема config.ini: [DATABASE] [BOT] [WEB] [PAYMENTS] [SECURITY] [LOGGING].
Старые ключи предыдущих версий читаются как fallback для совместимости.
"""
import os
import configparser
import secrets
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.ini"

# Маппинг старых ключей -> новые (для миграции старых config.ini)
_LEGACY_KEYS = {
    ("BOT", "admin_id"): "admin_telegram_id",
    ("PAYMENTS", "yookassa_shop_id"): "yoomoney_shop_id",
    ("PAYMENTS", "yookassa_secret_key"): "yoomoney_secret_key",
    ("SECURITY", "web_secret"): "web_secret_key",
}


def _resolve_config_path(explicit=None):
    """Порядок поиска: явный путь -> $VPN_BOT_CONFIG -> CWD -> корень проекта."""
    if explicit:
        return explicit
    env = os.environ.get("VPN_BOT_CONFIG")
    if env:
        return env
    cwd_file = Path.cwd() / "config.ini"
    if cwd_file.is_file():
        return str(cwd_file)
    return str(CONFIG_FILE)


class Config:
    """Класс для работы с конфигурацией."""

    def __init__(self, config_file: str = None):
        self.config_file = _resolve_config_path(config_file)
        self.config = configparser.ConfigParser()
        self.load_config()

    # ------------------------------------------------------------------ load
    def load_config(self) -> configparser.ConfigParser:
        """Загрузка конфигурации из файла (или создание дефолтной)."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
            self._apply_legacy_keys()
        else:
            self.create_default_config()
        return self.config

    def _apply_legacy_keys(self):
        """Перенос значений старых ключей в новые секции."""
        changed = False
        for (section, old), new in _LEGACY_KEYS.items():
            if not self.config.has_section(section):
                continue
            if self.config.has_option(section, old) and not self.config.has_option(section, new):
                value = self.config.get(section, old)
                if value and not value.startswith("YOUR_"):
                    self.config.set(section, new, value)
                    changed = True
        if changed:
            self._write()

    # ---------------------------------------------------------------- create
    def create_default_config(self):
        """Создание конфигурации по умолчанию."""
        self.config["DATABASE"] = {
            "path": "data/vpn_bot.db",
            "backup_path": "data/backups/",
            "backup_retention_days": "30",
        }
        self.config["BOT"] = {
            "token": "YOUR_BOT_TOKEN_HERE",
            "admin_telegram_id": "YOUR_ADMIN_TELEGRAM_ID",
        }
        self.config["WEB"] = {
            "secret_key": secrets.token_urlsafe(32),
            "host": "127.0.0.1",
            "port": "8080",
            "debug": "False",
        }
        self.config["PAYMENTS"] = {
            "yoomoney_receiver": "YOUR_YOOMONEY_WALLET",
            "yoomoney_token": "YOUR_YOOMONEY_TOKEN",
            "cryptobot_token": "",
        }
        self.config["SECURITY"] = {
            "max_login_attempts": "5",
            "lockout_duration_minutes": "30",
            "session_timeout_minutes": "60",
            "password_min_length": "8",
            "auto_unban_interval_hours": "6",
        }
        self.config["LOGGING"] = {
            "level": "INFO",
            "file": "logs/vpn_bot.log",
            "max_size_mb": "10",
            "backup_count": "5",
        }
        self._write()

    def _write(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
        try:
            os.chmod(self.config_file, 0o600)
        except OSError:
            pass  # Windows/ограниченная ФС

    # ----------------------------------------------------------------- paths
    def get_database_path(self) -> str:
        """Абсолютный путь к базе данных (независимо от CWD)."""
        path = self.config.get("DATABASE", "path", fallback="data/vpn_bot.db")
        db_path = Path(path)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)

    # ------------------------------------------------------------------ bot
    def get_bot_token(self) -> str:
        return self.config.get("BOT", "token", fallback="YOUR_BOT_TOKEN_HERE")

    def get_admin_telegram_id(self) -> int:
        for key in ("admin_telegram_id", "admin_id"):
            if self.config.has_option("BOT", key):
                try:
                    return int(self.config.get("BOT", key))
                except (TypeError, ValueError):
                    continue
        return 0

    # ------------------------------------------------------------------ web
    def get_web_secret(self) -> str:
        """Секретный ключ сессий; генерируется и сохраняется автоматически."""
        secret = ""
        if self.config.has_section("WEB"):
            secret = self.config.get("WEB", "secret_key", fallback="")
        if not secret or secret == "GENERATED_SECRET_KEY" or len(secret) < 16:
            secret = secrets.token_urlsafe(32)
            if not self.config.has_section("WEB"):
                self.config.add_section("WEB")
            self.config.set("WEB", "secret_key", secret)
            self._write()
        return secret

    def get_web_config(self) -> Dict[str, Any]:
        return {
            "secret_key": self.get_web_secret(),
            "host": self.config.get("WEB", "host", fallback="127.0.0.1"),
            "port": self.config.getint("WEB", "port", fallback=8080),
            "debug": self.config.getboolean("WEB", "debug", fallback=False),
        }

    # -------------------------------------------------------------- payments
    def get_payment_config(self) -> Dict[str, str]:
        return {
            "yoomoney_receiver": self.config.get(
                "PAYMENTS", "yoomoney_receiver", fallback=""
            ),
            "yoomoney_token": self.config.get(
                "PAYMENTS", "yoomoney_token", fallback=""
            ),
            "cryptobot_token": self.config.get(
                "PAYMENTS", "cryptobot_token", fallback=""
            ),
        }

    # -------------------------------------------------------------- security
    def get_security_settings(self) -> Dict[str, int]:
        return {
            "max_login_attempts": self.config.getint(
                "SECURITY", "max_login_attempts", fallback=5
            ),
            "lockout_duration_minutes": self.config.getint(
                "SECURITY", "lockout_duration_minutes", fallback=30
            ),
            "session_timeout_minutes": self.config.getint(
                "SECURITY", "session_timeout_minutes", fallback=60
            ),
            "password_min_length": self.config.getint(
                "SECURITY", "password_min_length", fallback=8
            ),
        }

    # --------------------------------------------------------------- logging
    def get_logging_config(self) -> Dict[str, Any]:
        return {
            "level": self.config.get("LOGGING", "level", fallback="INFO"),
            "file": self.config.get("LOGGING", "file", fallback="logs/vpn_bot.log"),
            "max_size_mb": self.config.getint("LOGGING", "max_size_mb", fallback=10),
            "backup_count": self.config.getint("LOGGING", "backup_count", fallback=5),
        }

    # ------------------------------------------------------------ validation
    def validate_config(self) -> bool:
        token = self.get_bot_token()
        return bool(token) and token != "YOUR_BOT_TOKEN_HERE"
