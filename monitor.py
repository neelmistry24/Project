from __future__ import annotations

from datetime import datetime

from capture import blur_screenshot, capture_screen, get_window_info, save_screenshot, sleep_interval
from classifier import ActivityClassifier
from config import ensure_directories, load_config
from database import ActivityDatabase, ActivityLog
from ocr_engine import extract_text


class Monitor:
    def __init__(self) -> None:
        self.config = load_config()
        ensure_directories(self.config)
        self.db = ActivityDatabase(self.config.database_path)
        self.classifier = ActivityClassifier(self.config)

    def capture_once(self) -> int | None:
        if not self.db.monitoring_enabled():
            return None

        image = capture_screen()
        window = get_window_info()
        ocr_text = extract_text(image, self.config.max_ocr_chars)
        result = self.classifier.classify(image, ocr_text, window)
        image_to_store = (
            blur_screenshot(image)
            if self.config.blur_private_screenshots and result.category in self.config.blur_categories
            else image
        )
        screenshot_path = (
            save_screenshot(image_to_store, self.config.screenshot_dir)
            if self.config.store_screenshots
            else ""
        )

        return self.db.insert_log(
            ActivityLog(
                captured_at=datetime.now(),
                category=result.category,
                tag=result.tag,
                confidence=result.confidence,
                active_app=window.active_app,
                window_title=window.window_title,
                browser_tab=window.browser_tab,
                idle_seconds=window.idle_seconds,
                ocr_text=ocr_text,
                screenshot_path=screenshot_path,
                explanation=result.explanation,
            )
        )

    def run_forever(self) -> None:
        print("Monitoring started. Use Ctrl+C to stop.")
        while True:
            event_id = self.capture_once()
            if event_id:
                print(f"Captured activity event #{event_id}")
            else:
                print("Monitoring paused by privacy toggle.")
            sleep_interval(self.config.capture_interval_seconds)


if __name__ == "__main__":
    Monitor().run_forever()
