"""Настройки бота. Всё, что часто меняется, живёт здесь."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Секреты из .env ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL") or None

# ID админа (кому показывать админку). Узнать свой ID можно у @userinfobot.
_admin = (os.getenv("ADMIN_ID") or "").strip()
ADMIN_ID = int(_admin) if _admin.isdigit() else None

# --- Услуги и цены (меняй под любой бизнес) ---
SERVICES = {
    "Стрижка": 1000,
    "Стрижка + борода": 1500,
    "Борода": 700,
    "Окрашивание": 2500,
}

# --- График работы ---
WORK_START = 10  # первый слот, час
WORK_END = 19  # последний слот, час
DAYS_AHEAD = 5  # на сколько дней вперёд можно записаться

# --- Напоминания ---
REMIND_AFTER_HOUR = 9  # напоминания о завтрашних записях уходят начиная с этого часа
