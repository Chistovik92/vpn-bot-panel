from yoomoney import Quickpay, Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentProcessor:
    def __init__(self, yoomoney_token, yoomoney_receiver):
        self.yoomoney_token = yoomoney_token
        self.yoomoney_receiver = yoomoney_receiver

    def create_yoomoney_payment(self, user_id, amount, tariff_name):
        """Создание платежа YooMoney"""
        try:
            label = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{tariff_name}"
            
            quickpay = Quickpay(
                receiver=self.yoomoney_receiver,
                quickpay_form="shop",
                targets=f"VPN доступ - {tariff_name}",
                paymentType="SB",
                sum=amount,
                label=label
            )
            
            return {
                'success': True,
                'payment_url': quickpay.redirected_url,
                'payment_id': label
            }
        except Exception as e:
            logger.error(f"YooMoney payment creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def check_yoomoney_payment(self, payment_id):
        """Проверка статуса платежа YooMoney"""
        try:
            client = Client(self.yoomoney_token)
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

    def create_stars_payment(self, user_id, amount, tariff_name):
        """Создание платежа через Telegram Stars"""
        # Здесь будет реализация для Telegram Stars
        # Пока заглушка
        return {
            'success': False,
            'error': 'Telegram Stars payment not implemented yet'
        }
