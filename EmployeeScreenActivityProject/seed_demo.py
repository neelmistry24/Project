from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from random import choice, randint, uniform

from PIL import Image, ImageDraw

from config import ensure_directories, load_config
from database import ActivityDatabase, ActivityLog


SAMPLES = [
    ("productive", "coding", "Visual Studio Code", "main.py - Employee Project"),
    ("productive", "spreadsheet", "Excel", "Sprint Report.xlsx"),
    ("productive", "documentation", "Chrome", "Google Docs - Project Plan"),
    ("non_productive", "social_media", "Chrome", "Instagram Reels"),
    ("non_productive", "video_streaming", "Chrome", "YouTube Music"),
    ("idle", "idle", "Unknown", "No user activity"),
]


def create_demo_image(path: Path, category: str, title: str) -> None:
    colors = {
        "productive": (34, 140, 90),
        "non_productive": (204, 75, 75),
        "idle": (95, 103, 115),
    }
    image = Image.new("RGB", (900, 520), colors[category])
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 860, 480), outline=(255, 255, 255), width=4)
    draw.text((80, 110), category.replace("_", "-").title(), fill=(255, 255, 255))
    draw.text((80, 170), title, fill=(255, 255, 255))
    image.save(path)


def main() -> None:
    config = load_config()
    ensure_directories(config)
    db = ActivityDatabase(config.database_path)
    base_time = datetime.now() - timedelta(hours=4)

    for index in range(24):
        category, tag, active_app, title = choice(SAMPLES)
        timestamp = base_time + timedelta(minutes=10 * index)
        screenshot_path = config.screenshot_dir / f"demo_{index:02d}_{category}.png"
        create_demo_image(screenshot_path, category, title)
        db.insert_log(
            ActivityLog(
                captured_at=timestamp,
                category=category,
                tag=tag,
                confidence=round(uniform(0.72, 0.98), 2),
                active_app=active_app,
                window_title=title,
                browser_tab=title if active_app == "Chrome" else "",
                idle_seconds=randint(190, 420) if category == "idle" else randint(0, 60),
                ocr_text=title,
                screenshot_path=str(screenshot_path),
                explanation="Demo activity record.",
            )
        )

    print("Demo data created. Run: streamlit run app.py")


if __name__ == "__main__":
    main()
