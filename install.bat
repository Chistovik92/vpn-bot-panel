@echo off
setlocal enabledelayedexpansion

echo 🚀 Запуск установки VPN Bot Panel для Windows...

:: Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не установлен. Установите Python 3.8 или выше.
    echo 📥 Скачайте с: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Проверка версии Python
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set PYTHON_MINOR=%%i
if !PYTHON_MINOR! lss 8 (
    echo ❌ Требуется Python 3.8 или выше. Текущая версия: 3.!PYTHON_MINOR!
    pause
    exit /b 1
)

echo ✅ Python 3.!PYTHON_MINOR! найден

:: Проверка Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git не установлен. Установите Git сначала.
    echo 📥 Скачайте с: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Настройка репозитория
if exist "vpn-bot-panel" (
    echo ℹ️ Директория проекта уже существует, обновление...
    cd vpn-bot-panel
    git pull origin main
) else (
    echo ℹ️ Клонирование репозитория...
    git clone https://github.com/Chistovik92/vpn-bot-panel.git
    cd vpn-bot-panel
)

echo ✅ Настройка репозитория завершена

:: Проверка необходимых файлов
if not exist "install.py" (
    echo ❌ install.py не найден
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ❌ requirements.txt не найден
    pause
    exit /b 1
)

:: Создание виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

:: Активация виртуального окружения
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

:: Установка зависимостей
echo 📦 Установка зависимостей...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Запуск установки
echo 🚀 Запуск установки...
set PYTHONPATH=%CD%
python install.py

:: Создание директорий
mkdir data 2>nul
mkdir data\vpn_configs 2>nul
mkdir data\backups 2>nul
mkdir logs 2>nul

echo.
echo 🎉 Установка завершена успешно!
echo.
echo 📝 Следующие шаги:
echo   1. Настройте параметры в config.ini
echo   2. Запустите бота с помощью: python bot.py
echo   3. Для управления используйте Boot-main-ini (только Linux)
echo.
echo ⚠️  Примечание: Главное меню управления доступно только на Linux
echo.

pause