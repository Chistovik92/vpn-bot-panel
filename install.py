#!/usr/bin/env python3
"""Интерактивная настройка VPN Bot Panel после установки.

Выполняется внутри venv (обычно вызывается install.sh):
создаёт config.ini, запрашивает токен бота и Telegram ID администратора,
инициализирует БД (миграции применяются автоматически) и задаёт пароль
веб-панели для супер-администратора.

Автоматизация: переменные окружения VPNBOT_TOKEN и VPNBOT_ADMIN_ID.
"""
import configparser
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Корректный вывод эмодзи/кириллицы в консолях с не-UTF-8 кодировкой
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

from getpass import getpass


def ask(prompt, default='', validate=None, error='Некорректное значение',
       secret=False):
    """Интерактивный ввод с валидацией; EOF/Ctrl+D трактуется как пропуск."""
    while True:
        try:
            raw = (getpass(prompt) if secret else input(prompt)).strip()
        except EOFError:
            return default
        if not raw and default:
            return default
        if not raw:
            continue
        if validate is None or validate(raw):
            return raw
        print(f'  ❌ {error}')


def valid_token(token):
    parts = token.split(':', 1)
    return len(token) >= 30 and parts[0].isdigit() and len(parts) == 2


def load_or_create_config():
    from app.config import Config
    config = Config()
    if not os.path.exists(config.config_file):
        config.create_default_config()
    else:
        config.load_config()
    # Гарантируем наличие всех секций новой схемы
    changed = False
    defaults = {
        'DATABASE': {'path': 'data/vpn_bot.db', 'backup_path': 'data/backups/'},
        'WEB': {'host': '127.0.0.1', 'port': '8080', 'debug': 'False'},
        'PAYMENTS': {'yoomoney_receiver': '', 'yoomoney_token': '',
                     'yoomoney_notification_secret': '', 'cryptobot_token': ''},
        'SECURITY': {'max_login_attempts': '5',
                     'lockout_duration_minutes': '30',
                     'session_timeout_minutes': '60',
                     'password_min_length': '8'},
        'LOGGING': {'level': 'INFO', 'file': 'logs/vpn_bot.log'},
    }
    for section, options in defaults.items():
        if not config.config.has_section(section):
            config.config.add_section(section)
            changed = True
        for key, value in options.items():
            if not config.config.has_option(section, key):
                config.config.set(section, key, value)
                changed = True
    if changed:
        with open(config.config_file, 'w', encoding='utf-8') as f:
            config.config.write(f)
    return config


def save_config(config):
    with open(config.config_file, 'w', encoding='utf-8') as f:
        config.config.write(f)
    try:
        os.chmod(config.config_file, 0o600)
    except OSError:
        pass


def setup_token_and_admin(config):
    env_token = os.environ.get('VPNBOT_TOKEN', '').strip()
    env_admin = os.environ.get('VPNBOT_ADMIN_ID', '').strip()

    if env_token and valid_token(env_token):
        token = env_token
    elif env_token:
        print('  ⚠️ VPNBOT_TOKEN в окружении некорректен, запрашиваю вручную')
        token = None
    elif not sys.stdin.isatty():
        token = None
    else:
        token = None

    if token is None and sys.stdin.isatty():
        token = ask(
            '\n🤖 Токен бота от @BotFather\n> ',
            validate=valid_token,
            error='Токен должен быть вида 123456789:ABC...')

    if token:
        if not config.config.has_section('BOT'):
            config.config.add_section('BOT')
        config.config.set('BOT', 'token', token)
        print('  ✅ Токен сохранён')

    admin_raw = env_admin
    if not admin_raw and sys.stdin.isatty():
        admin_raw = ask(
            '\n👑 Telegram ID администратора (профиль в боте получит роль super_admin)\n> ',
            validate=lambda v: v.isdigit(),
            error='ID должен состоять из цифр')
    if admin_raw.isdigit():
        config.config.set('BOT', 'admin_telegram_id', admin_raw)
        print(f'  ✅ Администратор: {admin_raw}')

    save_config(config)

    if not config.validate_config():
        print('\n  ⚠️ Токен бота не задан. Внесите его позже в config.ini [BOT] token.')
    if not config.get_admin_telegram_id():
        print('  ⚠️ admin_telegram_id не задан. Супер-админ не будет создан!')


def init_database(config):
    from app.database import Database
    db = Database(config.get_database_path())
    print(f'✅ База данных готова: {db.db_path}')
    return db


def ensure_super_admin(db, config):
    admin_tg = config.get_admin_telegram_id()
    if not admin_tg:
        return None
    user = db.get_user_by_telegram_id(admin_tg)
    if user:
        if user['role'] != 'super_admin':
            db.update_user_role(admin_tg, 'super_admin')
            print(f'✅ Роль пользователя {admin_tg} повышена до super_admin')
    else:
        db.create_user(admin_tg, 'admin', 'System Administrator',
                       role='super_admin')
        print(f'✅ Создан супер-администратор: {admin_tg}')
    return admin_tg


def setup_panel_password(db, admin_tg):
    if not admin_tg:
        return
    min_len = db.config.get_security_settings()['password_min_length']

    def ok(p):
        return len(p) >= min_len

    # 1) переменная окружения (автоустановка), 2) интерактивный ввод,
    # 3) предупреждение и выход без пароля
    password = os.environ.get('VPNBOT_PANEL_PASSWORD', '')
    if password and not ok(password):
        print(f'  ⚠️ VPNBOT_PANEL_PASSWORD короче {min_len} символов — игнорируется')
        password = ''
    if not password and sys.stdin.isatty():
        password = ask(
            f'\n🔐 Пароль для входа в веб-панель (мин. {min_len} символов)\n> ',
            validate=ok, error=f'Минимум {min_len} символов', secret=True)
        confirm = ask('Повторите пароль\n> ', validate=ok,
                      error='Минимум символов', secret=True)
        if password != confirm:
            print('  ❌ Пароли не совпадают. Задайте позже:')
            print(f'     python -m app.manage set-password {admin_tg}')
            return
    if not ok(password):
        print('  ⚠️ Пароль панели не задан (VPNBOT_PANEL_PASSWORD). '
              'Вход в панель будет невозможен, пока не выполните:\n'
              '     python -m app.manage set-password <TG_ID>')
        return
    db.set_password(admin_tg, password)
    print('  ✅ Пароль веб-панели установлен')


def main():
    print('=== Настройка VPN Bot Panel ===')
    config = load_or_create_config()
    print(f'✅ Конфигурация: {config.config_file}')

    setup_token_and_admin(config)

    # Перечитываем конфиг после изменений
    config.load_config()
    db = init_database(config)
    admin_tg = ensure_super_admin(db, config)
    setup_panel_password(db, admin_tg)

    print('\n=== Настройка завершена ===')
    print('Запуск: python run.py  (бот + панель)')
    print('Проверка состояния: python -m app.manage check')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nУстановка прервана пользователем')
        sys.exit(130)
