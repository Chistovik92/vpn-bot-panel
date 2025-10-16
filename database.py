from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config
import os

# Создаем директорию для базы данных если нужно
db_path = config.DATABASE_URL.replace('sqlite:///', '')
if db_path and not db_path.startswith('/'):
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

engine = create_engine(config.DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    language = Column(String, default=config.DEFAULT_LANGUAGE)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    subscriptions = relationship("Subscription", back_populates="user")

class Panel(Base):
    __tablename__ = 'panels'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    location = Column(String)
    is_active = Column(Boolean, default=True)
    max_clients = Column(Integer, default=100)
    current_clients = Column(Integer, default=0)
    last_check = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    panel_id = Column(Integer, ForeignKey('panels.id'))
    email = Column(String, nullable=False)
    telegram_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    expires_at = Column(DateTime)
    tariff = Column(String, default="monthly")
    
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    payment_method = Column(String, nullable=False)
    payment_id = Column(String, unique=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    subscription = relationship("Subscription", back_populates="payments")

class BotLog(Base):
    __tablename__ = 'bot_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    user_id = Column(Integer)
    action = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    panel_id = Column(Integer, ForeignKey('panels.id'))
    alert_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
