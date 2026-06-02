from __future__ import annotations

import sqlite3
from pathlib import Path

from PIL import Image

from capture import WindowInfo
from classifier import ActivityClassifier
from config import load_config


def load_image(path_text: str) -> Image.Image:
    path = Path(path_text or "")
    if path.exists():
        return Image.open(path).convert("RGB")
    return Image.new("RGB", (200, 100), "white")


def main() -> None:
    config = load_config()
    classifier = ActivityClassifier(config)
    conn = sqlite3.connect(config.database_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM activity_logs").fetchall()
    changed = 0

    for row in rows:
        image = load_image(row["screenshot_path"])
        window = WindowInfo(
            active_app=row["active_app"] or "Unknown",
            window_title=row["window_title"] or "",
            browser_tab=row["browser_tab"] or "",
            idle_seconds=int(row["idle_seconds"] or 0),
        )
        result = classifier.classify(image, row["ocr_text"] or "", window)

        if result.category != row["category"] or result.tag != row["tag"]:
            conn.execute(
                """
                UPDATE activity_logs
                SET category = ?,
                    tag = ?,
                    confidence = ?,
                    explanation = ?
                WHERE id = ?
                """,
                (
                    result.category,
                    result.tag,
                    result.confidence,
                    result.explanation,
                    row["id"],
                ),
            )
            changed += 1

    conn.commit()
    conn.close()
    print(f"Reclassified {len(rows)} records. Updated {changed} records.")


if __name__ == "__main__":
    main()
