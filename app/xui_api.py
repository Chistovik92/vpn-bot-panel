"""Интеграция с панелями 3x-ui: клиенты, inbounds, генерация конфигов."""
import json
import logging
import uuid
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class XUIAPI:
    """Клиент API панели 3x-ui (cookie-сессия после логина)."""

    def __init__(self, panel_url, username, password):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._logged_in = False

    def login(self):
        """Авторизация в панели, сохранение cookie сессии."""
        if self._logged_in:
            return True
        try:
            response = self.session.post(
                f'{self.panel_url}/login',
                data={'username': self.username, 'password': self.password},
                timeout=10,
            )
            data = response.json()
            if data.get('success'):
                self._logged_in = True
                return True
            logger.error('3x-ui login failed: %s', data.get('msg'))
            return False
        except Exception as e:
            logger.error('3x-ui login error: %s', e)
            return False

    def _make_request(self, endpoint, method='GET', data=None, params=None):
        """Выполнение запроса к API (с автологином)."""
        if not self.login():
            return None
        url = f'{self.panel_url}/{endpoint.lstrip("/")}'
        try:
            response = self.session.request(
                method, url, data=data, params=params, timeout=15
            )
            if response.status_code == 200:
                return response.json()
            logger.error('API Error %s %s: %s', method, url, response.text[:200])
            return None
        except Exception as e:
            logger.error('Request failed %s: %s', url, e)
            return None

    # -------------------------------------------------------------- inbounds
    def get_inbounds(self):
        result = self._make_request('panel/api/inbounds/list')
        if result and result.get('success'):
            return result
        return None

    def get_inbound(self, inbound_id):
        result = self._make_request(
            'panel/api/inbounds/get', method='POST', data={'id': inbound_id}
        )
        if result and result.get('success'):
            return result
        return None

    def add_client(self, inbound_id, email, uuid_str, limit_ip=0,
                   total_gb=0, expiry_time=0, flow=''):
        """Добавление клиента в inbound. Возвращает UUID клиента или None."""
        client = {
            'id': str(uuid_str),
            'email': email,
            'limitIp': limit_ip,
            'totalGB': total_gb,
            'expiryTime': expiry_time,
            'enable': True,
            'tgId': '',
            'subId': uuid.uuid4().hex[:16],
        }
        if flow:
            client['flow'] = flow
        data = {
            'id': inbound_id,
            'settings': json.dumps({'clients': [client]}),
        }
        result = self._make_request(
            'panel/api/inbounds/addClient', method='POST', data=data
        )
        if result and result.get('success'):
            return str(uuid_str)
        return None

    def delete_client(self, inbound_id, client_uuid):
        """Удаление клиента из inbound."""
        result = self._make_request(
            f'panel/api/inbounds/{inbound_id}/delClient/{client_uuid}',
            method='POST',
        )
        return bool(result and result.get('success'))

    def disable_client(self, inbound_id, client_uuid, email):
        """Отключение клиента (enable=False через обновление настроек)."""
        return self._update_client_enable(inbound_id, email, enable=False)

    def _update_client_enable(self, inbound_id, email, enable):
        inbound_info = self.get_inbound(inbound_id)
        if not inbound_info or not inbound_info.get('obj'):
            return False
        try:
            inbound = inbound_info['obj']
            settings = json.loads(inbound.get('settings', '{}'))
            found = False
            for client in settings.get('clients', []):
                if client.get('email') == email:
                    client['enable'] = enable
                    found = True
                    break
            if not found:
                return False
            data = {'id': inbound_id, 'settings': json.dumps(settings)}
            result = self._make_request(
                'panel/api/inbounds/update', method='POST', data=data
            )
            return bool(result and result.get('success'))
        except (ValueError, KeyError) as e:
            logger.error('Update client error: %s', e)
            return False

    def get_system_stats(self):
        result = self._make_request('panel/api/server/status')
        if result and result.get('success'):
            return result
        return None

    # ------------------------------------------------------------- configs
    def generate_config(self, server_host, inbound_row, client_uuid):
        """Генерация ссылки-конфига для клиента по протоколу inbound."""
        protocol = (inbound_row['protocol'] or 'vless').lower()
        port = inbound_row['port'] or 443
        remark = (inbound_row['remark'] or inbound_row['tag'] or 'vpn').replace(' ', '_')

        if protocol == 'vless':
            return (
                f'vless://{client_uuid}@{server_host}:{port}'
                f'?type=tcp&security=none#{remark}'
            )
        if protocol == 'trojan':
            return f'trojan://{client_uuid}@{server_host}:{port}?type=tcp#'
        if protocol == 'vmess':
            import base64
            payload = {
                'v': '2', 'ps': remark, 'add': server_host, 'port': str(port),
                'id': client_uuid, 'aid': '0', 'scy': 'auto', 'net': 'tcp',
                'type': 'none', 'host': '', 'path': '', 'tls': '',
            }
            encoded = base64.b64encode(json.dumps(payload).encode()).decode()
            return f'vmess://{encoded}'
        return None


class XUIAPIManager:
    """Менеджер работы с несколькими серверами 3x-ui."""

    def __init__(self, database):
        self.db = database

    @staticmethod
    def _get_xui_api(server):
        return XUIAPI(server['url'], server['username'], server['password'])

    @staticmethod
    def _host_of(server):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(server['url'])
            return parsed.hostname or server['url']
        except (ValueError, AttributeError):
            return server['url']

    # ------------------------------------------------------------------ sync
    def sync_server_inbounds(self, server_id):
        """Синхронизация inbound подключений сервера с локальной БД."""
        server = self.db.get_server(server_id)
        if not server:
            return False
        try:
            api = self._get_xui_api(server)
            data = api.get_inbounds()
            if not data or 'obj' not in data or data['obj'] is None:
                return False
            for inbound in data['obj']:
                self.db.add_inbound(
                    server_id=server_id,
                    inbound_id=inbound['id'],
                    tag=inbound.get('tag', ''),
                    port=inbound.get('port', 0),
                    protocol=inbound.get('protocol', ''),
                    listen=inbound.get('listen', ''),
                    remark=inbound.get('remark', ''),
                )
            self.update_server_stats(server_id)
            return True
        except Exception as e:
            logger.error('Sync error for server %s: %s', server_id, e)
            return False

    def update_server_stats(self, server_id):
        server = self.db.get_server(server_id)
        if not server:
            return
        active_users = self.db.get_active_users_count_on_server(server_id)
        self.db.update_server_stats(server_id, active_users)
        api = self._get_xui_api(server)
        if api.get_system_stats() is None:
            logger.warning('Server %s (%s) unreachable', server_id, server['name'])

    # ---------------------------------------------------------- subscriptions
    def create_user_subscription(self, user_id, tariff_id=None,
                                 custom_name=None, is_free=False):
        """Создание подписки: клиент на 3x-ui + запись в БД.

        Возвращает (subscription_id, config_or_error).
        """
        user = self.db.get_user_by_telegram_id(user_id)
        if not user:
            return None, 'Пользователь не найден'
        if self.db.is_user_banned(user_id) and not self.db.is_admin(user_id):
            return None, 'Пользователь забанен'

        tariff = None
        if tariff_id:
            tariff = self.db.get_tariff(tariff_id)
            if not tariff:
                return None, 'Тариф не найден'

        if is_free and not self.db.can_create_free_connection(user_id):
            return None, 'Достигнут лимит бесплатных подключений'

        server = self._select_optimal_server()
        if not server:
            return None, 'Нет доступных серверов'

        inbounds = self.db.get_inbounds(server['id'])
        if not inbounds:
            return None, 'На сервере нет доступных подключений (выполните синхронизацию)'
        inbound = inbounds[0]

        try:
            api = self._get_xui_api(server)
            client_uuid = str(uuid.uuid4())
            client_email = f'user{user_id}_{int(datetime.now().timestamp())}@vpn.local'

            total_gb = tariff['traffic_gb'] if tariff else 100
            expiry_days = tariff['duration_days'] if tariff else 365

            client_uuid_result = api.add_client(
                inbound_id=inbound['inbound_id'],
                email=client_email,
                uuid_str=client_uuid,
                total_gb=total_gb * 1073741824,
                expiry_time=int(
                    (datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000
                ),
            )
            if not client_uuid_result:
                return None, 'Ошибка создания клиента на сервере'

            subscription_id = self.db.create_subscription(
                user_id=user_id,
                server_id=server['id'],
                inbound_row_id=inbound['id'],
                tariff_id=tariff_id,
                client_email=client_email,
                client_uuid=client_uuid,
                client_id=client_uuid,
                custom_name=custom_name,
                is_free=is_free,
                expiry_days=expiry_days,
                total_gb=total_gb,
            )

            if is_free:
                self.db.increment_free_connections(user_id)
            self.update_server_stats(server['id'])

            config_data = api.generate_config(
                self._host_of(server), inbound, client_uuid
            )
            return subscription_id, config_data
        except Exception as e:
            logger.error('Subscription creation error: %s', e)
            return None, f'Ошибка создания подписки: {e}'

    # ------------------------------------------------------------------- bans
    def ban_user_on_server(self, user_id, server_id, banned_by, reason):
        server = self.db.get_server(server_id)
        if not server:
            return False, 'Сервер не найден'
        subscriptions = self.db.get_user_subscriptions_on_server(user_id, server_id)
        try:
            api = self._get_xui_api(server)
            banned_count = 0
            for sub in subscriptions:
                inbound = self.db.get_inbounds(server_id)
                inbound_api_id = next(
                    (i['inbound_id'] for i in inbound if i['id'] == sub['inbound_row_id']),
                    None,
                )
                if inbound_api_id and api.delete_client(
                        inbound_api_id, sub['client_uuid']):
                    self.db.deactivate_subscription(sub['id'])
                    self.db.add_server_ban(
                        user_id, server_id, sub['client_uuid'], banned_by, reason
                    )
                    banned_count += 1
            self.update_server_stats(server_id)
            return True, f'Забанено подключений: {banned_count}'
        except Exception as e:
            logger.error('Ban error: %s', e)
            return False, f'Ошибка бана: {e}'

    def ban_user_globally(self, user_id, banned_by, reason):
        servers = self.db.get_servers()
        total_banned = 0
        for server in servers:
            success, message = self.ban_user_on_server(
                user_id, server['id'], banned_by, reason
            )
            if success:
                try:
                    total_banned += int(message.rsplit(': ', 1)[-1])
                except ValueError:
                    pass
        self.db.ban_user(user_id, banned_by, reason, is_global=True)
        return True, (f'Пользователь забанен глобально. '
                      f'Отключено подключений: {total_banned}')

    def unban_user_globally(self, user_id, unbanned_by):
        self.db.unban_user(user_id, unbanned_by)
        self.db.log_action(unbanned_by, 'global_unban',
                           f'Глобальный разбан пользователя {user_id}')
        return True, 'Пользователь разбанен глобально'

    def check_and_auto_unban_admins(self):
        """Автоматическое снятие банов с администраторов и модераторов."""
        servers = self.db.get_servers()
        admin_users = self.db.get_admin_and_moderator_users()
        for admin in admin_users:
            for server in servers:
                for ban in self.db.get_server_bans_for_user(
                        admin['user_id'], server['id']):
                    self.db.remove_server_ban(ban['id'])
                    logger.info('Auto-unbanned admin %s on server %s',
                                admin['user_id'], server['id'])

    # -------------------------------------------------------------- selection
    def _select_optimal_server(self):
        servers = self.db.get_servers()
        active = [s for s in servers if s['is_active']]
        if not active:
            return None
        return min(active, key=lambda x: x['current_users'] / max(x['max_users'], 1))
