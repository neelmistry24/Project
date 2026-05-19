from __future__ import annotations

from PIL import Image


def extract_text(image: Image.Image, max_chars: int = 600) -> str:
    try:
        import pytesseract

        text = pytesseract.image_to_string(image)
    except Exception:
        text = ""
    return " ".join(text.split())[:max_chars]
