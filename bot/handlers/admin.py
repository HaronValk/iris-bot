from bot.models.database import Promotion, Master, Setting, Admin, Category, Service, Appointment
import bcrypt
from bot.models.database import Promotion, Master, Setting, Admin
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.keyboards.client import get_main_menu
from bot.models.database import Promotion, Master
from bot.models.database import Promotion, Master, Setting
admin_router = Router()
admin_sessions = {}
from datetime import datetime
from sqlalchemy import select, and_
from bot.models.database import Appointment
import asyncio
class AdminBroadcast(StatesGroup):
    waiting_text = State()
class AdminAuth(StatesGroup):
    waiting_login = State()
    waiting_password = State()

class AdminAddMaster(StatesGroup):
    waiting_name = State()
    waiting_spec = State()
    waiting_photo = State()

class AdminUpdatePhoto(StatesGroup):
    waiting_photo = State()

class AdminAddService(StatesGroup):
    waiting_cat = State()
    waiting_name = State()
    waiting_dur = State()
    waiting_price = State()

class AdminAddCategory(StatesGroup):
    waiting_name = State()
    waiting_icon = State()

class AdminAddPromo(StatesGroup):
    waiting_title = State()
    waiting_desc = State()
    waiting_disc = State()
    waiting_code = State()

class AdminAddAdmin(StatesGroup):
    waiting_user = State()
    waiting_pass = State()
    waiting_name = State()
class AdminEditInfo(StatesGroup):
    waiting_contact = State()

def get_admin_menu():
    b = InlineKeyboardBuilder()
    b.button(text="👤 Мастера", callback_data="adm_masters")
    b.button(text="💆 Услуги", callback_data="adm_services")
    b.button(text="📁 Категории", callback_data="adm_categories")
    b.button(text="🔐 Администраторы", callback_data="adm_admins")
    b.button(text="🎁 Акции", callback_data="adm_promos")
    b.button(text="📊 Статистика", callback_data="adm_stats")
    b.button(text="📅 Записи", callback_data="adm_appointments")
    b.button(text="💬 Изменить контакт Telegram", callback_data="adm_edit_contact")
    b.button(text="⚙️ Настройки", callback_data="adm_settings")
    b.button(text="📢 Рассылка", callback_data="adm_broadcast")
    b.button(text="🚪 Выйти", callback_data="adm_logout")
    b.adjust(1)
    return b.as_markup()

def is_admin(uid):
    return uid in admin_sessions

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, config, state: FSMContext):
    await state.clear()
    if message.from_user.id in config.SUPER_ADMIN_IDS:
        admin_sessions[message.from_user.id] = {"role": "super_admin", "name": "Супер-админ"}
        await message.answer("🔐 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=get_admin_menu())
        return
    if is_admin(message.from_user.id):
        await message.answer("🔐 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=get_admin_menu())
        return
    await state.set_state(AdminAuth.waiting_login)
    await message.answer("🔐 <b>ВХОД</b>\n\nВведите логин:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_cancel")]]))

@admin_router.message(StateFilter(AdminAuth.waiting_login))
async def auth_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(AdminAuth.waiting_password)
    await message.answer("Введите пароль:")

@admin_router.message(StateFilter(AdminAuth.waiting_password))
async def auth_password(message: Message, state: FSMContext, db):
    data = await state.get_data()
    admin = await db.auth_admin(data['login'], message.text.strip())
    if admin:
        admin_sessions[message.from_user.id] = {"role": admin.role, "name": admin.name}
        await message.answer(f"✅ Добро пожаловать, <b>{admin.name}</b>!", reply_markup=get_admin_menu())
    else:
        await message.answer("❌ Неверный логин или пароль.", reply_markup=get_main_menu())
    await state.clear()

@admin_router.callback_query(F.data == "adm_cancel")
async def adm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🚪 Отменено.")
    await callback.answer()

@admin_router.callback_query(F.data == "adm_logout")
async def adm_logout(callback: CallbackQuery, state: FSMContext):
    admin_sessions.pop(callback.from_user.id, None)
    await state.clear()
    await callback.message.edit_text("🚪 Вы вышли из админ-панели.")
    await callback.answer()

@admin_router.callback_query(F.data == "adm_back")
async def adm_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await callback.message.edit_text("🔐 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=get_admin_menu())
    await callback.answer()

@admin_router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    s = await db.get_statistics()
    await callback.message.edit_text(f"📊 <b>СТАТИСТИКА</b>\n\n📝 Всего: {s['total']}\n✅ Подтверждено: {s['confirmed']}\n❌ Отменено: {s['cancelled']}\n💰 Выручка: {s['revenue']} ₽", reply_markup=get_admin_menu())
    await callback.answer()

@admin_router.callback_query(F.data == "adm_appointments")
async def adm_appointments(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    apps = await db.get_all_appointments()
    if not apps:
        await callback.message.edit_text("📭 Записей нет.", reply_markup=get_admin_menu())
        await callback.answer()
        return
    
    text = "📅 <b>ПОСЛЕДНИЕ ЗАПИСИ:</b>\n\n"
    for a in apps[:15]:
        sv = a.service.name if a.service else '—'
        mn = a.master.name if a.master else '—'
        dt = a.datetime.strftime('%d.%m.%Y %H:%M') if a.datetime else '—'
        st = '✅' if a.status == 'confirmed' else '❌'
        text += f"{st} {a.client_name} | {sv} | {mn}\n   📅 {dt}\n\n"
    
    b = InlineKeyboardBuilder()
    # Кнопки отмены для каждой подтверждённой записи
    for a in apps:
        if a.status == 'confirmed':
            b.button(text=f"❌ Отменить: {a.client_name} {a.datetime.strftime('%d.%m %H:%M') if a.datetime else ''}", 
                     callback_data=f"adm_cancel_app_{a.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

# Обработчик отмены записи админом
@admin_router.callback_query(F.data.startswith("adm_cancel_app_"))
async def adm_cancel_appointment(callback: CallbackQuery, db, notif_service, config):
    if not is_admin(callback.from_user.id): return
    aid = int(callback.data.split("_")[-1])
    
    app = await db.get_appointment(aid)
    if not app:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    
    # Отменяем запись
    await db.cancel_appointment(aid, "Отменено администратором")
    
    # Уведомление админу
    if notif_service and config:
        await notif_service.notify_cancellation(app, config.ADMIN_CHAT_ID)
    
    # Уведомление клиенту
    if app.user_id:
        user = await db.get_user(app.user_id) if app.user_id else None
        if user:
            try:
                sv = app.service.name if app.service else '—'
                dt = app.datetime.strftime('%d.%m.%Y %H:%M') if app.datetime else '—'
                await callback.bot.send_message(
                    user.telegram_id,
                    f"❌ <b>Ваша запись отменена администратором</b>\n\n"
                    f"💆 {sv}\n📅 {dt}\n\n"
                    f"📞 Свяжитесь с нами: {config.SALON_PHONE}"
                )
            except:
                pass
    
    await callback.answer(f"✅ Запись #{aid} отменена!")
    await adm_appointments(callback, db)

# МАСТЕРА
@admin_router.callback_query(F.data == "adm_masters")
async def adm_masters(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    masters = await db.get_all_masters()
    text = "👤 <b>МАСТЕРА:</b>\n\n"
    for m in masters:
        status = '✅' if m.is_active else '❌'
        text += f"{status} <b>{m.name}</b> — {m.specialization or '—'}\n"
        text += f"   📸 Фото: {'есть' if m.photo_url else 'нет'}\n\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить мастера", callback_data="adm_add_master")
    for m in masters:
        act = "❌ Скрыть" if m.is_active else "✅ Показать"
        b.button(text=f"{act} {m.name}", callback_data=f"adm_toggle_master_{m.id}")
        b.button(text=f"📸 Фото для {m.name[:15]}", callback_data=f"adm_update_photo_{m.id}")
        b.button(text=f"🗑️ Удалить {m.name}", callback_data=f"adm_delete_master_{m.id}")  # ← НОВАЯ КНОПКА
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()
@admin_router.callback_query(F.data.startswith("adm_delete_master_"))
async def adm_delete_master(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    mid = int(callback.data.split("_")[-1])
    
    # Проверяем, есть ли будущие записи у мастера
    async with db.session_factory() as s:
        from datetime import datetime
        now = datetime.now()
        apps = await s.execute(
            select(Appointment).where(
                and_(
                    Appointment.master_id == mid,
                    Appointment.datetime > now,
                    Appointment.status == 'confirmed'
                )
            )
        )
        future_apps = apps.scalars().all()
        
        if future_apps:
            await callback.answer(
                f"❌ Нельзя удалить! У мастера {len(future_apps)} будущих записей.",
                show_alert=True
            )
            return
        
        master = await s.get(Master, mid)
        if master:
            name = master.name
            await s.delete(master)
            await s.commit()
            await callback.answer(f"✅ Мастер '{name}' удалён!")
    
    await adm_masters(callback, db)
@admin_router.callback_query(F.data == "adm_add_master")
async def adm_add_master(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await state.set_state(AdminAddMaster.waiting_name)
    await callback.message.edit_text("👤 <b>НОВЫЙ МАСТЕР</b>\n\nВведите имя:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_masters")]]))
    await callback.answer()

@admin_router.message(StateFilter(AdminAddMaster.waiting_name))
async def adm_add_master_name(message: Message, state: FSMContext):
    await state.update_data(mname=message.text.strip())
    await state.set_state(AdminAddMaster.waiting_spec)
    await message.answer("Введите специализацию (или -):")

@admin_router.message(StateFilter(AdminAddMaster.waiting_spec))
async def adm_add_master_spec(message: Message, state: FSMContext):
    spec = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(mspec=spec)
    await state.set_state(AdminAddMaster.waiting_photo)
    await message.answer("📸 Отправьте <b>фото мастера</b> (или - пропустить):")

@admin_router.message(StateFilter(AdminAddMaster.waiting_photo))
async def adm_add_master_photo(message: Message, state: FSMContext, db):
    data = await state.get_data()
    photo_url = None
    if message.photo:
        photo_url = message.photo[-1].file_id
    elif message.text and message.text.strip() != '-':
        photo_url = message.text.strip()
    
    async with db.session_factory() as s:
        m = Master(name=data['mname'], specialization=data.get('mspec'), photo_url=photo_url)
        s.add(m)
        await s.commit()
    
    text = f"✅ Мастер <b>{data['mname']}</b> добавлен!"
    if photo_url: text += "\n📸 Фото сохранено"
    await message.answer(text, reply_markup=get_admin_menu())
    await state.clear()

@admin_router.callback_query(F.data.startswith("adm_toggle_master_"))
async def adm_toggle_master(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    mid = int(callback.data.split("_")[-1])
    m = await db.toggle_master(mid)
    if m:
        await callback.answer(f"{'Активирован' if m.is_active else 'Скрыт'}: {m.name}")
        await adm_masters(callback, db)

@admin_router.callback_query(F.data.startswith("adm_update_photo_"))
async def adm_update_photo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    mid = int(callback.data.split("_")[-1])
    await state.update_data(photo_mid=mid)
    await state.set_state(AdminUpdatePhoto.waiting_photo)
    await callback.message.edit_text("📸 Отправьте <b>новое фото</b>:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_masters")]]))
    await callback.answer()

@admin_router.message(StateFilter(AdminUpdatePhoto.waiting_photo))
async def adm_update_photo_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    mid = data['photo_mid']
    photo_url = None
    if message.photo:
        photo_url = message.photo[-1].file_id
    
    if photo_url:
        async with db.session_factory() as s:
            m = await s.get(Master, mid)
            if m:
                m.photo_url = photo_url
                await s.commit()
                await message.answer(f"✅ Фото для <b>{m.name}</b> обновлено!", reply_markup=get_admin_menu())
    else:
        await message.answer("❌ Отправьте фото!")
    await state.clear()

# УСЛУГИ
@admin_router.callback_query(F.data == "adm_services")
async def adm_services(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    cats = await db.get_categories()
    all_sv = await db.get_all_services()
    text = "💆 <b>УСЛУГИ:</b>\n\n"
    for cat in cats:
        text += f"<b>{cat.icon} {cat.name}</b>\n"
        for s in [x for x in all_sv if x.category_id == cat.id]:
            text += f"  {'✅' if s.is_active else '❌'} {s.name} — {s.duration}мин, {int(s.price)}₽\n"
        text += "\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить услугу", callback_data="adm_add_service")
    for s in all_sv:
        act = "❌ Скрыть" if s.is_active else "✅ Показать"
        b.button(text=f"{act} {s.name[:30]}", callback_data=f"adm_toggle_service_{s.id}")
        b.button(text=f"✏️ Ред. {s.name[:25]}", callback_data=f"adm_edit_sv_{s.id}")
        b.button(text=f"🗑️ Удалить {s.name[:25]}", callback_data=f"adm_delete_sv_{s.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()
    # Редактирование услуги
class AdminEditService(StatesGroup):
    waiting_name = State()
    waiting_dur = State()
    waiting_price = State()

@admin_router.callback_query(F.data.startswith("adm_edit_sv_"))
async def adm_edit_sv_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    sid = int(callback.data.split("_")[-1])
    await state.update_data(edit_sid=sid)
    await state.set_state(AdminEditService.waiting_name)
    await callback.message.edit_text(
        "💆 Введите <b>новое название</b> услуги:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_services")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminEditService.waiting_name))
async def adm_edit_sv_name(message: Message, state: FSMContext):
    await state.update_data(edit_name=message.text.strip())
    await state.set_state(AdminEditService.waiting_dur)
    await message.answer("Введите <b>новую длительность</b> в минутах:")

@admin_router.message(StateFilter(AdminEditService.waiting_dur))
async def adm_edit_sv_dur(message: Message, state: FSMContext):
    try:
        d = int(message.text)
    except:
        await message.answer("❌ Введите число!")
        return
    await state.update_data(edit_dur=d)
    await state.set_state(AdminEditService.waiting_price)
    await message.answer("Введите <b>новую цену</b> в рублях:")

@admin_router.message(StateFilter(AdminEditService.waiting_price))
async def adm_edit_sv_save(message: Message, state: FSMContext, db):
    try:
        p = float(message.text)
    except:
        await message.answer("❌ Введите число!")
        return
    
    data = await state.get_data()
    sid = data['edit_sid']
    
    async with db.session_factory() as s:
        sv = await s.get(Service, sid)
        if sv:
            sv.name = data['edit_name']
            sv.duration = data['edit_dur']
            sv.price = p
            await s.commit()
            await message.answer(f"✅ Услуга обновлена!", reply_markup=get_admin_menu())
    
    await state.clear()

# Удаление услуги
@admin_router.callback_query(F.data.startswith("adm_delete_sv_"))
async def adm_delete_sv(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    sid = int(callback.data.split("_")[-1])
    
    async with db.session_factory() as s:
        # Проверяем будущие записи
        now = datetime.now()
        apps = await s.execute(
            select(Appointment).where(
                and_(
                    Appointment.service_id == sid,
                    Appointment.datetime > now,
                    Appointment.status == 'confirmed'
                )
            )
        )
        if apps.scalars().all():
            await callback.answer("❌ Есть будущие записи на эту услугу!", show_alert=True)
            return
        
        sv = await s.get(Service, sid)
        if sv:
            name = sv.name
            await s.delete(sv)
            await s.commit()
            await callback.answer(f"✅ Услуга '{name}' удалена!")
    
    await adm_services(callback, db)

@admin_router.callback_query(F.data == "adm_add_service")
async def adm_add_service(callback: CallbackQuery, state: FSMContext, db):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    cats = await db.get_categories()
    b = InlineKeyboardBuilder()
    for c in cats: b.button(text=f"{c.icon} {c.name}", callback_data=f"adm_sv_cat_{c.id}")
    b.button(text="◀️ Отмена", callback_data="adm_services")
    b.adjust(1)
    await state.set_state(AdminAddService.waiting_cat)
    await callback.message.edit_text("💆 <b>НОВАЯ УСЛУГА</b>\n\nВыберите категорию:", reply_markup=b.as_markup())
    await callback.answer()

@admin_router.callback_query(StateFilter(AdminAddService.waiting_cat), F.data.startswith("adm_sv_cat_"))
async def adm_add_service_name(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[-1])
    await state.update_data(sv_cat=cid)
    await state.set_state(AdminAddService.waiting_name)
    await callback.message.edit_text("Введите название:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_services")]]))
    await callback.answer()

@admin_router.message(StateFilter(AdminAddService.waiting_name))
async def adm_add_service_dur(message: Message, state: FSMContext):
    await state.update_data(sv_name=message.text.strip())
    await state.set_state(AdminAddService.waiting_dur)
    await message.answer("Введите длительность в минутах:")

@admin_router.message(StateFilter(AdminAddService.waiting_dur))
async def adm_add_service_price(message: Message, state: FSMContext):
    try: d = int(message.text)
    except: await message.answer("❌ Введите число!"); return
    await state.update_data(sv_dur=d)
    await state.set_state(AdminAddService.waiting_price)
    await message.answer("Введите цену в рублях:")

@admin_router.message(StateFilter(AdminAddService.waiting_price))
async def adm_add_service_save(message: Message, state: FSMContext, db):
    try: p = float(message.text)
    except: await message.answer("❌ Введите число!"); return
    data = await state.get_data()
    await db.create_service({"category_id": data['sv_cat'], "name": data['sv_name'], "duration": data['sv_dur'], "price": p})
    await message.answer(f"✅ Услуга <b>{data['sv_name']}</b> добавлена!", reply_markup=get_admin_menu())
    await state.clear()

@admin_router.callback_query(F.data.startswith("adm_toggle_service_"))
async def adm_toggle_service(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    sid = int(callback.data.split("_")[-1])
    s = await db.toggle_service(sid)
    if s: await callback.answer(f"{'Активирована' if s.is_active else 'Скрыта'}: {s.name}"); await adm_services(callback, db)

# КАТЕГОРИИ
@admin_router.callback_query(F.data == "adm_categories")
async def adm_categories(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    cats = await db.get_categories()
    text = "📁 <b>КАТЕГОРИИ:</b>\n\n"
    for c in cats:
        text += f"{c.icon} <b>{c.name}</b>\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить категорию", callback_data="adm_add_category")
    for c in cats:
        b.button(text=f"✏️ Ред. {c.name[:20]}", callback_data=f"adm_edit_cat_{c.id}")
        b.button(text=f"🗑️ Удалить {c.name[:20]}", callback_data=f"adm_delete_cat_{c.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "adm_add_category")
async def adm_add_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await state.set_state(AdminAddCategory.waiting_name)
    await callback.message.edit_text("📁 <b>НОВАЯ КАТЕГОРИЯ</b>\n\nВведите название:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_categories")]]))
    await callback.answer()
@admin_router.callback_query(F.data == "adm_categories")
async def adm_categories(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    cats = await db.get_categories()
    text = "📁 <b>КАТЕГОРИИ:</b>\n\n"
    for c in cats:
        text += f"{c.icon} <b>{c.name}</b>\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить категорию", callback_data="adm_add_category")
    for c in cats:
        b.button(text=f"✏️ Ред. {c.name[:20]}", callback_data=f"adm_edit_cat_{c.id}")
        b.button(text=f"🗑️ Удалить {c.name[:20]}", callback_data=f"adm_delete_cat_{c.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()
    # Редактирование категории
class AdminEditCategory(StatesGroup):
    waiting_name = State()
    waiting_icon = State()

@admin_router.callback_query(F.data.startswith("adm_edit_cat_"))
async def adm_edit_cat_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    cid = int(callback.data.split("_")[-1])
    await state.update_data(edit_cid=cid)
    await state.set_state(AdminEditCategory.waiting_name)
    await callback.message.edit_text(
        "📁 Введите <b>новое название</b> категории:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_categories")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminEditCategory.waiting_name))
async def adm_edit_cat_name(message: Message, state: FSMContext):
    await state.update_data(edit_name=message.text.strip())
    await state.set_state(AdminEditCategory.waiting_icon)
    await message.answer("Отправьте <b>новую иконку</b> (эмодзи) или <code>-</code>:")

@admin_router.message(StateFilter(AdminEditCategory.waiting_icon))
async def adm_edit_cat_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    cid = data['edit_cid']
    name = data['edit_name']
    icon = message.text.strip() if message.text.strip() != '-' else None
    
    async with db.session_factory() as s:
        cat = await s.get(Category, cid)
        if cat:
            cat.name = name
            if icon:
                cat.icon = icon
            await s.commit()
            await message.answer(f"✅ Категория обновлена!", reply_markup=get_admin_menu())
    
    await state.clear()

# Удаление категории
@admin_router.callback_query(F.data.startswith("adm_delete_cat_"))
async def adm_delete_cat(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    cid = int(callback.data.split("_")[-1])
    
    async with db.session_factory() as s:
        from bot.models.database import Service as Svc
        # Проверяем, есть ли услуги в категории
        svs = await s.execute(select(Svc).where(Svc.category_id == cid))
        if svs.scalars().all():
            await callback.answer("❌ Сначала удалите все услуги из категории!", show_alert=True)
            return
        
        from bot.models.database import Category as Cat
        cat = await s.get(Cat, cid)
        if cat:
            name = cat.name
            await s.delete(cat)
            await s.commit()
            await callback.answer(f"✅ Категория '{name}' удалена!")
    
    await adm_categories(callback, db)
@admin_router.message(StateFilter(AdminAddCategory.waiting_name))
async def adm_add_category_icon(message: Message, state: FSMContext):
    await state.update_data(cat_name=message.text.strip())
    await state.set_state(AdminAddCategory.waiting_icon)
    await message.answer("Отправьте эмодзи (или -):")

@admin_router.message(StateFilter(AdminAddCategory.waiting_icon))
async def adm_add_category_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    icon = message.text.strip() if message.text.strip() != '-' else "💆"
    await db.create_category(data['cat_name'], icon)
    await message.answer(f"✅ Категория {icon} <b>{data['cat_name']}</b> создана!", reply_markup=get_admin_menu())
    await state.clear()

# АКЦИИ
@admin_router.callback_query(F.data == "adm_promos")
async def adm_promos(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    promos = await db.get_active_promotions()
    text = "🎁 <b>АКЦИИ:</b>\n\n"
    if promos:
        for p in promos:
            text += f"<b>{p.title}</b>\n"
            if p.description: text += f"📝 {p.description}\n"
            if p.discount_percent: text += f"💰 Скидка: {p.discount_percent}%\n"
            if p.promo_code: text += f"🔑 Промокод: <code>{p.promo_code}</code>\n"
            text += "\n"
    else:
        text += "Нет акций\n"
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать", callback_data="adm_add_promo")
    for p in promos:
        b.button(text=f"🗑️ Удалить: {p.title[:30]}", callback_data=f"adm_delete_promo_{p.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "adm_add_promo")
async def adm_add_promo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await state.set_state(AdminAddPromo.waiting_title)
    await callback.message.edit_text("🎁 <b>НОВАЯ АКЦИЯ</b>\n\nВведите название:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_promos")]]))
    await callback.answer()

@admin_router.message(StateFilter(AdminAddPromo.waiting_title))
async def adm_add_promo_desc(message: Message, state: FSMContext):
    await state.update_data(pr_title=message.text.strip())
    await state.set_state(AdminAddPromo.waiting_desc)
    await message.answer("Введите описание (или -):")

@admin_router.message(StateFilter(AdminAddPromo.waiting_desc))
async def adm_add_promo_disc(message: Message, state: FSMContext):
    await state.update_data(pr_desc=message.text.strip() if message.text.strip() != '-' else None)
    await state.set_state(AdminAddPromo.waiting_disc)
    await message.answer("Введите процент скидки (или 0):")

@admin_router.message(StateFilter(AdminAddPromo.waiting_disc))
async def adm_add_promo_code(message: Message, state: FSMContext):
    try: d = float(message.text)
    except: await message.answer("❌ Введите число!"); return
    await state.update_data(pr_disc=d if d > 0 else None)
    await state.set_state(AdminAddPromo.waiting_code)
    await message.answer("Введите промокод (или -):")

@admin_router.message(StateFilter(AdminAddPromo.waiting_code))
async def adm_add_promo_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    code = message.text.strip() if message.text.strip() != '-' else None
    await db.create_promotion({"title": data['pr_title'], "description": data['pr_desc'], "discount_percent": data['pr_disc'], "promo_code": code})
    await message.answer(f"✅ Акция <b>{data['pr_title']}</b> создана!", reply_markup=get_admin_menu())
    await state.clear()

@admin_router.callback_query(F.data.startswith("adm_delete_promo_"))
async def adm_delete_promo(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    pid = int(callback.data.split("_")[-1])
    async with db.session_factory() as s:
        p = await s.get(Promotion, pid)
        if p: p.is_active = False; await s.commit()
        await callback.answer("✅ Удалено!")
    await adm_promos(callback, db)

# АДМИНИСТРАТОРЫ
@admin_router.callback_query(F.data == "adm_admins")
async def adm_admins(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    admins = await db.get_admins()  # ← Сначала получаем список
    text = "🔐 <b>АДМИНИСТРАТОРЫ:</b>\n\n"
    for a in admins:
        status = '✅' if a.is_active else '❌'
        text += f"{status} <b>{a.name}</b> (@{a.username}) — {a.role}\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить админа", callback_data="adm_add_admin")
    for a in admins:  # ← Этот цикл ДОЛЖЕН БЫТЬ ЗДЕСЬ, внутри функции
        if a.role != "super_admin":
            act = "❌ Заблокировать" if a.is_active else "✅ Разблокировать"
            b.button(text=f"{act} {a.name}", callback_data=f"adm_toggle_admin_{a.id}")
            b.button(text=f"🔑 Сброс пароля {a.name}", callback_data=f"adm_reset_password_{a.id}")
            b.button(text=f"🗑️ Удалить {a.name}", callback_data=f"adm_delete_admin_{a.id}")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("adm_delete_admin_"))
async def adm_delete_admin(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    aid = int(callback.data.split("_")[-1])
    
    async with db.session_factory() as s:
        admin = await s.get(Admin, aid)
        if admin and admin.role != "super_admin":
            await s.delete(admin)
            await s.commit()
            await callback.answer(f"✅ Админ '{admin.name}' удалён!")
        else:
            await callback.answer("❌ Нельзя удалить супер-админа", show_alert=True)
    
    await adm_admins(callback, db)

@admin_router.callback_query(F.data == "adm_add_admin")
async def adm_add_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await state.set_state(AdminAddAdmin.waiting_user)
    await callback.message.edit_text("🔐 <b>НОВЫЙ АДМИН</b>\n\nВведите логин:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_admins")]]))
    await callback.answer()

@admin_router.message(StateFilter(AdminAddAdmin.waiting_user))
async def adm_add_admin_pass(message: Message, state: FSMContext):
    await state.update_data(adm_user=message.text.strip())
    await state.set_state(AdminAddAdmin.waiting_pass)
    await message.answer("Введите пароль:")

@admin_router.message(StateFilter(AdminAddAdmin.waiting_pass))
async def adm_add_admin_name(message: Message, state: FSMContext):
    await state.update_data(adm_pass=message.text.strip())
    await state.set_state(AdminAddAdmin.waiting_name)
    await message.answer("Введите имя:")

@admin_router.message(StateFilter(AdminAddAdmin.waiting_name))
async def adm_add_admin_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    username = data['adm_user']
    password = data['adm_pass']
    name = message.text.strip()
    
    admin = await db.create_admin(username, password, name)
    if admin:
        await message.answer(
            f"✅ Администратор <b>{name}</b> добавлен!\n\n"
            f"🔐 <b>Данные для входа:</b>\n"
            f"Логин: <code>{username}</code>\n"
            f"Пароль: <code>{password}</code>\n\n"
            f"⚠️ <i>Сохраните пароль! Он не хранится в открытом виде.</i>",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer("❌ Такой логин уже существует.", reply_markup=get_admin_menu())
    await state.clear()
class AdminSettings(StatesGroup):
    waiting_welcome_text = State()
    waiting_welcome_photo = State()
class AdminResetPassword(StatesGroup):
    waiting_new_password = State()

@admin_router.callback_query(F.data.startswith("adm_reset_password_"))
async def adm_reset_password_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    aid = int(callback.data.split("_")[-1])
    await state.update_data(reset_aid=aid)
    await state.set_state(AdminResetPassword.waiting_new_password)
    await callback.message.edit_text(
        "🔐 Введите <b>новый пароль</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_admins")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminResetPassword.waiting_new_password))
async def adm_reset_password_save(message: Message, state: FSMContext, db):
    data = await state.get_data()
    aid = data['reset_aid']
    new_password = message.text.strip()
    
    async with db.session_factory() as s:
        admin = await s.get(Admin, aid)
        if admin:
            h = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            admin.password_hash = h
            await s.commit()
            await message.answer(
                f"✅ Пароль для <b>{admin.name}</b> изменён!\n\n"
                f"🔐 Новый пароль: <code>{new_password}</code>",
                reply_markup=get_admin_menu()
            )
    
    await state.clear()
# В функцию get_admin_menu добавьте кнопку:
@admin_router.callback_query(F.data == "adm_settings")
async def adm_settings(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    welcome_text = await db.get_setting("welcome_text")
    welcome_photo = await db.get_setting("welcome_photo")
    
    text = "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n"
    text += f"📝 Приветствие: {'установлено' if welcome_text else 'по умолчанию'}\n"
    text += f"🖼️ Фото: {'установлено' if welcome_photo else 'нет'}\n"
    
    b = InlineKeyboardBuilder()
    b.button(text="📝 Изменить текст", callback_data="adm_edit_welcome_text")
    b.button(text="🖼️ Изменить фото", callback_data="adm_edit_welcome_photo")
    b.button(text="◀️ Назад", callback_data="adm_back")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "adm_edit_welcome_text")
async def adm_edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminSettings.waiting_welcome_text)
    await callback.message.edit_text(
        "📝 Введите <b>новый текст приветствия</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_settings")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminSettings.waiting_welcome_text))
async def adm_save_welcome_text(message: Message, state: FSMContext, db):
    await db.set_setting("welcome_text", message.text)
    await message.answer("✅ Текст приветствия обновлён!", reply_markup=get_admin_menu())
    await state.clear()

@admin_router.callback_query(F.data == "adm_edit_welcome_photo")
async def adm_edit_welcome_photo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminSettings.waiting_welcome_photo)
    await callback.message.edit_text(
        "🖼️ Отправьте <b>новое фото</b> для приветствия:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_settings")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminSettings.waiting_welcome_photo))
async def adm_save_welcome_photo(message: Message, state: FSMContext, db):
    if message.photo:
        photo_url = message.photo[-1].file_id
        await db.set_setting("welcome_photo", photo_url)
        await message.answer("✅ Фото приветствия обновлено!", reply_markup=get_admin_menu())
    else:
        await message.answer("❌ Отправьте фото!")
    await state.clear()
@admin_router.callback_query(F.data.startswith("adm_toggle_admin_"))
async def adm_toggle_admin(callback: CallbackQuery, db):
    if not is_admin(callback.from_user.id): return
    aid = int(callback.data.split("_")[-1])
    a = await db.toggle_admin(aid)
    if a: await callback.answer(f"{'Разблокирован' if a.is_active else 'Заблокирован'}: {a.name}"); await adm_admins(callback, db)

@admin_router.callback_query(F.data == "ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()
@admin_router.callback_query(F.data == "adm_edit_contact")
async def adm_edit_contact(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminEditInfo.waiting_contact)
    await callback.message.edit_text(
        "💬 Введите <b>username администратора</b> (без @):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_settings")]])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminEditInfo.waiting_contact))
async def adm_save_contact(message: Message, state: FSMContext, db):
    await db.set_setting("admin_contact", message.text.strip().replace("@", ""))
    await message.answer("✅ Контакт обновлён!", reply_markup=get_admin_menu())
    await state.clear()

@admin_router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminBroadcast.waiting_text)
    await callback.message.edit_text(
        "📢 <b>РАССЫЛКА</b>\n\n"
        "Введите текст сообщения, которое будет отправлено всем пользователям бота.\n"
        "Для отмены нажмите /start",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_back")]
        ])
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminBroadcast.waiting_text))
async def adm_broadcast_send(message: Message, state: FSMContext, db):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = message.text.strip()
    if not text:
        await message.answer("❌ Текст не может быть пустым.")
        return

    await state.clear()
    await message.answer("⏳ Начинаю рассылку...")

    users = await db.get_all_users()
    sent = 0
    blocked = 0

    for u in users:
        if not u.telegram_id:
            continue
        try:
            await message.bot.send_message(chat_id=u.telegram_id, text=text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked += 1

    await message.answer(
        f"✅ Рассылка завершена\n\n"
        f"📨 Отправлено: <b>{sent}</b>\n"
        f"🚫 Не доставлено: <b>{blocked}</b>",
        reply_markup=get_admin_menu()
    )