import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import os
import sys

# Добавляем путь для импорта модулей
sys.path.append('/opt/vpnbot')

try:
    import config
    from database import init_db, get_db, User, Panel, Subscription, Payment
    from languages import get_bot_text
    from logger import setup_logging, log_user_action
    from monitoring import MonitoringService
except ImportError as e:
    print(f"Import error: {e}")
    print("Please check that all required files are in the same directory")
    exit(1)

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

class VPNBot:
    def __init__(self):
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            db = next(get_db())
            
            # Регистрируем пользователя если нужно
            db_user = db.query(User).filter(User.user_id == user.id).first()
            if not db_user:
                db_user = User(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language=config.DEFAULT_LANGUAGE
                )
                db.add(db_user)
                db.commit()
                log_user_action(user.id, 'register', f"New user registered: {user.username}")
            
            language = db_user.language
            
            keyboard = [
                [InlineKeyboardButton(get_bot_text(language, 'buy_vpn'), callback_data='buy_vpn')],
                [InlineKeyboardButton(get_bot_text(language, 'my_connections'), callback_data='my_connections')],
                [InlineKeyboardButton(get_bot_text(language, 'help'), callback_data='help')],
                [InlineKeyboardButton(get_bot_text(language, 'change_language'), callback_data='change_language')]
            ]
            
            if user.id in config.ADMIN_IDS:
                keyboard.append([InlineKeyboardButton(get_bot_text(language, 'admin_panel'), callback_data='admin_panel')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                get_bot_text(language, 'welcome', name=user.first_name),
                reply_markup=reply_markup
            )
            
            log_user_action(user.id, 'start', "User started bot")
            db.close()
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

    async def show_tariffs(self, query):
        """Показать доступные тарифы"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            db.close()
            
            keyboard = []
            for tariff_key, tariff in config.TARIFFS.items():
                tariff_name = tariff[f'name_{language}']
                keyboard.append([
                    InlineKeyboardButton(
                        f"{tariff_name} - {tariff['price']}₽",
                        callback_data=f'tariff_{tariff_key}'
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(get_bot_text(language, 'back'), callback_data='main_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            tariff_descriptions = []
            for tariff in config.TARIFFS.values():
                name = tariff[f'name_{language}']
                description = tariff[f'description_{language}']
                tariff_descriptions.append(f"• {name}: {tariff['price']}₽ - {description}")
            
            await query.edit_message_text(
                f"{get_bot_text(language, 'choose_tariff')}\n\n" + "\n".join(tariff_descriptions),
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error showing tariffs: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке тарифов.")

    async def handle_tariff_selection(self, query, context):
        """Обработка выбора тарифа"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            db.close()
            
            tariff_key = query.data.replace('tariff_', '')
            tariff = config.TARIFFS.get(tariff_key)
            
            if not tariff:
                await query.answer("Тариф не найден", show_alert=True)
                return
            
            context.user_data['selected_tariff'] = tariff_key
            
            keyboard = [
                [InlineKeyboardButton(get_bot_text(language, 'yoomoney_pay'), callback_data='payment_yoomoney')],
                [InlineKeyboardButton(get_bot_text(language, 'back'), callback_data='buy_vpn')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            tariff_name = tariff[f'name_{language}']
            
            await query.edit_message_text(
                get_bot_text(language, 'tariff_info', 
                            name=tariff_name, 
                            price=tariff['price'], 
                            days=tariff['days']) +
                get_bot_text(language, 'choose_payment'),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling tariff selection: {e}")
            await query.edit_message_text("❌ Ошибка при выборе тарифа.")

    async def handle_payment_selection(self, query, context):
        """Обработка выбора способа оплаты"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            
            payment_method = query.data.replace('payment_', '')
            tariff_key = context.user_data.get('selected_tariff')
            
            if not tariff_key:
                await query.answer("Сначала выберите тариф", show_alert=True)
                db.close()
                return
            
            tariff = config.TARIFFS[tariff_key]
            
            if payment_method == 'yoomoney':
                # В реальной реализации здесь будет создание платежа YooMoney
                # Пока демонстрационная реализация
                from yoomoney import Quickpay
                
                label = f"{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                quickpay = Quickpay(
                    receiver=config.YOOMONEY_RECEIVER,
                    quickpay_form="shop",
                    targets=f"VPN доступ - {tariff[f'name_{language}']}",
                    paymentType="SB",
                    sum=tariff['price'],
                    label=label
                )
                
                # Сохраняем информацию о платеже
                subscription = Subscription(
                    user_id=user.id,
                    email=f"{user.username or 'user'}_{user.id}",
                    telegram_id=str(user.id),
                    tariff=tariff_key,
                    expires_at=datetime.utcnow() + timedelta(days=tariff['days'])
                )
                db.add(subscription)
                db.commit()
                
                payment = Payment(
                    subscription_id=subscription.id,
                    amount=tariff['price'],
                    payment_method='yoomoney',
                    payment_id=label,
                    status='pending'
                )
                db.add(payment)
                db.commit()
                db.close()
                
                context.user_data['pending_payment'] = label
                
                keyboard = [
                    [InlineKeyboardButton(get_bot_text(language, 'check_payment'), callback_data='check_payment')],
                    [InlineKeyboardButton(get_bot_text(language, 'back'), callback_data='buy_vpn')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    get_bot_text(language, 'payment_instructions', url=quickpay.redirected_url),
                    reply_markup=reply_markup
                )
                
                log_user_action(user.id, 'payment_created', f"Payment created for {tariff_key}")
                
            else:
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен.")
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling payment selection: {e}")
            await query.edit_message_text("❌ Ошибка при создании платежа.")

    async def check_payment(self, query, context):
        """Проверка статуса платежа"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            
            payment_id = context.user_data.get('pending_payment')
            
            if not payment_id:
                await query.answer("Нет активных платежей", show_alert=True)
                db.close()
                return
            
            # В реальной реализации здесь проверка статуса платежа YooMoney
            # Пока демонстрационная логика
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if payment and payment.status == 'pending':
                # Имитируем успешную оплату
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()
                
                subscription = payment.subscription
                subscription.is_active = True
                subscription.activated_at = datetime.utcnow()
                
                # Находим доступную панель
                panel = db.query(Panel).filter(Panel.is_active == True).first()
                if panel:
                    subscription.panel_id = panel.id
                
                db.commit()
                
                tariff = config.TARIFFS[subscription.tariff]
                tariff_name = tariff[f'name_{language}']
                expires_date = subscription.expires_at.strftime('%d.%m.%Y')
                
                await query.edit_message_text(
                    get_bot_text(language, 'payment_success', 
                                email=subscription.email,
                                tariff=tariff_name,
                                expires=expires_date),
                    parse_mode='Markdown'
                )
                
                log_user_action(user.id, 'subscription_activated', f"Subscription activated: {subscription.email}")
            else:
                await query.answer(get_bot_text(language, 'payment_not_found'), show_alert=True)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error checking payment: {e}")
            await query.answer("❌ Ошибка при проверке платежа", show_alert=True)

    async def show_user_connections(self, query):
        """Показать подключения пользователя"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            
            subscriptions = db.query(Subscription).filter(
                Subscription.user_id == user.id
            ).order_by(Subscription.created_at.desc()).all()
            
            if not subscriptions:
                await query.edit_message_text(get_bot_text(language, 'no_connections'))
                db.close()
                return
            
            text = get_bot_text(language, 'user_connections')
            for sub in subscriptions:
                status = get_bot_text(language, 'connection_active') if sub.is_active else get_bot_text(language, 'connection_inactive')
                text += f"• {sub.email} - {status}\n"
                if sub.is_active and sub.expires_at:
                    expires_date = sub.expires_at.strftime('%d.%m.%Y')
                    text += f"  {get_bot_text(language, 'valid_until', date=expires_date)}\n"
                text += "\n"
            
            await query.edit_message_text(text, parse_mode='Markdown')
            db.close()
            log_user_action(user.id, 'view_connections', "User viewed connections")
            
        except Exception as e:
            logger.error(f"Error showing user connections: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке подключений.")

    async def show_help(self, query):
        """Показать справку"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            db.close()
            
            await query.edit_message_text(get_bot_text(language, 'help_text'), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing help: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке справки.")

    async def change_language(self, query):
        """Смена языка"""
        try:
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            
            if not db_user:
                await query.answer("Пользователь не найден", show_alert=True)
                return
            
            current_language = db_user.language
            new_language = 'en' if current_language == 'ru' else 'ru'
            
            db_user.language = new_language
            db.commit()
            db.close()
            
            keyboard = [
                [InlineKeyboardButton(get_bot_text(new_language, 'buy_vpn'), callback_data='buy_vpn')],
                [InlineKeyboardButton(get_bot_text(new_language, 'my_connections'), callback_data='my_connections')],
                [InlineKeyboardButton(get_bot_text(new_language, 'help'), callback_data='help')],
                [InlineKeyboardButton(get_bot_text(new_language, 'change_language'), callback_data='change_language')]
            ]
            
            if user.id in config.ADMIN_IDS:
                keyboard.append([InlineKeyboardButton(get_bot_text(new_language, 'admin_panel'), callback_data='admin_panel')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                get_bot_text(new_language, 'welcome', name=user.first_name),
                reply_markup=reply_markup
            )
            
            log_user_action(user.id, 'language_change', f"Language changed to {new_language}")
            
        except Exception as e:
            logger.error(f"Error changing language: {e}")
            await query.answer("❌ Ошибка при смене языка", show_alert=True)

    async def show_admin_panel(self, query):
        """Показать админ панель"""
        try:
            if query.from_user.id not in config.ADMIN_IDS:
                await query.answer("Доступ запрещен!", show_alert=True)
                return
            
            user = query.from_user
            db = next(get_db())
            db_user = db.query(User).filter(User.user_id == user.id).first()
            language = db_user.language if db_user else config.DEFAULT_LANGUAGE
            db.close()
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
                [InlineKeyboardButton("👥 Пользователи", callback_data='admin_users')],
                [InlineKeyboardButton("🖥️ Панели", callback_data='admin_panels')],
                [InlineKeyboardButton(get_bot_text(language, 'back'), callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👑 **Админ панель**\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing admin panel: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке админ панели.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        try:
            query = update.callback_query
            await query.answer()
            
            handlers = {
                'main_menu': self.start,
                'buy_vpn': self.show_tariffs,
                'my_connections': self.show_user_connections,
                'help': self.show_help,
                'admin_panel': self.show_admin_panel,
                'change_language': self.change_language,
            }
            
            if query.data.startswith('tariff_'):
                await self.handle_tariff_selection(query, context)
            elif query.data.startswith('payment_'):
                await self.handle_payment_selection(query, context)
            elif query.data == 'check_payment':
                await self.check_payment(query, context)
            elif query.data in handlers:
                if query.data == 'main_menu':
                    await handlers[query.data](update, context)
                else:
                    await handlers[query.data](query)
            else:
                await query.edit_message_text("Неизвестная команда")
                
        except Exception as e:
            logger.error(f"Error in button handler: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        try:
            if update and update.effective_user:
                for admin_id in config.ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"🚨 **Bot Error**\n\n"
                            f"Error: {str(context.error)}\n"
                            f"User: {update.effective_user.id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send error alert: {str(e)}")
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def run(self):
        """Запуск бота"""
        try:
            if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
                print("❌ Please set BOT_TOKEN in config.py or environment variables")
                return
            
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            
            # Обработчики команд
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            
            # Обработчик ошибок
            self.application.add_error_handler(self.error_handler)
            
            # Запуск мониторинга
            monitoring = MonitoringService(config.BOT_TOKEN, config.ADMIN_IDS)
            asyncio.get_event_loop().create_task(monitoring.start_monitoring())
            
            logger.info("Bot starting...")
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            print(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    # Инициализация базы данных
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        exit(1)
    
    # Запуск бота
    bot = VPNBot()
    bot.run()
