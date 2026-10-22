"""Работа с базой данных SQLite.

Файл data.db создаётся автоматически при первом запуске.
Ничего устанавливать не нужно — SQLite встроена в Python.
"""

import sqlite3
from datetime import date

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
            status TEXT NOT NULL DEFAULT 'active',
            done_at TEXT,
            UNIQUE (date, time)
        )
        """
    )
    # Миграции для баз, созданных старыми версиями бота
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)")}
    if "reminded" not in columns:
        conn.execute(
            "ALTER TABLE bookings ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0"
        )
    if "status" not in columns:
        conn.execute(
            "ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
        )
    if "done_at" not in columns:
        conn.execute("ALTER TABLE bookings ADD COLUMN done_at TEXT")
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
    """Актуальные записи пользователя: только предстоящие и не завершённые."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM bookings "
        "WHERE user_id = ? AND status = 'active' AND date >= ? "
        "ORDER BY date, time",
        (user_id, date.today().isoformat()),
    ).fetchall()
    conn.close()
    return rows


def get_admin_bookings(kind: str):
    """Записи для раздела админки: upcoming, past или done."""
    today = date.today().isoformat()
    conn = _connect()
    if kind == "upcoming":
        rows = conn.execute(
            "SELECT * FROM bookings WHERE status = 'active' AND date >= ? "
            "ORDER BY date, time",
            (today,),
        ).fetchall()
    elif kind == "past":
        rows = conn.execute(
            "SELECT * FROM bookings WHERE status = 'active' AND date < ? "
            "ORDER BY date DESC, time DESC",
            (today,),
        ).fetchall()
    elif kind == "done":
        rows = conn.execute(
            "SELECT * FROM bookings WHERE status = 'done' "
            "ORDER BY done_at DESC, date DESC, time DESC"
        ).fetchall()
    else:
        conn.close()
        raise ValueError(f"Неизвестный раздел админки: {kind}")
    conn.close()
    return rows


def get_admin_stats() -> dict:
    """Количество записей по разделам админки."""
    today = date.today().isoformat()
    conn = _connect()
    row = conn.execute(
        "SELECT "
        "SUM(CASE WHEN status = 'active' AND date >= ? THEN 1 ELSE 0 END) AS upcoming, "
        "SUM(CASE WHEN status = 'active' AND date < ? THEN 1 ELSE 0 END) AS past, "
        "SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done "
        "FROM bookings",
        (today, today),
    ).fetchone()
    conn.close()
    return {
        "upcoming": row["upcoming"] or 0,
        "past": row["past"] or 0,
        "done": row["done"] or 0,
    }


def delete_booking(booking_id: int) -> None:
    """Удаляет запись по её номеру."""
    conn = _connect()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()


def mark_done(booking_id: int) -> bool:
    """Помечает запись завершённой. False — если она уже не активна."""
    conn = _connect()
    cursor = conn.execute(
        "UPDATE bookings SET status = 'done', done_at = CURRENT_TIMESTAMP "
        "WHERE id = ? AND status = 'active'",
        (booking_id,),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def cleanup_done_bookings(days: int = 1) -> int:
    """Удаляет завершённые записи, помеченные больше `days` дней назад."""
    conn = _connect()
    cursor = conn.execute(
        "DELETE FROM bookings "
        "WHERE status = 'done' AND done_at IS NOT NULL "
        "AND done_at <= datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    removed = cursor.rowcount
    conn.close()
    return removed


def get_booking(booking_id: int):
    """Одна запись по её номеру (или None, если не найдена)."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM bookings WHERE id = ?", (booking_id,)
    ).fetchone()
    conn.close()
    return row


def get_pending_reminders(date_str: str):
    """Активные записи на указанную дату без отправленного напоминания."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM bookings "
        "WHERE date = ? AND reminded = 0 AND status = 'active'",
        (date_str,),
    ).fetchall()
    conn.close()
    return rows


def mark_reminded(booking_id: int) -> None:
    """Помечает, что напоминание по записи уже отправлено."""
    conn = _connect()
    conn.execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
