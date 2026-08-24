"""Платежные системы: YooMoney (основная) и CryptoBot."""
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PaymentProcessor(ABC):
    """Абстрактный класс для платежных систем."""

    @abstractmethod
    def create_payment(self, user_id, amount, description, tariff_id=None):
        pass

    @abstractmethod
    def check_payment(self, payment_id):
        pass


class YooMoneyProcessor(PaymentProcessor):
    """Платежи через YooMoney (Quickpay + проверка истории операций)."""

    def __init__(self, receiver, token):
        self.receiver = receiver
        self.token = token

    def create_payment(self, user_id, amount, description, tariff_id=None):
        try:
            from yoomoney import Quickpay

            payment_id = f'vpn{user_id}t{tariff_id or 0}_{int(time.time())}'
            quickpay = Quickpay(
                receiver=self.receiver,
                quickpay_form='shop',
                targets=description,
                paymentType='SB',
                sum=amount,
                label=payment_id,
            )
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_url': quickpay.redirected_url,
                'amount': amount,
            }
        except Exception as e:
            logger.error('YooMoney payment creation failed: %s', e)
            return {'success': False, 'error': str(e)}

    def check_payment(self, payment_id):
        try:
            from yoomoney import Client

            client = Client(self.token)
            history = client.operation_history(label=payment_id)
            for operation in history.operations:
                if operation.status == 'success':
                    return {
                        'success': True,
                        'status': 'completed',
                        'amount': operation.amount,
                        'datetime': str(operation.datetime),
                    }
            return {'success': True, 'status': 'pending'}
        except Exception as e:
            logger.error('YooMoney check failed: %s', e)
            return {'success': False, 'error': str(e)}


class CryptoBotProcessor(PaymentProcessor):
    """Платежи через CryptoBot."""

    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = 'https://pay.crypt.bot/api'

    def _headers(self):
        return {'Crypto-Pay-API-Token': self.api_token}

    def create_payment(self, user_id, amount, description, tariff_id=None):
        try:
            import requests

            payment_id = f'vpn{user_id}t{tariff_id or 0}_{int(time.time())}'
            payload = {
                'currency_type': 'fiat',
                'fiat': 'RUB',
                'amount': str(amount),
                'description': description,
                'payload': payment_id,
            }
            response = requests.post(
                f'{self.base_url}/createInvoice',
                json=payload, headers=self._headers(), timeout=10,
            )
            data = response.json()
            if response.status_code == 200 and data.get('ok'):
                invoice = data['result']
                return {
                    'success': True,
                    'payment_id': payment_id,
                    'payment_url': invoice['bot_invoice_url']
                    if 'bot_invoice_url' in invoice else invoice['pay_url'],
                    'amount': amount,
                }
            return {'success': False, 'error': data.get('error') or response.text}
        except Exception as e:
            logger.error('CryptoBot payment creation failed: %s', e)
            return {'success': False, 'error': str(e)}

    def check_payment(self, payment_id):
        try:
            import requests

            response = requests.get(
                f'{self.base_url}/getInvoices',
                params={'payload': payment_id},
                headers=self._headers(), timeout=10,
            )
            data = response.json()
            if response.status_code == 200 and data.get('ok'):
                items = list((data['result'].get('items') or {}).values())
                if items:
                    invoice = items[0]
                    if invoice['status'] == 'paid':
                        return {
                            'success': True,
                            'status': 'completed',
                            'amount': float(invoice['amount']),
                        }
                    return {'success': True, 'status': invoice['status']}
            return {'success': False, 'error': 'Payment not found'}
        except Exception as e:
            logger.error('CryptoBot check failed: %s', e)
            return {'success': False, 'error': str(e)}


class PaymentManager:
    """Менеджер платежей: создание счетов и подтверждение подписок."""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.processors = {}
        self._setup_processors()

    def _setup_processors(self):
        pc = self.config.get_payment_config()
        if pc.get('yoomoney_receiver'):
            self.processors['yoomoney'] = YooMoneyProcessor(
                pc['yoomoney_receiver'], pc.get('yoomoney_token', '')
            )
        if pc.get('cryptobot_token'):
            self.processors['cryptobot'] = CryptoBotProcessor(pc['cryptobot_token'])

    def get_available_processors(self):
        return list(self.processors.keys())

    def create_payment(self, user_id, tariff_id, processor_name='yoomoney'):
        tariff = self.db.get_tariff(tariff_id)
        if not tariff:
            return {'success': False, 'error': 'Тариф не найден'}
        if processor_name not in self.processors:
            return {'success': False, 'error': 'Платежная система недоступна'}

        result = self.processors[processor_name].create_payment(
            user_id, tariff['price'], f'VPN доступ - {tariff["name"]}', tariff_id
        )
        if result['success']:
            self.db.create_payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=tariff['price'],
                payment_method=processor_name,
                transaction_id=result['payment_id'],
            )
        return result

    def check_and_process(self, payment_id, user_id):
        """Проверка оплаты и активация подписки при успехе.

        Защита от повторной активации: только платеж в статусе pending.
        """
        payment = self.db.get_payment(payment_id)
        if not payment or payment['user_id'] != user_id:
            return {'success': False, 'error': 'Платеж не найден'}

        processor_name = payment['payment_method'] or 'yoomoney'
        if processor_name not in self.processors:
            return {'success': False, 'error': 'Платежная система недоступна'}

        check = self.processors[processor_name].check_payment(payment_id)
        if not check.get('success'):
            return {'success': False, 'error': check.get('error')}
        if check.get('status') != 'completed':
            return {'success': False, 'error': None}  # ещё не оплачен

        # Уже обработан ранее
        fresh = self.db.get_payment(payment_id)
        if fresh['status'] == 'completed':
            return {'success': True, 'config_data': '', 'already_activated': True}

        # Активация подписки
        from app.xui_api import XUIAPIManager
        api_manager = XUIAPIManager(self.db)
        subscription_id, config_data = api_manager.create_user_subscription(
            user_id, tariff_id=fresh['tariff_id']
        )
        if not subscription_id:
            return {'success': False, 'error': config_data}

        self.db.update_payment_status(payment_id, 'completed')
        self.db.log_action(
            user_id, 'payment_completed', f'{payment_id}: {fresh["amount"]} RUB'
        )
        return {'success': True, 'config_data': config_data,
                'subscription_id': subscription_id}
