"""Тесты базы данных VPN Bot Panel."""
from app.database import Database, UserRole


def make_db(tmp_path, monkeypatch, **config_overrides):
    """Создаёт Database во временном каталоге с тестовым config.ini."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'config.ini'
    token = config_overrides.pop('token', 'TEST_TOKEN')
    admin = config_overrides.pop('admin_telegram_id', '111111')
    config.write_text(
        '[DATABASE]\npath = data/test.db\n'
        f'[BOT]\ntoken = {token}\nadmin_telegram_id = {admin}\n',
        encoding='utf-8',
    )
    return Database(str(tmp_path / 'data' / 'test.db'))


def test_database_initializes(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    with db.get_connection() as conn:
        tables = {
            r[0] for r in conn.execute(
                "select name from sqlite_master where type='table'")
        }
    assert {'users', 'servers', 'inbounds', 'tariffs', 'subscriptions',
            'payments', 'server_bans', 'action_logs', 'audit_log'} <= tables


def test_create_user_preserves_role_and_balance(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.create_user(42, 'user42', 'User 42')
    db.update_user_balance(42, 500)
    db.update_user_role(42, UserRole.ADMIN.value)
    # Повторный /start не должен сбрасывать роль и баланс
    db.create_user(42, 'renamed', 'Renamed')
    user = db.get_user_by_telegram_id(42)
    assert user['balance'] == 500
    assert user['role'] == 'admin'
    assert user['full_name'] == 'Renamed'


def test_default_tariffs_created_once(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    first = len(db.get_all_tariffs())
    assert first >= 3
    # Повторная инициализация не дублирует тарифы (UNIQUE по имени)
    db.init_db()
    assert len(db.get_all_tariffs()) == first


def test_no_demo_super_admin(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    demo = db.get_user_by_telegram_id(1)
    assert demo is None or demo['role'] != 'super_admin'


def test_super_admin_from_config(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    admin = db.get_user_by_telegram_id(111111)
    assert admin is not None
    assert admin['role'] == 'super_admin'


def test_password_hash_roundtrip(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.create_user(42, 'user42', 'User 42')
    db.set_password(42, 'S3cretPass!')
    assert db.authenticate_user(42, 'S3cretPass!') is not None
    assert db.authenticate_user(42, 'wrong') is None


def test_payment_lifecycle(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.create_user(42, 'user42', 'User 42')
    tariff = db.get_all_tariffs()[0]
    txn = 'test_txn_1'
    db.create_payment(42, tariff['id'], tariff['price'], 'yoomoney', txn)
    payment = db.get_payment(txn)
    assert payment['status'] == 'pending'
    db.update_payment_status(txn, 'completed')
    assert db.get_payment(txn)['status'] == 'completed'


def test_subscription_and_stats(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.create_user(42, 'user42', 'User 42')
    server_id = db.add_server('srv1', 'https://x.example.com',
                              'u', 'p', 'DE', 42)
    db.add_inbound(server_id, 1, 'tag1', 443, 'vless', '', 'remark')
    inbounds = db.get_inbounds(server_id)
    assert len(inbounds) == 1
    sub_id = db.create_subscription(
        42, server_id, inbounds[0]['id'], None,
        'a@b.c', 'uuid-1', 'uuid-1', None, False, 30, 50)
    assert sub_id > 0
    stats = db.get_system_statistics()
    assert stats['active_subscriptions'] >= 1
    subs = db.get_user_subscriptions(42)
    assert len(subs) == 1
    assert subs[0]['server_name'] == 'srv1'


def test_cleanup_expired_subscriptions(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.create_user(42, 'user42', 'User 42')
    server_id = db.add_server('s', 'https://x.example.com', 'u', 'p', '', 42)
    db.add_inbound(server_id, 1, 't', 443, 'vless', '', '')
    inbound = db.get_inbounds(server_id)[0]
    from datetime import datetime, timedelta
    past = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    sub_id = db.create_subscription(
        42, server_id, inbound['id'], None, 'e@x.y', 'u1', 'u1',
        None, False, 1, 10)
    with db.get_connection() as conn:
        conn.execute('UPDATE subscriptions SET expiry_date = ? WHERE id = ?',
                     (past, sub_id))
    assert db.cleanup_expired_subscriptions() >= 1
    assert len(db.get_user_subscriptions(42)) == 0


OLD_SCHEMA_SQL = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    balance REAL DEFAULT 0.0,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP
);
CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);
CREATE TABLE inbounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    inbound_id INTEGER NOT NULL,
    tag TEXT NOT NULL
);
CREATE TABLE subscriptions (
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
    expiry_date TIMESTAMP,
    total_gb INTEGER DEFAULT 0
);
"""


def test_migrates_legacy_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.ini').write_text(
        '[DATABASE]\npath = data/test.db\n'
        '[BOT]\ntoken = T\nadmin_telegram_id = 111111\n', encoding='utf-8')
    db_path = str(tmp_path / 'data' / 'legacy.db')
    import os
    import sqlite3
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_SCHEMA_SQL)
    # Данные старой версии: юзер с балансом и подписка со старым inbound_id
    conn.execute(
        "INSERT INTO users (user_id, username, full_name, balance) "
        "VALUES (777, 'old', 'Old User', 150)")
    conn.execute(
        "INSERT INTO inbounds (id, server_id, inbound_id, tag) VALUES (5, 1, 9, 't')")
    conn.execute(
        "INSERT INTO servers (id, name, url, username, password) "
        "VALUES (1, 's', 'https://x.example.com', 'u', 'p')")
    conn.execute(
        "INSERT INTO subscriptions (user_id, server_id, inbound_id, client_email, "
        "client_uuid, is_active) VALUES (777, 1, 5, 'e@x.y', 'u-legacy', 1)")
    conn.commit()
    conn.close()

    from app.database import Database
    db = Database(db_path)

    # Колонки добавлены, данные сохранены
    user = db.get_user_by_telegram_id(777)
    assert user['balance'] == 150
    assert user['role'] == 'user'
    assert user['is_banned'] in (0, False)

    subs = db.get_user_subscriptions(777, only_active=False)
    assert len(subs) == 1
    assert subs[0]['inbound_row_id'] == 5

    # Схема рабочая: можно писать в новые поля
    db.create_user(777, 'old', 'Old User Updated')
    db.update_user_balance(777, -50)
    assert db.get_user_by_telegram_id(777)['balance'] == 100
    sub_id = db.create_subscription(
        777, 1, 5, None, 'new@x.y', 'uuid-new', 'uuid-new', None, False, 30, 10)
    assert sub_id > 0


def test_migration_is_idempotent(tmp_path, monkeypatch):
    db = make_db(tmp_path, monkeypatch)
    db.init_db()
    db.init_db()  # повторный вызов не должен падать или дублировать
    assert len(db.get_all_tariffs()) >= 3
