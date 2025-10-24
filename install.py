import os
import sys
import sqlite3
import subprocess
import importlib.util

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import Database
    from config import Config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Current directory:", os.getcwd())
    print("📁 Script directory:", os.path.dirname(os.path.abspath(__file__)))
    print("📁 Files in directory:", [f for f in os.listdir('.') if f.endswith('.py')])
    sys.exit(1)

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def create_config():
    """Create configuration file"""
    print("⚙️  Creating configuration file...")
    try:
        config = Config()
        config.create_config()
        print("✅ Configuration file created")
    except Exception as e:
        print(f"❌ Failed to create configuration file: {e}")
        sys.exit(1)

def init_database():
    """Initialize database"""
    print("🗃️ Initializing database...")
    try:
        db = Database()
        db.init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)

def main():
    """Main installation function"""
    print("🚀 Starting VPN Bot Panel installation...")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found")
        sys.exit(1)
    
    install_dependencies()
    create_config()
    init_database()
    
    print("\n🎉 Installation completed successfully!")
    print("📝 Next steps:")
    print("   1. Configure your settings in config.ini")
    print("   2. Run the bot with: python bot.py")

if __name__ == "__main__":
    main()