import requests
import logging
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json

logger = logging.getLogger(__name__)

class XUIAPI:
    def __init__(self, panel_config):
        self.panel_url = panel_config['url']
        self.username = panel_config['username']
        self.password = panel_config['password']
        self.auth = HTTPBasicAuth(self.username, self.password)
        
        # Настройка сессии с повторными попытками
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Настройка заголовков для CORS
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _handle_response(self, response, operation):
        try:
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise Exception(f"Authentication failed for {operation}")
            elif response.status_code == 403:
                raise Exception(f"Access denied for {operation}")
            elif response.status_code == 404:
                raise Exception(f"Resource not found for {operation}")
            else:
                raise Exception(f"HTTP {response.status_code} for {operation}: {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed for {operation}: {str(e)}")

    def login(self):
        """Авторизация в панели"""
        try:
            login_url = f"{self.panel_url}/login"
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            response = self.session.post(login_url, json=login_data, timeout=10)
            return self._handle_response(response, "login")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def create_client(self, email, telegram_id, expiry_days=30):
        """Создание клиента в панели"""
        try:
            # Сначала авторизуемся
            self.login()
            
            # Создаем клиента
            client_url = f"{self.panel_url}/api/client"
            client_data = {
                "email": email,
                "enable": False,  # Изначально выключено, включится после оплаты
                "expiryTime": expiry_days * 86400 * 1000,  # в миллисекундах
                "flow": "xtls-rprx-direct",
                "limitIp": 0,
                "totalGB": 0,
                "telegramId": str(telegram_id),
                "subId": ""
            }
            
            response = self.session.post(client_url, json=client_data, timeout=10)
            result = self._handle_response(response, "create_client")
            
            if result and result.get('success'):
                return result.get('id')
            else:
                raise Exception(f"Client creation failed: {result}")
                
        except Exception as e:
            logger.error(f"Create client failed: {str(e)}")
            raise

    def enable_client(self, client_id):
        """Включение клиента"""
        try:
            enable_url = f"{self.panel_url}/api/client/{client_id}/enable"
            response = self.session.post(enable_url, timeout=10)
            return self._handle_response(response, "enable_client")
        except Exception as e:
            logger.error(f"Enable client failed: {str(e)}")
            raise

    def disable_client(self, client_id):
        """Выключение клиента"""
        try:
            disable_url = f"{self.panel_url}/api/client/{client_id}/disable"
            response = self.session.post(disable_url, timeout=10)
            return self._handle_response(response, "disable_client")
        except Exception as e:
            logger.error(f"Disable client failed: {str(e)}")
            raise

    def get_clients(self):
        """Получение списка клиентов"""
        try:
            self.login()
            clients_url = f"{self.panel_url}/api/clients"
            response = self.session.get(clients_url, timeout=10)
            return self._handle_response(response, "get_clients")
        except Exception as e:
            logger.error(f"Get clients failed: {str(e)}")
            raise

    def get_panel_status(self):
        """Проверка статуса панели"""
        try:
            status_url = f"{self.panel_url}/api/status"
            response = self.session.get(status_url, timeout=10)
            return self._handle_response(response, "get_status")
        except Exception as e:
            logger.error(f"Get panel status failed: {str(e)}")
            return None

    def delete_client(self, client_id):
        """Удаление клиента"""
        try:
            delete_url = f"{self.panel_url}/api/client/{client_id}"
            response = self.session.delete(delete_url, timeout=10)
            return self._handle_response(response, "delete_client")
        except Exception as e:
            logger.error(f"Delete client failed: {str(e)}")
            raise
