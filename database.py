from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    category TEXT NOT NULL,
    tag TEXT NOT NULL,
    confidence REAL NOT NULL,
    active_app TEXT,
    window_title TEXT,
    browser_tab TEXT,
    idle_seconds INTEGER NOT NULL,
    ocr_text TEXT,
    screenshot_path TEXT,
    explanation TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_captured_at
ON activity_logs(captured_at);
"""


@dataclass(slots=True)
class ActivityLog:
    captured_at: datetime
    category: str
    tag: str
    confidence: float
    active_app: str
    window_title: str
    browser_tab: str
    idle_seconds: int
    ocr_text: str
    screenshot_path: str
    explanation: str


class ActivityDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES('monitoring_enabled', 'true')"
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES('productivity_goal_pct', '70')"
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str | bool | int) -> None:
        normalized = str(value).lower() if isinstance(value, bool) else str(value)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, normalized),
            )

    def monitoring_enabled(self) -> bool:
        return self.get_setting("monitoring_enabled", "true") == "true"

    def insert_log(self, log: ActivityLog) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO activity_logs (
                    captured_at, category, tag, confidence, active_app, window_title,
                    browser_tab, idle_seconds, ocr_text, screenshot_path, explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.captured_at.isoformat(timespec="seconds"),
                    log.category,
                    log.tag,
                    log.confidence,
                    log.active_app,
                    log.window_title,
                    log.browser_tab,
                    log.idle_seconds,
                    log.ocr_text,
                    log.screenshot_path,
                    log.explanation,
                ),
            )
            return int(cursor.lastrowid)

    def fetch_logs(self, limit: int = 500) -> list[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM activity_logs ORDER BY captured_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return list(rows)
