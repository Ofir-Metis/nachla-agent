"""OCR dispatcher for scanned Hebrew documents.

Tries OCR engines in order of preference:
1. Docling built-in OCR (free, decent Hebrew)
2. EasyOCR (free, good Hebrew, requires PyTorch)
3. Google Cloud Vision (excellent Hebrew, requires API key)

Each engine returns None if unavailable or extraction fails.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRDispatcher:
    """OCR for scanned Hebrew documents.

    Tries engines in order and returns the best result.
    """

    def __init__(self) -> None:
        self._engine_cache: dict[str, bool | None] = {
            "docling": None,
            "easyocr": None,
            "google_vision": None,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(self, file_path: str) -> str:
        """Extract text from a scanned image or PDF using the best available OCR.

        Tries engines in order; returns the longest result containing Hebrew characters.

        Args:
            file_path: Path to a PDF or image file.

        Returns:
            Extracted text, or empty string if all engines fail.
        """
        self._validate_file(file_path)

        results: list[tuple[str, str]] = []  # (engine_name, text)

        for engine_name, method in [
            ("docling", self._try_docling_ocr),
            ("easyocr", self._try_easyocr),
            ("google_vision", self._try_google_vision),
        ]:
            text = method(file_path)
            if text and text.strip():
                results.append((engine_name, text))
                logger.info("OCR engine '%s' extracted %d chars from %s", engine_name, len(text), file_path)

        if not results:
            logger.warning("All OCR engines failed for %s", file_path)
            return ""

        # Pick the best result: prefer the one with the most Hebrew characters
        best_engine, best_text = max(results, key=lambda r: self._hebrew_char_count(r[1]))
        logger.info("Selected OCR result from '%s' (%d Hebrew chars)", best_engine, self._hebrew_char_count(best_text))
        return best_text

    def get_available_engines(self) -> list[str]:
        """Return list of available OCR engine names."""
        available: list[str] = []

        # Check Docling
        if self._is_docling_available():
            available.append("docling")

        # Check EasyOCR
        if self._is_easyocr_available():
            available.append("easyocr")

        # Check Google Vision
        if self._is_google_vision_available():
            available.append("google_vision")

        return available

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    def _try_docling_ocr(self, file_path: str) -> str | None:
        """Attempt OCR via Docling's built-in OCR capabilities."""
        if not self._is_docling_available():
            return None
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(file_path)
            text = result.document.export_to_markdown()
            if text and text.strip():
                return text
        except Exception:
            logger.warning("Docling OCR failed for %s", file_path, exc_info=True)
        return None

    def _try_easyocr(self, file_path: str) -> str | None:
        """Attempt OCR via EasyOCR (Hebrew + English)."""
        if not self._is_easyocr_available():
            return None
        temp_image: str | None = None
        try:
            import easyocr

            reader = easyocr.Reader(["he", "en"], gpu=False)

            # EasyOCR works on images; for PDFs, convert first page
            path = Path(file_path)
            if path.suffix.lower() == ".pdf":
                temp_image = self._pdf_first_page_to_image(file_path)
                if temp_image is None:
                    return None
                target = temp_image
            else:
                target = file_path

            results = reader.readtext(target)
            texts = [r[1] for r in results if r[1]]
            return "\n".join(texts) if texts else None
        except Exception:
            logger.warning("EasyOCR failed for %s", file_path, exc_info=True)
        finally:
            # Clean up temporary image file
            if temp_image and os.path.exists(temp_image):
                try:
                    os.unlink(temp_image)
                except OSError:
                    pass
        return None

    def _try_google_vision(self, file_path: str) -> str | None:
        """Attempt OCR via Google Cloud Vision API.

        Requires GOOGLE_APPLICATION_CREDENTIALS environment variable.
        """
        if not self._is_google_vision_available():
            return None
        try:
            from google.cloud import vision

            client = vision.ImageAnnotatorClient()

            with open(file_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)
            response = client.text_detection(
                image=image,
                image_context=vision.ImageContext(language_hints=["he", "en"]),
            )

            if response.error.message:
                logger.warning("Google Vision error: %s", response.error.message)
                return None

            texts = response.text_annotations
            if texts:
                return texts[0].description
        except Exception:
            logger.warning("Google Vision OCR failed for %s", file_path, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Availability checks
    # ------------------------------------------------------------------

    def _is_docling_available(self) -> bool:
        if self._engine_cache["docling"] is None:
            try:
                from docling.document_converter import DocumentConverter  # noqa: F401

                self._engine_cache["docling"] = True
            except (ImportError, OSError):
                self._engine_cache["docling"] = False
        return self._engine_cache["docling"]  # type: ignore[return-value]

    def _is_easyocr_available(self) -> bool:
        if self._engine_cache["easyocr"] is None:
            try:
                import easyocr  # noqa: F401

                self._engine_cache["easyocr"] = True
            except (ImportError, OSError):
                self._engine_cache["easyocr"] = False
        return self._engine_cache["easyocr"]  # type: ignore[return-value]

    def _is_google_vision_available(self) -> bool:
        if self._engine_cache["google_vision"] is None:
            creds_set = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
            if not creds_set:
                self._engine_cache["google_vision"] = False
            else:
                try:
                    from google.cloud import vision  # noqa: F401

                    self._engine_cache["google_vision"] = True
                except ImportError:
                    self._engine_cache["google_vision"] = False
        return self._engine_cache["google_vision"]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_file(file_path: str) -> None:
        """Basic file validation."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

    @staticmethod
    def _hebrew_char_count(text: str) -> int:
        """Count Hebrew Unicode characters in text."""
        return sum(1 for ch in text if "\u0590" <= ch <= "\u05ff")

    @staticmethod
    def _pdf_first_page_to_image(file_path: str) -> str | None:
        """Convert the first page of a PDF to a temporary image for OCR."""
        try:
            import tempfile

            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    return None
                page = pdf.pages[0]
                img = page.to_image(resolution=300)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img.save(tmp.name, format="PNG")
                    return tmp.name
        except Exception:
            logger.warning("Failed to convert PDF page to image for %s", file_path, exc_info=True)
            return None
