# Конфигурация VPN Bot Panel

## Файл config.ini

Все настройки системы хранятся в `config.ini` (в корне проекта).
Порядок поиска: переменная окружения `VPN_BOT_CONFIG` → текущий каталог → корень проекта.

### Секция [DATABASE]

| Параметр | Значение по умолчанию | Описание |
|--------------|----------------------|----------|
| path | data/vpn_bot.db | Путь к базе SQLite (относительные пути — от корня проекта) |
| backup_path | data/backups/ | Директория для бэкапов |
| backup_retention_days | 30 | Сколько дней хранить бэкапы |

### Секция [BOT]

| Параметр | Значение по умолчанию | Описание |
|-------------------|--------------------------|----------|
| token | YOUR_BOT_TOKEN_HERE | Токен Telegram бота от @BotFather |
| admin_telegram_id | 123456789 | Telegram ID супер-администратора. Пользователь с этим ID получает роль `super_admin` при первом `/start` |

### Секция [WEB]

| Параметр | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| secret_key | Генерируется автоматически | Ключ подписи cookie-сессий |
| host | 127.0.0.1 | Хост веб-панели |
| port | 8080 | Порт веб-панели |
| debug | False | Режим отладки (не включать в production) |

### Секция [PAYMENTS]

| Параметр | По умолчанию | Описание |
|------------------------------|--------------------------|----------|
| yoomoney_receiver | YOUR_YOOMONEY_WALLET | Номер кошелька YooMoney для приёма платежей (Quickpay) |
| yoomoney_token | YOUR_YOOMONEY_TOKEN | OAuth-токен приложения YooMoney с правом operation-history (для проверки оплат) |
| yoomoney_notification_secret | (пусто) | Секрет HTTP-уведомлений YooMoney; включает мгновенную активацию через POST /webhook/yoomoney |
| cryptobot_token | (пусто) | Токен CryptoBot (опционально) |

### Секция [SECURITY]

| Параметр | По умолчанию | Описание |
|---------------------------|--------------|----------|
| max_login_attempts | 5 | Неудачных попыток входа до блокировки |
| lockout_duration_minutes | 30 | Длительность блокировки IP+ID после лимита попыток |
| session_timeout_minutes | 60 | Время жизни сессии веб-панели |
| password_min_length | 8 | Минимальная длина пароля (`app.manage set-password`) |
| auto_unban_interval_hours | 6 | Интервал авто-разбана модераторов/админов на серверах |

### Секция [LOGGING]

| Параметр | По умолчанию | Описание |
|--------------|--------------------|----------|
| level | INFO | Уровень логирования |
| file | logs/vpn_bot.log | Файл лога |
| max_size_mb | 10 | Ротация: максимальный размер файла |
| backup_count | 5 | Ротация: число старых файлов |

## Управление через CLI

```bash
python -m app.manage check                      # статус конфигурации и БД
python -m app.manage init                       # инициализация БД
python -m app.manage set-password <TG_ID>       # пароль для входа в панель
python -m app.manage set-role <TG_ID> admin     # user|moderator|admin|super_admin
```

## Миграции

При запуске база предыдущих версий автоматически приводится к текущей схеме:
недостающие колонки добавляются через ALTER TABLE, таблица subscriptions
пересоздаётся с сохранением данных. Старые таблицы первой версии
(services, vpn_configs, orders, admins) не удаляются.
