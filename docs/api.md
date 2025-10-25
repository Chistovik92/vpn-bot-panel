# API документация

## API 3x-ui

Система использует API панели 3x-ui для управления пользователями.

### Основные методы

#### Получение списка inbound подключений

GET /panel/api/inbounds/list

#### Добавление клиента

POST /panel/api/inbounds/addClient

Тело запроса:
```json
{
  "id": inbound_id,
  "settings": "{\"clients\": [{\"id\": \"uuid\", \"email\": \"email\", ...}]}"
}
```
Удаление клиента
Удаление осуществляется через обновление inbound, удаляя клиента из списка.

## Внутреннее API
### Платежные вебхуки
#### YooMoney
```text
POST /webhook/yoomoney
```
#### CryptoBot
```text
POST /webhook/cryptobot
```
### Интеграция с Telegram
Бот использует python-telegram-bot v20.7 для взаимодействия с Telegram Bot API.

#### Основные команды
/start - начать работу

/help - помощь

/tariffs - тарифы

/balance - баланс

/admin - панель администратора

/moderator - панель модератора