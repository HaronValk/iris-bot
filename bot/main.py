import asyncio, json, logging, re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from bot.config import Config
from bot.handlers import client_router, booking_router, admin_router
from bot.services.database import Database
from bot.services.notifications import NotificationService
from bot.models.database import Category, Service, Master

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('bot.log', encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

config = Config()
db = Database(config.DATABASE_URL)
storage = MemoryStorage()
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
notif_service = NotificationService(bot, db)
scheduler = AsyncIOScheduler()

dp.include_router(admin_router)
dp.include_router(booking_router)
dp.include_router(client_router)

@dp.update.middleware()
async def inject(handler, event: Update, data: dict):
    data['db'] = db
    data['notif_service'] = notif_service
    data['config'] = config
    return await handler(event, data)

def parse_duration(s):
    t = 0
    h = re.search(r'(\d+)\s*ч', s)
    if h: t += int(h.group(1)) * 60
    m = re.search(r'(\d+)\s*мин', s)
    if m: t += int(m.group(1))
    return t if t > 0 else 60

async def load_data():
    if await db.get_categories():
        return
    try:
        with open('services.json', encoding='utf-8') as f:
            sv = json.load(f)
    except:
        return
    cats = {}
    for s in sv:
        cn = s.get('category', 'Общее')
        ic = '💆'
        if 'лица' in cn.lower(): ic = '💆'
        elif 'комплекс' in cn.lower(): ic = '✨'
        elif 'фейс' in cn.lower(): ic = '🏆'
        elif 'аппарат' in cn.lower(): ic = '⚙️'
        elif 'пилинг' in cn.lower(): ic = '🧴'
        elif 'тела' in cn.lower(): ic = '🧘'
        elif 'доп' in cn.lower(): ic = '🩺'
        if cn not in cats:
            cats[cn] = {'icon': ic, 'services': []}
        cats[cn]['services'].append(s)
    
    async with db.session_factory() as sess:
        for i, (cn, cd) in enumerate(cats.items()):
            c = Category(name=cn, icon=cd['icon'], order=i)
            sess.add(c)
            await sess.flush()
            for s in cd['services']:
                sess.add(Service(category_id=c.id, name=s['name'], duration=parse_duration(s.get('duration', '60 мин')), price=float(s['price'])))
        await sess.commit()
    
    try:
        with open('masters.json', encoding='utf-8') as f:
            ms = json.load(f)
        async with db.session_factory() as sess:
            for m in ms:
                sess.add(Master(name=m['name'], specialization=m.get('specialization', '')))
            await sess.commit()
    except:
        pass
    
    logger.info("✅ Данные загружены")

async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "ВАШ_ТОКЕН":
        print("❌ Вставьте токен бота в .env!")
        return
    
    await db.init_db()
    await load_data()
    
    scheduler.add_job(notif_service.send_24h_reminders, 'interval', minutes=30)
    scheduler.add_job(notif_service.send_2h_reminders, 'interval', minutes=15)
    scheduler.start()
    
    logger.info(f"🤖 Бот {config.SALON_NAME} запущен!")
    logger.info(f"🌐 Сайт: {config.SALON_SITE_URL}")
    logger.info(f"🗺️ Карта: {config.SALON_MAP_URL}")
    logger.info(f"🔐 /admin (admin / admin123)")
    
    # Тестовое уведомление
    if config.ADMIN_CHAT_ID:
        try:
            await bot.send_message(config.ADMIN_CHAT_ID, "✅ Бот запущен и готов к работе!")
            logger.info("✅ Уведомление админу отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())