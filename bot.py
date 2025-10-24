#!/usr/bin/env python3
"""
VPN Bot Panel - Основной файл Telegram бота
"""

import os
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import Database
    from config import Config
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VPNBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.token = self.config.get_bot_token()
        
        if not self.token or self.token == 'YOUR_BOT_TOKEN_HERE':
            logger.error("❌ Токен бота не настроен. Установите его в config.ini")
            sys.exit(1)
            
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("balance", self.balance))
        self.application.add_handler(CommandHandler("services", self.services))
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.full_name)
        
        welcome_text = f"""
👋 Привет, {user.full_name}!

Добро пожаловать в VPN Bot Panel!

Доступные команды:
/start - Начать работу
/help - Помощь и инструкции
/balance - Проверить баланс
/services - Доступные услуги

Для получения помощи обращайтесь к администратору.
        """
        
        await update.message.reply_text(welcome_text)
        logger.info(f"Новый пользователь: {user.id} - {user.username}")
    
    async def help(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /help"""
        help_text = """
📖 Справка по VPN Bot Panel

Основные команды:
/start - Начать работу с ботом
/balance - Проверить текущий баланс
/services - Просмотреть доступные VPN услуги

💡 Как пользоваться:
1. Пополните баланс через админ-панель
2. Выберите подходящую услугу
3. Получите VPN конфигурацию

🆘 Поддержка:
Для получения помощи обращайтесь к администратору.
        """
        
        await update.message.reply_text(help_text)
    
    async def balance(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /balance"""
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data:
            balance = user_data['balance']
            await update.message.reply_text(f"💰 Ваш текущий баланс: {balance} ₽")
        else:
            await update.message.reply_text("❌ Ваш аккаунт не найден. Используйте /start")
    
    async def services(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /services"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name, description, price, duration_days FROM services WHERE is_active = 1')
                services = cursor.fetchall()
            
            if not services:
                await update.message.reply_text("❌ В настоящее время услуги недоступны")
                return
            
            services_text = "📋 Доступные VPN услуги:\n\n"
            for service in services:
                name, description, price, duration = service
                services_text += f"🔹 {name}\n"
                services_text += f"   📝 {description}\n"
                services_text += f"   💰 Цена: {price} ₽\n"
                services_text += f"   ⏱️ Срок: {duration} дней\n\n"
            
            services_text += "💡 Для покупки услуги обратитесь к администратору."
            
            await update.message.reply_text(services_text)
            
        except Exception as e:
            logger.error(f"Ошибка при получении услуг: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке услуг")
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск VPN Bot...")
        print("🤖 VPN Bot запускается...")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        try:
            self.application.run_polling()
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Запуск бота
    bot = VPNBot()
    bot.run()