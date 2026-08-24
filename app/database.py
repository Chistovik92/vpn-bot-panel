"""База данных VPN Bot Panel (SQLite).

Единая схема: пользователи с ролями, серверы 3x-ui, inbounds, тарифы,
подписки, платежи, баны, рекламные кампании, логи действий.
Поддерживается миграция баз предыдущих версий (ALTER TABLE / rebuild).
"""
import os
import sqlite3
import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum

from app.config import Config


class UserRole(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Недостающие колонки для миграции старых версий: таблица -> {колонка: DDL}
_REQUIRED_COLUMNS = {
    'users': {
        'role': "TEXT DEFAULT 'user'",
        'password_hash': 'TEXT',
        'is_banned': 'BOOLEAN DEFAULT FALSE',
        'ban_reason': 'TEXT',
        'banned_by': 'INTEGER',
        'banned_at': 'TIMESTAMP',
        'free_connections_limit': 'INTEGER DEFAULT 0',
        'used_free_connections': 'INTEGER DEFAULT 0',
    },
    'servers': {
        'location': "TEXT DEFAULT ''",
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'max_users': 'INTEGER DEFAULT 100',
        'current_users': 'INTEGER DEFAULT 0',
        'last_sync': 'TIMESTAMP',
        'created_by': 'INTEGER',
    },
    'inbounds': {
        'port': 'INTEGER',
        'protocol': 'TEXT',
        'listen': 'TEXT',
        'up': 'INTEGER DEFAULT 0',
        'down': 'INTEGER DEFAULT 0',
        'total': 'INTEGER DEFAULT 0',
        'remark': 'TEXT',
        'enable': 'BOOLEAN DEFAULT TRUE',
    },
    'tariffs': {
        'formatted_description': 'TEXT',
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'created_by': 'INTEGER',
        'buttons_json': 'TEXT',
    },
    'subscriptions': {
        'custom_name': 'TEXT',
        'is_free': 'BOOLEAN DEFAULT FALSE',
        'total_gb': 'INTEGER DEFAULT 0',
        'used_gb': 'REAL DEFAULT 0',
    },
    'payments': {
        'currency': "TEXT DEFAULT 'RUB'",
        'payment_method': 'TEXT',
        'status': "TEXT DEFAULT 'pending'",
        'transaction_id': 'TEXT',
        'tariff_id': 'INTEGER',
    },
}


class Database:
    def __init__(self, db_path=None):
        self.config = Config()
        self.db_path = db_path or self.config.get_database_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    # ----------------------------------------------------------- connections
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------------------------------------------------------------- schema
    @staticmethod
    def _table_columns(conn, table):
        cur = conn.execute(f'PRAGMA table_info({table})')
        return {row[1] for row in cur.fetchall()}

    def init_db(self):
        """Инициализация схемы БД и миграция старых версий."""
        with self.get_connection() as conn:
            c = conn.cursor()

            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    password_hash TEXT,
                    balance REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    banned_by INTEGER REFERENCES users (user_id),
                    banned_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    free_connections_limit INTEGER DEFAULT 0,
                    used_free_connections INTEGER DEFAULT 0
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    location TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    max_users INTEGER DEFAULT 100,
                    current_users INTEGER DEFAULT 0,
                    last_sync TIMESTAMP,
                    created_by INTEGER REFERENCES users (user_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS inbounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
                    inbound_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    port INTEGER,
                    protocol TEXT,
                    listen TEXT,
                    up INTEGER DEFAULT 0,
                    down INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    remark TEXT,
                    enable BOOLEAN DEFAULT TRUE,
                    UNIQUE (server_id, inbound_id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS tariffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    formatted_description TEXT,
                    price REAL NOT NULL,
                    duration_days INTEGER NOT NULL,
                    traffic_gb INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by INTEGER REFERENCES users (user_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    buttons_json TEXT
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                    server_id INTEGER NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
                    inbound_row_id INTEGER NOT NULL REFERENCES inbounds (id) ON DELETE CASCADE,
                    tariff_id INTEGER REFERENCES tariffs (id) ON DELETE SET NULL,
                    client_email TEXT NOT NULL,
                    client_uuid TEXT UNIQUE,
                    client_id TEXT,
                    custom_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_free BOOLEAN DEFAULT FALSE,
                    expiry_date TIMESTAMP,
                    total_gb INTEGER DEFAULT 0,
                    used_gb REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                    tariff_id INTEGER REFERENCES tariffs (id) ON DELETE SET NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    status TEXT DEFAULT 'pending',
                    transaction_id TEXT UNIQUE
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS server_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                    server_id INTEGER NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
                    client_uuid TEXT,
                    banned_by INTEGER REFERENCES users (user_id),
                    ban_reason TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_global BOOLEAN DEFAULT FALSE
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS ad_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    bot_username TEXT,
                    deep_link TEXT,
                    created_by INTEGER REFERENCES users (user_id),
                    is_active BOOLEAN DEFAULT TRUE,
                    clicks INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    requires_approval BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    approved_by INTEGER REFERENCES users (user_id),
                    approved_at TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users (user_id),
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL REFERENCES users (user_id),
                    action TEXT NOT NULL,
                    description TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS moderator_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                    max_free_connections INTEGER DEFAULT 3,
                    can_manage_servers BOOLEAN DEFAULT FALSE,
                    can_manage_tariffs BOOLEAN DEFAULT FALSE,
                    can_manage_users BOOLEAN DEFAULT TRUE,
                    can_create_ads BOOLEAN DEFAULT TRUE,
                    can_ban_users BOOLEAN DEFAULT TRUE,
                    requires_approval BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            self._migrate_legacy_schema(conn)

            # Супер-администратор из конфигурации (никаких демо-аккаунтов)
            admin_tg = self.config.get_admin_telegram_id()
            if admin_tg and not self._fetchone(
                    c, 'SELECT 1 FROM users WHERE user_id = ?', (admin_tg,)):
                c.execute(
                    '''INSERT INTO users (user_id, username, full_name, role,
                                          free_connections_limit)
                       VALUES (?, 'admin', 'System Administrator', ?, 9999)''',
                    (admin_tg, UserRole.SUPER_ADMIN.value),
                )

            # Тарифы по умолчанию
            default_tariffs = [
                ('Basic - 30 дней', 'Базовый тариф на 30 дней',
                 '🔹 <b>Basic - 30 дней</b>\n📅 Срок: 30 дней\n📊 Трафик: 50 GB\n'
                 '💎 Стабильное соединение',
                 5.0, 30, 50),
                ('Standard - 90 дней', 'Стандартный тариф на 90 дней',
                 '🔹 <b>Standard - 90 дней</b>\n📅 Срок: 90 дней\n📊 Трафик: 100 GB\n'
                 '⚡ Высокая скорость',
                 12.0, 90, 100),
                ('Premium - 180 дней', 'Премиум тариф на 180 дней',
                 '🔹 <b>Premium - 180 дней</b>\n📅 Срок: 180 дней\n📊 Трафик: 200 GB\n'
                 '🚀 Максимальная скорость',
                 20.0, 180, 200),
            ]
            for t in default_tariffs:
                c.execute(
                    '''INSERT OR IGNORE INTO tariffs
                       (name, description, formatted_description, price,
                        duration_days, traffic_gb)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    t,
                )

            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
                'CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_subscriptions_expiry ON subscriptions(expiry_date)',
                'CREATE INDEX IF NOT EXISTS idx_inbounds_server ON inbounds(server_id)',
                'CREATE INDEX IF NOT EXISTS idx_servers_active ON servers(is_active)',
                'CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)',
                'CREATE INDEX IF NOT EXISTS idx_server_bans_user ON server_bans(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_action_logs_created ON action_logs(created_at)',
            ]
            for idx in indexes:
                c.execute(idx)

            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                pass

    # ------------------------------------------------------------- migration
    def _migrate_legacy_schema(self, conn):
        """Приведение БД предыдущих версий к текущей схеме.

        1) Пересоздание subscriptions со старой колонкой inbound_id.
        2) ALTER TABLE ADD COLUMN для всех недостающих колонок.
        Старые таблицы прежней простой версии (services, vpn_configs, orders,
        admins) не трогаем — данные не удаляем.
        """
        existing_tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        }

        # subscriptions: inbound_id -> inbound_row_id (пересоздание таблицы)
        if 'subscriptions' in existing_tables:
            cols = self._table_columns(conn, 'subscriptions')
            if 'inbound_row_id' not in cols and 'inbound_id' in cols:
                conn.execute('PRAGMA foreign_keys = OFF')
                conn.execute('ALTER TABLE subscriptions RENAME TO subscriptions_old')
                conn.execute('''
                    CREATE TABLE subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                        server_id INTEGER NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
                        inbound_row_id INTEGER NOT NULL REFERENCES inbounds (id) ON DELETE CASCADE,
                        tariff_id INTEGER REFERENCES tariffs (id) ON DELETE SET NULL,
                        client_email TEXT NOT NULL,
                        client_uuid TEXT UNIQUE,
                        client_id TEXT,
                        custom_name TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_free BOOLEAN DEFAULT FALSE,
                        expiry_date TIMESTAMP,
                        total_gb INTEGER DEFAULT 0,
                        used_gb REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                old_cols = self._table_columns(conn, 'subscriptions_old')
                # пары: (колонка в старой таблице, колонка в новой)
                copy_map = [
                    ('id', 'id'),
                    ('user_id', 'user_id'),
                    ('server_id', 'server_id'),
                    ('inbound_id', 'inbound_row_id'),
                    ('tariff_id', 'tariff_id'),
                    ('client_email', 'client_email'),
                    ('client_uuid', 'client_uuid'),
                    ('client_id', 'client_id'),
                    ('custom_name', 'custom_name'),
                    ('is_active', 'is_active'),
                    ('expiry_date', 'expiry_date'),
                    ('total_gb', 'total_gb'),
                ]
                pairs = [(o, n) for o, n in copy_map if o in old_cols]
                select_cols = ', '.join(o for o, _ in pairs)
                insert_cols = ', '.join(n for _, n in pairs)
                conn.execute(
                    f'INSERT INTO subscriptions ({insert_cols}) '
                    f'SELECT {select_cols} FROM subscriptions_old')
                conn.execute('DROP TABLE subscriptions_old')
                conn.execute('PRAGMA foreign_keys = ON')

        # Добавление недостающих колонок
        for table, columns in _REQUIRED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = self._table_columns(conn, table)
            for column, ddl in columns.items():
                if column not in present:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')

    @staticmethod
    def _fetchone(cursor, sql, params=()):
        cursor.execute(sql, params)
        return cursor.fetchone()

    # ------------------------------------------------------------ passwords
    def _hash_password(self, password):
        salt = os.urandom(32)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000)
        return salt.hex() + ':' + digest.hex()

    def verify_password(self, stored_password, provided_password):
        try:
            salt_hex, digest_hex = stored_password.split(':')
            digest = hashlib.pbkdf2_hmac(
                'sha256', provided_password.encode(), bytes.fromhex(salt_hex), 200_000
            )
            return secrets.compare_digest(digest.hex(), digest_hex)
        except (ValueError, AttributeError, TypeError):
            return False

    # ------------------------------------------------------------- users
    def get_user_by_telegram_id(self, telegram_id):
        with self.get_connection() as conn:
            return self._fetchone(
                conn.cursor(), 'SELECT * FROM users WHERE user_id = ?', (telegram_id,)
            )

    def create_user(self, user_id, username, full_name, role=UserRole.USER.value):
        """Создание пользователя или обновление его данных.

        Upsert не сбрасывает роль и баланс существующего пользователя.
        """
        with self.get_connection() as conn:
            conn.cursor().execute(
                '''INSERT INTO users (user_id, username, full_name, role)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       username = excluded.username,
                       full_name = excluded.full_name''',
                (user_id, username, full_name, role),
            )

    def set_password(self, user_id, password):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE users SET password_hash = ? WHERE user_id = ?',
                (self._hash_password(password), user_id),
            )

    def authenticate_user(self, user_id, password):
        """Проверка пароля пользователя веб-панели."""
        user = self.get_user_by_telegram_id(user_id)
        if not user or not user['password_hash']:
            return None
        if not self.verify_password(user['password_hash'], password):
            return None
        return user

    def update_user_role(self, user_id, new_role, moderator_settings=None):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE users SET role = ? WHERE user_id = ?', (new_role, user_id))
            if new_role == UserRole.MODERATOR.value and moderator_settings:
                cur.execute(
                    '''INSERT OR REPLACE INTO moderator_settings
                       (user_id, max_free_connections, can_manage_servers,
                        can_manage_tariffs, can_manage_users, can_create_ads,
                        can_ban_users, requires_approval)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, *moderator_settings),
                )

    def get_user_role(self, user_id):
        user = self.get_user_by_telegram_id(user_id)
        return user['role'] if user else UserRole.USER.value

    def is_admin(self, user_id):
        role = self.get_user_role(user_id)
        return role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

    def is_moderator(self, user_id):
        role = self.get_user_role(user_id)
        return role in (UserRole.MODERATOR.value, UserRole.ADMIN.value,
                        UserRole.SUPER_ADMIN.value)

    def can_manage_servers(self, user_id):
        if self.is_admin(user_id):
            return True
        user = self.get_user_by_telegram_id(user_id)
        if user and user['role'] == UserRole.MODERATOR.value:
            with self.get_connection() as conn:
                row = self._fetchone(
                    conn.cursor(),
                    'SELECT can_manage_servers FROM moderator_settings WHERE user_id = ?',
                    (user_id,),
                )
                return bool(row and row['can_manage_servers'])
        return False

    def toggle_user_active(self, user_id):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE users SET is_active =
                   CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE user_id = ?''',
                (user_id,),
            )

    def get_all_users(self):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT user_id, username, full_name, balance, role,
                          registration_date, is_active, is_banned
                   FROM users ORDER BY registration_date DESC'''
            ).fetchall()

    # ------------------------------------------------------------- bans
    def ban_user(self, user_id, banned_by, reason, is_global=False):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''UPDATE users
                   SET is_banned = TRUE, ban_reason = ?, banned_by = ?,
                       banned_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?''',
                (reason, banned_by, user_id),
            )
            if is_global:
                cur.execute(
                    'UPDATE subscriptions SET is_active = FALSE WHERE user_id = ?',
                    (user_id,),
                )

    def unban_user(self, user_id, unbanned_by):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE users
                   SET is_banned = FALSE, ban_reason = NULL, banned_by = NULL,
                       banned_at = NULL
                   WHERE user_id = ?''',
                (user_id,),
            )
        self.log_action(unbanned_by, 'unban_user', f'Разбан пользователя {user_id}')

    def is_user_banned(self, user_id):
        with self.get_connection() as conn:
            row = self._fetchone(
                conn.cursor(), 'SELECT is_banned FROM users WHERE user_id = ?',
                (user_id,))
            return bool(row and row['is_banned'])

    def add_server_ban(self, user_id, server_id, client_uuid, banned_by, reason,
                       is_global=False):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO server_bans
                   (user_id, server_id, client_uuid, banned_by, ban_reason, is_global)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, server_id, client_uuid, banned_by, reason, is_global),
            )
            return cur.lastrowid

    def get_server_bans_for_user(self, user_id, server_id):
        with self.get_connection() as conn:
            return conn.execute(
                'SELECT * FROM server_bans WHERE user_id = ? AND server_id = ?',
                (user_id, server_id),
            ).fetchall()

    def remove_server_ban(self, ban_id):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM server_bans WHERE id = ?', (ban_id,))

    def get_global_bans(self):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT sb.*, u.username, u.full_name, s.name AS server_name
                   FROM server_bans sb
                   JOIN users u ON sb.user_id = u.user_id
                   JOIN servers s ON sb.server_id = s.id
                   WHERE sb.is_global = TRUE'''
            ).fetchall()

    def get_admin_and_moderator_users(self):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT * FROM users
                   WHERE role IN (?, ?, ?) AND is_active = TRUE AND is_banned = FALSE''',
                (UserRole.MODERATOR.value, UserRole.ADMIN.value,
                 UserRole.SUPER_ADMIN.value),
            ).fetchall()

    # ------------------------------------------------------------- servers
    def add_server(self, name, url, username, password, location, created_by,
                   max_users=100):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO servers
                   (name, url, username, password, location, created_by, max_users)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, url, username, password, location, created_by, max_users),
            )
            return cur.lastrowid

    def delete_server(self, server_id):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM servers WHERE id = ?', (server_id,))

    def toggle_server(self, server_id):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE servers SET is_active =
                   CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id = ?''',
                (server_id,),
            )

    def get_server(self, server_id):
        with self.get_connection() as conn:
            return self._fetchone(
                conn.cursor(), 'SELECT * FROM servers WHERE id = ?', (server_id,))

    def get_servers(self, user_id=None):
        with self.get_connection() as conn:
            if user_id and not self.is_admin(user_id):
                return conn.execute(
                    'SELECT * FROM servers WHERE is_active = TRUE ORDER BY name'
                ).fetchall()
            return conn.execute('SELECT * FROM servers ORDER BY name').fetchall()

    def update_server_stats(self, server_id, current_users):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE servers SET current_users = ?, last_sync = CURRENT_TIMESTAMP
                   WHERE id = ?''',
                (current_users, server_id),
            )

    def get_active_users_count_on_server(self, server_id):
        with self.get_connection() as conn:
            row = self._fetchone(
                conn.cursor(),
                'SELECT COUNT(*) FROM subscriptions WHERE server_id = ? AND is_active = TRUE',
                (server_id,),
            )
            return row[0]

    # ------------------------------------------------------------ inbounds
    def get_inbounds(self, server_id):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT * FROM inbounds WHERE server_id = ? AND enable = TRUE
                   ORDER BY inbound_id''',
                (server_id,),
            ).fetchall()

    def add_inbound(self, server_id, inbound_id, tag, port, protocol, listen, remark):
        with self.get_connection() as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO inbounds
                   (server_id, inbound_id, tag, port, protocol, listen, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (server_id, inbound_id, tag, port, protocol, listen, remark),
            )

    # -------------------------------------------------------------- tariffs
    def get_tariff(self, tariff_id):
        with self.get_connection() as conn:
            return self._fetchone(
                conn.cursor(), 'SELECT * FROM tariffs WHERE id = ?', (tariff_id,))

    def get_all_tariffs(self):
        with self.get_connection() as conn:
            return conn.execute(
                'SELECT * FROM tariffs WHERE is_active = TRUE ORDER BY price'
            ).fetchall()

    def create_tariff(self, name, description, formatted_description, price,
                      duration_days, traffic_gb, created_by, buttons_json=None):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO tariffs
                   (name, description, formatted_description, price, duration_days,
                    traffic_gb, created_by, buttons_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, description, formatted_description, price, duration_days,
                 traffic_gb, created_by, buttons_json),
            )
            return cur.lastrowid

    def update_tariff_formatted_description(self, tariff_id, formatted_description,
                                            buttons_json=None):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE tariffs SET formatted_description = ?, buttons_json = ? WHERE id = ?',
                (formatted_description, buttons_json, tariff_id),
            )

    def toggle_tariff(self, tariff_id):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE tariffs SET is_active =
                   CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id = ?''',
                (tariff_id,),
            )

    # --------------------------------------------------------- subscriptions
    def create_subscription(self, user_id, server_id, inbound_row_id, tariff_id,
                            client_email, client_uuid, client_id, custom_name,
                            is_free, expiry_days, total_gb):
        with self.get_connection() as conn:
            cur = conn.cursor()
            expiry_str = (
                datetime.now() + timedelta(days=expiry_days)
            ).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                '''INSERT INTO subscriptions
                   (user_id, server_id, inbound_row_id, tariff_id, client_email,
                    client_uuid, client_id, custom_name, is_free, expiry_date,
                    total_gb)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, server_id, inbound_row_id, tariff_id, client_email,
                 client_uuid, str(client_id), custom_name, is_free, expiry_str,
                 total_gb),
            )
            return cur.lastrowid

    def deactivate_subscription(self, subscription_id):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE subscriptions SET is_active = FALSE WHERE id = ?',
                (subscription_id,))

    def get_user_subscriptions(self, user_id, only_active=True):
        query = '''
            SELECT sub.*, s.name AS server_name, i.protocol, i.port AS inbound_port
            FROM subscriptions sub
            LEFT JOIN servers s ON s.id = sub.server_id
            LEFT JOIN inbounds i ON i.id = sub.inbound_row_id
            WHERE sub.user_id = ?
        '''
        if only_active:
            query += ' AND sub.is_active = TRUE'
        query += ' ORDER BY sub.created_at DESC'
        with self.get_connection() as conn:
            return conn.execute(query, (user_id,)).fetchall()

    def get_user_subscriptions_on_server(self, user_id, server_id):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT * FROM subscriptions
                   WHERE user_id = ? AND server_id = ? AND is_active = TRUE''',
                (user_id, server_id),
            ).fetchall()

    def cleanup_expired_subscriptions(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''UPDATE subscriptions SET is_active = FALSE
                   WHERE expiry_date < CURRENT_TIMESTAMP AND is_active = TRUE'''
            )
            return cur.rowcount

    # -------------------------------------------------------------- payments
    def create_payment(self, user_id, tariff_id, amount, payment_method,
                       transaction_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO payments
                   (user_id, tariff_id, amount, payment_method, transaction_id)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, tariff_id, amount, payment_method, transaction_id),
            )
            return cur.lastrowid

    def update_payment_status(self, transaction_id, status):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE payments SET status = ? WHERE transaction_id = ?',
                (status, transaction_id),
            )

    def get_payment(self, transaction_id):
        with self.get_connection() as conn:
            return self._fetchone(
                conn.cursor(),
                'SELECT * FROM payments WHERE transaction_id = ?',
                (transaction_id,),
            )

    def get_all_payments(self):
        with self.get_connection() as conn:
            return conn.execute(
                '''SELECT p.*, u.username
                   FROM payments p LEFT JOIN users u ON u.user_id = p.user_id
                   ORDER BY p.payment_date DESC'''
            ).fetchall()

    def update_user_balance(self, user_id, amount):
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id))

    def get_user_balance(self, user_id):
        user = self.get_user_by_telegram_id(user_id)
        return user['balance'] if user else 0.0

    # ------------------------------------------------------ free connections
    def can_create_free_connection(self, user_id):
        user = self.get_user_by_telegram_id(user_id)
        if not user:
            return False
        if self.is_admin(user_id):
            return True
        if user['role'] == UserRole.MODERATOR.value:
            return user['used_free_connections'] < user['free_connections_limit']
        return False

    def increment_free_connections(self, user_id):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE users SET used_free_connections = used_free_connections + 1
                   WHERE user_id = ?''',
                (user_id,),
            )

    # ------------------------------------------------------------ ad campaigns
    def create_ad_campaign(self, name, description, bot_username, deep_link,
                           created_by, requires_approval=False):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                '''INSERT INTO ad_campaigns
                   (name, description, bot_username, deep_link, created_by,
                    requires_approval)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (name, description, bot_username, deep_link, created_by,
                 requires_approval),
            )
            return cur.lastrowid

    def approve_ad_campaign(self, campaign_id, approved_by):
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE ad_campaigns
                   SET is_approved = TRUE, approved_by = ?,
                       approved_at = CURRENT_TIMESTAMP
                   WHERE id = ?''',
                (approved_by, campaign_id),
            )

    # ------------------------------------------------------------------ logs
    def log_action(self, user_id, action, details=None, ip_address=None,
                   user_agent=None):
        with self.get_connection() as conn:
            conn.execute(
                '''INSERT INTO action_logs (user_id, action, details, ip_address,
                                            user_agent)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, action, details, ip_address, user_agent),
            )

    def log_audit(self, admin_id, action, description=None, ip_address=None,
                  user_agent=None):
        with self.get_connection() as conn:
            conn.execute(
                '''INSERT INTO audit_log (admin_id, action, description,
                                          ip_address, user_agent)
                   VALUES (?, ?, ?, ?, ?)''',
                (admin_id, action, description, ip_address, user_agent),
            )

    def get_recent_audit(self, limit=100):
        with self.get_connection() as conn:
            return conn.execute(
                'SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?',
                (limit,)).fetchall()

    # ------------------------------------------------------------- statistics
    def get_system_statistics(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            stats = {}
            stats['total_users'] = self._fetchone(cur, 'SELECT COUNT(*) FROM users')[0]
            stats['regular_users'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM users WHERE role = ?',
                (UserRole.USER.value,))[0]
            stats['moderators'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM users WHERE role = ?',
                (UserRole.MODERATOR.value,))[0]
            stats['admins'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM users WHERE role IN (?, ?)',
                (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value))[0]
            stats['active_servers'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM servers WHERE is_active = TRUE')[0]
            stats['active_subscriptions'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE')[0]
            row = self._fetchone(
                cur, "SELECT SUM(amount) FROM payments WHERE status = 'completed'")
            stats['total_revenue'] = row[0] or 0
            stats['total_payments'] = self._fetchone(
                cur, 'SELECT COUNT(*) FROM payments')[0]
            return stats


def test_database():
    """Проверка подключения и инициализации БД."""
    try:
        db = Database()
        with db.get_connection() as conn:
            tables = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
            }
        required = {'users', 'servers', 'inbounds', 'tariffs', 'subscriptions',
                    'payments', 'server_bans', 'action_logs'}
        missing = required - tables
        if missing:
            print(f'❌ Отсутствуют таблицы: {missing}')
            return False
        print(f'✅ Database OK: {db.db_path}')
        return True
    except Exception as e:
        print(f'❌ Database test failed: {e}')
        return False


if __name__ == '__main__':
    test_database()
