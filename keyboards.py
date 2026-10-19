"""Все клавиатуры (кнопки) бота собраны здесь."""

from datetime import date, datetime, timedelta

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import DAYS_AHEAD, SERVICES, WORK_END, WORK_START


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню (кнопки внизу экрана)."""
    rows = [
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Прайс"), KeyboardButton(text="Мои записи")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="Админка")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def services_kb() -> InlineKeyboardMarkup:
    """Список услуг. В callback_data кладём номер услуги (svc:0, svc:1...)."""
    buttons = [
        [InlineKeyboardButton(text=f"{name} — {price} ₽", callback_data=f"svc:{i}")]
        for i, (name, price) in enumerate(SERVICES.items())
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dates_kb() -> InlineKeyboardMarkup:
    """Ближайшие дни для записи."""
    buttons = []
    today = date.today()
    for i in range(DAYS_AHEAD):
        day = today + timedelta(days=i)
        label = day.strftime("%d.%m")
        if i == 0:
            label += " (сегодня)"
        elif i == 1:
            label += " (завтра)"
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"date:{day.isoformat()}")]
        )
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def available_slots(taken: list[str], date_str: str) -> list[str]:
    """Свободные слоты на дату: убираем занятые и уже прошедшие (для сегодня)."""
    now = datetime.now()
    slots = []
    for hour in range(WORK_START, WORK_END + 1):
        slot = f"{hour:02d}:00"
        if slot in taken:
            continue
        # на сегодня не показываем часы, которые уже прошли
        if date_str == now.date().isoformat() and hour <= now.hour:
            continue
        slots.append(slot)
    return slots


def times_kb(slots: list[str]) -> InlineKeyboardMarkup:
    """Кнопки со свободными часами."""
    buttons = []
    row = []
    for slot in slots:
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time:{slot}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_kb() -> InlineKeyboardMarkup:
    """Кнопки подтверждения записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
        ]
    )
