@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo === VPN Bot Panel - Windows setup ===

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERR] Python not found. Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info[0]*100+sys.version_info[1])" 2^>nul') do set PYVER=%%i
if !PYVER! lss 310 (
    echo [ERR] Python 3.10 or newer is required.
    pause
    exit /b 1
)

:: Create venv
if not exist venv\Scripts\python.exe (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERR] Failed to create venv. Make sure Python includes venv support.
        pause
        exit /b 1
    )
)

:: Install dependencies
echo [INFO] Installing dependencies from requirements.txt...
venv\Scripts\python.exe -m pip install --upgrade pip -q
venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERR] Dependency installation failed.
    pause
    exit /b 1
)

:: Create config.ini from example
if not exist config.ini (
    if exist config.ini.example (
        copy /y config.ini.example config.ini >nul
        echo [OK]   config.ini created from example. Edit it before running!
    ) else (
        echo [WARN] config.ini.example not found. Run: venv\Scripts\python.exe -c "from app.config import Config; Config().create_default_config()"
    )
)

:: Init database (runs migrations too)
venv\Scripts\python.exe -m app.manage init

echo.
echo === Setup complete! ===
echo Next steps:
echo   1. Edit config.ini: set [BOT] token and admin_telegram_id
echo   2. Create panel password:
echo        venv\Scripts\python.exe -m app.manage set-password ^<TG_ID^>
echo      ^(user must write /start to the bot first^)
echo   3. Run the app:
echo        venv\Scripts\python.exe run.py
echo.
pause
