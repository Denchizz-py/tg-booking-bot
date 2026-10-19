"""Работа с базой данных SQLite.

Файл data.db создаётся автоматически при первом запуске.
Ничего устанавливать не нужно — SQLite встроена в Python.
"""

import sqlite3

DB_PATH = "data.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы обращаться к полям по имени
    return conn


def init_db() -> None:
    """Создаёт таблицу записей, если её ещё нет, и обновляет схему."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reminded INTEGER NOT NULL DEFAULT 0,
            UNIQUE (date, time)
        )
        """
    )
    # Миграция для баз, созданных старой версией бота: добавляем колонку reminded
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(bookings)")]
    if "reminded" not in columns:
        conn.execute(
            "ALTER TABLE bookings ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
    conn.close()


def add_booking(user_id, username, full_name, service, date_str, time_str) -> bool:
    """Добавляет запись. Возвращает False, если слот уже занят."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO bookings (user_id, username, full_name, service, date, time) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, service, date_str, time_str),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Слот уже занят (сработало ограничение UNIQUE по дате и времени)
        return False
    finally:
        conn.close()


def get_taken_slots(date_str: str) -> list[str]:
    """Список занятых часов на конкретную дату."""
    conn = _connect()
    rows = conn.execute(
        "SELECT time FROM bookings WHERE date = ?", (date_str,)
    ).fetchall()
    conn.close()
    return [row["time"] for row in rows]


def get_user_bookings(user_id: int):
    """Все записи конкретного пользователя."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY date, time", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_all_bookings():
    """Все записи (для админа)."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM bookings ORDER BY date, time").fetchall()
    conn.close()
    return rows


def delete_booking(booking_id: int) -> None:
    """Удаляет запись по её номеру."""
    conn = _connect()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()


def get_booking(booking_id: int):
    """Одна запись по её номеру (или None, если не найдена)."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM bookings WHERE id = ?", (booking_id,)
    ).fetchone()
    conn.close()
    return row


def get_pending_reminders(date_str: str):
    """Записи на указанную дату, по которым ещё не отправлено напоминание."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM bookings WHERE date = ? AND reminded = 0", (date_str,)
    ).fetchall()
    conn.close()
    return rows


def mark_reminded(booking_id: int) -> None:
    """Помечает, что напоминание по записи уже отправлено."""
    conn = _connect()
    conn.execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
