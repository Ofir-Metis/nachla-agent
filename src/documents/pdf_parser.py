"""PDF text and table extraction for Hebrew documents.

Primary engine: Docling (IBM) for complex PDFs with layout/table AI.
Fallback engine: pdfplumber for simpler cases or when Docling is unavailable.

All text extraction enforces UTF-8 encoding.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Maximum file size for upload validation (50 MB).
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

# If a survey map date is older than this many years, emit a warning.
SURVEY_MAP_MAX_AGE_YEARS = 2


class ParsedDocument(BaseModel):
    """Structured result of parsing a PDF document."""

    file_path: str = Field(..., description="Path to the source PDF file")
    text: str = Field(default="", description="Full extracted text content")
    tables: list[list[list[str]]] = Field(
        default_factory=list,
        description="List of tables; each table is a list of rows; each row is a list of cell strings",
    )
    is_scanned: bool = Field(default=False, description="Whether the PDF appears to be scanned (image-based)")
    metadata: dict = Field(default_factory=dict, description="Page count, creation date, etc.")
    warnings: list[str] = Field(default_factory=list, description="Warnings generated during parsing")


class PDFParser:
    """Parse Hebrew PDFs -- text and tables.

    Primary: Docling (IBM) for complex PDFs with layout/table AI.
    Fallback: pdfplumber for simpler cases.
    """

    def __init__(self) -> None:
        self._docling_available: bool | None = None
        self._pdfplumber_available: bool | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a PDF and return structured content.

        Tries Docling first; falls back to pdfplumber on failure.
        Extracts text once and reuses for scanned-detection to avoid
        opening the PDF multiple times.
        """
        self.validate_file(file_path)

        # Extract text once and reuse for scanned detection
        text = self.extract_text(file_path)
        scanned = len(text.strip()) < 50
        tables = self.extract_tables(file_path)
        metadata = self._extract_metadata(file_path)
        warnings: list[str] = []

        if scanned:
            warnings.append("PDF appears to be scanned (image-based). OCR may be required for full extraction.")

        if not text.strip():
            warnings.append("No text could be extracted from the PDF.")

        # Extract survey map date and warn if stale
        survey_date = self.extract_survey_map_date(file_path)
        if survey_date:
            metadata["survey_map_date"] = survey_date

        return ParsedDocument(
            file_path=file_path,
            text=text,
            tables=tables,
            is_scanned=scanned,
            metadata=metadata,
            warnings=warnings,
        )

    def is_scanned(self, file_path: str) -> bool:
        """Detect if a PDF is scanned (image-based) vs native text.

        Heuristic: if extracted text is very short (< 50 chars) the document
        is likely a scanned image.
        """
        self.validate_file(file_path)
        text = self._extract_text_pdfplumber(file_path) or ""
        return len(text.strip()) < 50

    def extract_text(self, file_path: str) -> str:
        """Extract full text content from a PDF.

        Tries Docling first, then pdfplumber.
        """
        self.validate_file(file_path)

        # Try Docling
        text = self._extract_text_docling(file_path)
        if text and text.strip():
            return text

        # Fallback to pdfplumber
        text = self._extract_text_pdfplumber(file_path)
        if text and text.strip():
            return text

        return ""

    def extract_tables(self, file_path: str) -> list[list[list[str]]]:
        """Extract tables as a list of tables, each a list of rows of cell strings.

        Tries Docling first, then pdfplumber.
        """
        self.validate_file(file_path)

        tables = self._extract_tables_docling(file_path)
        if tables:
            return tables

        tables = self._extract_tables_pdfplumber(file_path)
        if tables:
            return tables

        return []

    def extract_survey_map_date(self, file_path: str) -> str | None:
        """Try to extract the date from a survey map PDF.

        Looks for common Hebrew date patterns in the text.
        Warns if the map is older than 2 years.

        Returns:
            ISO date string (YYYY-MM-DD) if found, else None.
        """
        self.validate_file(file_path)
        text = self.extract_text(file_path)
        if not text:
            return None

        found_date = self._find_date_in_text(text)
        if found_date:
            age_days = (date.today() - found_date).days
            if age_days > SURVEY_MAP_MAX_AGE_YEARS * 365:
                logger.warning(
                    "Survey map date %s is older than %d years (%d days old).",
                    found_date.isoformat(),
                    SURVEY_MAP_MAX_AGE_YEARS,
                    age_days,
                )
            return found_date.isoformat()

        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_file(file_path: str) -> None:
        """Validate that the file exists, is a PDF, and is under 50 MB."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File is not a PDF (extension={path.suffix!r}): {file_path}")
        size = path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File exceeds 50 MB limit ({size / (1024 * 1024):.1f} MB): {file_path}")

    # ------------------------------------------------------------------
    # Docling backend
    # ------------------------------------------------------------------

    def _check_docling(self) -> bool:
        if self._docling_available is None:
            try:
                from docling.document_converter import DocumentConverter  # noqa: F401

                self._docling_available = True
            except (ImportError, OSError):
                self._docling_available = False
                logger.info("Docling not available; will use pdfplumber fallback.")
        return self._docling_available

    def _extract_text_docling(self, file_path: str) -> str | None:
        if not self._check_docling():
            return None
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(file_path)
            text = result.document.export_to_markdown()
            if text and text.strip():
                logger.debug("Docling extracted %d chars from %s", len(text), file_path)
                return text
        except Exception:
            logger.warning("Docling text extraction failed for %s", file_path, exc_info=True)
        return None

    def _extract_tables_docling(self, file_path: str) -> list[list[list[str]]] | None:
        if not self._check_docling():
            return None
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(file_path)
            doc = result.document
            tables: list[list[list[str]]] = []
            # Docling exposes tables through the document model
            if hasattr(doc, "tables") and doc.tables:
                for table in doc.tables:
                    if hasattr(table, "export_to_dataframe"):
                        df = table.export_to_dataframe()
                        rows: list[list[str]] = []
                        # Header row
                        rows.append([str(c) for c in df.columns])
                        for _, row in df.iterrows():
                            rows.append([str(v) for v in row])
                        tables.append(rows)
            if tables:
                logger.debug("Docling extracted %d tables from %s", len(tables), file_path)
                return tables
        except Exception:
            logger.warning("Docling table extraction failed for %s", file_path, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # pdfplumber backend
    # ------------------------------------------------------------------

    def _check_pdfplumber(self) -> bool:
        if self._pdfplumber_available is None:
            try:
                import pdfplumber  # noqa: F401

                self._pdfplumber_available = True
            except ImportError:
                self._pdfplumber_available = False
                logger.error("pdfplumber is not installed. Cannot parse PDFs.")
        return self._pdfplumber_available

    def _extract_text_pdfplumber(self, file_path: str) -> str | None:
        if not self._check_pdfplumber():
            return None
        try:
            import pdfplumber

            parts: list[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        parts.append(page_text)
            text = "\n\n".join(parts)
            if text.strip():
                logger.debug("pdfplumber extracted %d chars from %s", len(text), file_path)
                return text
        except Exception:
            logger.warning("pdfplumber text extraction failed for %s", file_path, exc_info=True)
        return None

    def _extract_tables_pdfplumber(self, file_path: str) -> list[list[list[str]]] | None:
        if not self._check_pdfplumber():
            return None
        try:
            import pdfplumber

            all_tables: list[list[list[str]]] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            cleaned: list[list[str]] = []
                            for row in table:
                                if row is None:
                                    continue
                                cleaned.append([str(cell) if cell is not None else "" for cell in row])
                            if cleaned:
                                all_tables.append(cleaned)
            if all_tables:
                logger.debug("pdfplumber extracted %d tables from %s", len(all_tables), file_path)
                return all_tables
        except Exception:
            logger.warning("pdfplumber table extraction failed for %s", file_path, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _extract_metadata(self, file_path: str) -> dict:
        """Extract basic metadata using pdfplumber."""
        metadata: dict = {
            "file_size_bytes": os.path.getsize(file_path),
        }
        if not self._check_pdfplumber():
            return metadata
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                metadata["page_count"] = len(pdf.pages)
                if pdf.metadata:
                    for key in ("CreationDate", "ModDate", "Author", "Title", "Producer"):
                        if key in pdf.metadata and pdf.metadata[key]:
                            metadata[key.lower()] = pdf.metadata[key]
        except Exception:
            logger.warning("Failed to extract metadata from %s", file_path, exc_info=True)
        return metadata

    # ------------------------------------------------------------------
    # Date extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_date_in_text(text: str) -> date | None:
        """Search for dates in common formats within text.

        Supported patterns:
        - DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY
        - YYYY-MM-DD (ISO)
        """
        # DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
        pattern_dmy = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](20\d{2}|19\d{2})\b")
        for match in pattern_dmy.finditer(text):
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                continue

        # YYYY-MM-DD
        pattern_iso = re.compile(r"\b(20\d{2}|19\d{2})[/.\-](\d{1,2})[/.\-](\d{1,2})\b")
        for match in pattern_iso.finditer(text):
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                continue

        return None
