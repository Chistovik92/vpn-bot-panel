import asyncio
import logging
from datetime import datetime, timedelta
from database import SessionLocal, Panel, Alert
from xui_api import XUIAPI
from telegram import Bot
import config

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, bot_token, admin_ids):
        self.bot_token = bot_token
        self.admin_ids = admin_ids
        self.last_alert_time = {}

    async def check_panels_status(self):
        """Проверка статуса всех панелей"""
        db = SessionLocal()
        try:
            panels = db.query(Panel).filter(Panel.is_active == True).all()
            
            for panel in panels:
                try:
                    xui = XUIAPI({
                        'url': panel.url,
                        'username': panel.username,
                        'password': panel.password
                    })
                    
                    status = xui.get_panel_status()
                    panel.last_check = datetime.utcnow()
                    
                    if status is None:
                        # Панель недоступна
                        await self.send_panel_alert(panel, "Панель недоступна")
                    else:
                        # Панель работает нормально
                        logger.info(f"Panel {panel.name} is online")
                        
                except Exception as e:
                    logger.error(f"Panel {panel.name} check failed: {str(e)}")
                    await self.send_panel_alert(panel, f"Ошибка проверки: {str(e)}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Panels status check failed: {str(e)}")
        finally:
            db.close()

    async def send_panel_alert(self, panel, message):
        """Отправка уведомления о проблеме с панелью"""
        alert_key = f"panel_{panel.id}"
        current_time = datetime.utcnow()
        
        # Проверяем коолдаун
        if alert_key in self.last_alert_time:
            time_diff = (current_time - self.last_alert_time[alert_key]).total_seconds()
            if time_diff < config.ALERT_COOLDOWN:
                return
        
        self.last_alert_time[alert_key] = current_time
        
        # Сохраняем алерт в базу
        db = SessionLocal()
        try:
            alert = Alert(
                panel_id=panel.id,
                alert_type="panel_down",
                message=f"{panel.name}: {message}",
                created_at=current_time
            )
            db.add(alert)
            db.commit()
        finally:
            db.close()
        
        # Отправляем уведомления администраторам
        bot = Bot(token=self.bot_token)
        for admin_id in self.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚨 **Alert - {panel.name}**\n\n{message}\n\n"
                    f"URL: {panel.url}\n"
                    f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_id}: {str(e)}")

    async def check_subscriptions(self):
        """Проверка истекших подписок"""
        db = SessionLocal()
        try:
            from database import Subscription
            expired_subs = db.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.expires_at < datetime.utcnow()
            ).all()
            
            for sub in expired_subs:
                # Отключаем подписку
                sub.is_active = False
                
                # Находим панель и отключаем клиента
                panel = db.query(Panel).filter(Panel.id == sub.panel_id).first()
                if panel:
                    try:
                        xui = XUIAPI({
                            'url': panel.url,
                            'username': panel.username,
                            'password': panel.password
                        })
                        # Здесь нужно найти client_id по email и отключить
                        # xui.disable_client(client_id)
                    except Exception as e:
                        logger.error(f"Failed to disable client for expired sub {sub.id}: {str(e)}")
            
            db.commit()
            logger.info(f"Disabled {len(expired_subs)} expired subscriptions")
            
        except Exception as e:
            logger.error(f"Subscriptions check failed: {str(e)}")
        finally:
            db.close()

    async def start_monitoring(self):
        """Запуск мониторинга"""
        while True:
            try:
                await self.check_panels_status()
                await self.check_subscriptions()
            except Exception as e:
                logger.error(f"Monitoring cycle failed: {str(e)}")
            
            await asyncio.sleep(config.CHECK_INTERVAL)
