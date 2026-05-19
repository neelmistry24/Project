from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from database import ActivityDatabase


def recent_dataframe(db: ActivityDatabase, limit: int = 500) -> pd.DataFrame:
    rows = [dict(row) for row in db.fetch_logs(limit)]
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "captured_at",
                "category",
                "tag",
                "confidence",
                "active_app",
                "window_title",
                "browser_tab",
                "idle_seconds",
                "ocr_text",
                "screenshot_path",
                "explanation",
            ]
        )
    df = pd.DataFrame(rows)
    df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
    return df


def summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    total = len(df)
    if total == 0:
        return {
            "total": 0,
            "productive": 0,
            "non_productive": 0,
            "idle": 0,
            "productive_pct": 0.0,
        }
    counts = df["category"].value_counts()
    productive = int(counts.get("productive", 0))
    return {
        "total": total,
        "productive": productive,
        "non_productive": int(counts.get("non_productive", 0)),
        "idle": int(counts.get("idle", 0)),
        "productive_pct": round(productive / total * 100, 1),
    }


def export_csv(df: pd.DataFrame, export_dir: Path) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = export_dir / f"activity_report_{timestamp}.csv"
    df.to_csv(path, index=False)
    return path
