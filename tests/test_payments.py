"""Тесты платежей: процессоры на моках и вебхук YooMoney."""
import hashlib

import pytest


@pytest.fixture()
def pay_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.ini').write_text(
        '[DATABASE]\npath = data/pay.db\n'
        '[BOT]\ntoken = T\nadmin_telegram_id = 111111\n',
        encoding='utf-8')
    from app.database import Database
    from app.config import Config
    from app.payment import PaymentManager, PaymentProcessor
    db = Database(str(tmp_path / 'data' / 'pay.db'))
    db.create_user(42, 'user42', 'User')

    class FakeProcessor(PaymentProcessor):
        name = 'fake'

        def __init__(self):
            self.paid = False

        def create_payment(self, user_id, amount, description, tariff_id=None):
            return {'success': True, 'payment_id': f'fake_{user_id}_{tariff_id}',
                    'payment_url': 'https://pay.example/1', 'amount': amount}

        def check_payment(self, payment_id):
            if self.paid:
                return {'success': True, 'status': 'completed', 'amount': 5}
            return {'success': True, 'status': 'pending'}

    pm = PaymentManager(db, Config())
    fake = FakeProcessor()
    pm.processors['fake'] = fake
    yield db, pm, fake


def test_create_and_check_pending(pay_env):
    db, pm, fake = pay_env
    tariff = db.get_all_tariffs()[0]
    result = pm.create_payment(42, tariff['id'], 'fake')
    assert result['success']
    payment = db.get_payment(result['payment_id'])
    assert payment['status'] == 'pending'

    # Оплаты еще нет -> активации нет
    out = pm.check_and_process(result['payment_id'], 42)
    assert out['success'] is False and out['error'] is None
    assert db.get_payment(result['payment_id'])['status'] == 'pending'


def test_activation_flow_once_only(pay_env, monkeypatch):
    db, pm, fake = pay_env
    tariff = db.get_all_tariffs()[0]
    result = pm.create_payment(42, tariff['id'], 'fake')
    txn = result['payment_id']

    # Серверов нет: активация вернёт ошибку (нет доступных серверов)
    fake.paid = True
    out = pm.check_and_process(txn, 42)
    assert out['success'] is False
    assert 'сервер' in out['error'].lower()

    # Добавим сервер+inbound и мокаем создание клиента на 3x-ui
    server_id = db.add_server('s1', 'https://x.example.com', 'u', 'p', '', 111111)
    db.add_inbound(server_id, 7, 'tag7', 443, 'vless', '', 'r')
    from app import xui_api as xui_module

    def fake_create(self, user_id, tariff_id=None, custom_name=None,
                    is_free=False):
        sub_id = db.create_subscription(
            user_id, server_id, db.get_inbounds(server_id)[0]['id'],
            tariff_id, 'e@x.y', 'uuid-x', 'uuid-x', None, False, 30, 50)
        return sub_id, 'vless://config-link'

    monkeypatch.setattr(xui_module.XUIAPIManager,
                        'create_user_subscription', fake_create)
    out = pm.check_and_process(txn, 42)
    assert out['success'], out.get('error')
    assert db.get_payment(txn)['status'] == 'completed'
    subs = db.get_user_subscriptions(42)
    assert len(subs) == 1

    # Повторная проверка не создает вторую подписку
    out2 = pm.activate_payment(txn)
    assert out2.get('already_activated')
    assert len(db.get_user_subscriptions(42)) == 1


def test_wrong_owner_cannot_activate(pay_env):
    db, pm, fake = pay_env
    tariff = db.get_all_tariffs()[0]
    result = pm.create_payment(42, tariff['id'], 'fake')
    fake.paid = True
    out = pm.check_and_process(result['payment_id'], 999999)
    assert out['success'] is False


@pytest.fixture()
def webhook_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    secret = 'webhooksecret'
    (tmp_path / 'config.ini').write_text(
        '[DATABASE]\npath = data/webhook.db\n'
        '[BOT]\ntoken = T\nadmin_telegram_id = 111111\n'
        f'[PAYMENTS]\nyoomoney_notification_secret = {secret}\n',
        encoding='utf-8')
    from app.database import Database
    from app.config import Config
    from app.web import create_app
    db = Database(str(tmp_path / 'data' / 'webhook.db'))
    db.create_user(42, 'user42', 'User')
    application = create_app(config=Config(), database=db)
    application.config['TESTING'] = True

    def signed(**fields):
        base = [
            fields.get('notification_type', 'p2p-incoming'),
            fields.get('operation_id', 'op1'),
            fields.get('amount', '5.00'),
            fields.get('currency', '643'),
            fields.get('datetime', '2026-01-01T00:00:00'),
            fields.get('sender', '41001x'),
            fields.get('codepro', 'false'),
            fields.get('label', ''),
            secret,
        ]
        fields.setdefault('notification_type', base[0])
        fields.setdefault('operation_id', base[1])
        fields.setdefault('amount', base[2])
        fields.setdefault('currency', base[3])
        fields.setdefault('datetime', base[4])
        fields.setdefault('sender', base[5])
        fields.setdefault('codepro', base[6])
        fields['sha1_hash'] = hashlib.sha1('&'.join(base).encode()).hexdigest()
        return fields

    yield application, db, signed


def test_webhook_rejects_bad_signature(webhook_env):
    application, _, _ = webhook_env
    client = application.test_client()
    resp = client.post('/webhook/yoomoney', data={'label': 'x',
                                                  'sha1_hash': 'bad'})
    assert resp.status_code == 403


def test_webhook_activates_payment(webhook_env, monkeypatch):
    application, db, signed = webhook_env
    server_id = db.add_server('s1', 'https://x.example.com', 'u', 'p', '', 111111)
    db.add_inbound(server_id, 7, 'tag7', 443, 'vless', '', 'r')
    txn = 'txn_webhook_1'
    db.create_payment(42, None, 5.0, 'yoomoney', txn)

    # Мокаем создание клиента в XUI, чтобы не ходить в сеть
    from app import xui_api as xui_module
    calls = {}

    def fake_create(self, user_id, tariff_id=None, custom_name=None, is_free=False):
        calls['user_id'] = user_id
        return 1234, 'vless://config-link'

    monkeypatch.setattr(xui_module.XUIAPIManager,
                        'create_user_subscription', fake_create)

    client = application.test_client()
    resp = client.post('/webhook/yoomoney', data=signed(label=txn))
    assert resp.status_code == 200
    assert db.get_payment(txn)['status'] == 'completed'
    assert calls['user_id'] == 42

    # Повторный вебхук не дублирует подписку
    resp2 = client.post('/webhook/yoomoney', data=signed(label=txn))
    assert resp2.status_code == 200


def test_webhook_underpaid(webhook_env):
    application, db, signed = webhook_env
    txn = 'txn_small_1'
    db.create_payment(42, None, 10.0, 'yoomoney', txn)
    client = application.test_client()
    resp = client.post('/webhook/yoomoney',
                       data=signed(label=txn, amount='1.00'))
    assert resp.status_code == 400
