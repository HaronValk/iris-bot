from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.keyboards.client import (
    get_services_categories_keyboard, get_services_keyboard,
    get_masters_keyboard, get_month_calendar, get_confirmation_keyboard,
    get_main_menu
)
import re
import logging

logger = logging.getLogger(__name__)
booking_router = Router()

class BookingStates(StatesGroup):
    selecting_category = State()
    selecting_service = State()
    selecting_master = State()
    selecting_date = State()
    entering_time_manual = State()
    confirming = State()
    entering_promo = State()
    entering_name = State()
    entering_phone = State()

# ========== СТАРТ ЗАПИСИ ==========
@booking_router.callback_query(F.data == "start_booking")
async def start_booking_cb(callback: CallbackQuery, state: FSMContext, db):
    await callback.answer()
    await state.clear()
    cats = await db.get_categories()
    if not cats:
        await callback.message.answer("😔 Запись временно недоступна.")
        return
    await callback.message.answer("Выберите категорию:", reply_markup=get_services_categories_keyboard(cats))
    await state.set_state(BookingStates.selecting_category)

@booking_router.message(F.text == "📅 Записаться на процедуру")
async def start_booking_msg(message: Message, state: FSMContext, db):
    await state.clear()
    cats = await db.get_categories()
    if not cats:
        await message.answer("😔 Запись временно недоступна.")
        return
    await message.answer("Выберите категорию:", reply_markup=get_services_categories_keyboard(cats))
    await state.set_state(BookingStates.selecting_category)

@booking_router.callback_query(StateFilter(BookingStates.selecting_category), F.data.startswith("category_"))
async def select_service(callback: CallbackQuery, state: FSMContext, db):
    cid = int(callback.data.split("_")[1])
    svs = await db.get_services_by_category(cid)
    if not svs:
        await callback.answer("Нет услуг", show_alert=True)
        return
    await state.update_data(category_id=cid)
    await callback.message.edit_text("Выберите услугу:", reply_markup=get_services_keyboard(svs, cid))
    await state.set_state(BookingStates.selecting_service)
    await callback.answer()

@booking_router.callback_query(StateFilter(BookingStates.selecting_service), F.data.startswith("service_"))
async def select_master(callback: CallbackQuery, state: FSMContext, db):
    sid = int(callback.data.split("_")[1])
    sv = await db.get_service(sid)
    if not sv:
        await callback.answer("Не найдена", show_alert=True)
        return
    await state.update_data(service_id=sid, service_name=sv.name, service_price=sv.price)
    masters = await db.get_masters()
    await callback.message.edit_text(
        f"Вы выбрали: <b>{sv.name}</b>\n⏱ {sv.duration} мин | 💰 {int(sv.price)} ₽\n\nВыберите мастера:",
        reply_markup=get_masters_keyboard(masters)
    )
    await state.set_state(BookingStates.selecting_master)
    await callback.answer()

@booking_router.callback_query(StateFilter(BookingStates.selecting_master), F.data.startswith("master_"))
async def select_date(callback: CallbackQuery, state: FSMContext, db, config):
    mid = int(callback.data.split("_")[1])
    if mid > 0:
        m = await db.get_master(mid)
        await state.update_data(master_id=mid, master_name=m.name)
    else:
        await state.update_data(master_id=None, master_name="Любой мастер")
    today = datetime.now().date()
    max_date = today + timedelta(days=config.MAX_DAYS_BOOKING)
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=get_month_calendar(today.year, today.month, end_date=max_date)
    )
    await state.set_state(BookingStates.selecting_date)
    await callback.answer()

# Навигация по календарю (перерисовываем сообщение)
@booking_router.callback_query(StateFilter(BookingStates.selecting_date), F.data.startswith("cal_prev_"))
async def cal_prev(callback: CallbackQuery, config):
    parts = callback.data.split("_")
    year, month = int(parts[2]), int(parts[3])
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    max_date = datetime.now().date() + timedelta(days=config.MAX_DAYS_BOOKING)
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=get_month_calendar(year, month, end_date=max_date)
    )
    await callback.answer()

@booking_router.callback_query(StateFilter(BookingStates.selecting_date), F.data.startswith("cal_next_"))
async def cal_next(callback: CallbackQuery, config):
    parts = callback.data.split("_")
    year, month = int(parts[2]), int(parts[3])
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    max_date = datetime.now().date() + timedelta(days=config.MAX_DAYS_BOOKING)
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=get_month_calendar(year, month, end_date=max_date)
    )
    await callback.answer()

@booking_router.callback_query(F.data == "cal_ignore")
async def cal_ignore(callback: CallbackQuery):
    await callback.answer()

# Выбор даты → запрос времени вручную
@booking_router.callback_query(StateFilter(BookingStates.selecting_date), F.data.startswith("date_"))
async def date_selected(callback: CallbackQuery, state: FSMContext, db):
    ds = callback.data.split("_")[1]
    dt = datetime.strptime(ds, "%Y-%m-%d").date()
    if dt < datetime.now().date():
        await callback.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
        return
    await state.update_data(date=ds)
    data = await state.get_data()
    sv = await db.get_service(data['service_id'])
    await callback.message.edit_text(
        f"📅 Выбрана дата: <b>{dt.strftime('%d.%m.%Y')}</b>\n"
        f"💆 {sv.name} ({sv.duration} мин)\n\n"
        "⏰ Введите <b>удобное время</b> в формате ЧЧ:ММ (например, 10:00):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_date")]
        ])
    )
    await state.set_state(BookingStates.entering_time_manual)
    await callback.answer()

# Ручной ввод времени с валидацией
@booking_router.message(StateFilter(BookingStates.entering_time_manual))
async def process_time_input(message: Message, state: FSMContext, db, config):
    text = message.text.strip()
    if not re.match(r'^\d{2}:\d{2}$', text):
        await message.answer("❌ Неверный формат. Введите время как 10:00 или 14:30:")
        return
    hours, minutes = text.split(':')
    try:
        h, m = int(hours), int(minutes)
        if h < 0 or h > 23 or m < 0 or m > 59:
            raise ValueError
    except:
        await message.answer("❌ Некорректное время. Введите ещё раз (ЧЧ:ММ):")
        return
    if h < config.WORK_START_HOUR or h >= config.WORK_END_HOUR:
        await message.answer(
    f"❌ Мы работаем с {config.WORK_START_HOUR}:00 до {config.WORK_END_HOUR}:00. Выберите другое время:"
)
        return

    data = await state.get_data()
    selected_date = data['date']
    service = await db.get_service(data['service_id'])
    master_id = data.get('master_id')

    available = await db.is_time_available(selected_date, text, service.duration, master_id)
    if not available:
        await message.answer("❌ Это время занято. Попробуйте другое:")
        return

    await state.update_data(time=text)
    df = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    await message.answer(
        f"📋 <b>ПРОВЕРЬТЕ:</b>\n\n"
        f"💆 {data['service_name']}\n"
        f"👤 {data['master_name']}\n"
        f"📅 {df}\n"
        f"⏰ {text}\n"
        f"💰 {int(data['service_price'])} ₽\n\n"
        "Всё верно?",
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(BookingStates.confirming)

# Назад к календарю
@booking_router.callback_query(F.data == "back_to_date")
async def back_to_date(callback: CallbackQuery, state: FSMContext, config):
    today = datetime.now().date()
    max_date = today + timedelta(days=config.MAX_DAYS_BOOKING)
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=get_month_calendar(today.year, today.month, end_date=max_date)
    )
    await state.set_state(BookingStates.selecting_date)
    await callback.answer()

# ========== ПОДТВЕРЖДЕНИЕ И ФИНАЛИЗАЦИЯ ==========
@booking_router.callback_query(StateFilter(BookingStates.confirming), F.data == "confirm_yes")
async def ask_promo(callback: CallbackQuery, state: FSMContext, db):
    u = await db.get_user(callback.from_user.id)
    if u and u.name and u.phone:
        await state.update_data(client_name=u.name, client_phone=u.phone)
    await callback.message.edit_text(
        "🎁 Если у вас есть <b>промокод</b>, введите его сейчас\nили нажмите <b>Пропустить</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Пропустить", callback_data="skip_promo")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_date")]
        ])
    )
    await state.set_state(BookingStates.entering_promo)
    await callback.answer()

@booking_router.callback_query(F.data == "skip_promo")
async def skip_promo(callback: CallbackQuery, state: FSMContext, db, notif_service, config):
    u = await db.get_user(callback.from_user.id)
    if u and u.name and u.phone:
        await state.update_data(client_name=u.name, client_phone=u.phone)
        await finalize_booking(callback, state, db, notif_service, config)
        return
    await callback.message.edit_text("📝 Введите ваше <b>имя и фамилию</b>:")
    await state.set_state(BookingStates.entering_name)
    await callback.answer()

@booking_router.message(StateFilter(BookingStates.entering_promo))
async def process_promo(message: Message, state: FSMContext, db, notif_service, config):
    promo_code = message.text.strip().upper()
    promos = await db.get_active_promotions()
    valid_promo = None
    for p in promos:
        if p.promo_code and p.promo_code.upper() == promo_code:
            valid_promo = p
            break
    if valid_promo:
        discount = valid_promo.discount_percent or 0
        await state.update_data(promo_code=promo_code, discount=discount)
        await message.answer(f"✅ Промокод <code>{promo_code}</code> принят!\n💰 Скидка: <b>{discount}%</b>")
    else:
        await state.update_data(promo_code=None, discount=0)
        await message.answer("❌ Промокод не найден. Продолжаем без скидки.")
    u = await db.get_user(message.from_user.id)
    if u and u.name and u.phone:
        await state.update_data(client_name=u.name, client_phone=u.phone)
        await finalize_booking(message, state, db, notif_service, config)
        return
    await message.answer("📝 Введите ваше <b>имя и фамилию</b>:")
    await state.set_state(BookingStates.entering_name)

@booking_router.message(StateFilter(BookingStates.entering_name))
async def ask_phone(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Имя слишком короткое.")
        return
    await state.update_data(client_name=name)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("📞 Отправьте номер телефона:", reply_markup=kb)
    await state.set_state(BookingStates.entering_phone)

@booking_router.message(StateFilter(BookingStates.entering_phone))
async def finalize_from_phone(message: Message, state: FSMContext, db, notif_service, config):
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    elif message.text:
        phone = ''.join(filter(str.isdigit, message.text))
    else:
        await message.answer("❌ Не удалось получить номер.")
        return
    if len(phone) < 10:
        await message.answer("❌ Минимум 10 цифр.")
        return
    await state.update_data(client_phone=phone)
    await finalize_booking(message, state, db, notif_service, config)

async def finalize_booking(event, state: FSMContext, db, notif_service=None, config=None):
    data = await state.get_data()
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    discount = data.get('discount', 0)
    price = int(data['service_price'])
    final_price = price
    if discount > 0:
        final_price = int(price * (1 - discount / 100))
    app = await db.create_appointment(
        event.from_user.id, data['service_id'],
        f"{data['date']} {data['time']}",
        data['client_name'], data['client_phone'],
        data.get('master_id'), data.get('promo_code')
    )
    if not app:
        await msg.answer("❌ Ошибка при создании записи.")
        return
    df = datetime.strptime(data['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
    addr = config.SALON_ADDRESS if config else 'г. Москва'
    price_text = f"💰 {price} ₽"
    if discount > 0:
        price_text += f" → <b>{final_price} ₽</b> (скидка {discount}%)"
    await msg.answer(
        f"✅ <b>ЗАПИСЬ ПОДТВЕРЖДЕНА!</b>\n\n"
        f"💆 {data['service_name']}\n"
        f"👤 {data['master_name']}\n"
        f"📅 {df}\n"
        f"⏰ {data['time']}\n"
        f"{price_text}\n\n"
        f"📍 {addr}\n\nСпасибо! 🌸",
        reply_markup=get_main_menu()
    )
    if notif_service and config and config.ADMIN_CHAT_ID:
        await notif_service.notify_new_appointment(app, config.ADMIN_CHAT_ID)
    await db.save_user(event.from_user.id, event.from_user.username, data['client_name'], phone=data['client_phone'])
    await state.clear()

# Навигация
@booking_router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext, db):
    await state.clear()
    cats = await db.get_categories()
    await callback.message.edit_text("Выберите категорию:", reply_markup=get_services_categories_keyboard(cats))
    await state.set_state(BookingStates.selecting_category)
    await callback.answer()

@booking_router.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.selecting_service)
    await callback.answer()