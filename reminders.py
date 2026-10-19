"""Фоновые напоминания клиентам: за день до записи.

Запускается из bot.py как фоновая задача и проверяет базу каждые 30 минут.
Каждому клиенту напоминание уходит один раз (флаг reminded в базе).
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from config import REMIND_AFTER_HOUR
from database import get_pending_reminders, mark_reminded

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30 * 60  # проверять каждые 30 минут


async def reminder_loop(bot: Bot) -> None:
    """Каждые 30 минут рассылает напоминания о завтрашних записях."""
    while True:
        try:
            now = datetime.now()
            # напоминания уходят не раньше REMIND_AFTER_HOUR (например, с 9 утра)
            if now.hour >= REMIND_AFTER_HOUR:
                tomorrow = (now + timedelta(days=1)).date().isoformat()
                for booking in get_pending_reminders(tomorrow):
                    try:
                        await bot.send_message(
                            booking["user_id"],
                            "🔔 Напоминание о записи\n\n"
                            f"Завтра в {booking['time']} — {booking['service']}.\n"
                            "Если планы изменились, отмени запись: «Мои записи».",
                        )
                        mark_reminded(booking["id"])
                    except Exception as exc:
                        # например, пользователь заблокировал бота — не роняем цикл
                        logger.warning(
                            "Не удалось отправить напоминание #%s: %s",
                            booking["id"],
                            exc,
                        )
        except Exception:
            logger.exception("Ошибка в цикле напоминаний")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
