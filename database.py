import os
import sys
import sqlite3
import hashlib
import secrets
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
        self._create_secure_database()
        
    def _create_secure_database(self):
        """Create database with secure settings"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True, mode=0o755)
        
        # Set secure permissions for database directory
        db_dir = os.path.dirname(self.db_path)
        if os.path.exists(db_dir):
            os.chmod(db_dir, 0o755)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with security features"""
        conn = sqlite3.connect(self.db_path)
        
        # Enable foreign keys and secure settings
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA secure_delete = ON")
        conn.execute("PRAGMA auto_vacuum = FULL")
        
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
        """Initialize database tables with security features"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Admins table (for admin panel access)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'admin',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                )
            ''')
            
            # Users table (for bot users)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    balance REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_activity TIMESTAMP
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
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Payments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    status TEXT DEFAULT 'pending',
                    transaction_id TEXT UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
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
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE CASCADE
                )
            ''')
            
            # Audit log table for security
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT NOT NULL,
                    description TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admins (id) ON DELETE SET NULL
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
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_expiry ON orders(expiry_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)')
            
            print(f"✅ Database initialized at: {self.db_path}")
            
            # Set secure permissions for database file
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, 0o600)
                print("✅ Secure permissions set for database file")
    
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
    
    def add_vpn_config(self, user_id, config_name, config_data, expires_days=30):
        """Add VPN configuration for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vpn_configs (user_id, config_name, config_data, expires_at)
                VALUES (?, ?, ?, datetime('now', ?))
            ''', (user_id, config_name, config_data, f'+{expires_days} days'))

    # Admin methods
    def get_admin_by_username(self, username):
        """Get admin by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM admins 
                WHERE username = ? AND is_active = TRUE 
                AND (locked_until IS NULL OR locked_until < datetime('now'))
            ''', (username,))
            return cursor.fetchone()
    
    def get_admin_by_telegram_id(self, telegram_id):
        """Get admin by telegram_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM admins 
                WHERE telegram_id = ? AND is_active = TRUE
                AND (locked_until IS NULL OR locked_until < datetime('now'))
            ''', (telegram_id,))
            return cursor.fetchone()
    
    def update_admin_last_login(self, admin_id, ip_address=None, user_agent=None):
        """Update admin last login timestamp and reset login attempts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE admins 
                SET last_login = CURRENT_TIMESTAMP, login_attempts = 0, locked_until = NULL
                WHERE id = ?
            ''', (admin_id,))
            
            # Log the login
            if ip_address:
                cursor.execute('''
                    INSERT INTO audit_log (admin_id, action, description, ip_address, user_agent)
                    VALUES (?, 'login', 'Admin logged in', ?, ?)
                ''', (admin_id, ip_address, user_agent))
    
    def increment_login_attempts(self, admin_id):
        """Increment failed login attempts and lock if necessary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE admins 
                SET login_attempts = login_attempts + 1 
                WHERE id = ?
            ''', (admin_id,))
            
            # Lock account after 5 failed attempts for 30 minutes
            cursor.execute('''
                UPDATE admins 
                SET locked_until = datetime('now', '+30 minutes')
                WHERE id = ? AND login_attempts >= 5
            ''', (admin_id,))
    
    def log_admin_action(self, admin_id, action, description, ip_address=None, user_agent=None):
        """Log admin actions for audit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_log (admin_id, action, description, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_id, action, description, ip_address, user_agent))

    # Security methods
    def cleanup_expired_data(self):
        """Clean up expired VPN configs and orders"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate expired VPN configs
            cursor.execute('''
                UPDATE vpn_configs 
                SET is_active = FALSE 
                WHERE expires_at < datetime('now') AND is_active = TRUE
            ''')
            
            # Expire old orders
            cursor.execute('''
                UPDATE orders 
                SET status = 'expired' 
                WHERE expiry_date < datetime('now') AND status = 'active'
            ''')
            
            expired_configs = cursor.rowcount
            if expired_configs > 0:
                print(f"🔄 Cleaned up {expired_configs} expired VPN configurations")

# Test function for debugging
def test_database():
    """Test database connection and initialization"""
    try:
        db = Database()
        db.init_db()
        
        # Test security features
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Check foreign keys are enabled
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Foreign keys enabled")
            else:
                print("❌ Foreign keys not enabled")
                
        print("✅ Database test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()