import os
import sqlite3

from config import DB_PATH


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'model')),
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approved_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_transcript TEXT,
                formatted_output TEXT,
                approved_docx_text TEXT NOT NULL,
                session_label TEXT,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_message(user_id: int, role: str, content: str) -> None:
    if role not in {"user", "model"}:
        raise ValueError("role must be 'user' or 'model'")
    if not content.strip():
        return

    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )


def get_history(user_id: int, last_n: int = 10) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (user_id, last_n),
        ).fetchall()

    return [{"role": role, "parts": [content]} for role, content in reversed(rows)]


def save_approved_version(
    user_id: int,
    approved_text: str,
    session_label: str = "",
    original_transcript: str | None = None,
    formatted_output: str | None = None,
) -> None:
    if not approved_text.strip():
        raise ValueError("Approved document text is empty")

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO approved_versions (
                user_id,
                original_transcript,
                formatted_output,
                approved_docx_text,
                session_label
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                original_transcript,
                formatted_output,
                approved_text,
                session_label,
            ),
        )


def get_recent_approved_versions(user_id: int, limit: int = 3) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT approved_docx_text
            FROM approved_versions
            WHERE user_id = ?
            ORDER BY submitted_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [row[0] for row in rows]
