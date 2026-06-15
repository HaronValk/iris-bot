from datetime import datetime, timedelta
from aiogram import Bot
import logging
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
    
    async def notify_new_appointment(self, appointment, admin_chat_id):
        logger.info(f"🔔 Пытаюсь отправить на {admin_chat_id}")
        
        if not admin_chat_id:
            logger.error("❌ ADMIN_CHAT_ID пустой!")
            return
        
        try:
            sv = appointment.service.name if appointment.service else '—'
            mn = appointment.master.name if appointment.master else '—'
            dt = appointment.datetime.strftime('%d.%m.%Y %H:%M') if appointment.datetime else '—'
            
            text = (
                f"🆕 <b>НОВАЯ ЗАПИСЬ!</b>\n\n"
                f"👤 {appointment.client_name}\n"
                f"📞 {appointment.client_phone}\n"
                f"💆 {sv}\n"
                f"👤 Мастер: {mn}\n"
                f"📅 {dt}\n"
                f"💰 {int(appointment.service.price) if appointment.service else '—'} ₽"
            )
            
            logger.info(f"📤 Отправляю: {text[:100]}...")
            await self.bot.send_message(admin_chat_id, text)
            logger.info(f"✅ Отправлено в {admin_chat_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
    
    async def notify_cancellation(self, appointment, admin_chat_id):
        if not admin_chat_id:
            return
        try:
            sv = appointment.service.name if appointment.service else '—'
            dt = appointment.datetime.strftime('%d.%m.%Y %H:%M') if appointment.datetime else '—'
            text = f"❌ <b>ЗАПИСЬ ОТМЕНЕНА</b>\n\n👤 {appointment.client_name}\n💆 {sv}\n📅 {dt}"
            await self.bot.send_message(admin_chat_id, text)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
    
    async def send_24h_reminders(self):
        tomorrow = datetime.now() + timedelta(days=1)
        apps = await self.db.get_appointments_for_period(
            tomorrow.replace(hour=0, minute=0),
            tomorrow.replace(hour=23, minute=59)
        )
        for a in apps:
            try:
                sv = a.service.name if a.service else '—'
                text = f"⏰ <b>НАПОМИНАНИЕ</b>\n\nЗавтра в {a.datetime.strftime('%H:%M')} вас ждёт:\n💆 {sv}\n\nВсё в силе?"
                u = await self.db.get_user(a.user_id) if a.user_id else None
                if u:
                    await self.bot.send_message(u.telegram_id, text)
            except:
                pass
    
    async def send_2h_reminders(self):
        now = datetime.now()
        start = now + timedelta(hours=2)
        apps = await self.db.get_appointments_for_period(start, start + timedelta(minutes=30))
        for a in apps:
            try:
                sv = a.service.name if a.service else '—'
                text = f"⏰ <b>СКОРО ВИЗИТ!</b>\n\nЧерез 2 часа в {a.datetime.strftime('%H:%M')}:\n💆 {sv}"
                u = await self.db.get_user(a.user_id) if a.user_id else None
                if u:
                    await self.bot.send_message(u.telegram_id, text)
            except:
                pass