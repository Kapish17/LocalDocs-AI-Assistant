"""
OCR fallback for scanned PDFs and images (needs_ocr / _get_easyocr_reader /
ocr_extract / run_ocr_pass), used by the FastAPI upload path so scanned PDFs
still produce usable text instead of silently ingesting an empty Document.

Uses EasyOCR (pure-Python OCR engine, no external Tesseract binary needed)
and PyMuPDF (fitz) for PDF page rasterization (no dependency on the
external 'poppler' binary either) — both optional; if either isn't
installed, OCR is skipped with a clear log message rather than crashing
ingestion.

Nothing here imports fastapi.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_reader = None  # process-wide EasyOCR model cache — model init takes a few
                 # seconds, so it's loaded once and reused via a plain
                 # module-level cache.


def needs_ocr(text: Optional[str], min_chars: int = 40) -> bool:
    """True when normal text extraction produced too little usable text to
    be worth trusting — i.e. this is (probably) a scanned page/document."""
    return len((text or "").strip()) < min_chars


def _get_ocr_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)  # set gpu=True if a CUDA GPU + torch-cuda is available
    return _reader


def ocr_page_image(pil_image) -> str:
    """Runs OCR on a single PIL image and returns extracted text (empty on
    failure/unavailability)."""
    try:
        reader = _get_ocr_reader()
        import numpy as np
    except ImportError:
        logger.warning("easyocr/numpy not installed — skipping OCR. Run: pip install easyocr")
        return ""
    except Exception as e:
        logger.warning("Failed to load EasyOCR model: %s", e)
        return ""

    try:
        result = reader.readtext(np.array(pil_image), detail=0, paragraph=True)
        return "\n".join(result).strip()
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return ""


def ocr_pdf_page(file_path: Path, page_index: int) -> str:
    """Rasterizes one page (0-indexed) of a PDF and OCRs it. Returns "" if
    PyMuPDF/EasyOCR aren't available or OCR fails — callers should treat
    that as "no OCR text available", not as a hard failure."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError:
        logger.warning("PyMuPDF/Pillow not installed — skipping OCR for scanned PDF page. Run: pip install pymupdf pillow")
        return ""

    try:
        doc = fitz.open(str(file_path))
        try:
            if page_index >= len(doc):
                return ""
            page = doc[page_index]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return ocr_page_image(img)
        finally:
            doc.close()
    except Exception as e:
        logger.warning("OCR failed for %s page %d: %s", file_path.name, page_index + 1, e)
        return ""


def ocr_image_file(file_path: Path) -> str:
    """OCRs a standalone image file (.png/.jpg/.jpeg)."""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed — skipping OCR for image. Run: pip install pillow")
        return ""
    try:
        img = Image.open(file_path).convert("RGB")
        return ocr_page_image(img)
    except Exception as e:
        logger.warning("OCR failed for %s: %s", file_path.name, e)
        return ""
