"""Админка: разделы записей, завершение, отмена и уведомления клиентам.

Разделы: предстоящие, прошедшие, завершённые.
Завершённые записи удаляются автоматически через сутки (cleanup_done_bookings).
"""

import logging
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, SERVICES
from database import (
    cleanup_done_bookings,
    delete_booking,
    get_admin_bookings,
    get_admin_stats,
    get_booking,
    mark_done,
)
from keyboards import (
    admin_booking_kb,
    admin_cancel_kb,
    admin_list_kb,
    admin_menu_kb,
)

logger = logging.getLogger(__name__)

router = Router()

TITLES = {
    "upcoming": "📅 Предстоящие записи",
    "past": "🕓 Прошедшие записи",
    "done": "✅ Завершённые записи",
}


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and user_id == ADMIN_ID


def _fmt_day(iso: str) -> str:
    """2026-10-23 -> 23.10.2026"""
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y")


def _menu_text(stats: dict) -> str:
    return (
        "🛠 <b>Админка</b>\n\n"
        f"Предстоящих: <b>{stats['upcoming']}</b> · "
        f"прошедших: <b>{stats['past']}</b> · "
        f"завершённых: <b>{stats['done']}</b>\n\n"
        "Выбери раздел:"
    )


def _list_text(rows, kind: str) -> str:
    if not rows:
        return f"{TITLES[kind]}\n\nЗаписей нет."
    lines = [f"{TITLES[kind]} ({len(rows)})", ""]
    for row in rows:
        uname = f"@{escape(row['username'])}" if row["username"] else "без username"
        lines.append(
            f"#{row['id']} · {_fmt_day(row['date'])} в {row['time']} — "
            f"{escape(row['service'])}\n"
            f"   {escape(row['full_name'])} ({uname})"
        )
    return "\n".join(lines)


def _card_text(booking) -> str:
    price = SERVICES.get(booking["service"])
    service = escape(booking["service"]) + (f" — {price} ₽" if price else "")
    uname = (
        f"@{escape(booking['username'])}" if booking["username"] else "без username"
    )
    lines = [
        f"📋 <b>Запись #{booking['id']}</b>",
        "",
        f"Услуга: {service}",
        f"Дата: <b>{_fmt_day(booking['date'])} в {booking['time']}</b>",
        f"Клиент: {escape(booking['full_name'])} ({uname})",
    ]
    if booking["status"] == "done":
        lines.append("Статус: ✅ Завершена")
        lines.append("")
        lines.append("Удалится автоматически через сутки после завершения.")
    else:
        lines.append("Статус: 🟢 Активна")
    return "\n".join(lines)


async def _notify_client(bot, booking) -> None:
    """Сообщает клиенту, что запись отменена администратором."""
    try:
        await bot.send_message(
            booking["user_id"],
            "❌ Твоя запись отменена администратором.\n\n"
            f"Было: {_fmt_day(booking['date'])} в {booking['time']} — "
            f"{escape(booking['service'])}.\n"
            "Если хочешь, выбери другое время: «Записаться».",
        )
    except Exception as exc:
        # клиент мог заблокировать бота — не роняем админку
        logger.warning("Не удалось уведомить клиента #%s: %s", booking["id"], exc)


@router.message(F.text == "Админка")
async def admin_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    removed = cleanup_done_bookings()
    if removed:
        logger.info("Автоочистка: удалено завершённых записей — %s", removed)

    stats = get_admin_stats()
    await message.answer(_menu_text(stats), reply_markup=admin_menu_kb(stats))


@router.callback_query(F.data == "adm:menu")
async def admin_menu_cb(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    stats = get_admin_stats()
    await callback.message.edit_text(_menu_text(stats), reply_markup=admin_menu_kb(stats))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:list:"))
async def admin_list(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    kind = callback.data.split(":")[2]
    if kind not in TITLES:
        await callback.answer("Раздел не найден", show_alert=True)
        return

    rows = get_admin_bookings(kind)
    await callback.message.edit_text(
        _list_text(rows, kind), reply_markup=admin_list_kb(rows, kind)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:view:"))
async def admin_view(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    _, _, raw_id, kind = callback.data.split(":")
    booking = get_booking(int(raw_id))
    if booking is None:
        await callback.answer("Запись не найдена", show_alert=True)
        rows = get_admin_bookings(kind)
        await callback.message.edit_text(
            _list_text(rows, kind), reply_markup=admin_list_kb(rows, kind)
        )
        return

    await callback.message.edit_text(
        _card_text(booking), reply_markup=admin_booking_kb(booking, kind)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:done:"))
async def admin_done(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    _, _, raw_id, kind = callback.data.split(":")
    booking_id = int(raw_id)
    if not mark_done(booking_id):
        await callback.answer("Запись уже завершена или удалена", show_alert=True)
        return

    booking = get_booking(booking_id)
    await callback.message.edit_text(
        _card_text(booking), reply_markup=admin_booking_kb(booking, kind)
    )
    await callback.answer("Завершено")


@router.callback_query(F.data.startswith("adm:cancel:"))
async def admin_cancel_ask(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    _, _, raw_id, kind = callback.data.split(":")
    booking = get_booking(int(raw_id))
    if booking is None:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        "❌ <b>Отменить запись?</b>\n\n"
        f"#{booking['id']} · {_fmt_day(booking['date'])} в {booking['time']} — "
        f"{escape(booking['service'])}\n"
        f"Клиент: {escape(booking['full_name'])}\n\n"
        "Клиент получит уведомление об отмене.",
        reply_markup=admin_cancel_kb(booking["id"], kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:del:"))
async def admin_cancel_do(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    _, _, raw_id, kind = callback.data.split(":")
    booking_id = int(raw_id)
    booking = get_booking(booking_id)
    if booking is None:
        await callback.answer("Запись уже удалена", show_alert=True)
        return

    delete_booking(booking_id)
    await _notify_client(callback.bot, booking)

    rows = get_admin_bookings(kind)
    await callback.message.edit_text(
        _list_text(rows, kind), reply_markup=admin_list_kb(rows, kind)
    )
    await callback.answer("Запись отменена")


@router.callback_query(F.data.startswith("del:"))
async def legacy_delete(callback: CallbackQuery) -> None:
    """Старые кнопки «🗑 Удалить» из сообщений предыдущей версии админки."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недоступно", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])
    booking = get_booking(booking_id)
    if booking is not None:
        delete_booking(booking_id)
        await _notify_client(callback.bot, booking)

    await callback.message.edit_text("🗑 Запись удалена.")
    await callback.answer("Удалено")

