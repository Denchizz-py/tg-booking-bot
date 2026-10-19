"""Пошаговый процесс записи (FSM — конечный автомат).

Логика: услуга → дата → время → подтверждение → сохранение в базу.
"""

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, SERVICES
from database import add_booking, get_taken_slots
from keyboards import available_slots, confirm_kb, dates_kb, services_kb, times_kb

router = Router()


class Booking(StatesGroup):
    """Шаги, на которых находится пользователь во время записи."""

    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


def _fmt_date(iso: str) -> str:
    """2026-10-14 -> 14.10.2026"""
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y")


@router.message(F.text == "Записаться")
async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Booking.choosing_service)
    await message.answer("Выбери услугу:", reply_markup=services_kb())


@router.callback_query(Booking.choosing_service, F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    index = int(callback.data.split(":")[1])
    service = list(SERVICES.keys())[index]
    await state.update_data(service=service)
    await state.set_state(Booking.choosing_date)
    await callback.message.edit_text(
        f"Услуга: <b>{service}</b>\n\nВыбери день:",
        reply_markup=dates_kb(),
    )
    await callback.answer()


@router.callback_query(Booking.choosing_date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext) -> None:
    date_str = callback.data.split(":")[1]
    taken = get_taken_slots(date_str)
    slots = available_slots(taken, date_str)

    if not slots:
        # на этот день свободного времени не осталось — предлагаем другой день
        await callback.answer(
            "На этот день свободного времени не осталось", show_alert=True
        )
        return

    await state.update_data(date=date_str)
    await state.set_state(Booking.choosing_time)
    await callback.message.edit_text(
        f"День: <b>{_fmt_date(date_str)}</b>\n\nВыбери время:",
        reply_markup=times_kb(slots),
    )
    await callback.answer()


@router.callback_query(Booking.choosing_time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext) -> None:
    # split(":", 1) — делим только по ПЕРВОМУ двоеточию,
    # иначе "time:16:00" разобьётся на части и потеряется ":00".
    time_str = callback.data.split(":", 1)[1]
    await state.update_data(time=time_str)
    data = await state.get_data()
    await state.set_state(Booking.confirming)
    await callback.message.edit_text(
        "Проверь запись:\n\n"
        f"Услуга: <b>{data['service']}</b>\n"
        f"Дата: <b>{_fmt_date(data['date'])}</b>\n"
        f"Время: <b>{time_str}</b>\n\n"
        "Всё верно?",
        reply_markup=confirm_kb(),
    )
    await callback.answer()


@router.callback_query(Booking.confirming, F.data == "confirm")
async def do_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user = callback.from_user

    ok = add_booking(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        service=data["service"],
        date_str=data["date"],
        time_str=data["time"],
    )
    await state.clear()

    if not ok:
        await callback.message.edit_text(
            "😔 Это время только что заняли. Запишись ещё раз — выбери другое."
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Готово, ты записан!\n\n"
        f"Услуга: <b>{data['service']}</b>\n"
        f"Дата: <b>{_fmt_date(data['date'])}</b>\n"
        f"Время: <b>{data['time']}</b>"
    )
    await callback.answer("Записал!")

    # Уведомляем админа о новой записи
    if ADMIN_ID:
        uname = f"@{user.username}" if user.username else "без username"
        await callback.bot.send_message(
            ADMIN_ID,
            "🔔 Новая запись!\n"
            f"Клиент: {user.full_name} ({uname})\n"
            f"Услуга: {data['service']}\n"
            f"Дата: {_fmt_date(data['date'])} в {data['time']}",
        )


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено. Возвращайся, когда будешь готов 🙂")
    await callback.answer()
