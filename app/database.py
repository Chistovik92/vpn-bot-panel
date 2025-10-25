import os
import sqlite3
import hashlib
import secrets
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum

class UserRole(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Database:
        # Добавить эти методы в класс Database

    def get_server(self, server_id):
        """Получение сервера по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
            return cursor.fetchone()

    def get_tariff(self, tariff_id):
        """Получение тарифа по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tariffs WHERE id = ?', (tariff_id,))
            return cursor.fetchone()

    def get_all_tariffs(self):
        """Получение всех тарифов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tariffs ORDER BY price')
            return cursor.fetchall()

    def get_inbounds(self, server_id):
        """Получение inbound подключений сервера"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM inbounds WHERE server_id = ? AND enable = TRUE', (server_id,))
            return cursor.fetchall()

    def add_inbound(self, server_id, inbound_id, tag, port, protocol, listen, remark):
        """Добавление inbound подключения"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO inbounds 
                (server_id, inbound_id, tag, port, protocol, listen, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (server_id, inbound_id, tag, port, protocol, listen, remark))

    def create_subscription(self, user_id, server_id, inbound_id, tariff_id, client_email, 
                          client_uuid, client_id, custom_name, is_free, expiry_days, total_gb):
        """Создание подписки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            expiry_date = datetime.now() + timedelta(days=expiry_days)
            
            cursor.execute('''
                INSERT INTO subscriptions 
                (user_id, server_id, inbound_id, tariff_id, client_email, client_uuid, 
                 client_id, custom_name, is_free, expiry_date, total_gb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, server_id, inbound_id, tariff_id, client_email, client_uuid,
                  client_id, custom_name, is_free, expiry_date, total_gb))
            
            return cursor.lastrowid

    def deactivate_subscription(self, subscription_id):
        """Деактивация подписки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE subscriptions SET is_active = FALSE WHERE id = ?', (subscription_id,))

    def get_user_subscriptions_on_server(self, user_id, server_id):
        """Получение подписок пользователя на сервере"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM subscriptions 
                WHERE user_id = ? AND server_id = ? AND is_active = TRUE
            ''', (user_id, server_id))
            return cursor.fetchall()

    def get_server_bans_for_user(self, user_id, server_id):
        """Получение банов пользователя на сервере"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM server_bans 
                WHERE user_id = ? AND server_id = ?
            ''', (user_id, server_id))
            return cursor.fetchall()

    def remove_server_ban(self, ban_id):
        """Удаление бана на сервере"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM server_bans WHERE id = ?', (ban_id,))

    def get_admin_and_moderator_users(self):
        """Получение администраторов и модераторов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users 
                WHERE role IN (?, ?, ?) AND is_active = TRUE AND is_banned = FALSE
            ''', (UserRole.MODERATOR.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value))
            return cursor.fetchall()

    def create_payment(self, user_id, tariff_id, amount, payment_method, transaction_id):
        """Создание записи о платеже"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (user_id, tariff_id, amount, payment_method, transaction_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, tariff_id, amount, payment_method, transaction_id))
            return cursor.lastrowid

    def update_payment_status(self, transaction_id, status):
        """Обновление статуса платежа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE payments SET status = ? WHERE transaction_id = ?
            ''', (status, transaction_id))

    def update_user_balance(self, user_id, amount):
        """Обновление баланса пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            ''', (amount, user_id))
    def __init__(self, db_path=None):
        from app.config import Config
        self.config = Config()
        self.db_path = db_path or self.config.get_database_path()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Инициализация базы данных с расширенной структурой"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Пользователи системы (все роли)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    balance REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    banned_by INTEGER,
                    banned_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    free_connections_limit INTEGER DEFAULT 0,
                    used_free_connections INTEGER DEFAULT 0,
                    FOREIGN KEY (banned_by) REFERENCES users (id)
                )
            ''')
            
            # Серверы 3x-ui
            cursor.execute('''
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
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Inbound подключения на серверах
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inbounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
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
                    is_reserved BOOLEAN DEFAULT FALSE,
                    reserved_for INTEGER,
                    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE,
                    FOREIGN KEY (reserved_for) REFERENCES users (id)
                )
            ''')
            
            # Тарифы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tariffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    formatted_description TEXT,
                    price REAL NOT NULL,
                    duration_days INTEGER NOT NULL,
                    traffic_gb INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    buttons_json TEXT, -- JSON с кнопками
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Подписки пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    server_id INTEGER NOT NULL,
                    inbound_id INTEGER NOT NULL,
                    tariff_id INTEGER,
                    client_email TEXT NOT NULL,
                    client_uuid TEXT UNIQUE,
                    client_id INTEGER,
                    custom_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_free BOOLEAN DEFAULT FALSE,
                    expiry_date TIMESTAMP,
                    total_gb INTEGER DEFAULT 0,
                    used_gb REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE,
                    FOREIGN KEY (inbound_id) REFERENCES inbounds (id) ON DELETE CASCADE,
                    FOREIGN KEY (tariff_id) REFERENCES tariffs (id) ON DELETE SET NULL
                )
            ''')
            
            # Платежи
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tariff_id INTEGER,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    status TEXT DEFAULT 'pending',
                    transaction_id TEXT UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (tariff_id) REFERENCES tariffs (id) ON DELETE SET NULL
                )
            ''')
            
            # Баны пользователей на серверах
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    server_id INTEGER NOT NULL,
                    client_id INTEGER,
                    banned_by INTEGER,
                    ban_reason TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_global BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE,
                    FOREIGN KEY (banned_by) REFERENCES users (id)
                )
            ''')
            
            # Рекламные кампании
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ad_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    bot_username TEXT,
                    deep_link TEXT,
                    created_by INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    clicks INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    requires_approval BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    approved_by INTEGER,
                    approved_at TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id),
                    FOREIGN KEY (approved_by) REFERENCES users (id)
                )
            ''')
            
            # Логи действий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Настройки модераторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderator_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    max_free_connections INTEGER DEFAULT 3,
                    can_manage_servers BOOLEAN DEFAULT FALSE,
                    can_manage_tariffs BOOLEAN DEFAULT FALSE,
                    can_manage_users BOOLEAN DEFAULT TRUE,
                    can_create_ads BOOLEAN DEFAULT TRUE,
                    can_ban_users BOOLEAN DEFAULT TRUE,
                    requires_approval BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Создание супер администратора по умолчанию
            default_admin = self.get_user_by_telegram_id(1)  # Telegram ID 1 для демо
            if not default_admin:
                cursor.execute('''
                    INSERT INTO users (user_id, username, full_name, role, free_connections_limit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (1, 'admin', 'System Administrator', UserRole.SUPER_ADMIN.value, 9999))
            
            # Создание тарифов по умолчанию
            default_tariffs = [
                ('Basic - 30 дней', 'Базовый тариф на 30 дней', '🔹 <b>Basic - 30 дней</b>\n📅 Срок: 30 дней\n📊 Трафик: 50 GB\n💎 Стабильное соединение', 5.0, 30, 50),
                ('Standard - 90 дней', 'Стандартный тариф на 90 дней', '🔹 <b>Standard - 90 дней</b>\n📅 Срок: 90 дней\n📊 Трафик: 100 GB\n⚡ Высокая скорость', 12.0, 90, 100),
                ('Premium - 180 дней', 'Премиум тариф на 180 дней', '🔹 <b>Premium - 180 дней</b>\n📅 Срок: 180 дней\n📊 Трафик: 200 GB\n🚀 Максимальная скорость', 20.0, 180, 200),
            ]
            
            admin_id = 1
            for tariff in default_tariffs:
                cursor.execute('''
                    INSERT OR IGNORE INTO tariffs (name, description, formatted_description, price, duration_days, traffic_gb, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (*tariff, admin_id))
            
            # Создание индексов
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
                'CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_subscriptions_expiry ON subscriptions(expiry_date)',
                'CREATE INDEX IF NOT EXISTS idx_servers_active ON servers(is_active)',
                'CREATE INDEX IF NOT EXISTS idx_server_bans_user ON server_bans(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_server_bans_global ON server_bans(is_global)',
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            # Установка безопасных прав
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, 0o600)
    
    def _hash_password(self, password):
        """Хеширование пароля"""
        salt = os.urandom(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + password_hash.hex()
    
    def verify_password(self, stored_password, provided_password):
        """Проверка пароля"""
        try:
            salt_hex, password_hash_hex = stored_password.split(':')
            salt = bytes.fromhex(salt_hex)
            new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
            return new_hash.hex() == password_hash_hex
        except:
            return False
    
    # Методы для работы с пользователями и ролями
    def get_user_by_telegram_id(self, telegram_id):
        """Получение пользователя по Telegram ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (telegram_id,))
            return cursor.fetchone()
    
    def create_user(self, user_id, username, full_name, role=UserRole.USER.value):
        """Создание пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, full_name, role)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, full_name, role))
            return cursor.lastrowid
    
    def update_user_role(self, user_id, new_role, moderator_settings=None):
        """Обновление роли пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET role = ? WHERE user_id = ?
            ''', (new_role, user_id))
            
            # Если назначаем модератора, создаем настройки
            if new_role == UserRole.MODERATOR.value and moderator_settings:
                cursor.execute('''
                    INSERT OR REPLACE INTO moderator_settings 
                    (user_id, max_free_connections, can_manage_servers, can_manage_tariffs, 
                     can_manage_users, can_create_ads, can_ban_users, requires_approval)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, *moderator_settings))
    
    def get_user_role(self, user_id):
        """Получение роли пользователя"""
        user = self.get_user_by_telegram_id(user_id)
        return user['role'] if user else UserRole.USER.value
    
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        role = self.get_user_role(user_id)
        return role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    def is_moderator(self, user_id):
        """Проверка, является ли пользователь модератором"""
        role = self.get_user_role(user_id)
        return role in [UserRole.MODERATOR.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    def can_manage_servers(self, user_id):
        """Может ли пользователь управлять серверами"""
        if self.is_admin(user_id):
            return True
        
        user = self.get_user_by_telegram_id(user_id)
        if user and user['role'] == UserRole.MODERATOR.value:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT can_manage_servers FROM moderator_settings WHERE user_id = ?', (user_id,))
                setting = cursor.fetchone()
                return setting and setting['can_manage_servers']
        
        return False
    
    # Методы для управления банами
    def ban_user(self, user_id, banned_by, reason, is_global=False):
        """Бан пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновляем статус пользователя
            cursor.execute('''
                UPDATE users 
                SET is_banned = TRUE, ban_reason = ?, banned_by = ?, banned_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (reason, banned_by, user_id))
            
            # Если глобальный бан, помечаем все подписки неактивными
            if is_global:
                cursor.execute('''
                    UPDATE subscriptions SET is_active = FALSE WHERE user_id = ?
                ''', (user_id,))
            
            return True
    
    def unban_user(self, user_id, unbanned_by):
        """Разбан пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET is_banned = FALSE, ban_reason = NULL, banned_by = NULL, banned_at = NULL
                WHERE user_id = ?
            ''', (user_id,))
            
            # Логируем действие
            self.log_action(unbanned_by, 'unban_user', f'Разбан пользователя {user_id}')
            
            return True
    
    def add_server_ban(self, user_id, server_id, client_id, banned_by, reason, is_global=False):
        """Добавление бана на сервере"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO server_bans (user_id, server_id, client_id, banned_by, ban_reason, is_global)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, server_id, client_id, banned_by, reason, is_global))
            return cursor.lastrowid
    
    def get_global_bans(self):
        """Получение списка глобальных банов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sb.*, u.username, u.full_name, s.name as server_name
                FROM server_bans sb
                JOIN users u ON sb.user_id = u.user_id
                JOIN servers s ON sb.server_id = s.id
                WHERE sb.is_global = TRUE
            ''')
            return cursor.fetchall()
    
    def is_user_banned(self, user_id):
        """Проверка, забанен ли пользователь"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            return user and user['is_banned']
    
    # Методы для работы с серверами
    def add_server(self, name, url, username, password, location, created_by):
        """Добавление сервера"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO servers (name, url, username, password, location, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, url, username, password, location, created_by))
            return cursor.lastrowid
    
    def get_servers(self, user_id=None):
        """Получение списка серверов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id and not self.is_admin(user_id):
                # Модераторы видят только активные серверы
                cursor.execute('''
                    SELECT * FROM servers 
                    WHERE is_active = TRUE 
                    ORDER BY name
                ''')
            else:
                # Администраторы видят все серверы
                cursor.execute('SELECT * FROM servers ORDER BY name')
            
            return cursor.fetchall()
    
    # Методы для работы с тарифами
    def create_tariff(self, name, description, formatted_description, price, duration_days, traffic_gb, created_by, buttons_json=None):
        """Создание тарифа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tariffs (name, description, formatted_description, price, duration_days, traffic_gb, created_by, buttons_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, formatted_description, price, duration_days, traffic_gb, created_by, buttons_json))
            return cursor.lastrowid
    
    def update_tariff_formatted_description(self, tariff_id, formatted_description, buttons_json=None):
        """Обновление форматированного описания тарифа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tariffs 
                SET formatted_description = ?, buttons_json = ?
                WHERE id = ?
            ''', (formatted_description, buttons_json, tariff_id))
            return True
    
    # Методы для рекламных кампаний
    def create_ad_campaign(self, name, description, bot_username, deep_link, created_by, requires_approval=False):
        """Создание рекламной кампании"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ad_campaigns (name, description, bot_username, deep_link, created_by, requires_approval)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, bot_username, deep_link, created_by, requires_approval))
            return cursor.lastrowid
    
    def approve_ad_campaign(self, campaign_id, approved_by):
        """Одобрение рекламной кампании"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE ad_campaigns 
                SET is_approved = TRUE, approved_by = ?, approved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (approved_by, campaign_id))
            return True
    
    # Методы для логов
    def log_action(self, user_id, action, details=None, ip_address=None, user_agent=None):
        """Логирование действия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO action_logs (user_id, action, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, details, ip_address, user_agent))
    
    # Методы для бесплатных подключений
    def can_create_free_connection(self, user_id):
        """Может ли пользователь создать бесплатное подключение"""
        user = self.get_user_by_telegram_id(user_id)
        if not user:
            return False
        
        if self.is_admin(user_id):
            return True
        
        if user['role'] == UserRole.MODERATOR.value:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT used_free_connections, free_connections_limit 
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                user_data = cursor.fetchone()
                if user_data and user_data['used_free_connections'] < user_data['free_connections_limit']:
                    return True
        
        return False
    
    def increment_free_connections(self, user_id):
        """Увеличение счетчика использованных бесплатных подключений"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET used_free_connections = used_free_connections + 1 
                WHERE user_id = ?
            ''', (user_id,))
    
    # Статистика
    def get_system_statistics(self):
        """Получение системной статистики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Пользователи
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (UserRole.USER.value,))
            stats['regular_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (UserRole.MODERATOR.value,))
            stats['moderators'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role IN (?, ?)', 
                         (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value))
            stats['admins'] = cursor.fetchone()[0]
            
            # Серверы и подписки
            cursor.execute('SELECT COUNT(*) FROM servers WHERE is_active = TRUE')
            stats['active_servers'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE')
            stats['active_subscriptions'] = cursor.fetchone()[0]
            
            # Финансы
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "completed"')
            stats['total_revenue'] = cursor.fetchone()[0] or 0
            
            return stats