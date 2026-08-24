# Архитектура VPN Bot Panel

## Обзор

Система состоит из трёх компонентов, работающих с общей SQLite-базой:

1. **Telegram-бот** (`app/bot.py`) — витрина для пользователей: покупка
   тарифов, выдача конфигов, личные подписки; команды модерации.
2. **Веб-панель** (`app/web.py`) — Flask-приложение с ролевым доступом:
   статистика, управление серверами/тарифами, аудит.
3. **CLI** (`app/manage.py`) — администрирование: пароли, роли,
   проверка состояния.

Точка входа `run.py` запускает панель в фоновом потоке и бота в главном.
Отдельно можно запускать `bot.py` или `web_panel.py`.

## Структура пакета app/

| Модуль | Назначение |
|------------------|------------|
| `config.py` | Единая работа с config.ini (миграция старых ключей) |
| `database.py` | Схема SQLite, миграции, все запросы. Роли: user/moderator/admin/super_admin |
| `xui_api.py` | Клиент 3x-ui (cookie-логин, inbounds, клиенты, генерация vless/vmess/trojan ссылок), менеджер серверов и подписок |
| `payment.py` | Процессоры YooMoney/CryptoBot + PaymentManager (создание счёта, проверка, однократная активация) |
| `web.py` | Веб-панель: CSRF, rate limit логина, аудит |
| `bot.py` | Обработчики Telegram, JobQueue очистки истёкших подписок |
| `languages.py` | Словарь текстов интерфейса |

Файлы в корне проекта (`bot.py`, `database.py`, `config.py`, `payment.py`,
`xui_api.py`, `admin_panel.py`, `web_panel.py`) — тонкие обёртки обратной
совместимости над `app/*`. Новой код должен импортировать только `app.*`.

## Поток покупки

```
/tariffs -> выбор тарифа -> PaymentManager.create_payment()
   -> запись в payments (status=pending) + ссылка Quickpay
Пользователь оплачивает ->
   а) нажимает "Проверить оплату" -> check_payment через API YooMoney
   б) приходит POST /webhook/yoomoney (sha1-подпись)
-> activate_payment(): создание клиента на 3x-ui + запись в subscriptions,
   payments.status=completed (идемпотентно)
```

## Безопасность

- Пароли: PBKDF2-HMAC-SHA256, 200 000 итераций, случайная соль.
- Панель: вход по Telegram ID + пароль; блокировка после N неудач;
  CSRF-токены на всех POST; защита от open redirect;
  security-заголовки; аудит действий в audit_log/action_logs.
- БД: foreign_keys=ON, WAL; права 0600 на файлы (где поддерживается ФС).
- Никаких демо-аккаунтов: супер-админ создаётся из `admin_telegram_id`.

## Тесты

```bash
pytest -q          # 24 теста: БД, миграции, веб-безопасность, платежи
```

CI (GitHub Actions `.github/workflows/ci.yml`): compileall + pytest
на Python 3.10–3.13.
