import sqlite3
import threading
from datetime import datetime
from config import DB_PATH, DEFAULT_WELCOME_TEXT, DEFAULT_WELCOME_IMAGE

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Return a per-thread SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            last_name   TEXT,
            joined_at   TEXT NOT NULL,
            is_blocked  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    # Seed default settings if absent
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("welcome_text", DEFAULT_WELCOME_TEXT),
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("welcome_image", DEFAULT_WELCOME_IMAGE),
    )
    conn.commit()


# ── Users ────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, first_name: str, last_name: str) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO users (user_id, username, first_name, last_name, joined_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name
        """,
        (user_id, username or "", first_name or "", last_name or "",
         datetime.utcnow().isoformat()),
    )
    conn.commit()


def get_all_users() -> list[sqlite3.Row]:
    return get_conn().execute(
        "SELECT user_id FROM users WHERE is_blocked = 0"
    ).fetchall()


def get_user_count() -> int:
    row = get_conn().execute("SELECT COUNT(*) FROM users").fetchone()
    return row[0] if row else 0


def get_active_count() -> int:
    row = get_conn().execute(
        "SELECT COUNT(*) FROM users WHERE is_blocked = 0"
    ).fetchone()
    return row[0] if row else 0


def mark_blocked(user_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()


# ── Settings ─────────────────────────────────────────────────────

def get_setting(key: str) -> str:
    row = get_conn().execute(
        "SELECT value FROM settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else ""


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
