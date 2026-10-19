"""Админка: просмотр и удаление записей. Доступна только админу."""

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_ID
from database import delete_booking, get_all_bookings

router = Router()


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and user_id == ADMIN_ID


@router.message(F.text == "Админка")
async def admin_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    rows = get_all_bookings()
    if not rows:
        await message.answer("Записей пока нет.")
        return

    await message.answer(f"📋 Всего записей: <b>{len(rows)}</b>")
    for row in rows:
        uname = f"@{row['username']}" if row["username"] else "без username"
        text = (
            f"#{row['id']} — {row['date']} в {row['time']}\n"
            f"Услуга: {row['service']}\n"
            f"Клиент: {row['full_name']} ({uname})"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{row['id']}")]
            ]
        )
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("del:"))
async def delete_cb(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])
    delete_booking(booking_id)
    await callback.message.edit_text("🗑 Запись удалена.")
    await callback.answer("Удалено")
