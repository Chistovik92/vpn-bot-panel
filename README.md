# 🚀 VPN Bot Panel

Профессиональная система управления VPN через Telegram бота с поддержкой серверов 3x-ui, многоуровневой системой ролей и интеграцией платежей.

## ✨ Особенности

### 🔐 Многоуровневая система ролей
- **Супер администратор** - полный контроль системы
- **Администратор** - управление серверами, тарифами, пользователями
- **Модератор** - мониторинг, реклама, ограниченное управление
- **Пользователь** - покупка тарифов, управление подключениями

### 💰 Поддержка платежных систем
- YooMoney (банковские карты)
- CryptoBot (криптовалюты)
- Легкое добавление новых провайдеров

### 🛡️ Безопасность предприятия
- Защищенные права доступа (только root)
- Шифрование конфиденциальных данных
- Автоматические бэкапы
- Система банов и модерации

### 🎛️ Управление серверами 3x-ui
- Автоматическая синхронизация inbound подключений
- Мониторинг нагрузки в реальном времени
- Автоматический разбан администраторов
- Оптимальное распределение пользователей

## 🚀 Быстрый старт

### Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/yourusername/vpn-bot-panel.git
cd vpn-bot-panel

# Запустите установку
sudo ./scripts/install.sh
```

Следуйте инструкциям установщика для настройки:

Токен Telegram бота

Супер администратора

Платежных систем

Безопасных прав доступа

### Ручная установка
```bash
# Установите зависимости
sudo apt update
sudo apt install python3-venv python3-pip git sqlite3

# Настройте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите Python зависимости
pip install -r requirements.txt

# Настройте конфигурацию
cp config.ini.example config.ini
# Отредактируйте config.ini

# Инициализируйте базу данных
python3 -c "from app.database import Database; db = Database(); db.init_db()"

# Запустите бота
python3 run.py
```

## 📖 Документация
### Команды бота
#### Для пользователей:
/start - начать работу с ботом

/tariffs - просмотр и покупка тарифов

/mysubscriptions - управление подключениями

/balance - проверка баланса

#### Для модераторов:
/moderator - панель модератора

/free - создать бесплатное подключение

/stats - статистика серверов

#### Для администраторов:
/admin - панель администратора

/addserver - добавить сервер 3x-ui

/addmoderator - назначить модератора

/ban - забанить пользователя

/unban - разбанить пользователя

/sync - синхронизировать серверы

#### Системные команды
```bash
# Запуск через systemd
sudo systemctl start vpn-bot-panel
sudo systemctl stop vpn-bot-panel
sudo systemctl restart vpn-bot-panel
sudo systemctl status vpn-bot-panel

# Обновление системы
sudo ./scripts/update.sh

# Ручной бэкап
sudo ./scripts/backup.sh
```

### ⚙️ Конфигурация
Основные настройки в config.ini:
```ini
[DATABASE]
path = data/vpn_bot.db              # Путь к базе данных

[BOT]
token = YOUR_BOT_TOKEN_HERE         # Токен Telegram бота
admin_telegram_id = 123456789       # ID супер администратора

[WEB]
port = 5000                         # Порт веб-панели
debug = False                       # Режим отладки

[PAYMENTS]
yoomoney_shop_id = YOUR_SHOP_ID     # ID магазина YooMoney
yoomoney_secret_key = YOUR_KEY      # Секретный ключ
```

### 🏗️ Архитектура
```text
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │◄──►│   VPN Bot Panel  │◄──►│   3x-ui Panels  │
│                 │    │                  │    │                 │
│ • User Commands │    │ • Role Management│    │ • API Integration│
│ • Payments      │    │ • Payment System │    │ • User Management│
│ • Notifications │    │ • Server Mgmt    │    │ • Config Gen     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│   Payment       │    │   Database       │
│   Processors    │    │                  │
│                 │    │ • Users & Roles  │
│ • YooMoney      │    │ • Servers & Inb. │
│ • CryptoBot     │    │ • Subscriptions  │
└─────────────────┘    └──────────────────┘
```

### 🔧 Технические требования
Python: 3.8+

ОС: Ubuntu 18.04+, Debian 9+, CentOS 7+

Память: 512MB RAM минимум

Хранилище: 1GB свободного места

Доступ к интернету: для API платежных систем

### 🤝 Участие в разработке
Мы приветствуем вклад в развитие проекта!

Форкните репозиторий

Создайте ветку для фичи (git checkout -b feature/AmazingFeature)

Закоммитьте изменения (git commit -m 'Add some AmazingFeature')

Запушьте ветку (git push origin feature/AmazingFeature)

Откройте Pull Request

## 📄 Лицензия
Этот проект распространяется под лицензией MIT. Подробнее см. в файле LICENSE.

### 🆘 Поддержка
Документация

Issues

Discussions

⭐ Если вам понравился этот проект, поставьте звезду на GitHub!