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


# --- Админка ---


def _short_date(iso: str) -> str:
    """2026-10-23 -> 23.10"""
    return datetime.fromisoformat(iso).strftime("%d.%m")


def admin_menu_kb(stats: dict) -> InlineKeyboardMarkup:
    """Разделы админки со счётчиками записей."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📅 Предстоящие ({stats['upcoming']})",
                    callback_data="adm:list:upcoming",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🕓 Прошедшие ({stats['past']})",
                    callback_data="adm:list:past",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✅ Завершённые ({stats['done']})",
                    callback_data="adm:list:done",
                )
            ],
        ]
    )


def admin_list_kb(rows, kind: str) -> InlineKeyboardMarkup:
    """Список записей раздела: одна кнопка на запись + возврат."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"#{row['id']} · {_short_date(row['date'])} {row['time']} · {row['service']}",
                callback_data=f"adm:view:{row['id']}:{kind}",
            )
        ]
        for row in rows
    ]
    buttons.append(
        [InlineKeyboardButton(text="◀ В админку", callback_data="adm:menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_booking_kb(booking, kind: str) -> InlineKeyboardMarkup:
    """Кнопки карточки: завершить (для активной) и отменить запись."""
    buttons = []
    if booking["status"] == "active":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Завершить",
                    callback_data=f"adm:done:{booking['id']}:{kind}",
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"adm:cancel:{booking['id']}:{kind}",
                ),
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"adm:cancel:{booking['id']}:{kind}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="◀ К списку", callback_data=f"adm:list:{kind}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_cancel_kb(booking_id: int, kind: str) -> InlineKeyboardMarkup:
    """Подтверждение отмены записи админом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, отменить запись",
                    callback_data=f"adm:del:{booking_id}:{kind}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Нет, оставить",
                    callback_data=f"adm:view:{booking_id}:{kind}",
                )
            ],
        ]
    )
