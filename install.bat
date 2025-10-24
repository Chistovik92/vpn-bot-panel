@echo off
setlocal enabledelayedexpansion

echo 🚀 Starting VPN Bot Panel installation...

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Check Python version
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set PYTHON_MINOR=%%i
if !PYTHON_MINOR! lss 8 (
    echo ❌ Python 3.8 or higher is required. Current version: 3.!PYTHON_MINOR!
    pause
    exit /b 1
)

echo ✅ Python 3.!PYTHON_MINOR! found

:: Check required files
if not exist "install.py" (
    echo ❌ install.py not found
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ❌ requirements.txt not found
    pause
    exit /b 1
)

:: Create virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo 📦 Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Run installation
echo 🚀 Running installation...
set PYTHONPATH=%CD%
python install.py

echo.
echo 🎉 Installation completed successfully!
echo.
echo 📝 Next steps:
echo   1. Configure your settings in config.ini
echo   2. Set your bot token in config.ini
echo   3. Run the bot with: python bot.py
echo.

pause