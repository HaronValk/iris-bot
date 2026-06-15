from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import calendar

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Записаться на процедуру")],
        [KeyboardButton(text="💆 Услуги и цены"), KeyboardButton(text="👤 Наши мастера")],
        [KeyboardButton(text="🎁 Акции и скидки")],
        [KeyboardButton(text="📍 Адрес и время работы"), KeyboardButton(text="📞 Связаться с администратором")],
        [KeyboardButton(text="📋 Мои записи")],
    ], resize_keyboard=True, input_field_placeholder="Выберите действие...")

def get_services_categories_keyboard(categories):
    b = InlineKeyboardBuilder()
    for c in categories:
        if c.is_active:
            b.button(text=f"{c.icon} {c.name}", callback_data=f"category_{c.id}")
    b.button(text="◀️ Назад", callback_data="main_menu")
    b.adjust(1)
    return b.as_markup()

def get_services_keyboard(services, category_id):
    b = InlineKeyboardBuilder()
    for s in services:
        if s.is_active:
            b.button(text=f"{s.name} — {int(s.price)}₽", callback_data=f"service_{s.id}")
    b.button(text="📅 Записаться", callback_data="start_booking")
    b.button(text="◀️ К категориям", callback_data="back_to_categories")
    b.adjust(1)
    return b.as_markup()

def get_masters_keyboard(masters):
    b = InlineKeyboardBuilder()
    for m in masters:
        b.button(text=f"👤 {m.name}", callback_data=f"master_{m.id}")
    b.button(text="👤 Без предпочтений", callback_data="master_0")
    b.button(text="◀️ Назад", callback_data="back_to_services")
    b.adjust(1)
    return b.as_markup()

def get_month_calendar(year: int, month: int, selected_date: str = None, end_date=None):
    """Календарь на месяц. Даты позже end_date помечаются ❌ (недоступны)."""
    b = InlineKeyboardBuilder()
    mn = ["Январь","Февраль","Март","Апрель","Май","Июнь",
          "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    b.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(text=f"{mn[month-1]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_next_{year}_{month}")
    )

    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()
    # Если end_date не задан, берём от today + MAX_DAYS_BOOKING (или просто большое число)
    # но мы будем получать его из booking.py

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
            else:
                dt = datetime(year, month, day).date()
                # Проверка: прошедшая дата или дальше ограничения
                if dt < today or (end_date and dt > end_date):
                    row.append(InlineKeyboardButton(text="❌", callback_data="cal_ignore"))
                else:
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str == selected_date:
                        row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"date_{date_str}"))
                    else:
                        row.append(InlineKeyboardButton(text=str(day), callback_data=f"date_{date_str}"))
        b.row(*row)

    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters"))
    return b.as_markup()

def get_confirmation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, записаться", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="🔄 Изменить", callback_data="back_to_date")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
    ])