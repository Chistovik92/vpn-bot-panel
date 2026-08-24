#!/usr/bin/env python3
"""VPN Bot Panel - Telegram бот с системой ролей."""
import logging
from datetime import time as datetime_time

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, CallbackContext,
    MessageHandler, filters, CallbackQueryHandler,
)

from app.database import Database, UserRole
from app.config import Config
from app.xui_api import XUIAPIManager
from app.payment import PaymentManager

logger = logging.getLogger(__name__)


class VPNBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.api_manager = XUIAPIManager(self.db)
        self.payment_manager = PaymentManager(self.db, self.config)
        self.token = self.config.get_bot_token()

        if not self.config.validate_config():
            raise ValueError('Bot token not configured. Check config.ini [BOT] token')

        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        self.setup_jobs()

    def setup_jobs(self):
        """Периодические задачи: ежедневная очистка истёкших подписок."""
        job_queue = self.application.job_queue
        if job_queue is not None:
            job_queue.run_daily(
                self._cleanup_job, time=datetime_time(3, 0),
                name='cleanup_expired_subscriptions',
            )

    async def _cleanup_job(self, context: CallbackContext) -> None:
        expired = self.db.cleanup_expired_subscriptions()
        if expired:
            logger.info('Деактивировано истёкших подписок: %s', expired)

    # ------------------------------------------------------------- handlers
    def setup_handlers(self):
        app = self.application
        app.add_handler(CommandHandler('start', self.start))
        app.add_handler(CommandHandler('help', self.help))
        app.add_handler(CommandHandler('balance', self.balance))
        app.add_handler(CommandHandler('tariffs', self.show_tariffs))
        app.add_handler(CommandHandler('mysubscriptions', self.my_subscriptions))

        app.add_handler(CommandHandler('admin', self.admin_panel))
        app.add_handler(CommandHandler('moderator', self.moderator_panel))
        app.add_handler(CommandHandler('stats', self.show_stats))

        app.add_handler(CommandHandler('addserver', self.add_server))
        app.add_handler(CommandHandler('servers', self.list_servers))
        app.add_handler(CommandHandler('sync', self.sync_servers))
        app.add_handler(CommandHandler('addmoderator', self.add_moderator))
        app.add_handler(CommandHandler('ban', self.ban_user))
        app.add_handler(CommandHandler('unban', self.unban_user))
        app.add_handler(CommandHandler('free', self.create_free_connection))

        app.add_handler(CallbackQueryHandler(
            self.button_handler, pattern='^(tariff|payment|admin|moderator)_'))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        self.db.create_user(user.id, user.username or '', user.full_name or '')
        role = self.db.get_user_role(user.id)

        if role == UserRole.SUPER_ADMIN.value:
            await self._show_staff_panel(update, '👑 Супер Администратор', user)
        elif role == UserRole.ADMIN.value:
            await self._show_staff_panel(update, '🛡️ Администратор', user)
        elif role == UserRole.MODERATOR.value:
            await self._show_moderator_panel(update, user)
        else:
            await self._show_user_panel(update, user)

    def _user_keyboard(self):
        return ReplyKeyboardMarkup(
            [
                [KeyboardButton('💰 Тарифы'), KeyboardButton('📊 Мои подключения')],
                [KeyboardButton('⚖️ Баланс'), KeyboardButton('ℹ️ Помощь')],
            ],
            resize_keyboard=True,
        )

    async def _show_user_panel(self, update, user):
        text = (
            f'👋 Привет, {user.full_name}!\n\n'
            'Добро пожаловать в VPN Bot Panel!\n\n'
            '**Возможности:**\n'
            '• Покупка VPN тарифов\n'
            '• Управление своими подключениями\n\n'
            '**Команды:**\n'
            '/tariffs - посмотреть и купить тарифы\n'
            '/mysubscriptions - мои подключения\n'
            '/balance - баланс'
        )
        await update.message.reply_text(
            text, reply_markup=self._user_keyboard(), parse_mode='Markdown')

    async def _show_staff_panel(self, update, title, user):
        text = (
            f'{title}\n{user.full_name}\n\n'
            '**Управление:**\n'
            '/addserver - добавить сервер 3x-ui\n'
            '/servers - список серверов\n'
            '/sync - синхронизация серверов\n'
            '/stats - статистика системы\n'
            '/addmoderator USER_ID - назначить модератора\n'
            '/ban USER_ID ПРИЧИНА - забанить\n'
            '/unban USER_ID - разбанить'
        )
        keyboard = [
            [KeyboardButton('💰 Тарифы'), KeyboardButton('📊 Мои подключения')],
            [KeyboardButton('🖥️ Серверы'), KeyboardButton('🔄 Синхронизировать')],
            [KeyboardButton('📈 Статистика'), KeyboardButton('ℹ️ Помощь')],
        ]
        await update.message.reply_text(
            text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown')

    async def _show_moderator_panel(self, update, user):
        text = (
            f'🔧 Модератор\n{user.full_name}\n\n'
            '**Доступно:**\n'
            '/stats - статистика серверов\n'
            f'/free - бесплатное подключение '
            f'({self._free_left(user.id)} осталось)\n'
            '/ban USER_ID ПРИЧИНА - забанить'
        )
        await update.message.reply_text(
            text, reply_markup=self._user_keyboard(), parse_mode='Markdown')

    def _free_left(self, user_id):
        u = self.db.get_user_by_telegram_id(user_id)
        if not u:
            return 0
        return max(u['free_connections_limit'] - u['used_free_connections'], 0)

    # ------------------------------------------------------------ base cmds
    async def help(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text(
            '📖 **Справка**\n\n'
            '/tariffs - купить VPN\n'
            '/mysubscriptions - мои подключения\n'
            '/balance - проверить баланс\n\n'
            'После покупки вы получите ссылку-конфиг для вашего VPN клиента.\n'
            'По вопросам оплаты обращайтесь к администратору.',
            parse_mode='Markdown')

    async def balance(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        bal = self.db.get_user_balance(user.id)
        await update.message.reply_text(f'⚖️ Ваш баланс: {bal:.2f} ₽')

    async def show_tariffs(self, update: Update, context: CallbackContext) -> None:
        tariffs = self.db.get_all_tariffs()
        if not tariffs:
            await update.message.reply_text('❌ Тарифы недоступны')
            return

        processors = self.payment_manager.get_available_processors()
        text = '💰 **Доступные тарифы:**\n\n'
        keyboard = []
        for t in tariffs:
            text += (
                f'🔹 **{t["name"]}**\n'
                f'   📅 {t["duration_days"]} дней | 📊 {t["traffic_gb"]} GB\n'
                f'   💰 {t["price"]:.2f} ₽\n\n'
            )
            row = [InlineKeyboardButton(f'{t["name"]} — {t["price"]:.0f}₽',
                                        callback_data=f'tariff_{t["id"]}_buy')]
            keyboard.append(row)

        if not processors:
            text += '⚠️ Платежные системы не настроены.'
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def my_subscriptions(self, update: Update, context: CallbackContext) -> None:
        subs = self.db.get_user_subscriptions(update.effective_user.id)
        if not subs:
            await update.message.reply_text(
                '📭 У вас нет активных подключений.\nИспользуйте /tariffs')
            return
        text = '📊 **Ваши подключения:**\n\n'
        for s in subs:
            status = '✅' if s['is_active'] else '❌'
            name = s['custom_name'] or s['server_name'] or f'#{s["id"]}'
            text += f'{status} **{name}**\n   до {s["expiry_date"] or "∞"}\n\n'
        await update.message.reply_text(text, parse_mode='Markdown')

    # ------------------------------------------------------------ purchase
    async def process_tariff_purchase(self, query, tariff_id):
        user_id = query.from_user.id
        result = self.payment_manager.create_payment(user_id, tariff_id, 'yoomoney')
        if not result['success']:
            await query.edit_message_text(f'❌ Ошибка платежа: {result.get("error")}')
            return
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Проверить оплату',
                                 callback_data=f'payment_check_{result["payment_id"]}')
        ]])
        await query.edit_message_text(
            f'💳 **Счет создан**\n\n'
            f'Сумма: {result["amount"]:.2f} ₽\n'
            f'ID платежа: `{result["payment_id"]}`\n\n'
            f'[Перейти к оплате]({result["payment_url"]})\n\n'
            'После оплаты нажмите «Проверить оплату».',
            reply_markup=kb, parse_mode='Markdown', disable_web_page_preview=True)

    async def check_payment_status(self, query, payment_id):
        user_id = query.from_user.id
        result = self.payment_manager.check_and_process(payment_id, user_id)
        if result['success']:
            cfg = result.get('config_data') or ''
            await query.edit_message_text(
                '✅ **Оплата подтверждена! Подключение активировано.**\n\n'
                f'**Конфигурация:**\n`{cfg}`',
                parse_mode='Markdown')
        else:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton('🔁 Проверить снова',
                                     callback_data=f'payment_check_{payment_id}')
            ]])
            reason = result.get('error') or 'Оплата еще не поступила.'
            await query.edit_message_text(f'⏳ {reason}', reply_markup=kb)

    # -------------------------------------------------------------- staff
    async def admin_panel(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.is_admin(user.id):
            await update.message.reply_text('❌ Нет прав администратора')
            return
        s = self.db.get_system_statistics()
        kb = [[
            InlineKeyboardButton('🖥️ Серверы', callback_data='admin_servers'),
            InlineKeyboardButton('👥 Пользователи', callback_data='admin_users'),
        ]]
        await update.message.reply_text(
            f"👑 **Панель администратора**\n\n"
            f"👥 Пользователей: {s['total_users']} (мод.: {s['moderators']}, адм.: {s['admins']})\n"
            f"🖥️ Серверов: {s['active_servers']}\n"
            f"📡 Подписок: {s['active_subscriptions']}\n"
            f"💳 Платежей: {s['total_payments']}\n"
            f"💰 Доход: {s['total_revenue']:.2f} ₽",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    async def moderator_panel(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.is_moderator(user.id):
            await update.message.reply_text('❌ Нет прав модератора')
            return
        s = self.db.get_system_statistics()
        await update.message.reply_text(
            f"🔧 **Панель модератора**\n\n"
            f"👥 Пользователей: {s['total_users']}\n"
            f"🖥️ Серверов: {s['active_servers']}\n"
            f"📡 Подписок: {s['active_subscriptions']}\n"
            f"🎁 Бесплатных осталось: {self._free_left(user.id)}",
            parse_mode='Markdown')

    async def show_stats(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.is_moderator(user.id):
            await update.message.reply_text('❌ Недостаточно прав')
            return
        s = self.db.get_system_statistics()
        lines = [f"📈 **Статистика**",
                 f"👥 Всего пользователей: {s['total_users']}",
                 f"🖥️ Активных серверов: {s['active_servers']}",
                 f"📡 Активных подписок: {s['active_subscriptions']}"]
        for server in self.db.get_servers(user.id):
            load = (server['current_users'] / max(server['max_users'], 1)) * 100
            icon = '🟢' if load < 80 else '🟡' if load < 95 else '🔴'
            lines.append(
                f"{icon} {server['name']}: {server['current_users']}/{server['max_users']}")
        await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')

    async def add_server(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.can_manage_servers(user.id):
            await update.message.reply_text('❌ Нет прав управления серверами')
            return
        # /addserver Название URL логин пароль [локация]
        if len(context.args or []) < 4:
            await update.message.reply_text(
                '📝 Формат:\n`/addserver Название URL логин пароль [локация]`\n\n'
                'Пример:\n`/addserver DE1 https://panel.example.com admin pass Германия`',
                parse_mode='Markdown')
            return
        name, url, srv_user, srv_pass = context.args[:4]
        location = context.args[4] if len(context.args) > 4 else ''
        server_id = self.db.add_server(name, url, srv_user, srv_pass, location, user.id)
        ok = self.api_manager.sync_server_inbounds(server_id)
        msg = ('✅ Сервер добавлен и синхронизирован' if ok
               else '⚠️ Сервер добавлен, но синхронизация не удалась — проверьте данные')
        await update.message.reply_text(msg)
        self.db.log_action(user.id, 'add_server', f'{name} ({url})')

    async def list_servers(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.can_manage_servers(user.id):
            await update.message.reply_text('❌ Нет прав')
            return
        servers = self.db.get_servers(user.id)
        if not servers:
            await update.message.reply_text(
                '📭 Серверов нет. Добавьте через /addserver')
            return
        text = '🖥️ **Серверы:**\n\n'
        for s in servers:
            status = '✅' if s['is_active'] else '❌'
            sync = (s['last_sync'] or 'никогда').split('.')[0]
            text += (f"{status} **{s['name']}** ({s['location'] or '-'})\n"
                     f"   👥 {s['current_users']}/{s['max_users']} | sync: {sync}\n")
        await update.message.reply_text(text, parse_mode='Markdown')

    async def sync_servers(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.can_manage_servers(user.id):
            await update.message.reply_text('❌ Нет прав')
            return
        servers = self.db.get_servers(user.id)
        if not servers:
            await update.message.reply_text('📭 Серверов нет')
            return
        ok_count = sum(
            1 for s in servers
            if self.api_manager.sync_server_inbounds(s['id']))
        await update.message.reply_text(
            f'🔄 Синхронизация завершена: {ok_count}/{len(servers)} серверов')

    async def add_moderator(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if self.db.get_user_role(user.id) != UserRole.SUPER_ADMIN.value:
            await update.message.reply_text('❌ Только супер-администратор назначает модераторов')
            return
        if not context.args:
            await update.message.reply_text(
                '📝 Формат: `/addmoderator USER_ID`', parse_mode='Markdown')
            return
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text('❌ Неверный ID')
            return
        settings = (5, False, False, True, True, True, True)
        self.db.update_user_role(target_id, UserRole.MODERATOR.value, settings)
        await update.message.reply_text(
            f'✅ Пользователь {target_id} назначен модератором '
            '(лимит бесплатных подключений: 5)')
        self.db.log_action(user.id, 'add_moderator', f'moderator={target_id}')

    async def ban_user(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.is_moderator(user.id):
            await update.message.reply_text('❌ Нет прав бана')
            return
        if len(context.args or []) < 2:
            await update.message.reply_text(
                '📝 Формат: `/ban USER_ID ПРИЧИНА`', parse_mode='Markdown')
            return
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text('❌ Неверный ID')
            return
        reason = ' '.join(context.args[1:])
        is_global = self.db.is_admin(user.id)
        if is_global:
            success, message = self.api_manager.ban_user_globally(
                target_id, user.id, reason)
        else:
            servers = self.db.get_servers()
            if servers:
                success, message = self.api_manager.ban_user_on_server(
                    target_id, servers[0]['id'], user.id, reason)
            else:
                success, message = False, 'Нет доступных серверов'
        icon = '✅' if success else '❌'
        ban_type = 'глобальный' if is_global else 'на сервере'
        await update.message.reply_text(
            f'{icon} Бан ({ban_type}): {message}\nПричина: {reason}')
        self.db.log_action(user.id, 'ban_user', f'user={target_id}: {reason}')

    async def unban_user(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.is_moderator(user.id):
            await update.message.reply_text('❌ Нет прав')
            return
        if not context.args:
            await update.message.reply_text(
                '📝 Формат: `/unban USER_ID`', parse_mode='Markdown')
            return
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text('❌ Неверный ID')
            return
        _, message = self.api_manager.unban_user_globally(target_id, user.id)
        await update.message.reply_text(f'✅ {message}')

    async def create_free_connection(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        if not self.db.can_create_free_connection(user.id):
            await update.message.reply_text(
                '❌ Функция доступна модераторам и администраторам с лимитом')
            return
        custom_name = ' '.join(context.args) if context.args else None
        sub_id, config_data = self.api_manager.create_user_subscription(
            user.id, custom_name=custom_name, is_free=True)
        if sub_id:
            await update.message.reply_text(
                f'✅ **Бесплатное подключение создано!**\n'
                f'Осталось: {self._free_left(user.id)}\n\n'
                f'**Конфигурация:**\n`{config_data}`',
                parse_mode='Markdown')
            self.db.log_action(user.id, 'create_free_connection', f'sub={sub_id}')
        else:
            await update.message.reply_text(f'❌ {config_data}')

    # ------------------------------------------------------------ callbacks
    async def button_handler(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith('tariff_'):
            parts = data.split('_')  # tariff_<id>_buy
            await self.process_tariff_purchase(query, int(parts[1]))
        elif data.startswith('payment_check_'):
            await self.check_payment_status(query, data.replace('payment_check_', '', 1))
        elif data.startswith('admin_'):
            await self.handle_admin_action(query, data.split('_', 1)[1])
        elif data.startswith('moderator_'):
            await self.handle_moderator_action(query, data.split('_', 1)[1])

    async def handle_admin_action(self, query, action):
        user = query.from_user
        if not self.db.is_admin(user.id):
            await query.edit_message_text('❌ Нет прав администратора')
            return
        if action == 'servers':
            servers = self.db.get_servers(user.id)
            text = '🖥️ **Серверы:**\n\n'
            for s in servers:
                status = '✅' if s['is_active'] else '❌'
                text += (f"{status} **{s['name']}** ({s['location'] or '-'})\n"
                         f"   👥 {s['current_users']}/{s['max_users']}\n")
            await query.edit_message_text(text, parse_mode='Markdown')
        elif action == 'users':
            users = self.db.get_all_users()[:20]
            text = '👥 **Последние пользователи:**\n\n'
            for u in users:
                banned = '🚫' if u['is_banned'] else ''
                text += f"{banned}{u['full_name'] or '-'} (@{u['username'] or '-'}) — {u['role']}\n"
            await query.edit_message_text(text, parse_mode='Markdown')

    async def handle_moderator_action(self, query, action):
        user = query.from_user
        if not self.db.is_moderator(user.id):
            await query.edit_message_text('❌ Нет прав модератора')
            return
        if action == 'servers':
            servers = self.db.get_servers()
            text = '📈 **Мониторинг серверов:**\n\n'
            for s in servers:
                load = (s['current_users'] / max(s['max_users'], 1)) * 100
                icon = '🟢' if load < 80 else '🟡' if load < 95 else '🔴'
                text += (f"{icon} **{s['name']}** ({s['location'] or '-'})\n"
                         f"   👥 {s['current_users']}/{s['max_users']} ({load:.0f}%)\n")
            await query.edit_message_text(text, parse_mode='Markdown')

    # -------------------------------------------------------------- messages
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        text = update.message.text
        routes = {
            '💰 Тарифы': self.show_tariffs,
            '📊 Мои подключения': self.my_subscriptions,
            '⚖️ Баланс': self.balance,
            'ℹ️ Помощь': self.help,
            '📈 Статистика': self.show_stats,
            '🖥️ Серверы': self.list_servers,
            '🔄 Синхронизировать': self.sync_servers,
            '👑 Админ панель': self.admin_panel,
            '🛡️ Админ панель': self.admin_panel,
            '🔧 Панель модератора': self.moderator_panel,
            '🎁 Бесплатное подключение': self.create_free_connection,
        }
        handler = routes.get(text)
        if handler:
            await handler(update, context)
        else:
            await update.message.reply_text('❓ Не понял. Используйте /help')

    # ------------------------------------------------------------------- run
    def run(self):
        logger.info('🚀 Запуск VPN Bot...')
        print('🤖 VPN Bot запускается... (Ctrl+C для остановки)')
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error('Ошибка при запуске бота: %s', e)
            raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    VPNBot().run()
