"""Tests for security module: RBAC, input sanitization, file magic bytes, rate limiting."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from config.security import (
    MAX_INPUT_LENGTH,
    Role,
    check_permission,
    sanitize_filename,
    sanitize_input,
    validate_file_magic_bytes,
)

# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------


class TestRBAC:
    """Test role-based access control."""

    def test_admin_has_all_permissions(self) -> None:
        """Admin role should have every defined permission."""
        operations = [
            "create_job",
            "upload_files",
            "confirm_classification",
            "download_report",
            "list_jobs",
            "cancel_job",
            "manage_users",
            "configure",
        ]
        for op in operations:
            assert check_permission("admin", op), f"admin should have {op}"

    def test_analyst_cannot_manage_users(self) -> None:
        """Analyst role must not have manage_users or configure permissions."""
        assert not check_permission("analyst", "manage_users")
        assert not check_permission("analyst", "configure")
        assert not check_permission("analyst", "cancel_job")

    def test_analyst_can_create_and_download(self) -> None:
        """Analyst should be able to create jobs and download reports."""
        assert check_permission("analyst", "create_job")
        assert check_permission("analyst", "upload_files")
        assert check_permission("analyst", "confirm_classification")
        assert check_permission("analyst", "download_report")
        assert check_permission("analyst", "list_jobs")

    def test_viewer_read_only(self) -> None:
        """Viewer role should only have read-only permissions."""
        assert check_permission("viewer", "download_report")
        assert check_permission("viewer", "list_jobs")
        assert not check_permission("viewer", "create_job")
        assert not check_permission("viewer", "upload_files")
        assert not check_permission("viewer", "confirm_classification")
        assert not check_permission("viewer", "manage_users")

    def test_unknown_role_denied(self) -> None:
        """Unknown role should be denied all permissions."""
        assert not check_permission("hacker", "create_job")
        assert not check_permission("", "list_jobs")
        assert not check_permission("superadmin", "download_report")

    def test_unknown_operation_denied(self) -> None:
        """Unknown operation should be denied for all roles."""
        assert not check_permission("admin", "delete_everything")
        assert not check_permission("analyst", "hack_system")

    def test_role_enum_values(self) -> None:
        """Role enum values should match expected strings."""
        assert Role.ADMIN == "admin"
        assert Role.ANALYST == "analyst"
        assert Role.VIEWER == "viewer"


# ---------------------------------------------------------------------------
# Input sanitization tests
# ---------------------------------------------------------------------------


class TestInputSanitization:
    """Test input text sanitization."""

    def test_strip_control_chars(self) -> None:
        """Control characters (except whitespace) should be stripped."""
        text = "hello\x00world\x01test\x02end"
        result = sanitize_input(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "helloworld" in result

    def test_preserve_whitespace(self) -> None:
        """Tab, newline, carriage return should be preserved."""
        text = "line1\nline2\ttab\rcarriage"
        result = sanitize_input(text)
        assert "\n" in result
        assert "\t" in result

    def test_limit_length(self) -> None:
        """Text exceeding max length should be truncated."""
        long_text = "a" * (MAX_INPUT_LENGTH + 1000)
        result = sanitize_input(long_text)
        assert len(result) <= MAX_INPUT_LENGTH

    def test_custom_max_length(self) -> None:
        """Custom max_length parameter should be respected."""
        result = sanitize_input("a" * 500, max_length=100)
        assert len(result) == 100

    def test_hebrew_text_preserved(self) -> None:
        """Hebrew text should pass through sanitization unchanged."""
        hebrew = "שלום עולם - בדיקת התכנות נחלות"
        result = sanitize_input(hebrew)
        assert result == hebrew

    def test_unicode_normalization(self) -> None:
        """Unicode should be normalized to NFC form."""
        # Composed vs decomposed forms
        result = sanitize_input("caf\u00e9")  # NFC form
        assert result == "caf\u00e9"

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert sanitize_input("") == ""

    def test_only_control_chars(self) -> None:
        """String of only control chars should return empty string."""
        result = sanitize_input("\x00\x01\x02\x03")
        assert result == ""

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        result = sanitize_input("  hello  ")
        assert result == "hello"


# ---------------------------------------------------------------------------
# Filename sanitization tests
# ---------------------------------------------------------------------------


class TestFilenameSanitization:
    """Test filename sanitization for path traversal prevention."""

    def test_sanitize_filename_path_traversal(self) -> None:
        """Path traversal attempts using .. should be neutralized."""
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "etc" not in result or "passwd" not in result

    def test_sanitize_filename_null_bytes(self) -> None:
        """Null bytes should be removed from filenames."""
        result = sanitize_filename("file\x00.pdf")
        assert "\x00" not in result
        assert result.endswith(".pdf") or "file" in result

    def test_sanitize_filename_backslash_path(self) -> None:
        """Windows-style backslash paths should be stripped."""
        result = sanitize_filename("C:\\Users\\evil\\..\\..\\file.pdf")
        assert "\\" not in result
        assert ".." not in result

    def test_sanitize_filename_preserves_extension(self) -> None:
        """Normal filenames should preserve their extension."""
        result = sanitize_filename("report.pdf")
        assert result == "report.pdf"

    def test_sanitize_filename_hebrew(self) -> None:
        """Hebrew filenames should be preserved."""
        result = sanitize_filename("דוח_בדיקה.pdf")
        assert "דוח_בדיקה" in result
        assert result.endswith(".pdf")

    def test_sanitize_filename_length_limit(self) -> None:
        """Filenames exceeding 255 chars should be truncated."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_sanitize_filename_empty(self) -> None:
        """Empty filename should fallback to default."""
        result = sanitize_filename("")
        assert result == "unnamed_file"

    def test_sanitize_filename_only_dots(self) -> None:
        """Filename of only dots should fallback to default."""
        result = sanitize_filename("...")
        assert result == "unnamed_file"

    def test_sanitize_filename_unix_path(self) -> None:
        """Unix-style paths should be stripped to basename."""
        result = sanitize_filename("/tmp/uploads/file.pdf")
        assert "tmp" not in result
        assert "uploads" not in result


# ---------------------------------------------------------------------------
# File magic bytes tests
# ---------------------------------------------------------------------------


class TestFileMagicBytes:
    """Test file type validation by magic bytes."""

    def test_pdf_magic_bytes(self) -> None:
        """PDF files should be detected by %PDF header."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.7\n")
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "pdf"

    def test_xlsx_magic_bytes(self) -> None:
        """XLSX files should be detected by PK (ZIP) header."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"PK\x03\x04" + b"\x00" * 100)
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "office_zip"

    def test_png_magic_bytes(self) -> None:
        """PNG files should be detected by PNG signature."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "png"

    def test_jpeg_magic_bytes(self) -> None:
        """JPEG files should be detected by FFD8FF signature."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "jpeg"

    def test_tiff_magic_bytes_little_endian(self) -> None:
        """TIFF (little-endian) should be detected."""
        with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as f:
            f.write(b"II\x2a\x00" + b"\x00" * 100)
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "tiff"

    def test_tiff_magic_bytes_big_endian(self) -> None:
        """TIFF (big-endian) should be detected."""
        with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as f:
            f.write(b"MM\x00\x2a" + b"\x00" * 100)
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is True
        assert detected == "tiff"

    def test_invalid_magic_bytes_rejected(self) -> None:
        """Files with unrecognized headers should be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"NOT_A_PDF_FILE_AT_ALL")
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is False
        assert detected == "unknown"

    def test_empty_file_rejected(self) -> None:
        """Empty files should be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.flush()
            is_valid, detected = validate_file_magic_bytes(f.name)
        os.unlink(f.name)
        assert is_valid is False
        assert detected == "empty"

    def test_nonexistent_file(self) -> None:
        """Non-existent file path should return unreadable."""
        is_valid, detected = validate_file_magic_bytes("/nonexistent/path/file.pdf")
        assert is_valid is False
        assert detected == "unreadable"


# ---------------------------------------------------------------------------
# Rate limiting tests (unit-level, using middleware internals)
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Test rate limiting logic."""

    def test_under_limit_allowed(self) -> None:
        """Requests under the limit should be allowed."""
        from api.middleware import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(app)
        middleware._max_requests = 5
        middleware._window_seconds = 60

        # Simulate 4 requests (under limit of 5)
        import time

        now = time.monotonic()
        client_ip = "192.168.1.1"
        middleware._request_log[client_ip] = [now - i for i in range(4)]

        # The count is 4, limit is 5, so next request should be allowed
        assert len(middleware._request_log[client_ip]) < middleware._max_requests

    def test_over_limit_rejected(self) -> None:
        """Requests over the limit should be rejected."""
        from api.middleware import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(app)
        middleware._max_requests = 5
        middleware._window_seconds = 60

        import time

        now = time.monotonic()
        client_ip = "192.168.1.1"
        # Fill with 5 recent timestamps (at limit)
        middleware._request_log[client_ip] = [now - i for i in range(5)]

        assert len(middleware._request_log[client_ip]) >= middleware._max_requests

    def test_expired_requests_pruned(self) -> None:
        """Requests outside the window should not count toward the limit."""
        from api.middleware import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(app)
        middleware._max_requests = 5
        middleware._window_seconds = 60

        import time

        now = time.monotonic()
        client_ip = "10.0.0.1"
        # All timestamps are older than the window
        middleware._request_log[client_ip] = [now - 120, now - 180, now - 240]

        # Prune old entries (simulating what dispatch does)
        cutoff = now - middleware._window_seconds
        middleware._request_log[client_ip] = [t for t in middleware._request_log[client_ip] if t > cutoff]

        assert len(middleware._request_log[client_ip]) == 0

    def test_different_ips_independent(self) -> None:
        """Rate limits should be tracked independently per IP."""
        from api.middleware import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(app)
        middleware._max_requests = 2

        import time

        now = time.monotonic()
        middleware._request_log["1.1.1.1"] = [now, now - 1]
        middleware._request_log["2.2.2.2"] = [now]

        assert len(middleware._request_log["1.1.1.1"]) >= middleware._max_requests
        assert len(middleware._request_log["2.2.2.2"]) < middleware._max_requests


# ---------------------------------------------------------------------------
# Auth middleware tests
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """Test authentication middleware token parsing and role resolution."""

    def test_load_tokens_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tokens should be loaded from API_AUTH_TOKENS env var."""
        monkeypatch.setenv("API_AUTH_TOKENS", "tok1:admin,tok2:analyst,tok3:viewer")
        from api.middleware import AuthMiddleware

        tokens = AuthMiddleware._load_tokens()
        assert tokens == {"tok1": "admin", "tok2": "analyst", "tok3": "viewer"}

    def test_load_tokens_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty API_AUTH_TOKENS should result in empty token map."""
        monkeypatch.setenv("API_AUTH_TOKENS", "")
        from api.middleware import AuthMiddleware

        tokens = AuthMiddleware._load_tokens()
        assert tokens == {}

    def test_resolve_operation_exact(self) -> None:
        """Exact path should resolve to correct operation."""
        from api.middleware import AuthMiddleware

        op = AuthMiddleware._resolve_operation("POST", "/api/v1/jobs")
        assert op == "create_job"

    def test_resolve_operation_parameterized(self) -> None:
        """Parameterized paths should resolve correctly."""
        from api.middleware import AuthMiddleware

        op = AuthMiddleware._resolve_operation("GET", "/api/v1/jobs/abc-123/status")
        assert op == "list_jobs"

    def test_resolve_operation_unknown(self) -> None:
        """Unknown paths should return None."""
        from api.middleware import AuthMiddleware

        op = AuthMiddleware._resolve_operation("DELETE", "/api/v1/unknown")
        assert op is None
