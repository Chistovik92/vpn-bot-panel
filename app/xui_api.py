import requests
import json
import logging
import uuid
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

class XUIAPIManager:
    def __init__(self, database):
        self.db = database
    
    def _get_xui_api(self, server):
        """Создание экземпляра XUI API для сервера"""
        return XUIAPI(server['url'], server['username'], server['password'])
    
    def sync_server_inbounds(self, server_id):
        """Синхронизация inbound подключений сервера"""
        server = self.db.get_server(server_id)
        if not server:
            return False
        
        try:
            xui_api = self._get_xui_api(server)
            inbounds_data = xui_api.get_inbounds()
            
            if not inbounds_data or 'obj' not in inbounds_data:
                return False
            
            for inbound in inbounds_data['obj']:
                self.db.add_inbound(
                    server_id=server_id,
                    inbound_id=inbound['id'],
                    tag=inbound.get('tag', ''),
                    port=inbound.get('port', 0),
                    protocol=inbound.get('protocol', ''),
                    listen=inbound.get('listen', ''),
                    remark=inbound.get('remark', '')
                )
            
            # Обновляем статистику сервера
            self.update_server_stats(server_id)
            return True
            
        except Exception as e:
            logger.error(f"Sync error for server {server_id}: {str(e)}")
            return False
    
    def update_server_stats(self, server_id):
        """Обновление статистики сервера"""
        server = self.db.get_server(server_id)
        if not server:
            return
        
        try:
            xui_api = self._get_xui_api(server)
            stats = xui_api.get_system_stats()
            
            if stats:
                # Подсчитываем активных пользователей
                active_users = self.db.get_active_users_count_on_server(server_id)
                self.db.update_server_stats(server_id, active_users)
                
        except Exception as e:
            logger.error(f"Stats update error for server {server_id}: {str(e)}")
    
    def create_user_subscription(self, user_id, tariff_id=None, custom_name=None, is_free=False):
        """Создание подписки для пользователя"""
        user = self.db.get_user_by_telegram_id(user_id)
        if not user:
            return None, "Пользователь не найден"
        
        # Проверка бана
        if self.db.is_user_banned(user_id) and not self.db.is_admin(user_id):
            return None, "Пользователь забанен"
        
        tariff = None
        if tariff_id:
            tariff = self.db.get_tariff(tariff_id)
            if not tariff:
                return None, "Тариф не найден"
        
        # Для бесплатных подключений проверяем лимиты
        if is_free and not self.db.can_create_free_connection(user_id):
            return None, "Достигнут лимит бесплатных подключений"
        
        # Выбор оптимального сервера
        server = self._select_optimal_server()
        if not server:
            return None, "Нет доступных серверов"
        
        # Получение доступных inbound подключений
        inbounds = self.db.get_inbounds(server['id'])
        if not inbounds:
            return None, "На сервере нет доступных подключений"
        
        inbound = inbounds[0]
        
        try:
            xui_api = self._get_xui_api(server)
            
            # Генерация уникальных данных
            client_uuid = str(uuid.uuid4())
            client_email = f"user{user_id}_{int(datetime.now().timestamp())}@vpn.com"
            
            # Настройки для подключения
            total_gb = tariff['traffic_gb'] if tariff else 100  # По умолчанию 100GB для бесплатных
            expiry_days = tariff['duration_days'] if tariff else 365  # 1 год для бесплатных
            
            # Создание клиента на сервере
            client_id = xui_api.add_client(
                inbound_id=inbound['inbound_id'],
                email=client_email,
                uuid_str=client_uuid,
                total_gb=total_gb * 1073741824,  # Convert GB to bytes
                expiry_time=int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)
            )
            
            if not client_id:
                return None, "Ошибка создания клиента на сервере"
            
            # Создание подписки в базе данных
            subscription_id = self.db.create_subscription(
                user_id=user_id,
                server_id=server['id'],
                inbound_id=inbound['id'],
                tariff_id=tariff_id,
                client_email=client_email,
                client_uuid=client_uuid,
                client_id=client_id,
                custom_name=custom_name,
                is_free=is_free,
                expiry_days=expiry_days,
                total_gb=total_gb
            )
            
            # Для бесплатных подключений увеличиваем счетчик
            if is_free:
                self.db.increment_free_connections(user_id)
            
            # Генерация конфигурации
            config_data = xui_api.generate_config(inbound['inbound_id'], client_id, inbound['protocol'])
            
            return subscription_id, config_data
            
        except Exception as e:
            logger.error(f"Subscription creation error: {str(e)}")
            return None, f"Ошибка создания подписки: {str(e)}"
    
    def ban_user_on_server(self, user_id, server_id, banned_by, reason):
        """Бан пользователя на конкретном сервере"""
        server = self.db.get_server(server_id)
        if not server:
            return False, "Сервер не найден"
        
        # Получаем подписки пользователя на этом сервере
        subscriptions = self.db.get_user_subscriptions_on_server(user_id, server_id)
        
        try:
            xui_api = self._get_xui_api(server)
            banned_count = 0
            
            for subscription in subscriptions:
                # Удаляем клиента с сервера
                if xui_api.delete_client(subscription['inbound_id'], subscription['client_id']):
                    # Деактивируем подписку
                    self.db.deactivate_subscription(subscription['id'])
                    # Добавляем запись о бане
                    self.db.add_server_ban(user_id, server_id, subscription['client_id'], banned_by, reason)
                    banned_count += 1
            
            return True, f"Забанено подключений: {banned_count}"
            
        except Exception as e:
            logger.error(f"Ban error: {str(e)}")
            return False, f"Ошибка бана: {str(e)}"
    
    def ban_user_globally(self, user_id, banned_by, reason):
        """Глобальный бан пользователя на всех серверах"""
        servers = self.db.get_servers()
        total_banned = 0
        
        for server in servers:
            success, message = self.ban_user_on_server(user_id, server['id'], banned_by, reason)
            if success:
                total_banned += int(message.split(": ")[1])
        
        # Помечаем пользователя забаненным в системе
        self.db.ban_user(user_id, banned_by, reason, is_global=True)
        
        return True, f"Пользователь забанен глобально. Отключено подключений: {total_banned}"
    
    def unban_user_globally(self, user_id, unbanned_by):
        """Глобальный разбан пользователя"""
        # Снимаем бан в системе
        self.db.unban_user(user_id, unbanned_by)
        
        # Логируем действие
        self.db.log_action(unbanned_by, 'global_unban', f'Глобальный разбан пользователя {user_id}')
        
        return True, "Пользователь разбанен глобально"
    
    def check_and_auto_unban_admins(self):
        """Автоматическая проверка и разбан администраторов/модераторов"""
        servers = self.db.get_servers()
        admin_users = self.db.get_admin_and_moderator_users()
        
        for admin in admin_users:
            for server in servers:
                # Проверяем, есть ли бан на этом сервере
                server_bans = self.db.get_server_bans_for_user(admin['user_id'], server['id'])
                for ban in server_bans:
                    # Автоматически снимаем бан для администраторов/модераторов
                    try:
                        xui_api = self._get_xui_api(server)
                        # Восстанавливаем подключение если нужно
                        self.db.remove_server_ban(ban['id'])
                        logger.info(f"Auto-unbanned admin {admin['user_id']} on server {server['id']}")
                    except Exception as e:
                        logger.error(f"Auto-unban error for admin {admin['user_id']}: {str(e)}")
    
    def _select_optimal_server(self):
        """Выбор оптимального сервера"""
        servers = self.db.get_servers()
        
        if not servers:
            return None
        
        # Фильтруем только активные серверы
        active_servers = [s for s in servers if s['is_active']]
        
        if not active_servers:
            return None
        
        # Выбираем сервер с наименьшей нагрузкой
        return min(active_servers, key=lambda x: x['current_users'] / x['max_users'])

class XUIAPI:
    def __init__(self, panel_url, username, password):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint, method='GET', data=None):
        """Выполнение запроса к API"""
        url = f"{self.panel_url}/{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, timeout=10)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=10)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=10)
            elif method == 'DELETE':
                response = self.session.delete(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
    
    def get_inbounds(self):
        """Получение списка inbound подключений"""
        return self._make_request('panel/api/inbounds/list')
    
    def get_inbound(self, inbound_id):
        """Получение информации о inbound"""
        data = {"id": inbound_id}
        return self._make_request('panel/api/inbounds/get', method='POST', data=data)
    
    def add_client(self, inbound_id, email, uuid_str, limit_ip=0, total_gb=0, expiry_time=0):
        """Добавление клиента в inbound"""
        data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": str(uuid_str),
                    "email": email,
                    "limitIp": limit_ip,
                    "totalGB": total_gb,
                    "expiryTime": expiry_time,
                    "enable": True,
                    "tgId": "",
                    "subId": ""
                }]
            })
        }
        
        result = self._make_request('panel/api/inbounds/addClient', method='POST', data=data)
        if result and result.get('success'):
            # Получаем ID нового клиента
            inbound_info = self.get_inbound(inbound_id)
            if inbound_info and 'obj' in inbound_info:
                settings = json.loads(inbound_info['obj']['settings'])
                for client in settings.get('clients', []):
                    if client.get('email') == email:
                        return client.get('id')
        return None
    
    def delete_client(self, inbound_id, client_id):
        """Удаление клиента из inbound"""
        # Сначала получаем текущие настройки inbound
        inbound_info = self.get_inbound(inbound_id)
        if not inbound_info or 'obj' not in inbound_info:
            return False
        
        inbound = inbound_info['obj']
        settings = json.loads(inbound.get('settings', '{}'))
        
        # Удаляем клиента из списка
        clients = settings.get('clients', [])
        settings['clients'] = [client for client in clients if client.get('id') != client_id]
        
        data = {
            "id": inbound_id,
            "settings": json.dumps(settings)
        }
        
        result = self._make_request('panel/api/inbounds/update', method='POST', data=data)
        return result and result.get('success')
    
    def get_system_stats(self):
        """Получение статистики системы"""
        return self._make_request('panel/api/server/status')
    
    def generate_config(self, inbound_id, client_id, protocol='vless'):
        """Генерация конфигурации для клиента"""
        inbound_info = self.get_inbound(inbound_id)
        if not inbound_info or 'obj' not in inbound_info:
            return None
        
        inbound = inbound_info['obj']
        settings = json.loads(inbound.get('settings', '{}'))
        
        # Поиск клиента
        client_data = None
        for client in settings.get('clients', []):
            if client.get('id') == client_id:
                client_data = client
                break
        
        if not client_data:
            return None
        
        # Генерация конфига в зависимости от протокола
        if protocol.lower() == 'vless':
            return self._generate_vless_config(inbound, client_data)
        elif protocol.lower() == 'vmess':
            return self._generate_vmess_config(inbound, client_data)
        elif protocol.lower() == 'trojan':
            return self._generate_trojan_config(inbound, client_data)
        else:
            return self._generate_vless_config(inbound, client_data)
    
    def _generate_vless_config(self, inbound, client):
        """Генерация VLESS конфигурации"""
        config = f"""vless://{client['id']}@{inbound['listen']}:{inbound['port']}?type=tcp&security={inbound.get('streamSettings', {}).get('security', 'none')}&flow={client.get('flow', '')}#{client['email'].replace(' ', '_')}"""
        return config
    
    def _generate_vmess_config(self, inbound, client):
        """Генерация VMess конфигурации"""
        import base64
        import json
        
        config_data = {
            "v": "2",
            "ps": client['email'],
            "add": inbound['listen'],
            "port": inbound['port'],
            "id": client['id'],
            "aid": "0",
            "scy": "auto",
            "net": "tcp",
            "type": "none",
            "host": "",
            "path": "",
            "tls": "none"
        }
        
        config_json = json.dumps(config_data)
        config_base64 = base64.b64encode(config_json.encode()).decode()
        return f"vmess://{config_base64}"
    
    def _generate_trojan_config(self, inbound, client):
        """Генерация Trojan конфигурации"""
        return f"trojan://{client['id']}@{inbound['listen']}:{inbound['port']}?type=tcp&security=tls#{client['email'].replace(' ', '_')}"