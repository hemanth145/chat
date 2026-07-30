import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS vendors (
    phone TEXT PRIMARY KEY,
    name TEXT,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_phone TEXT NOT NULL,
    call_sid TEXT,
    transcript TEXT NOT NULL,
    summary TEXT,
    important INTEGER DEFAULT 0,
    escalated INTEGER DEFAULT 0,
    escalation_reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (vendor_phone) REFERENCES vendors(phone)
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def get_or_create_vendor(phone: str) -> sqlite3.Row:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE phone = ?", (phone,)).fetchone()
        if row:
            return row
        conn.execute(
            "INSERT INTO vendors (phone, name, created_at) VALUES (?, ?, ?)",
            (phone, None, datetime.now(timezone.utc).isoformat()),
        )
        return conn.execute("SELECT * FROM vendors WHERE phone = ?", (phone,)).fetchone()


def recent_calls_for_vendor(phone: str, limit: int = 3) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM calls WHERE vendor_phone = ? ORDER BY id DESC LIMIT ?",
            (phone, limit),
        ).fetchall()


def set_vendor_name(phone: str, name: str):
    with _connect() as conn:
        conn.execute("UPDATE vendors SET name = ? WHERE phone = ?", (name, phone))


def save_call(
    vendor_phone: str,
    call_sid: str,
    transcript: str,
    summary: str,
    important: bool,
    escalated: bool,
    escalation_reason: str | None,
):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO calls
               (vendor_phone, call_sid, transcript, summary, important, escalated, escalation_reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vendor_phone,
                call_sid,
                transcript,
                summary,
                int(important),
                int(escalated),
                escalation_reason,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
