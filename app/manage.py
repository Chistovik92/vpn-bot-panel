#!/usr/bin/env python3
"""CLI управления VPN Bot Panel.

Примеры:
    python -m app.manage init
    python -m app.manage set-password 123456789        # спросит пароль
    python -m app.manage set-role 123456789 admin
    python -m app.manage check
"""
import getpass
import sys

from app.database import Database, UserRole

VALID_ROLES = {r.value for r in UserRole}


def _db():
    return Database()


def cmd_init():
    db = _db()
    print(f'✅ База данных инициализирована: {db.db_path}')


def cmd_set_password(telegram_id: int):
    db = _db()
    if not db.get_user_by_telegram_id(telegram_id):
        print(f'❌ Пользователь {telegram_id} не найден (пусть напишет боту /start)')
        sys.exit(1)
    password = getpass.getpass('Новый пароль: ')
    confirm = getpass.getpass('Повторите пароль: ')
    if password != confirm:
        print('❌ Пароли не совпадают')
        sys.exit(1)
    if len(password) < db.config.get_security_settings()['password_min_length']:
        print('❌ Слишком короткий пароль')
        sys.exit(1)
    db.set_password(telegram_id, password)
    print('✅ Пароль обновлён')


def cmd_set_role(telegram_id: int, role: str):
    if role not in VALID_ROLES:
        print(f'❌ Неверная роль. Допустимо: {", ".join(sorted(VALID_ROLES))}')
        sys.exit(1)
    db = _db()
    if not db.get_user_by_telegram_id(telegram_id):
        print(f'❌ Пользователь {telegram_id} не найден')
        sys.exit(1)
    db.update_user_role(telegram_id, role)
    print(f'✅ Роль пользователя {telegram_id}: {role}')


def cmd_check():
    from app.config import Config
    config = Config()
    ok = config.validate_config()
    print(f"Bot token: {'✅ настроен' if ok else '❌ НЕ настроен'}")
    admin = config.get_admin_telegram_id()
    print(f"Admin telegram id: {admin or '❌ не задан'}")
    Database()  # заодно проверит схему
    print('✅ База данных в порядке')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    try:
        if cmd == 'init':
            cmd_init()
        elif cmd == 'set-password' and len(sys.argv) >= 3:
            cmd_set_password(int(sys.argv[2]))
        elif cmd == 'set-role' and len(sys.argv) >= 4:
            cmd_set_role(int(sys.argv[2]), sys.argv[3].lower())
        elif cmd == 'check':
            cmd_check()
        else:
            print(__doc__)
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
