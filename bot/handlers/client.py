from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.keyboards.client import *
from datetime import datetime
client_router = Router()

@client_router.message(Command("start"))
async def cmd_start(message: Message, db, config, state: FSMContext):
    await state.clear()
    await db.save_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    
    # Получаем настройки приветствия
    welcome_text = await db.get_setting("welcome_text")
    welcome_photo = await db.get_setting("welcome_photo")
    
    if not welcome_text:
        welcome_text = f"🌸 Добро пожаловать в <b>{config.SALON_NAME}</b>!\n\nЯ помогу вам записаться на процедуру, расскажу об услугах и отвечу на вопросы.\n\nЧем могу помочь?"
    
    if welcome_photo:
        try:
            await message.answer_photo(welcome_photo, caption=welcome_text, reply_markup=get_main_menu())
        except:
            await message.answer(welcome_text, reply_markup=get_main_menu())
    else:
        await message.answer(welcome_text, reply_markup=get_main_menu())

@client_router.message(F.text == "💆 Услуги и цены")
async def show_services(message: Message, db):
    cats = await db.get_categories()
    if not cats:
        await message.answer("😔 Услуги временно недоступны.")
        return
    await message.answer("✨ <b>Наши услуги:</b>\n\nВыберите категорию:", reply_markup=get_services_categories_keyboard(cats))

@client_router.callback_query(F.data.startswith("category_"))
async def show_category(callback: CallbackQuery, db):
    cid = int(callback.data.split("_")[1])
    svs = await db.get_services_by_category(cid)
    cat = await db.get_category(cid)
    if not svs:
        await callback.answer("Услуги не найдены", show_alert=True)
        return
    
    text = f"<b>{cat.icon} {cat.name}</b>\n\n"
    for s in svs:
        text += f"• <b>{s.name}</b>\n"
        text += f"  ⏱ {s.duration} мин | 💰 {int(s.price)} ₽"
        if s.description:
            text += f"\n  📝 {s.description}"
        text += "\n\n"
    
    text += "Выберите услугу для записи:"
    await callback.message.edit_text(text, reply_markup=get_services_keyboard(svs, cid))
    await callback.answer()

@client_router.callback_query(F.data == "back_to_categories")
async def back_to_cats(callback: CallbackQuery, db):
    cats = await db.get_categories()
    await callback.message.edit_text("✨ <b>Наши услуги:</b>\n\nВыберите категорию:", reply_markup=get_services_categories_keyboard(cats))
    await callback.answer()

@client_router.message(F.text == "👤 Наши мастера")
async def show_masters(message: Message, db):
    masters = await db.get_all_masters()
    if not masters:
        await message.answer("😔 Информация о мастерах временно недоступна.")
        return
    for m in masters:
        if not m.is_active:
            continue
        text = f"👤 <b>{m.name}</b>\n"
        if m.specialization:
            text += f"📝 {m.specialization}\n"
        if m.photo_url:
            try:
                await message.answer_photo(m.photo_url, caption=text)
            except:
                await message.answer(text)
        else:
            await message.answer(text)

@client_router.message(F.text == "🎁 Акции и скидки")
async def show_promos(message: Message, db):
    promos = await db.get_active_promotions()
    if not promos:
        await message.answer("🎁 На данный момент акций нет.")
        return
    text = "🎁 <b>ДЕЙСТВУЮЩИЕ АКЦИИ:</b>\n\n"
    for p in promos:
        text += f"<b>{p.title}</b>\n"
        if p.description: text += f"{p.description}\n"
        if p.discount_percent: text += f"💰 Скидка: {p.discount_percent}%\n"
        if p.promo_code: text += f"🔑 Промокод: <code>{p.promo_code}</code>\n"
        text += "\n"
    await message.answer(text)

@client_router.message(F.text == "📍 Адрес и время работы")
async def show_info(message: Message, config):
    text = (
        f"📍 <b>{config.SALON_NAME}</b>\n\n"
        f"🏠 <b>Адрес:</b> {config.SALON_ADDRESS}\n\n"
        f"🕐 <b>Режим работы:</b>\n{config.SALON_WORK_HOURS}\n\n"
        f"📞 <b>Телефон:</b> {config.SALON_PHONE}"
    )
    
    buttons = []
    if config.SALON_MAP_URL:
        buttons.append([InlineKeyboardButton(text="🗺️ Открыть на карте", url=config.SALON_MAP_URL)])
    if config.SALON_SITE_URL:
        buttons.append([InlineKeyboardButton(text="🌐 Наш сайт", url=config.SALON_SITE_URL)])
    
    if buttons:
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await message.answer(text)

@client_router.message(F.text == "📞 Связаться с администратором")
async def contact_admin(message: Message, config, db):
    text = "📞 <b>Связь с администратором:</b>\n\nВыберите удобный способ:"
    
    # Получаем контакты из настроек БД или из .env
    phone = await db.get_setting("salon_phone") or config.SALON_PHONE
    admin_contact = await db.get_setting("admin_contact") or "gotohellbro"
    
    buttons = []
    buttons.append([InlineKeyboardButton(text="📞 Позвонить", callback_data="call_admin")])
    buttons.append([InlineKeyboardButton(text="💬 Написать в Telegram", url=f"https://t.me/{admin_contact}")])
    buttons.append([InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@client_router.callback_query(F.data == "call_admin")
async def call_admin(callback: CallbackQuery, config, db):
    phone = await db.get_setting("salon_phone") or config.SALON_PHONE
    await callback.answer()
    await callback.message.answer(
        f"📞 <b>Позвоните нам:</b>\n\n<code>{phone}</code>\n\nСкопируйте номер и позвоните!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ])
    )
@client_router.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message, db, state: FSMContext):
    await state.clear()
    apps = await db.get_user_appointments(message.from_user.id)
    if not apps:
        await message.answer("📋 У вас пока нет записей.")
        return
    now = datetime.now()
    upcoming = [a for a in apps if a.datetime > now]
    if not upcoming:
        await message.answer("📋 Нет предстоящих записей.")
        return
    text = "📋 <b>ВАШИ ЗАПИСИ:</b>\n\n"
    for a in upcoming[:10]:
        sv = a.service.name if a.service else '—'
        text += f"📌 <b>{sv}</b>\n📅 {a.datetime.strftime('%d.%m.%Y %H:%M')}\n💰 {int(a.service.price) if a.service else 0} ₽\n\n"
    await message.answer(text)

@client_router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🏠 Главное меню:", reply_markup=get_main_menu())
    await callback.answer()