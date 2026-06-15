import logging
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from bot.models.database import Base, User, Admin, Category, Service, Master, Appointment, Promotion, Setting

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_db(self):
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        await self._create_default_admin()

    async def _create_default_admin(self):
        async with self.session_factory() as s:
            r = await s.execute(select(Admin))
            if not r.scalars().first():
                h = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
                s.add(Admin(username="admin", password_hash=h, name="Администратор", role="super_admin"))
                await s.commit()

    async def auth_admin(self, u, p):
        async with self.session_factory() as s:
            r = await s.execute(select(Admin).where(Admin.username == u))
            a = r.scalar_one_or_none()
            if a and a.is_active and bcrypt.checkpw(p.encode(), a.password_hash.encode()):
                return a

    async def get_admins(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Admin))).scalars().all()

    async def create_admin(self, u, p, name, role="admin"):
        async with self.session_factory() as s:
            if (await s.execute(select(Admin).where(Admin.username == u))).scalar_one_or_none():
                return
            h = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            a = Admin(username=u, password_hash=h, name=name, role=role)
            s.add(a); await s.commit(); return a

    async def toggle_admin(self, aid):
        async with self.session_factory() as s:
            a = await s.get(Admin, aid)
            if a and a.role != "super_admin":
                a.is_active = not a.is_active; await s.commit(); return a

    async def save_user(self, tid, username=None, first_name=None, last_name=None, phone=None):
        async with self.session_factory() as s:
            r = await s.execute(select(User).where(User.telegram_id == tid))
            u = r.scalar_one_or_none()
            if u:
                if username: u.username = username
                if first_name: u.name = f"{first_name} {last_name or ''}".strip()
                if phone: u.phone = phone
            else:
                u = User(telegram_id=tid, username=username, name=f"{first_name} {last_name or ''}".strip(), phone=phone)
                s.add(u)
            await s.commit(); return u

    async def get_user(self, tid):
        async with self.session_factory() as s:
            return (await s.execute(select(User).where(User.telegram_id == tid))).scalar_one_or_none()

    async def get_categories(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Category).where(Category.is_active == True).order_by(Category.order))).scalars().all()

    async def get_category(self, cid):
        async with self.session_factory() as s:
            return (await s.execute(select(Category).where(Category.id == cid))).scalar_one_or_none()

    async def create_category(self, name, icon="💆"):
        async with self.session_factory() as s:
            c = Category(name=name, icon=icon); s.add(c); await s.commit(); return c

    async def get_services_by_category(self, cid):
        async with self.session_factory() as s:
            return (await s.execute(select(Service).where(and_(Service.category_id == cid, Service.is_active == True)))).scalars().all()

    async def get_service(self, sid):
        async with self.session_factory() as s:
            return (await s.execute(select(Service).where(Service.id == sid))).scalar_one_or_none()

    async def get_all_services(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Service))).scalars().all()

    async def create_service(self, data):
        async with self.session_factory() as s:
            sv = Service(**data, is_active=True); s.add(sv); await s.commit(); return sv

    async def toggle_service(self, sid):
        async with self.session_factory() as s:
            sv = await s.get(Service, sid)
            if sv: sv.is_active = not sv.is_active; await s.commit()
            return sv

    async def get_masters(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Master).where(Master.is_active == True))).scalars().all()

    async def get_all_masters(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Master))).scalars().all()

    async def get_master(self, mid):
        async with self.session_factory() as s:
            return (await s.execute(select(Master).where(Master.id == mid))).scalar_one_or_none()

    async def create_master(self, name, spec=None, phone=None):
        async with self.session_factory() as s:
            m = Master(name=name, specialization=spec, phone=phone); s.add(m); await s.commit(); return m

    async def toggle_master(self, mid):
        async with self.session_factory() as s:
            m = await s.get(Master, mid)
            if m: m.is_active = not m.is_active; await s.commit()
            return m

    async def get_free_slots(self, date, duration, master_id=None):
        slots = []
        from bot.config import Config
        cfg = Config()
        for h in range(cfg.WORK_START_HOUR, cfg.WORK_END_HOUR):
            for m in [0, 30]:
                if h == cfg.WORK_END_HOUR - 1 and m > 0:
                    break
                slots.append(f"{h:02d}:{m:02d}")
        async with self.session_factory() as s:
            start = datetime.combine(date, datetime.min.time())
            end = start + timedelta(days=1)
            q = select(Appointment).where(and_(Appointment.datetime >= start, Appointment.datetime < end, Appointment.status == 'confirmed'))
            if master_id: q = q.where(Appointment.master_id == master_id)
            for a in (await s.execute(q)).scalars():
                t = a.datetime.strftime("%H:%M")
                if t in slots: slots.remove(t)
        return slots

    async def is_time_available(self, date_str: str, time_str: str, duration: int, master_id: int = None):
        from datetime import datetime, timedelta
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_time = dt + timedelta(minutes=duration)
        async with self.session_factory() as s:
            q = select(Appointment).where(
                and_(
                    Appointment.status == 'confirmed',
                    Appointment.datetime < end_time,
                    Appointment.datetime >= dt - timedelta(minutes=120)
                )
            )
            if master_id:
                q = q.where(Appointment.master_id == master_id)
            apps = (await s.execute(q)).scalars().all()
            for a in apps:
                a_duration = a.service.duration if a.service else 60
                a_end = a.datetime + timedelta(minutes=a_duration)
                if dt < a_end and end_time > a.datetime:
                    return False
            return True

    async def create_appointment(self, user_id, service_id, datetime_str, client_name, client_phone, master_id=None, promo_code=None):
        async with self.session_factory() as s:
            r = await s.execute(select(User).where(User.telegram_id == user_id))
            u = r.scalar_one_or_none()
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            a = Appointment(user_id=u.id if u else None, service_id=service_id, master_id=master_id, datetime=dt, client_name=client_name, client_phone=client_phone, promo_code=promo_code)
            s.add(a)
            if u: u.visits_count += 1
            await s.commit(); await s.refresh(a)
            if a.service_id: a.service = await s.get(Service, a.service_id)
            if a.master_id: a.master = await s.get(Master, a.master_id)
            return a

    async def get_user_appointments(self, tid):
        async with self.session_factory() as s:
            r = await s.execute(select(User).where(User.telegram_id == tid))
            u = r.scalar_one_or_none()
            if not u: return []
            return (await s.execute(select(Appointment).where(Appointment.user_id == u.id).options(selectinload(Appointment.service)).order_by(Appointment.datetime.desc()))).scalars().all()

    async def get_appointment(self, aid):
        async with self.session_factory() as s:
            return (await s.execute(select(Appointment).where(Appointment.id == aid).options(selectinload(Appointment.service), selectinload(Appointment.master)))).scalar_one_or_none()

    async def cancel_appointment(self, aid, reason=None):
        async with self.session_factory() as s:
            a = await s.get(Appointment, aid)
            if a: a.status = 'cancelled'; a.cancellation_reason = reason; await s.commit()

    async def get_appointments_for_period(self, start, end):
        async with self.session_factory() as s:
            return (await s.execute(select(Appointment).where(and_(Appointment.datetime >= start, Appointment.datetime <= end, Appointment.status == 'confirmed')).options(selectinload(Appointment.service)))).scalars().all()

    async def get_all_appointments(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).order_by(Appointment.datetime.desc()))).scalars().all()

    async def get_active_promotions(self):
        async with self.session_factory() as s:
            return (await s.execute(select(Promotion).where(Promotion.is_active == True))).scalars().all()

    async def create_promotion(self, data):
        async with self.session_factory() as s:
            p = Promotion(**data, is_active=True); s.add(p); await s.commit(); return p

    async def get_statistics(self):
        async with self.session_factory() as s:
            apps = (await s.execute(select(Appointment))).scalars().all()
            total = len(apps)
            confirmed = len([a for a in apps if a.status == 'confirmed'])
            cancelled = len([a for a in apps if a.status == 'cancelled'])
            revenue = 0
            for a in apps:
                if a.status == 'confirmed':
                    sv = await s.get(Service, a.service_id)
                    if sv: revenue += sv.price
            return {"total": total, "confirmed": confirmed, "cancelled": cancelled, "revenue": int(revenue)}

    # ---- методы для настроек (приветствие и фото) ----
    async def get_setting(self, key: str):
        async with self.session_factory() as s:
            r = await s.execute(select(Setting).where(Setting.key == key))
            setting = r.scalar_one_or_none()
            return setting.value if setting else None
    async def get_all_users(self):
        async with self.session_factory() as s:
            result = await s.execute(select(User))
            return result.scalars().all()
    async def set_setting(self, key: str, value: str):
        async with self.session_factory() as s:
            r = await s.execute(select(Setting).where(Setting.key == key))
            setting = r.scalar_one_or_none()
            if setting:
                setting.value = value
            else:
                s.add(Setting(key=key, value=value))
            await s.commit()