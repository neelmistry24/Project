from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time

from PIL import Image, ImageFilter
import mss


@dataclass(slots=True)
class WindowInfo:
    active_app: str
    window_title: str
    browser_tab: str
    idle_seconds: int


def capture_screen() -> Image.Image:
    with mss.mss() as screen:
        monitor = screen.monitors[1]
        shot = screen.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.rgb)


def save_screenshot(image: Image.Image, screenshot_dir: Path) -> str:
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = screenshot_dir / f"screen_{timestamp}.png"
    image.save(path)
    return str(path)


def blur_screenshot(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=14))


def get_window_info() -> WindowInfo:
    try:
        import pygetwindow as gw

        window = gw.getActiveWindow()
        title = window.title if window else ""
    except Exception:
        title = ""

    active_app = _guess_app_from_title(title)
    return WindowInfo(
        active_app=active_app,
        window_title=title,
        browser_tab=title if active_app.lower() in {"chrome", "edge", "firefox"} else "",
        idle_seconds=get_idle_seconds(),
    )


def get_idle_seconds() -> int:
    try:
        import ctypes

        class LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LastInputInfo()
        info.cbSize = ctypes.sizeof(LastInputInfo)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0, int(millis / 1000))
    except Exception:
        return 0


def _guess_app_from_title(title: str) -> str:
    lowered = title.lower()
    if "chrome" in lowered:
        return "Chrome"
    if "edge" in lowered:
        return "Edge"
    if "firefox" in lowered:
        return "Firefox"
    if "visual studio code" in lowered or "vscode" in lowered:
        return "Visual Studio Code"
    if "excel" in lowered:
        return "Excel"
    if "word" in lowered:
        return "Word"
    return title.split("-")[-1].strip() if title else "Unknown"


def sleep_interval(seconds: int) -> None:
    time.sleep(max(1, int(seconds)))
