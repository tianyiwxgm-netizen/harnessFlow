"""L2-03 OCR fallback · pytesseract wrapper · degrades gracefully if binary missing."""

from __future__ import annotations

from pathlib import Path


def extract_text(image_path: Path) -> str:
    """Run pytesseract on image · return text. On any failure return ''."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        img = Image.open(str(image_path))
        text = pytesseract.image_to_string(img)
        return str(text).strip()
    except Exception:
        # tesseract binary missing, image unreadable, etc. → empty string · caller handles.
        return ""
