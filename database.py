import os
import sys
import sqlite3
from contextlib import contextmanager

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import Config
except ImportError as e:
    print(f"❌ Error importing config: {e}")
    # Попытка прямого импорта
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", "config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    Config = config_module.Config

class Database:
    def __init__(self):
        self.config = Config()
        self.db_path = self.config.get_database_path()
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    balance REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # VPN configurations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vpn_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    config_name TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Payments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Services table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    duration_days INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    expiry_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (service_id) REFERENCES services (id)
                )
            ''')
            
            # Insert default services if they don't exist
            default_services = [
                ('VPN Basic - 1 Month', 'Basic VPN service for 1 month', 5.0, 30),
                ('VPN Standard - 3 Months', 'Standard VPN service for 3 months', 12.0, 90),
                ('VPN Premium - 6 Months', 'Premium VPN service for 6 months', 20.0, 180),
                ('VPN Ultimate - 1 Year', 'Ultimate VPN service for 1 year', 35.0, 365)
            ]
            
            for service in default_services:
                cursor.execute('''
                    INSERT OR IGNORE INTO services (name, description, price, duration_days)
                    VALUES (?, ?, ?, ?)
                ''', service)
            
            print(f"✅ Database initialized at: {self.db_path}")
    
    def add_user(self, user_id, username, full_name):
        """Add a new user to the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, full_name))
    
    def get_user(self, user_id):
        """Get user by user_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    
    def update_balance(self, user_id, amount):
        """Update user balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            ''', (amount, user_id))
    
    def add_vpn_config(self, user_id, config_name, config_data):
        """Add VPN configuration for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vpn_configs (user_id, config_name, config_data)
                VALUES (?, ?, ?)
            ''', (user_id, config_name, config_data))

# Test function for debugging
def test_database():
    """Test database connection and initialization"""
    try:
        db = Database()
        db.init_db()
        print("✅ Database test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()