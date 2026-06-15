import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN","")
        self.ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID","")
        self.SUPER_ADMIN_IDS = [int(x.strip()) for x in os.getenv("SUPER_ADMIN_IDS","").split(",") if x.strip()]
        self.DATABASE_URL = os.getenv("DATABASE_URL","sqlite+aiosqlite:///salon.db")
        self.SALON_NAME = os.getenv("SALON_NAME","IRIS")
        self.SALON_ADDRESS = os.getenv("SALON_ADDRESS","г. Москва")
        self.SALON_MAP_URL = os.getenv("SALON_MAP_URL", "")          # ← ДОБАВИТЬ
        self.SALON_SITE_URL = os.getenv("SALON_SITE_URL", "")        # ← ДОБАВИТЬ
        self.SALON_PHONE = os.getenv("SALON_PHONE","+7")
        self.SALON_WORK_HOURS = os.getenv("SALON_WORK_HOURS","10:00-21:00")
        self.MIN_HOURS_BEFORE_BOOKING = int(os.getenv("MIN_HOURS_BEFORE_BOOKING","2"))
        self.MAX_DAYS_BOOKING = int(os.getenv("MAX_DAYS_BOOKING","14"))
        self.WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", "8"))
        self.WORK_END_HOUR = int(os.getenv("WORK_END_HOUR", "22"))