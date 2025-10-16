# VPN Bot & Web Panel

Многоязычный Telegram бот для продажи VPN ключей с интеграцией YooMoney и веб-панелью управления.

## 🌟 Возможности

- 🤖 Telegram бот для продажи VPN ключей
- 💳 Поддержка оплаты через YooMoney
- 🌐 Многоязычный интерфейс (русский/английский)
- 📊 Веб-панель управления для администратора
- 🚀 Автоматическая установка и обновление
- 📈 Мониторинг панелей 3x-ui в реальном времени
- 🔔 Уведомления администратора о проблемах
- 💾 Автоматические бэкапы и восстановление
- 🔐 SSL сертификат на 10 лет
- 🔄 Обновление из GitHub через веб-панель

## 🛠 Требования

- Ubuntu 22.04 LTS или 24.04 LTS
- Python 3.8+
- Nginx
- Systemd

## 🚀 Быстрая установка

### Автоматическая установка с GitHub

```bash
# Скачать и запустить установщик
curl -L -o install.sh https://raw.githubusercontent.com/your_username/vpn-bot-panel/main/install.sh
chmod +x install.sh
sudo ./install.sh

**  ### Ручная установка**

bash
# Клонировать репозиторий
git clone https://github.com/your_username/vpn-bot-panel.git
cd vpn-bot-panel

# Запустить установку
chmod +x install.sh
sudo ./install.sh

** ## ⚙️ Настройка**

После установки настройте бота:

bash
sudo nano /opt/vpnbot/.env

Установите следующие переменные:

env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
YOOMONEY_RECEIVER=4100111234567890
YOOMONEY_TOKEN=your_yoomoney_token
📱 Использование
Веб-панель
URL: https://your_server_ip

Логин: admin

Пароль: сгенерированный при установке (смотрите вывод установщика)

Telegram бот
Начните с команды /start

Выберите тариф и способ оплаты

После оплаты VPN подключение активируется автоматически

Добавление панелей 3x-ui
bash
# Через скрипт
add_vpn_panel 'Название;URL;Логин;Пароль;Локация'

# Пример
add_vpn_panel 'Germany #1;https://panel1.com:8080;admin;password123;Germany'
🔄 Обновление
bash
# Автоматическое обновление
sudo /root/vpnbot_update.sh

# Или через веб-панель в разделе System
🛠 Управление службами
bash
# Статус служб
systemctl status vpnbot vpnbot-web

# Перезапуск
systemctl restart vpnbot vpnbot-web

# Логи
journalctl -u vpnbot -f
journalctl -u vpnbot-web -f
📊 Мониторинг
Автоматическая проверка состояния панелей каждые 5 минут

Уведомления в Telegram при проблемах

Мониторинг истекающих подписок

Статистика использования и доходов

🔒 Безопасность
Автоматическая настройка firewall

Защита веб-панели паролем

Регулярное обновление безопасности

Автоматические бэкапы

SSL шифрование

🆘 Поддержка
При проблемах проверьте:

Логи: journalctl -u vpnbot -f

Конфигурацию: /opt/vpnbot/.env

Статус служб: systemctl status vpnbot
