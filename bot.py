"""Бот записи на aiogram 3.

Запуск: python bot.py
Настройки и секреты — в config.py и .env.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, PROXY_URL
from database import init_db
from handlers import admin, booking, common
from reminders import reminder_loop

# Диспетчер и порядок обработчиков.
# booking и admin идут первыми, common (с общей подсказкой) — последним.
dp = Dispatcher()
dp.include_router(booking.router)
dp.include_router(admin.router)
dp.include_router(common.router)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise SystemExit(
            "Ошибка: токен не найден.\n"
            "Открой файл .env и вставь токен после BOT_TOKEN="
        )

    init_db()  # создаём базу данных при старте

    bot = Bot(token=BOT_TOKEN, session=AiohttpSession(proxy=PROXY_URL))
    print("Бот записи запущен. Нажми Ctrl+C, чтобы остановить.")
    asyncio.create_task(reminder_loop(bot))  # фоновые напоминания клиентам
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())