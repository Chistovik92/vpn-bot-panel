import logging
import logging.handlers
from database import BotLog, SessionLocal
from datetime import datetime
import config

class DatabaseHandler(logging.Handler):
    def emit(self, record):
        try:
            db = SessionLocal()
            log_entry = BotLog(
                level=record.levelname,
                message=self.format(record),
                user_id=getattr(record, 'user_id', None),
                action=getattr(record, 'action', None),
                created_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception:
            pass  # Avoid recursion if database is down

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Файловый handler
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Консольный handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Database handler
    db_handler = DatabaseHandler()
    db_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(db_handler)

def log_user_action(user_id, action, message, level='INFO'):
    logger = logging.getLogger('user_actions')
    extra = {'user_id': user_id, 'action': action}
    if level == 'INFO':
        logger.info(message, extra=extra)
    elif level == 'WARNING':
        logger.warning(message, extra=extra)
    elif level == 'ERROR':
        logger.error(message, extra=extra)
