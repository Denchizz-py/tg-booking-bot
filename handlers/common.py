"""Общие команды: /start, прайс, мои записи (с отменой) и подсказка на остальное."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_ID, SERVICES
from database import delete_booking, get_booking, get_user_bookings
from keyboards import main_menu

router = Router()


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and user_id == ADMIN_ID


def _fmt_day(iso: str) -> str:
    """2026-10-18 -> 18.10.2026"""
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Это бот записи. Выбери, что дальше:",
        reply_markup=main_menu(_is_admin(message.from_user.id)),
    )


@router.message(F.text == "Прайс")
async def cmd_price(message: Message) -> None:
    lines = [f"• {name} — {price} ₽" for name, price in SERVICES.items()]
    await message.answer("Наши услуги:\n" + "\n".join(lines))


@router.message(F.text == "Мои записи")
async def cmd_my_bookings(message: Message) -> None:
    rows = get_user_bookings(message.from_user.id)
    if not rows:
        await message.answer("У тебя пока нет записей. Нажми «Записаться» 🙂")
        return

    lines = []
    buttons = []
    for row in rows:
        day = _fmt_day(row["date"])
        lines.append(f"• {day} в {row['time']} — {row['service']}")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ Отменить: {day} {row['time']}",
                    callback_data=f"cancb:{row['id']}",
                )
            ]
        )
    await message.answer(
        "Твои записи:\n" + "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("cancb:"))
async def cancel_ask(callback: CallbackQuery) -> None:
    """Клиент нажал «Отменить» — спрашиваем подтверждение."""
    booking_id = int(callback.data.split(":")[1])
    booking = get_booking(booking_id)

    # отменять можно только свою запись
    if booking is None or booking["user_id"] != callback.from_user.id:
        await callback.answer("Эта запись не найдена", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, отменить", callback_data=f"cancy:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Нет, оставить", callback_data=f"cancn:{booking_id}"
                )
            ],
        ]
    )
    await callback.message.edit_text(
        "Точно отменить запись?\n\n"
        f"📌 {_fmt_day(booking['date'])} в {booking['time']} — {booking['service']}",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancy:"))
async def cancel_do(callback: CallbackQuery) -> None:
    """Подтверждённая отмена: удаляем запись и уведомляем админа."""
    booking_id = int(callback.data.split(":")[1])
    booking = get_booking(booking_id)

    if booking is None or booking["user_id"] != callback.from_user.id:
        await callback.answer("Эта запись не найдена", show_alert=True)
        return

    delete_booking(booking_id)
    await callback.message.edit_text("✅ Запись отменена. Ждём тебя в другой раз!")
    await callback.answer("Отменено")

    if ADMIN_ID:
        uname = f"@{booking['username']}" if booking["username"] else "без username"
        await callback.bot.send_message(
            ADMIN_ID,
            "❌ Клиент отменил запись\n"
            f"Клиент: {booking['full_name']} ({uname})\n"
            f"Услуга: {booking['service']}\n"
            f"Было: {_fmt_day(booking['date'])} в {booking['time']}",
        )


@router.callback_query(F.data.startswith("cancn:"))
async def cancel_no(callback: CallbackQuery) -> None:
    """Клиент передумал отменять — запись остаётся."""
    booking_id = int(callback.data.split(":")[1])
    booking = get_booking(booking_id)

    if booking is None:
        await callback.message.edit_text("Запись не найдена.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📌 {_fmt_day(booking['date'])} в {booking['time']} — {booking['service']}\n"
        "Запись остаётся в силе 👍"
    )
    await callback.answer()


@router.message(F.text)
async def fallback(message: Message) -> None:
    await message.answer("Не понял 🤔 Воспользуйся кнопками меню.")
