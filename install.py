import os
import sys
import sqlite3
import subprocess
import importlib.util
import hashlib
import secrets
import string
from getpass import getpass

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
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("🔄 Trying alternative installation method...")
        try:
            # Попробуем установить пакеты по одному
            packages = [
                "python-telegram-bot==20.7",
                "yookassa==1.0.0", 
                "aiohttp==3.9.1",
                "cryptography==41.0.7"
            ]
            for package in packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print("✅ Dependencies installed (alternative method)")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies with alternative method")
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

def generate_password(length=12):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def setup_admin_account():
    """Setup admin account interactively"""
    print("\n👑 Setting up administrator account...")
    
    db = Database()
    
    while True:
        print("\nChoose an option:")
        print("1. Enter admin credentials manually")
        print("2. Generate credentials automatically")
        print("3. Skip admin setup (configure later)")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            return setup_manual_admin(db)
        elif choice == '2':
            return setup_auto_admin(db)
        elif choice == '3':
            print("⚠️  Admin setup skipped. You can configure it later in the admin panel.")
            return True
        else:
            print("❌ Invalid choice. Please try again.")

def setup_manual_admin(db):
    """Setup admin with manual credentials"""
    print("\n📝 Manual admin setup:")
    
    # Telegram ID
    while True:
        telegram_id = input("Enter admin Telegram ID: ").strip()
        if telegram_id.isdigit():
            telegram_id = int(telegram_id)
            break
        else:
            print("❌ Telegram ID must be a number. Please try again.")
    
    # Username
    username = input("Enter admin username: ").strip()
    if not username:
        username = f"admin_{telegram_id}"
    
    # Password
    while True:
        password = getpass("Enter admin password: ").strip()
        if len(password) >= 8:
            confirm = getpass("Confirm password: ").strip()
            if password == confirm:
                break
            else:
                print("❌ Passwords don't match. Please try again.")
        else:
            print("❌ Password must be at least 8 characters long.")
    
    # Full name
    full_name = input("Enter admin full name (optional): ").strip()
    if not full_name:
        full_name = "Administrator"
    
    return save_admin_to_db(db, telegram_id, username, password, full_name)

def setup_auto_admin(db):
    """Setup admin with auto-generated credentials"""
    print("\n🎲 Auto-generating admin credentials...")
    
    # Telegram ID
    while True:
        telegram_id = input("Enter admin Telegram ID: ").strip()
        if telegram_id.isdigit():
            telegram_id = int(telegram_id)
            break
        else:
            print("❌ Telegram ID must be a number. Please try again.")
    
    # Generate credentials
    username = f"admin_{telegram_id}"
    password = generate_password()
    full_name = "Administrator"
    
    print(f"\n✅ Auto-generated credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   Full name: {full_name}")
    print(f"   Telegram ID: {telegram_id}")
    
    print("\n💾 Saving credentials...")
    return save_admin_to_db(db, telegram_id, username, password, full_name)

def save_admin_to_db(db, telegram_id, username, password, full_name):
    """Save admin account to database"""
    try:
        password_hash = hash_password(password)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if admin already exists
            cursor.execute('SELECT * FROM admins WHERE telegram_id = ? OR username = ?', 
                         (telegram_id, username))
            existing_admin = cursor.fetchone()
            
            if existing_admin:
                # Update existing admin
                cursor.execute('''
                    UPDATE admins 
                    SET username = ?, password_hash = ?, full_name = ?, is_active = TRUE
                    WHERE telegram_id = ?
                ''', (username, password_hash, full_name, telegram_id))
                action = "updated"
            else:
                # Insert new admin
                cursor.execute('''
                    INSERT INTO admins (telegram_id, username, password_hash, full_name, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (telegram_id, username, password_hash, full_name, True))
                action = "created"
            
            conn.commit()
        
        print(f"✅ Admin account {action} successfully!")
        print(f"   Username: {username}")
        print(f"   Telegram ID: {telegram_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save admin account: {e}")
        return False

def setup_bot_config():
    """Setup bot configuration interactively"""
    print("\n🤖 Bot configuration setup:")
    
    config = Config()
    
    # Load existing config or create new
    if os.path.exists(config.config_file):
        config.load_config()
    
    # Bot token
    print("\nTelegram Bot Token:")
    print("1. Enter token now")
    print("2. Skip and configure later in config.ini")
    
    choice = input("Enter your choice (1-2): ").strip()
    
    if choice == '1':
        token = input("Enter your bot token: ").strip()
        if token:
            config.config['BOT']['token'] = token
            print("✅ Bot token saved")
    
    # Admin ID for bot notifications
    print("\nAdmin Telegram ID for bot notifications:")
    print("1. Enter admin ID now") 
    print("2. Skip and configure later")
    
    choice = input("Enter your choice (1-2): ").strip()
    
    if choice == '1':
        admin_id = input("Enter admin Telegram ID: ").strip()
        if admin_id and admin_id.isdigit():
            config.config['BOT']['admin_id'] = admin_id
            print("✅ Admin ID saved")
    
    # Save config
    try:
        with open(config.config_file, 'w', encoding='utf-8') as configfile:
            config.config.write(configfile)
        print("✅ Configuration saved to config.ini")
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")

def display_final_instructions():
    """Display final instructions after installation"""
    print("\n" + "="*50)
    print("🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
    print("="*50)
    
    print("\n📝 NEXT STEPS:")
    print("1. Edit config.ini to complete your configuration:")
    print("   - Set your bot token in the [BOT] section")
    print("   - Configure payment methods in [PAYMENTS] section")
    print("   - Adjust VPN settings in [VPN] section")
    
    print("\n2. Start the bot:")
    print("   python bot.py")
    
    print("\n3. Access the admin panel:")
    print("   - Use the credentials you created during installation")
    print("   - Or run this installer again to create new admin accounts")
    
    print("\n🔧 For support and updates, visit:")
    print("   https://github.com/Chistovik92/vpn-bot-panel")
    print("\n")

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
    setup_admin_account()
    setup_bot_config()
    display_final_instructions()

if __name__ == "__main__":
    main()