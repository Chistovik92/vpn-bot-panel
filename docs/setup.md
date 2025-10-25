# Установка VPN Bot Panel

## Автоматическая установка

Для автоматической установки выполните:

```bash
sudo ./scripts/install.sh
```

### Скрипт установки выполнит:

* Установку системных зависимостей
* Настройку виртуального окружения Python
* Установку Python зависимостей
* Инициализацию базы данных
* Настройку супер администратора
* Настройку платежных систем
* Создание systemd сервиса
* Настройку автоматических бэкапов

## Ручная установка
### Требования
* Python 3.8+
* SQLite3
* Доступ к серверу 3x-ui
### Шаги
1. Установите системные пакеты
Для Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3-venv python3-pip git sqlite3
```
2. Клонируйте репозиторий
```bash
git clone https://github.com/yourusername/vpn-bot-panel.git
cd vpn-bot-panel
```
3. Настройте виртуальное окружение
```bash
python3 -m venv venv
source venv/bin/activate
```
4. Установите зависимости
```bash
pip install -r requirements.txt
```
5. Настройте конфигурацию
```bash
cp config.ini.example config.ini
# Отредактируйте config.ini
```
6. Инициализируйте базу данных
```bash
python3 -c "from app.database import Database; db = Database(); db.init_db()"
```
7. Запустите бота
```bash
python3 run.py
```
### Настройка сервиса
Для запуска в фоновом режиме используйте systemd:
```bash
sudo systemctl start vpn-bot-panel
sudo systemctl enable vpn-bot-panel
```
### Обновление
Для обновления выполните:
```bash
sudo ./scripts/update.sh
```
