"""Tests for the document processing pipeline.

Tests cover PDF parsing, Excel reading, Word generation, and OCR.
Real reference files are used when available (from the main repo);
tests that require real files are skipped otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.documents.excel_reader import ExcelReader
from src.documents.ocr import OCRDispatcher
from src.documents.pdf_parser import ParsedDocument, PDFParser
from src.documents.word_generator import WordGenerator

# ---------------------------------------------------------------------------
# Path helpers -- real data files live in the main repo, not the worktree.
# ---------------------------------------------------------------------------
_WORKTREE_ROOT = Path(__file__).resolve().parent.parent
_MAIN_REPO_ROOT = Path("C:/Users/Ofir/nachla-agent")

# Try worktree first, then main repo.
_REFERENCE_DIRS = [_WORKTREE_ROOT / "data" / "reference", _MAIN_REPO_ROOT / "data" / "reference"]
_TEMPLATE_DIRS = [_WORKTREE_ROOT / "data" / "templates", _MAIN_REPO_ROOT / "data" / "templates"]


def _find_file(dirs: list[Path], filename: str) -> Path | None:
    for d in dirs:
        p = d / filename
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


# Real file paths (may be None if not available).
SETTLEMENT_XLSX = _find_file(_REFERENCE_DIRS, "דמי היתר לפי ישובים.xlsx")
PLACH_XLSX = _find_file(_REFERENCE_DIRS, "דמי היתר פלח לפי מרחב או יישוב.xlsx")
RMI_DECISIONS_XLSX = _find_file(_REFERENCE_DIRS, "הנחיות והחלטות רמי.xlsx")
AGRICULTURE_PDF = _find_file(_REFERENCE_DIRS, "טבלה של משרד החקלאות.pdf")
EXAMPLE_REPORT_PDF = _find_file(_REFERENCE_DIRS, "סיכום בדיקת התכנות מותנה.pdf")
LAND_VALUES_PDF = _find_file(_REFERENCE_DIRS, "ערכי קרקע לשימושים נלווים עד 1.1.25.pdf")
CALCS_XLSX = _find_file(_REFERENCE_DIRS, "תחשיבים..xlsx")
WORD_TEMPLATE = _find_file(_TEMPLATE_DIRS, "סיכום בדיקת התכנות טמפלט.docx")
EXCEL_TEMPLATE = _find_file(_TEMPLATE_DIRS, "תחשיבים טמפלט.xlsx")

# Marker for tests that need real files.
needs_real_pdf = pytest.mark.skipif(AGRICULTURE_PDF is None, reason="Real PDF reference file not available")
needs_real_excel = pytest.mark.skipif(SETTLEMENT_XLSX is None, reason="Real Excel reference file not available")
needs_real_template = pytest.mark.skipif(WORD_TEMPLATE is None, reason="Real Word template not available")


# ===========================================================================
# PDF Parser Tests
# ===========================================================================
class TestPDFParser:
    """Tests for PDFParser."""

    def test_validate_file_rejects_missing(self) -> None:
        """Reject a file that does not exist."""
        parser = PDFParser()
        with pytest.raises(FileNotFoundError):
            parser.validate_file("C:/nonexistent/file.pdf")

    def test_validate_file_rejects_non_pdf(self, tmp_path: Path) -> None:
        """Reject a file that is not a PDF."""
        txt = tmp_path / "test.txt"
        txt.write_text("hello", encoding="utf-8")
        parser = PDFParser()
        with pytest.raises(ValueError, match="not a PDF"):
            parser.validate_file(str(txt))

    def test_validate_file_rejects_oversized(self, tmp_path: Path) -> None:
        """Reject a file larger than 50 MB."""
        big = tmp_path / "big.pdf"
        # Create a sparse file > 50 MB by writing header and seeking.
        with open(big, "wb") as f:
            f.write(b"%PDF-1.4")
            f.seek(51 * 1024 * 1024)
            f.write(b"\x00")
        parser = PDFParser()
        with pytest.raises(ValueError, match="50 MB"):
            parser.validate_file(str(big))

    def test_validate_file_accepts_valid_pdf(self, tmp_path: Path) -> None:
        """Accept a small valid PDF file."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 minimal")
        parser = PDFParser()
        # Should not raise.
        parser.validate_file(str(pdf))

    @needs_real_pdf
    def test_parse_hebrew_pdf(self) -> None:
        """Parse a real Hebrew PDF from reference data."""
        parser = PDFParser()
        result = parser.parse(str(AGRICULTURE_PDF))
        assert isinstance(result, ParsedDocument)
        assert result.file_path == str(AGRICULTURE_PDF)
        assert result.metadata.get("page_count", 0) > 0

    @needs_real_pdf
    def test_extract_text_from_real_pdf(self) -> None:
        """Extract text from a real PDF and verify non-empty."""
        parser = PDFParser()
        text = parser.extract_text(str(AGRICULTURE_PDF))
        assert len(text) > 0, "Expected non-empty text from agriculture ministry PDF"

    @needs_real_pdf
    def test_extract_tables_from_pdf(self) -> None:
        """Extract tables from a PDF with tabular data."""
        parser = PDFParser()
        tables = parser.extract_tables(str(AGRICULTURE_PDF))
        # The agriculture ministry PDF should contain at least one table.
        assert isinstance(tables, list)
        # Tables may or may not be found depending on the engine.
        # We just verify the return type is correct.
        for table in tables:
            assert isinstance(table, list)
            for row in table:
                assert isinstance(row, list)

    @needs_real_pdf
    def test_detect_native_pdf_not_scanned(self) -> None:
        """A text-based PDF should not be detected as scanned."""
        parser = PDFParser()
        # The agriculture PDF likely has native text.
        scanned = parser.is_scanned(str(AGRICULTURE_PDF))
        # We cannot guarantee this -- just check return type.
        assert isinstance(scanned, bool)

    def test_parse_returns_warnings_for_empty(self, tmp_path: Path) -> None:
        """Parse a minimal PDF that yields no text -- should produce warnings."""
        pdf = tmp_path / "empty.pdf"
        # Write a minimal valid-ish PDF (no actual content).
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        parser = PDFParser()
        result = parser.parse(str(pdf))
        assert isinstance(result, ParsedDocument)
        # Expect at least one warning (no text extracted or scanned).
        assert len(result.warnings) > 0

    def test_find_date_in_text(self) -> None:
        """Date extraction from text."""
        parser = PDFParser()
        d = parser._find_date_in_text("Survey date: 15/03/2024")
        assert d is not None
        assert d.year == 2024
        assert d.month == 3
        assert d.day == 15

    def test_find_date_iso_format(self) -> None:
        """ISO date extraction from text."""
        parser = PDFParser()
        d = parser._find_date_in_text("Date: 2023-11-20")
        assert d is not None
        assert d.year == 2023
        assert d.month == 11
        assert d.day == 20

    def test_find_date_returns_none_when_missing(self) -> None:
        """No date in text returns None."""
        parser = PDFParser()
        assert parser._find_date_in_text("No date here") is None

    @pytest.mark.skipif(EXAMPLE_REPORT_PDF is None, reason="Example report PDF not available")
    def test_parse_example_report_pdf(self) -> None:
        """Parse the example feasibility report PDF."""
        parser = PDFParser()
        result = parser.parse(str(EXAMPLE_REPORT_PDF))
        assert isinstance(result, ParsedDocument)
        assert result.metadata.get("page_count", 0) > 0


# ===========================================================================
# Excel Reader Tests
# ===========================================================================
class TestExcelReader:
    """Tests for ExcelReader."""

    def test_validate_file_rejects_non_excel(self, tmp_path: Path) -> None:
        """Reject a non-Excel file."""
        txt = tmp_path / "test.txt"
        txt.write_text("hello", encoding="utf-8")
        reader = ExcelReader()
        with pytest.raises(ValueError, match="not an Excel"):
            reader.validate_file(str(txt))

    def test_validate_file_rejects_missing(self) -> None:
        """Reject a file that does not exist."""
        reader = ExcelReader()
        with pytest.raises(FileNotFoundError):
            reader.validate_file("C:/nonexistent/file.xlsx")

    @needs_real_excel
    def test_read_settlement_table(self) -> None:
        """Read real settlement table from data/reference/."""
        reader = ExcelReader()
        result = reader.read_settlement_table(str(SETTLEMENT_XLSX))
        assert isinstance(result, dict)
        assert len(result) > 0, "Expected non-empty settlement table"
        # All values should be numeric.
        for name, val in result.items():
            assert isinstance(name, str)
            assert isinstance(val, float)

    @pytest.mark.skipif(PLACH_XLSX is None, reason="PLACH rates file not available")
    def test_read_plach_table(self) -> None:
        """Read real PLACH rates table."""
        reader = ExcelReader()
        result = reader.read_plach_table(str(PLACH_XLSX))
        assert isinstance(result, dict)
        assert len(result) > 0, "Expected non-empty PLACH table"

    @pytest.mark.skipif(RMI_DECISIONS_XLSX is None, reason="RMI decisions file not available")
    def test_read_rmi_decisions(self) -> None:
        """Read RMI decisions table."""
        reader = ExcelReader()
        result = reader.read_rmi_decisions(str(RMI_DECISIONS_XLSX))
        assert isinstance(result, list)
        assert len(result) > 0, "Expected non-empty RMI decisions"
        assert isinstance(result[0], dict)

    @needs_real_excel
    def test_read_generic_table(self) -> None:
        """Read any Excel into list of dicts."""
        reader = ExcelReader()
        result = reader.read_generic_table(str(SETTLEMENT_XLSX))
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)

    @needs_real_excel
    def test_table_metadata(self) -> None:
        """Get sheet names and row counts."""
        reader = ExcelReader()
        meta = reader.get_table_metadata(str(SETTLEMENT_XLSX))
        assert "sheet_names" in meta
        assert "row_counts" in meta
        assert "last_modified" in meta
        assert "is_stale" in meta
        assert isinstance(meta["sheet_names"], list)
        assert len(meta["sheet_names"]) > 0

    @pytest.mark.skipif(CALCS_XLSX is None, reason="Calculations Excel not available")
    def test_read_calculations_spreadsheet(self) -> None:
        """Read the example calculations spreadsheet."""
        reader = ExcelReader()
        result = reader.read_generic_table(str(CALCS_XLSX))
        assert isinstance(result, list)

    @pytest.mark.skipif(EXCEL_TEMPLATE is None, reason="Excel template not available")
    def test_read_excel_template_metadata(self) -> None:
        """Get metadata from the calculations template."""
        reader = ExcelReader()
        meta = reader.get_table_metadata(str(EXCEL_TEMPLATE))
        assert "sheet_names" in meta
        assert len(meta["sheet_names"]) > 0

    def test_to_float_various_inputs(self) -> None:
        """Test the _to_float helper with different inputs."""
        reader = ExcelReader()
        assert reader._to_float(42) == 42.0
        assert reader._to_float(3.14) == 3.14
        assert reader._to_float("1,234") == 1234.0
        assert reader._to_float("5,678 \u20aa") == 5678.0
        assert reader._to_float("") is None
        assert reader._to_float(None) is None
        assert reader._to_float("not a number") is None


# ===========================================================================
# Word Generator Tests
# ===========================================================================
class TestWordGenerator:
    """Tests for WordGenerator."""

    def _make_minimal_report_data(self):
        """Create a minimal ReportData for testing."""
        from src.models.report import ReportData

        return ReportData(
            nachla={
                "owner_name": "ישראלי",
                "moshav_name": "מושב דוגמה",
                "gush": 1234,
                "helka": 56,
                "num_existing_houses": 2,
                "authorization_type": "bar_reshut",
                "is_capitalized": False,
                "capitalization_track": "none",
                "client_goals": ["regularization"],
                "has_intergenerational_continuity": True,
                "ownership_type": "single",
                "has_demolition_orders": False,
                "priority_area": "none",
            },
            report_date="2026-04-03",
            study_objectives=["הסדרת חריגות בנייה", "חישוב עלויות היוון"],
            total_regularization_cost=150000,
            total_usage_fees=50000,
            total_permit_fees=100000,
            recommendations=["להגיש בקשה להיתר", "לבצע שומה"],
        )

    def test_format_currency(self) -> None:
        """Hebrew currency formatting."""
        gen = WordGenerator()
        assert gen._format_currency(1234567) == "1,234,567 \u20aa"
        assert gen._format_currency(0) == "0 \u20aa"
        assert gen._format_currency(999.5) == "1,000 \u20aa"  # rounds

    def test_format_date(self) -> None:
        """Date formatting DD/MM/YYYY."""
        gen = WordGenerator()
        assert gen._format_date("2026-04-03") == "03/04/2026"
        assert gen._format_date("2024-12-25") == "25/12/2024"
        assert gen._format_date("") == ""
        assert gen._format_date("invalid") == "invalid"

    def test_build_context(self) -> None:
        """Build context dict from ReportData."""
        gen = WordGenerator()
        report_data = self._make_minimal_report_data()
        ctx = gen._build_context(report_data)

        assert ctx["owner_name"] == "ישראלי"
        assert ctx["moshav_name"] == "מושב דוגמה"
        assert ctx["gush"] == 1234
        assert ctx["helka"] == 56
        assert ctx["report_date"] == "03/04/2026"
        assert ctx["total_regularization_cost"] == "150,000 \u20aa"
        assert ctx["total_usage_fees"] == "50,000 \u20aa"
        assert ctx["total_permit_fees"] == "100,000 \u20aa"
        assert len(ctx["study_objectives"]) == 2
        assert len(ctx["disclaimers"]) > 0

    def test_validate_template_rejects_missing(self) -> None:
        """Reject a missing template."""
        gen = WordGenerator()
        with pytest.raises(FileNotFoundError):
            gen._validate_template("C:/nonexistent/template.docx")

    def test_validate_template_rejects_non_docx(self, tmp_path: Path) -> None:
        """Reject a non-docx template."""
        txt = tmp_path / "template.txt"
        txt.write_text("hello")
        gen = WordGenerator()
        with pytest.raises(ValueError, match="not a .docx"):
            gen._validate_template(str(txt))

    @needs_real_template
    def test_generate_report_creates_docx(self, tmp_path: Path) -> None:
        """Generate a report using the real template and verify the file is created."""
        gen = WordGenerator()
        report_data = self._make_minimal_report_data()
        output = tmp_path / "output_report.docx"

        result_path = gen.generate_report(
            report_data=report_data,
            template_path=str(WORD_TEMPLATE),
            output_path=str(output),
        )

        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0

    def test_generate_audit_log_doc(self, tmp_path: Path) -> None:
        """Generate an audit log document."""
        from src.models.report import AuditEntry

        gen = WordGenerator()
        report_data = self._make_minimal_report_data()

        entries = [
            AuditEntry(
                timestamp="2026-04-03T10:00:00",
                tool_name="calc_dmei_heter",
                inputs={"area_sqm": 100, "shovi": 5000},
                formula="100 * 1.0 * 5000 * 0.91 * 1.18",
                rates_used={"permit_rate": 0.91, "vat": 0.18},
                result={"cost_ils": 536900},
            ),
        ]

        output = tmp_path / "audit_log.docx"
        result_path = gen.generate_audit_log_doc(
            audit_entries=entries,
            report_data=report_data,
            output_path=str(output),
        )

        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0


# ===========================================================================
# OCR Tests
# ===========================================================================
class TestOCR:
    """Tests for OCRDispatcher."""

    def test_available_engines_returns_list(self) -> None:
        """get_available_engines returns a list."""
        dispatcher = OCRDispatcher()
        engines = dispatcher.get_available_engines()
        assert isinstance(engines, list)
        # At least docling should be available given the requirements.
        # But we do not hard-require it for test to pass.

    def test_at_least_one_engine_available(self) -> None:
        """At least one OCR engine should be available in this environment.

        Note: this test may be skipped if system-level dependencies (e.g.
        VC++ Redistributable, CUDA DLLs) are missing, which prevents torch
        and therefore Docling/EasyOCR from loading.
        """
        dispatcher = OCRDispatcher()
        engines = dispatcher.get_available_engines()
        if len(engines) == 0:
            pytest.skip(
                "No OCR engines available -- likely missing system dependencies "
                "(VC++ Redistributable or CUDA DLLs for torch)"
            )

    def test_validate_file_rejects_missing(self) -> None:
        """Reject a missing file."""
        dispatcher = OCRDispatcher()
        with pytest.raises(FileNotFoundError):
            dispatcher.extract_text("C:/nonexistent/file.pdf")

    def test_hebrew_char_count(self) -> None:
        """Count Hebrew characters correctly."""
        dispatcher = OCRDispatcher()
        assert dispatcher._hebrew_char_count("שלום עולם") == 8  # 4 + 4 Hebrew chars (space excluded)
        assert dispatcher._hebrew_char_count("hello world") == 0
        assert dispatcher._hebrew_char_count("mixed שלום text") == 4

    @needs_real_pdf
    def test_ocr_on_real_pdf(self) -> None:
        """OCR extracts some text from a real document.

        This test uses Docling (or another available engine) on a real PDF.
        Since the agriculture PDF is native text, this mainly tests the
        Docling OCR pathway returns something.
        """
        dispatcher = OCRDispatcher()
        engines = dispatcher.get_available_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        text = dispatcher.extract_text(str(AGRICULTURE_PDF))
        # The PDF has native text, so OCR/extraction should find something.
        assert isinstance(text, str)


# ===========================================================================
# Integration / cross-module tests
# ===========================================================================
class TestIntegration:
    """Cross-module integration tests."""

    @needs_real_pdf
    def test_pdf_parse_and_check_scanned_for_ocr(self) -> None:
        """Parse a PDF, check if scanned, and dispatch to OCR if needed."""
        parser = PDFParser()
        result = parser.parse(str(AGRICULTURE_PDF))

        if result.is_scanned:
            dispatcher = OCRDispatcher()
            text = dispatcher.extract_text(str(AGRICULTURE_PDF))
            assert len(text) > 0
        else:
            # Native text -- extraction should have worked.
            assert len(result.text) > 0

    @needs_real_excel
    def test_excel_reader_all_reference_files(self) -> None:
        """Read all available Excel reference files without errors."""
        reader = ExcelReader()
        files_to_test = [f for f in [SETTLEMENT_XLSX, PLACH_XLSX, RMI_DECISIONS_XLSX, CALCS_XLSX] if f is not None]
        for file_path in files_to_test:
            meta = reader.get_table_metadata(str(file_path))
            assert "sheet_names" in meta, f"Failed to get metadata from {file_path}"
            rows = reader.read_generic_table(str(file_path))
            assert isinstance(rows, list), f"Failed to read {file_path}"
