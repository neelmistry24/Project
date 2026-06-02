from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = {
    "database_path": "data/activity.db",
    "screenshot_dir": "data/screenshots",
    "export_dir": "data/exports",
    "capture_interval_seconds": 30,  # 5 minutes
    "idle_threshold_seconds": 60,  # 10 minutes
    "store_screenshots": True,
    "blur_private_screenshots": True,
    "blur_categories": ["non_productive"],
    "max_ocr_chars": 600,
    "privacy_mode_default": False,
    "productive_keywords": [
        "vscode",
        "visual studio code",
        "pycharm",
        "python",
        "excel",
        "word",
        "powerpoint",
        "google docs",
        "google sheets",
        "jira",
        "github",
        "stack overflow",
        "fastapi",
        "streamlit",
        "code",
        "terminal",
        "project",
        "report",
    ],
    "non_productive_keywords": [
        "youtube",
        "netflix",
        "instagram",
        "facebook",
        "whatsapp",
        "spotify",
        "game",
        "gaming",
        "reels",
        "shorts",
        "twitter",
        "x.com",
        "prime video",
        "hotstar",
    ],
}


@dataclass(slots=True)
class AppConfig:
    database_path: Path
    screenshot_dir: Path
    export_dir: Path
    capture_interval_seconds: int
    idle_threshold_seconds: int
    store_screenshots: bool
    blur_private_screenshots: bool
    blur_categories: list[str]
    max_ocr_chars: int
    privacy_mode_default: bool
    productive_keywords: list[str]
    non_productive_keywords: list[str]


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


def load_config() -> AppConfig:
    raw = DEFAULT_CONFIG.copy()
    config_path = ROOT_DIR / "config.yaml"
    if config_path.exists():
        try:
            import yaml

            file_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            raw.update(file_config)
        except Exception:
            pass
    return AppConfig(
        database_path=_resolve_path(raw["database_path"]),
        screenshot_dir=_resolve_path(raw["screenshot_dir"]),
        export_dir=_resolve_path(raw["export_dir"]),
        capture_interval_seconds=int(raw["capture_interval_seconds"]),
        idle_threshold_seconds=int(raw["idle_threshold_seconds"]),
        store_screenshots=bool(raw["store_screenshots"]),
        blur_private_screenshots=bool(raw["blur_private_screenshots"]),
        blur_categories=[item.lower() for item in raw["blur_categories"]],
        max_ocr_chars=int(raw["max_ocr_chars"]),
        privacy_mode_default=bool(raw["privacy_mode_default"]),
        productive_keywords=[item.lower() for item in raw["productive_keywords"]],
        non_productive_keywords=[item.lower() for item in raw["non_productive_keywords"]],
    )


def ensure_directories(config: AppConfig) -> None:
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    config.screenshot_dir.mkdir(parents=True, exist_ok=True)
    config.export_dir.mkdir(parents=True, exist_ok=True)
