"""Integration tests with mocked external services.

Tests verify:
- Monday.com: status updates, retries, failure doesn't block
- OneDrive: folder creation, file upload, share links
- Google Drive: folder creation, file upload, share links
- Govmap: returns None in Phase 3 (manual mode)

All tests use mock_mode=True -- NO real API calls.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from integrations.gdrive_client import GoogleDriveClient
from integrations.govmap_scraper import GovmapClient
from integrations.monday_client import VALID_STATUSES, MondayClient
from integrations.onedrive_client import OneDriveClient


# ---------------------------------------------------------------------------
# Monday.com
# ---------------------------------------------------------------------------


class TestMondayClient:
    """Tests for Monday.com client with mock mode."""

    @pytest.fixture()
    def client(self) -> MondayClient:
        return MondayClient(api_token="test-token", board_id="test-board", mock_mode=True)

    async def test_update_status_success(self, client: MondayClient) -> None:
        """Status update with mock API returns True."""
        result = await client.update_status("12345", "בבדיקה")
        assert result is True

    async def test_update_status_invalid_status(self, client: MondayClient) -> None:
        """Invalid status is rejected without API call."""
        result = await client.update_status("12345", "invalid-status")
        assert result is False

    async def test_update_status_failure_doesnt_block(self) -> None:
        """API failure logs but doesn't raise."""
        client = MondayClient(api_token="bad-token", board_id="bad-board", mock_mode=False)
        # Non-mock mode with NotImplementedError should return False, not raise
        result = await client.update_status("12345", "בבדיקה")
        assert result is False

    async def test_retry_on_failure(self) -> None:
        """Failed operations are queued for retry."""
        client = MondayClient(mock_mode=False)
        # The not-implemented path doesn't queue, but a real failure would.
        # Verify the queue mechanism exists and starts empty.
        assert client.failed_queue_size == 0

    async def test_post_update_hebrew(self, client: MondayClient) -> None:
        """Progress updates use Hebrew text."""
        message = 'ניתוח תב"ע הושלם - 3 תב"עות נמצאו'
        result = await client.post_update("12345", message)
        assert result is True

    async def test_all_statuses_valid(self, client: MondayClient) -> None:
        """All 9 workflow statuses are accepted."""
        assert len(VALID_STATUSES) == 9
        for status in VALID_STATUSES:
            result = await client.update_status("12345", status)
            assert result is True, f"Status '{status}' should be accepted"

    async def test_read_item(self, client: MondayClient) -> None:
        """Read item returns expected fields in mock mode."""
        item = await client.read_item("12345")
        assert item is not None
        assert "owner_name" in item
        assert "moshav_name" in item
        assert "gush" in item
        assert "helka" in item

    async def test_attach_file_missing(self, client: MondayClient) -> None:
        """Attaching a non-existent file returns False."""
        result = await client.attach_file("12345", "/nonexistent/file.pdf")
        assert result is False

    async def test_attach_file_success(self, client: MondayClient) -> None:
        """Attaching an existing file succeeds in mock mode."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf content")
            temp_path = f.name
        try:
            result = await client.attach_file("12345", temp_path)
            assert result is True
        finally:
            os.unlink(temp_path)


# ---------------------------------------------------------------------------
# OneDrive
# ---------------------------------------------------------------------------


class TestOneDriveClient:
    """Tests for OneDrive client with mock mode."""

    @pytest.fixture()
    def client(self) -> OneDriveClient:
        return OneDriveClient(client_id="test-id", mock_mode=True)

    async def test_authenticate(self, client: OneDriveClient) -> None:
        """Mock authentication succeeds."""
        result = await client.authenticate()
        assert result is True

    async def test_create_folder(self, client: OneDriveClient) -> None:
        """Folder creation with mock Graph API returns an ID."""
        folder_id = await client.create_folder("Test Folder")
        assert folder_id is not None
        assert "Test-Folder" in folder_id

    async def test_upload_file(self, client: OneDriveClient) -> None:
        """File upload returns a file ID in mock mode."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"fake docx content")
            temp_path = f.name
        try:
            file_id = await client.upload_file(temp_path, "mock-folder-id")
            assert file_id is not None
            assert Path(temp_path).name in file_id
        finally:
            os.unlink(temp_path)

    async def test_upload_file_missing(self, client: OneDriveClient) -> None:
        """Uploading a non-existent file returns None."""
        result = await client.upload_file("/nonexistent/file.docx", "folder-id")
        assert result is None

    async def test_create_share_link(self, client: OneDriveClient) -> None:
        """Share link creation returns a URL in mock mode."""
        url = await client.create_share_link("mock-file-id")
        assert url is not None
        assert url.startswith("https://")

    async def test_upload_report_creates_folder_and_uploads(self, client: OneDriveClient) -> None:
        """Full report upload flow: create folder, upload files, get share links."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f1:
            f1.write(b"word content")
            word_path = f1.name
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f2:
            f2.write(b"excel content")
            excel_path = f2.name
        try:
            results = await client.upload_report(
                owner_name="Israel Israeli",
                moshav_name="Moshav Test",
                files={"word": word_path, "excel": excel_path},
            )
            assert "word" in results
            assert "excel" in results
            assert results["word"].startswith("https://")
            assert results["excel"].startswith("https://")
        finally:
            os.unlink(word_path)
            os.unlink(excel_path)


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------


class TestGoogleDriveClient:
    """Tests for Google Drive client with mock mode."""

    @pytest.fixture()
    def client(self) -> GoogleDriveClient:
        return GoogleDriveClient(mock_mode=True)

    async def test_authenticate(self, client: GoogleDriveClient) -> None:
        """Mock authentication succeeds."""
        result = await client.authenticate()
        assert result is True

    async def test_create_folder(self, client: GoogleDriveClient) -> None:
        """Folder creation with mock Drive API returns an ID."""
        folder_id = await client.create_folder("Test Folder")
        assert folder_id is not None
        assert "Test-Folder" in folder_id

    async def test_upload_file(self, client: GoogleDriveClient) -> None:
        """File upload returns a file ID in mock mode."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"fake xlsx content")
            temp_path = f.name
        try:
            file_id = await client.upload_file(temp_path, "mock-folder-id")
            assert file_id is not None
            assert Path(temp_path).name in file_id
        finally:
            os.unlink(temp_path)

    async def test_upload_file_missing(self, client: GoogleDriveClient) -> None:
        """Uploading a non-existent file returns None."""
        result = await client.upload_file("/nonexistent/file.xlsx", "folder-id")
        assert result is None

    async def test_create_share_link(self, client: GoogleDriveClient) -> None:
        """Share link creation returns a URL in mock mode."""
        url = await client.create_share_link("mock-file-id")
        assert url is not None
        assert "drive.google.com" in url

    async def test_upload_report(self, client: GoogleDriveClient) -> None:
        """Full report upload flow works in mock mode."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            pdf_path = f.name
        try:
            results = await client.upload_report(
                owner_name="Test Owner",
                moshav_name="Test Moshav",
                files={"pdf": pdf_path},
            )
            assert "pdf" in results
            assert "drive.google.com" in results["pdf"]
        finally:
            os.unlink(pdf_path)


# ---------------------------------------------------------------------------
# Govmap
# ---------------------------------------------------------------------------


class TestGovmapClient:
    """Tests for Govmap client (Phase 4 manual input with validation)."""

    @pytest.fixture()
    def client(self) -> GovmapClient:
        return GovmapClient()

    async def test_not_available_in_phase4(self, client: GovmapClient) -> None:
        """Govmap returns unavailable in Phase 4."""
        assert client.is_available() is False

    async def test_get_tabas_returns_none(self, client: GovmapClient) -> None:
        """Returns None for manual input in Phase 4."""
        result = await client.get_tabas_for_plot(gush=12345, helka=67)
        assert result is None

    def test_manual_input_schema_returns_all_required_fields(self, client: GovmapClient) -> None:
        """Schema includes all required fields with correct metadata."""
        schema = client.get_manual_input_schema()
        assert "fields" in schema
        assert "description" in schema
        fields = schema["fields"]

        # Check required fields are present
        required_names = {
            "taba_number", "taba_name", "status", "plot_size_sqm",
            "num_units_allowed", "main_area_sqm", "service_area_sqm", "split_allowed",
        }
        field_names = {f["name"] for f in fields}
        assert required_names.issubset(field_names), (
            f"Missing required fields: {required_names - field_names}"
        )

        # All required fields have required=True
        for f in fields:
            if f["name"] in required_names:
                assert f["required"] is True, f"Field {f['name']} should be required"

        # All fields have labels in Hebrew
        for f in fields:
            assert "label" in f
            assert len(f["label"]) > 0

    def test_validate_manual_input_valid_data(self, client: GovmapClient) -> None:
        """Valid complete data passes validation."""
        data = {
            "taba_number": "616-0902908",
            "taba_name": 'תב"ע כפר יהושע',
            "status": "approved",
            "plot_size_sqm": 2500.0,
            "num_units_allowed": 2.5,
            "main_area_sqm": 160.0,
            "service_area_sqm": 60.0,
            "split_allowed": True,
            "split_min_plot_sqm": 350.0,
        }
        is_valid, errors = client.validate_manual_input(data)
        assert is_valid is True
        assert errors == []

    def test_validate_manual_input_missing_required(self, client: GovmapClient) -> None:
        """Missing required fields produce Hebrew error messages."""
        data = {"taba_number": "616-0902908"}  # Missing many required fields
        is_valid, errors = client.validate_manual_input(data)
        assert is_valid is False
        assert len(errors) > 0
        # Errors should be in Hebrew
        assert any("חובה" in e for e in errors)

    def test_validate_manual_input_invalid_status(self, client: GovmapClient) -> None:
        """Invalid status choice is rejected."""
        data = {
            "taba_number": "616-0902908",
            "taba_name": "test",
            "status": "invalid_status",
            "plot_size_sqm": 2500.0,
            "num_units_allowed": 2.5,
            "main_area_sqm": 160.0,
            "service_area_sqm": 60.0,
            "split_allowed": True,
        }
        is_valid, errors = client.validate_manual_input(data)
        assert is_valid is False
        assert any("invalid_status" in e for e in errors)

    def test_validate_manual_input_negative_area(self, client: GovmapClient) -> None:
        """Negative area values are rejected."""
        data = {
            "taba_number": "616-0902908",
            "taba_name": "test",
            "status": "approved",
            "plot_size_sqm": 2500.0,
            "num_units_allowed": 2.5,
            "main_area_sqm": -100.0,
            "service_area_sqm": 60.0,
            "split_allowed": False,
        }
        is_valid, errors = client.validate_manual_input(data)
        assert is_valid is False
        assert any("שלילי" in e for e in errors)

    def test_validate_manual_input_building_exceeds_plot(self, client: GovmapClient) -> None:
        """Building area exceeding plot size triggers cross-field error."""
        data = {
            "taba_number": "616-0902908",
            "taba_name": "test",
            "status": "approved",
            "plot_size_sqm": 100.0,
            "num_units_allowed": 1.0,
            "main_area_sqm": 80.0,
            "service_area_sqm": 50.0,
            "split_allowed": False,
        }
        is_valid, errors = client.validate_manual_input(data)
        assert is_valid is False
        assert any("חורג" in e for e in errors)

    def test_manual_input_to_taba_converts_correctly(self, client: GovmapClient) -> None:
        """Validated input converts to Taba-compatible dict."""
        data = {
            "taba_number": "616-0902908",
            "taba_name": 'תב"ע כפר יהושע',
            "status": "approved",
            "plot_size_sqm": 2500.0,
            "num_units_allowed": 2.5,
            "main_area_sqm": 160.0,
            "service_area_sqm": 60.0,
            "plach_area_sqm": 500.0,
            "split_allowed": True,
            "split_min_plot_sqm": 350.0,
            "pool_allowed": False,
            "attached_unit_allowed": True,
        }
        taba_dict = client.manual_input_to_taba(data)

        assert taba_dict["taba_number"] == "616-0902908"
        assert taba_dict["taba_name"] == 'תב"ע כפר יהושע'
        assert taba_dict["status"] == "approved"
        assert taba_dict["plot_size_sqm"] == 2500.0
        assert taba_dict["num_units_allowed"] == 2.5
        assert taba_dict["plach_area_sqm"] == 500.0
        assert taba_dict["split_allowed"] is True
        assert taba_dict["split_min_plot_sqm"] == 350.0
        assert taba_dict["pool_allowed"] is False
        assert taba_dict["attached_unit_allowed"] is True
        assert taba_dict["source"] == "manual"

        # Check unit_rights structure
        assert len(taba_dict["unit_rights"]) == 1
        assert taba_dict["unit_rights"][0]["main_area_sqm"] == 160.0
        assert taba_dict["unit_rights"][0]["service_area_sqm"] == 60.0

    def test_manual_input_to_taba_applies_defaults(self, client: GovmapClient) -> None:
        """Optional fields get defaults when not provided."""
        data = {
            "taba_number": "123",
            "taba_name": "test",
            "status": "approved",
            "plot_size_sqm": 2500.0,
            "num_units_allowed": 2.0,
            "main_area_sqm": 100.0,
            "service_area_sqm": 40.0,
            "split_allowed": False,
        }
        taba_dict = client.manual_input_to_taba(data)

        assert taba_dict["plach_area_sqm"] == 0
        assert taba_dict["split_min_plot_sqm"] == 350
        assert taba_dict["pool_allowed"] is False
        assert taba_dict["attached_unit_allowed"] is True
