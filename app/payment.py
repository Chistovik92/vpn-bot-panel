import logging
from abc import ABC, abstractmethod
import sqlite3

logger = logging.getLogger(__name__)

class PaymentProcessor(ABC):
    """Абстрактный класс для платежных систем"""
    
    @abstractmethod
    def create_payment(self, user_id, amount, description, tariff_id=None):
        pass
    
    @abstractmethod
    def check_payment(self, payment_id):
        pass
    
    @abstractmethod
    def process_webhook(self, request_data):
        pass

class YooMoneyProcessor(PaymentProcessor):
    """Обработчик платежей через YooMoney"""
    
    def __init__(self, shop_id, secret_key):
        self.shop_id = shop_id
        self.secret_key = secret_key
    
    def create_payment(self, user_id, amount, description, tariff_id=None):
        """Создание платежа YooMoney"""
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from yoomoney import Quickpay
            
            payment_id = f"vpn_{user_id}_{tariff_id}_{int(__import__('time').time())}"
            
            quickpay = Quickpay(
                receiver=self.shop_id,
                quickpay_form="shop",
                targets=description,
                paymentType="SB",
                sum=amount,
                label=payment_id
            )
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_url': quickpay.redirected_url,
                'amount': amount
            }
        except Exception as e:
            logger.error(f"YooMoney payment creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_payment(self, payment_id):
        """Проверка статуса платежа YooMoney"""
        try:
            from yoomoney import Client
            
            client = Client(self.secret_key)
            history = client.operation_history(label=payment_id)
            
            for operation in history.operations:
                if operation.status == 'success':
                    return {
                        'success': True,
                        'status': 'completed',
                        'amount': operation.amount,
                        'datetime': operation.datetime
                    }
            
            return {
                'success': True,
                'status': 'pending'
            }
        except Exception as e:
            logger.error(f"YooMoney payment check failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, request_data):
        """Обработка вебхука от YooMoney"""
        # Реализация обработки вебхуков
        pass

class CryptoBotProcessor(PaymentProcessor):
    """Обработчик платежей через CryptoBot"""
    
    def __init__(self, api_token, shop_id):
        self.api_token = api_token
        self.shop_id = shop_id
        self.base_url = "https://pay.crypt.bot/api"
    
    def create_payment(self, user_id, amount, description, tariff_id=None):
        """Создание платежа через CryptoBot"""
        try:
            import requests
            
            payment_id = f"vpn_{user_id}_{tariff_id}_{int(__import__('time').time())}"
            
            payload = {
                "amount": amount,
                "asset": "USDT",
                "description": description,
                "paid_btn_name": "viewItem",
                "paid_btn_url": f"https://t.me/your_bot?start=payment_{payment_id}",
                "payload": payment_id,
                "allow_comments": False,
                "allow_anonymous": False
            }
            
            headers = {
                "Crypto-Pay-API-Token": self.api_token,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/createInvoice",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    invoice = data['result']
                    return {
                        'success': True,
                        'payment_id': payment_id,
                        'payment_url': invoice['pay_url'],
                        'amount': amount,
                        'invoice_id': invoice['invoice_id']
                    }
            
            return {
                'success': False,
                'error': response.text
            }
            
        except Exception as e:
            logger.error(f"CryptoBot payment creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_payment(self, payment_id):
        """Проверка статуса платежа CryptoBot"""
        try:
            import requests
            
            headers = {
                "Crypto-Pay-API-Token": self.api_token
            }
            
            response = requests.get(
                f"{self.base_url}/getInvoices?payload={payment_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data['result']['items']:
                    invoice = data['result']['items'][0]
                    if invoice['status'] == 'paid':
                        return {
                            'success': True,
                            'status': 'completed',
                            'amount': float(invoice['amount']),
                            'datetime': invoice['paid_at']
                        }
                    else:
                        return {
                            'success': True,
                            'status': invoice['status']
                        }
            
            return {
                'success': False,
                'error': 'Payment not found'
            }
            
        except Exception as e:
            logger.error(f"CryptoBot payment check failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, request_data):
        """Обработка вебхука от CryptoBot"""
        pass

class PaymentManager:
    """Менеджер платежей"""
    
    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.processors = {}
        self._setup_processors()
    
    def _setup_processors(self):
        """Настройка платежных процессоров"""
        payment_config = self.config.get_payment_config()
        
        # YooMoney
        if payment_config.get('yoomoney_shop_id') and payment_config.get('yoomoney_secret_key'):
            self.processors['yoomoney'] = YooMoneyProcessor(
                payment_config['yoomoney_shop_id'],
                payment_config['yoomoney_secret_key']
            )
        
        # CryptoBot
        if payment_config.get('cryptobot_token') and payment_config.get('cryptobot_shop_id'):
            self.processors['cryptobot'] = CryptoBotProcessor(
                payment_config['cryptobot_token'],
                payment_config['cryptobot_shop_id']
            )
    
    def get_available_processors(self):
        """Получение доступных платежных систем"""
        return list(self.processors.keys())
    
    def create_payment(self, user_id, tariff_id, processor_name):
        """Создание платежа"""
        tariff = self.db.get_tariff(tariff_id)
        if not tariff:
            return {'success': False, 'error': 'Тариф не найден'}
        
        if processor_name not in self.processors:
            return {'success': False, 'error': 'Платежная система не доступна'}
        
        processor = self.processors[processor_name]
        
        description = f"VPN доступ - {tariff['name']}"
        result = processor.create_payment(user_id, tariff['price'], description, tariff_id)
        
        if result['success']:
            # Сохраняем платеж в БД
            self.db.create_payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=tariff['price'],
                payment_method=processor_name,
                transaction_id=result['payment_id']
            )
        
        return result
    
    def check_payment(self, payment_id, processor_name):
        """Проверка статуса платежа"""
        if processor_name not in self.processors:
            return {'success': False, 'error': 'Платежная система не доступна'}
        
        processor = self.processors[processor_name]
        return processor.check_payment(payment_id)
    
    def process_successful_payment(self, payment_id, user_id, tariff_id):
        """Обработка успешного платежа"""
        from app.xui_api import XUIAPIManager
        
        # Создаем подписку
        api_manager = XUIAPIManager(self.db)
        subscription_id, config_data = api_manager.create_user_subscription(user_id, tariff_id)
        
        if subscription_id:
            # Обновляем статус платежа
            self.db.update_payment_status(payment_id, 'completed')
            
            # Пополняем баланс пользователя (или активируем подписку)
            self.db.update_user_balance(user_id, -self.db.get_tariff(tariff_id)['price'])
            
            return {
                'success': True,
                'subscription_id': subscription_id,
                'config_data': config_data
            }
        else:
            return {
                'success': False,
                'error': config_data  # Здесь config_data содержит ошибку
            }