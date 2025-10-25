#!/usr/bin/env python3
"""
VPN Bot Panel - Расширенный Telegram бот с системой ролей
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
from telegram.ext import ContextTypes

from app.database import Database, UserRole
from app.config import Config
from app.xui_api import XUIAPIManager
from app.payment import PaymentManager

class VPNBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.api_manager = XUIAPIManager(self.db)
        self.payment_manager = PaymentManager(self.db, self.config)
        self.token = self.config.get_bot_token()
        
        if not self.token or self.token == 'YOUR_BOT_TOKEN_HERE':
            logging.error("❌ Токен бота не настроен. Установите его в config.ini")
            raise ValueError("Bot token not configured")
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        # Основные команды для всех пользователей
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("balance", self.balance))
        self.application.add_handler(CommandHandler("tariffs", self.show_tariffs))
        self.application.add_handler(CommandHandler("mysubscriptions", self.my_subscriptions))
        
        # Команды для модераторов и администраторов
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("moderator", self.moderator_panel))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        
        # Команды управления для администраторов
        self.application.add_handler(CommandHandler("addserver", self.add_server))
        self.application.add_handler(CommandHandler("servers", self.list_servers))
        self.application.add_handler(CommandHandler("sync", self.sync_servers))
        self.application.add_handler(CommandHandler("addmoderator", self.add_moderator))
        self.application.add_handler(CommandHandler("ban", self.ban_user))
        self.application.add_handler(CommandHandler("unban", self.unban_user))
        
        # Команды для бесплатных подключений
        self.application.add_handler(CommandHandler("free", self.create_free_connection))
        
        # Обработчики callback запросов
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^tariff_"))
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^payment_"))
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^admin_"))
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^moderator_"))
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^server_"))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.create_user(user.id, user.username, user.full_name)
        
        # Логируем действие
        self.db.log_action(user.id, 'start_bot')
        
        role = self.db.get_user_role(user.id)
        
        if role == UserRole.SUPER_ADMIN.value:
            await self._show_super_admin_panel(update, user)
        elif role == UserRole.ADMIN.value:
            await self._show_admin_panel(update, user)
        elif role == UserRole.MODERATOR.value:
            await self._show_moderator_panel(update, user)
        else:
            await self._show_user_panel(update, user)
    
    async def _show_super_admin_panel(self, update, user):
        """Показ панели супер администратора"""
        welcome_text = f"""
👑 **Привет, {user.full_name}!**

Вы вошли как **Супер Администратор** системы.

**Полный доступ к функциям:**
• Управление серверами 3x-ui
• Добавление/удаление администраторов и модераторов
• Управление тарифами и оформлением
• Система банов и модерации
• Финансовая статистика
• Создание бесплатных подключений

**Основные команды:**
/admin - Расширенная панель управления
/addserver - Добавить сервер 3x-ui
/addmoderator - Назначить модератора
/stats - Статистика системы
/free - Создать бесплатное подключение
"""
        
        keyboard = [
            [KeyboardButton("💰 Тарифы"), KeyboardButton("📊 Мои подключения")],
            [KeyboardButton("👑 Админ панель"), KeyboardButton("🔄 Синхронизировать")],
            [KeyboardButton("📈 Статистика"), KeyboardButton("🎁 Бесплатное подключение")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_admin_panel(self, update, user):
        """Показ панели администратора"""
        welcome_text = f"""
🛡️ **Привет, {user.full_name}!**

Вы вошли как **Администратор** системы.

**Доступные функции:**
• Управление серверами 3x-ui
• Управление тарифами и оформлением
• Система банов и модерации
• Создание бесплатных подключений

**Основные команды:**
/admin - Панель управления
/addserver - Добавить сервер 3x-ui
/stats - Статистика системы
/free - Создать бесплатное подключение
"""
        
        keyboard = [
            [KeyboardButton("💰 Тарифы"), KeyboardButton("📊 Мои подключения")],
            [KeyboardButton("🛡️ Админ панель"), KeyboardButton("🔄 Синхронизировать")],
            [KeyboardButton("📈 Статистика"), KeyboardButton("🎁 Бесплатное подключение")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_moderator_panel(self, update, user):
        """Показ панели модератора"""
        welcome_text = f"""
🔧 **Привет, {user.full_name}!**

Вы вошли как **Модератор** системы.

**Доступные функции:**
• Мониторинг серверов и нагрузки
• Создание рекламных ссылок
• Управление пользователями (бан/разбан)
• Создание ограниченного числа бесплатных подключений

**Основные команды:**
/moderator - Панель модератора
/stats - Статистика серверов
/free - Создать бесплатное подключение
"""
        
        keyboard = [
            [KeyboardButton("💰 Тарифы"), KeyboardButton("📊 Мои подключения")],
            [KeyboardButton("🔧 Панель модератора"), KeyboardButton("📈 Статистика")],
            [KeyboardButton("🎁 Бесплатное подключение"), KeyboardButton("ℹ️ Помощь")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_user_panel(self, update, user):
        """Показ панели обычного пользователя"""
        welcome_text = f"""
👋 **Привет, {user.full_name}!**

Добро пожаловать в VPN Bot Panel!

**Доступные функции:**
• Покупка VPN тарифов
• Управление своими подключениями
• Смена серверов

**Основные команды:**
/tariffs - Посмотреть и купить тарифы
/mysubscriptions - Мои активные подключения
/balance - Проверить баланс

Для получения помощи используйте /help
"""
        
        keyboard = [
            [KeyboardButton("💰 Тарифы"), KeyboardButton("📊 Мои подключения")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def admin_panel(self, update: Update, context: CallbackContext) -> None:
        """Панель администратора"""
        user = update.effective_user
        
        if not self.db.is_admin(user.id):
            await update.message.reply_text("❌ У вас нет прав администратора")
            return
        
        stats = self.db.get_system_statistics()
        
        text = "👑 **Панель администратора**\n\n"
        text += f"📊 **Статистика системы:**\n"
        text += f"   👥 Пользователей: {stats['total_users']}\n"
        text += f"   👤 Обычные: {stats['regular_users']}\n"
        text += f"   🔧 Модераторы: {stats['moderators']}\n"
        text += f"   🛡️ Администраторы: {stats['admins']}\n"
        text += f"   🖥️ Серверов: {stats['active_servers']}\n"
        text += f"   📡 Подписок: {stats['active_subscriptions']}\n"
        text += f"   💰 Общий доход: {stats['total_revenue']:.2f} ₽\n\n"
        
        text += "**Управление системой:**"
        
        keyboard = [
            [InlineKeyboardButton("🖥️ Управление серверами", callback_data="admin_servers")],
            [InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
            [InlineKeyboardButton("💰 Управление тарифами", callback_data="admin_tariffs")],
            [InlineKeyboardButton("🔧 Назначить модератора", callback_data="admin_add_moderator")],
            [InlineKeyboardButton("📊 Подробная статистика", callback_data="admin_stats")],
        ]
        
        if self.db.get_user_role(user.id) == UserRole.SUPER_ADMIN.value:
            keyboard.append([InlineKeyboardButton("⚙️ Системные настройки", callback_data="admin_settings")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def moderator_panel(self, update: Update, context: CallbackContext) -> None:
        """Панель модератора"""
        user = update.effective_user
        
        if not self.db.is_moderator(user.id):
            await update.message.reply_text("❌ У вас нет прав модератора")
            return
        
        stats = self.db.get_system_statistics()
        
        text = "🔧 **Панель модератора**\n\n"
        text += f"📊 **Статистика:**\n"
        text += f"   👥 Пользователей: {stats['total_users']}\n"
        text += f"   🖥️ Серверов: {stats['active_servers']}\n"
        text += f"   📡 Активных подписок: {stats['active_subscriptions']}\n\n"
        
        text += "**Доступные действия:**"
        
        keyboard = [
            [InlineKeyboardButton("📈 Мониторинг серверов", callback_data="moderator_servers")],
            [InlineKeyboardButton("👥 Управление пользователями", callback_data="moderator_users")],
            [InlineKeyboardButton("📢 Создать рекламную ссылку", callback_data="moderator_ads")],
            [InlineKeyboardButton("🎁 Мои бесплатные подключения", callback_data="moderator_free")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_moderator(self, update: Update, context: CallbackContext) -> None:
        """Добавление модератора"""
        user = update.effective_user
        
        if self.db.get_user_role(user.id) != UserRole.SUPER_ADMIN.value:
            await update.message.reply_text("❌ Только супер администратор может назначать модераторов")
            return
        
        if context.args and len(context.args) >= 1:
            try:
                target_user_id = int(context.args[0])
                target_username = context.args[1] if len(context.args) > 1 else "Модератор"
                
                # Настройки модератора по умолчанию
                moderator_settings = (
                    5,  # max_free_connections
                    False,  # can_manage_servers
                    False,  # can_manage_tariffs
                    True,   # can_manage_users
                    True,   # can_create_ads
                    True,   # can_ban_users
                    True    # requires_approval
                )
                
                self.db.update_user_role(target_user_id, UserRole.MODERATOR.value, moderator_settings)
                
                await update.message.reply_text(
                    f"✅ Пользователь {target_username} (ID: {target_user_id}) назначен модератором!\n\n"
                    f"**Настройки по умолчанию:**\n"
                    f"• Макс. бесплатных подключений: 5\n"
                    f"• Может управлять пользователями: Да\n"
                    f"• Может создавать рекламу: Да\n"
                    f"• Может банить пользователей: Да\n"
                    f"• Требуется одобрение: Да",
                    parse_mode='Markdown'
                )
                
                # Логируем действие
                self.db.log_action(user.id, 'add_moderator', f'Назначен модератор {target_user_id}')
                
            except (ValueError, IndexError):
                await update.message.reply_text(
                    "❌ Неверный формат команды.\n"
                    "Используйте: /addmoderator USER_ID [USERNAME]\n"
                    "Пример: /addmoderator 123456789 JohnDoe"
                )
        else:
            await update.message.reply_text(
                "📝 **Добавление модератора**\n\n"
                "Формат команды:\n"
                "`/addmoderator USER_ID [USERNAME]`\n\n"
                "Пример:\n"
                "`/addmoderator 123456789 ИванИванов`",
                parse_mode='Markdown'
            )
    
    async def create_free_connection(self, update: Update, context: CallbackContext) -> None:
        """Создание бесплатного подключения"""
        user = update.effective_user
        
        if not self.db.can_create_free_connection(user.id):
            await update.message.reply_text(
                "❌ Вы не можете создать бесплатное подключение.\n"
                "Эта функция доступна только модераторам и администраторам."
            )
            return
        
        custom_name = None
        if context.args:
            custom_name = ' '.join(context.args)
        
        # Создаем подключение
        subscription_id, config_data = self.api_manager.create_user_subscription(
            user.id, 
            custom_name=custom_name, 
            is_free=True
        )
        
        if subscription_id:
            await update.message.reply_text(
                f"✅ **Бесплатное подключение создано!**\n\n"
                f"**Название:** {custom_name or 'Бесплатное подключение'}\n"
                f"**Срок:** 1 год\n"
                f"**Трафик:** 100 GB\n\n"
                f"**Конфигурация:**\n"
                f"```\n{config_data}\n```\n\n"
                f"Используйте эту конфигурацию в вашем VPN клиенте.",
                parse_mode='Markdown'
            )
            
            # Логируем действие
            self.db.log_action(user.id, 'create_free_connection', f'Создано бесплатное подключение {subscription_id}')
        else:
            await update.message.reply_text(
                f"❌ **Ошибка создания подключения**\n\n{config_data}",
                parse_mode='Markdown'
            )
    
    async def ban_user(self, update: Update, context: CallbackContext) -> None:
        """Бан пользователя"""
        user = update.effective_user
        
        if not self.db.is_moderator(user.id):
            await update.message.reply_text("❌ У вас нет прав для бана пользователей")
            return
        
        if context.args and len(context.args) >= 2:
            try:
                target_user_id = int(context.args[0])
                reason = ' '.join(context.args[1:])
                is_global = self.db.is_admin(user.id)  # Только админы могут банить глобально
                
                if is_global:
                    success, message = self.api_manager.ban_user_globally(target_user_id, user.id, reason)
                else:
                    # Модераторы банит только на текущем сервере
                    servers = self.db.get_servers(user.id)
                    if servers:
                        success, message = self.api_manager.ban_user_on_server(target_user_id, servers[0]['id'], user.id, reason)
                    else:
                        success, message = False, "Нет доступных серверов"
                
                if success:
                    await update.message.reply_text(
                        f"✅ **Пользователь забанен**\n\n"
                        f"**ID пользователя:** {target_user_id}\n"
                        f"**Причина:** {reason}\n"
                        f"**Тип бана:** {'Глобальный' if is_global else 'На сервере'}\n"
                        f"**Результат:** {message}",
                        parse_mode='Markdown'
                    )
                    
                    # Логируем действие
                    self.db.log_action(user.id, 'ban_user', f'Забанен пользователь {target_user_id}: {reason}')
                else:
                    await update.message.reply_text(f"❌ Ошибка бана: {message}")
                
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID пользователя")
        else:
            await update.message.reply_text(
                "📝 **Бан пользователя**\n\n"
                "Формат команды:\n"
                "`/ban USER_ID ПРИЧИНА`\n\n"
                "Пример:\n"
                "`/ban 123456789 Нарушение правил`",
                parse_mode='Markdown'
            )
    
    async def button_handler(self, update: Update, context: CallbackContext) -> None:
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        if data.startswith('tariff_'):
            tariff_id = int(data.split('_')[1])
            await self.process_tariff_purchase(query, tariff_id)
        
        elif data.startswith('admin_'):
            action = data.split('_')[1]
            await self.handle_admin_action(query, action)
        
        elif data.startswith('moderator_'):
            action = data.split('_')[1]
            await self.handle_moderator_action(query, action)
    
    async def handle_admin_action(self, query, action):
        """Обработка действий администратора"""
        user = query.from_user
        
        if not self.db.is_admin(user.id):
            await query.edit_message_text("❌ У вас нет прав администратора")
            return
        
        if action == 'servers':
            servers = self.db.get_servers(user.id)
            text = "🖥️ **Управление серверами**\n\n"
            
            for server in servers:
                status = "✅ Активен" if server['is_active'] else "❌ Неактивен"
                load = f"{server['current_users']}/{server['max_users']}"
                text += f"🔹 **{server['name']}** ({server['location']})\n"
                text += f"   📍 {server['url']}\n"
                text += f"   👤 Нагрузка: {load}\n"
                text += f"   🚦 Статус: {status}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔄 Синхронизировать все", callback_data="admin_sync_all")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif action == 'add_moderator':
            await query.edit_message_text(
                "📝 **Добавление модератора**\n\n"
                "Используйте команду:\n"
                "`/addmoderator USER_ID [USERNAME]`\n\n"
                "Пример:\n"
                "`/addmoderator 123456789 ИванИванов`\n\n"
                "Модератор получит ограниченные права управления системой.",
                parse_mode='Markdown'
            )
    
    async def handle_moderator_action(self, query, action):
        """Обработка действий модератора"""
        user = query.from_user
        
        if not self.db.is_moderator(user.id):
            await query.edit_message_text("❌ У вас нет прав модератора")
            return
        
        if action == 'servers':
            servers = self.db.get_servers(user.id)
            text = "📈 **Мониторинг серверов**\n\n"
            
            for server in servers:
                load_percent = (server['current_users'] / server['max_users']) * 100
                status_icon = "🟢" if load_percent < 80 else "🟡" if load_percent < 95 else "🔴"
                
                text += f"{status_icon} **{server['name']}**\n"
                text += f"   📍 {server['location']}\n"
                text += f"   👤 {server['current_users']}/{server['max_users']} ({load_percent:.1f}%)\n"
                text += f"   🕒 Последняя синхронизация: {server['last_sync'] or 'Никогда'}\n\n"
            
            await query.edit_message_text(text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработка текстовых сообщений"""
        text = update.message.text
        user = update.effective_user
        
        # Обработка обычных текстовых команд через кнопки
        if text == "💰 Тарифы":
            await self.show_tariffs(update, context)
        elif text == "📊 Мои подключения":
            await self.my_subscriptions(update, context)
        elif text == "👑 Админ панель":
            await self.admin_panel(update, context)
        elif text == "🛡️ Админ панель":
            await self.admin_panel(update, context)
        elif text == "🔧 Панель модератора":
            await self.moderator_panel(update, context)
        elif text == "🔄 Синхронизировать":
            await self.sync_servers(update, context)
        elif text == "📈 Статистика":
            await self.show_stats(update, context)
        elif text == "🎁 Бесплатное подключение":
            await self.create_free_connection(update, context)
        elif text == "ℹ️ Помощь":
            await self.help(update, context)
        else:
            await update.message.reply_text("❌ Неизвестная команда. Используйте /help для справки.")
    
    # Добавьте остальные методы (show_tariffs, my_subscriptions, add_server, list_servers, sync_servers, show_stats, help, balance)
    # которые были в предыдущей реализации, с учетом новой системы ролей
    
    def run(self):
        """Запуск бота"""
        logging.info("🚀 Запуск VPN Bot с системой ролей...")
        print("🤖 VPN Bot запускается...")
        
        try:
            self.application.run_polling()
        except Exception as e:
            logging.error(f"❌ Ошибка при запуске бота: {e}")
            raise