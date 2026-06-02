from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from capture import WindowInfo
from config import AppConfig


@dataclass(slots=True)
class ClassificationResult:
    category: str
    tag: str
    confidence: float
    explanation: str


class ActivityClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def classify(self, image: Image.Image, ocr_text: str, window: WindowInfo) -> ClassificationResult:
        text = " ".join(
            [window.active_app, window.window_title, window.browser_tab, ocr_text]
        ).lower()
        has_screen_context = bool(text.strip()) and text.strip() not in {"unknown", "desktop"}
        brightness = self._average_brightness(image)

        productive_hit = self._first_keyword(text, self.config.productive_keywords)
        non_productive_hit = self._first_keyword(text, self.config.non_productive_keywords)

        if brightness < 12:
            return ClassificationResult(
                category="idle",
                tag="locked_or_blank_screen",
                confidence=0.72,
                explanation="Screen appears blank or locked.",
            )

        if self._looks_like_desktop_or_no_work(text, has_screen_context):
            return ClassificationResult(
                category="idle",
                tag="desktop_or_no_active_work",
                confidence=0.8,
                explanation="No active work application or useful screen text was detected.",
            )

        if non_productive_hit:
            return ClassificationResult(
                category="non_productive",
                tag=self._tag_for_keyword(non_productive_hit),
                confidence=0.88,
                explanation=f"Matched non-productive keyword: {non_productive_hit}.",
            )

        if productive_hit:
            return ClassificationResult(
                category="productive",
                tag=self._tag_for_keyword(productive_hit),
                confidence=0.86,
                explanation=f"Matched productive keyword: {productive_hit}.",
            )

        if window.idle_seconds >= self.config.idle_threshold_seconds and not has_screen_context:
            return ClassificationResult(
                category="idle",
                tag="idle_no_screen_context",
                confidence=0.8,
                explanation=f"No input activity for {window.idle_seconds} seconds and no active work context was detected.",
            )

        return ClassificationResult(
            category="productive",
            tag="general_work",
            confidence=0.55,
            explanation="No distraction signal found; defaulted to general productive work.",
        )

    @staticmethod
    def _first_keyword(text: str, keywords: list[str]) -> str:
        return next((keyword for keyword in keywords if keyword in text), "")

    @staticmethod
    def _average_brightness(image: Image.Image) -> float:
        grayscale = image.convert("L").resize((64, 64))
        pixels = list(grayscale.getdata())
        return sum(pixels) / len(pixels)

    @staticmethod
    def _looks_like_desktop_or_no_work(text: str, has_screen_context: bool) -> bool:
        desktop_signals = [
            "desktop",
            "program manager",
            "file explorer",
            "windows explorer",
            "taskbar",
            "start menu",
            "unknown",
        ]
        if not has_screen_context:
            return True
        return any(signal in text for signal in desktop_signals)

    @staticmethod
    def _tag_for_keyword(keyword: str) -> str:
        mapping = {
            "youtube": "video_streaming",
            "netflix": "video_streaming",
            "instagram": "social_media",
            "facebook": "social_media",
            "whatsapp": "messaging",
            "spotify": "entertainment",
            "excel": "spreadsheet",
            "word": "documentation",
            "google docs": "documentation",
            "google sheets": "spreadsheet",
            "vscode": "coding",
            "visual studio code": "coding",
            "python": "coding",
            "github": "development",
            "jira": "project_management",
        }
        return mapping.get(keyword, keyword.replace(" ", "_"))
