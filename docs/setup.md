# Установка VPN Bot Panel

## Автоматическая установка (Linux)

Одна команда:

```bash
wget -O install.sh https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Установщик выполнит:

* установку системных пакетов (python3-venv, git);
* клонирование репозитория в `/opt/vpn-bot-panel`;
* создание venv и установку зависимостей;
* интерактивную настройку: токен бота, Telegram ID администратора,
  пароль веб-панели (`install.py`);
* создание и запуск единого systemd-сервиса `vpnbot.service`
  (бот + панель в одном процессе).

## Ручная установка

### Требования

* Python 3.10+
* Git
* Доступ к серверам 3x-ui

### Шаги

```bash
# 1. Системные пакеты (Ubuntu/Debian)
sudo apt update && sudo apt install -y python3-venv python3-pip git

# 2. Код
git clone https://github.com/Chistovik92/vpn-bot-panel.git /opt/vpn-bot-panel
cd /opt/vpn-bot-panel

# 3. Окружение и зависимости
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 4. Конфигурация
cp config.ini.example config.ini   # затем отредактируйте [BOT] token/admin_telegram_id

# 5. Интерактивная настройка + инициализация БД с миграциями
PYTHONPATH=. ./venv/bin/python install.py

# 6. Пароль веб-панели для администратора
PYTHONPATH=. ./venv/bin/python -m app.manage set-password <TELEGRAM_ID>

# 7. Запуск
./venv/bin/python run.py
```

## systemd-сервис

```ini
# /etc/systemd/system/vpnbot.service
[Unit]
Description=VPN Bot Panel (Telegram bot + web panel)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/vpn-bot-panel
ExecStart=/opt/vpn-bot-panel/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vpnbot
```

## Управление после установки

```bash
sudo ./Boot-main-ini                 # интерактивное меню
systemctl status vpnbot              # статус сервиса
journalctl -u vpnbot -f              # живые логи
sudo ./update.sh                     # обновление из main (+ миграции)
sudo ./uninstall.sh                  # полное удаление с бэкапом
```

## Windows

Запустите `install.bat` — он создаст окружение, поставит зависимости,
создаст config.ini из примера и инициализирует БД.
