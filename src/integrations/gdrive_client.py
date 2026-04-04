"""Google Drive integration via official Google API client.

Uses google-api-python-client (official Google SDK), NOT a hobby MCP server.
Per expert review #13: hobby MCP servers for cloud storage are not production-ready.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import partial
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Retry constants
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2

# MIME types for common report formats
_MIME_TYPES: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".txt": "text/plain",
}


class GoogleDriveClient:
    """Google Drive file upload and folder management.

    Uses google-api-python-client for all operations.
    """

    def __init__(
        self,
        credentials_path: str | None = None,
        *,
        mock_mode: bool = False,
    ) -> None:
        """Initialize with Google service account credentials.

        Args:
            credentials_path: Path to service account JSON key file.
                Falls back to GOOGLE_DRIVE_CREDENTIALS_PATH env var.
            mock_mode: If True, simulate all API calls.
        """
        self._credentials_path = credentials_path or os.getenv(
            "GOOGLE_DRIVE_CREDENTIALS_PATH", ""
        )
        self._mock_mode = mock_mode
        self._service: Any = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with Google Drive API using a service account.

        Returns:
            True if authentication succeeded, False otherwise.
        """
        if self._mock_mode:
            self._authenticated = True
            logger.info("Mock: Google Drive authentication successful")
            return True

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self._credentials_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )

            loop = asyncio.get_event_loop()
            self._service = await loop.run_in_executor(
                None,
                partial(build, "drive", "v3", credentials=credentials),
            )
            self._authenticated = True
            logger.info("Google Drive authentication successful")
            return True
        except ImportError:
            logger.error(
                "google-api-python-client or google-auth not installed. "
                "Install with: pip install google-api-python-client google-auth"
            )
            return False
        except FileNotFoundError:
            logger.error(
                "Google credentials file not found: %s", self._credentials_path
            )
            return False
        except Exception:
            logger.error("Google Drive authentication failed", exc_info=True)
            return False

    async def create_folder(
        self, folder_name: str, parent_id: str | None = None
    ) -> str | None:
        """Create a folder if it doesn't exist.

        Args:
            folder_name: Name for the new folder.
            parent_id: Parent folder ID (None for root).

        Returns:
            Folder ID or None on failure.
        """
        if self._mock_mode:
            folder_id = f"mock-gdrive-folder-{folder_name.replace(' ', '-')}"
            logger.info(
                "Mock: Created Google Drive folder '%s' -> %s", folder_name, folder_id
            )
            return folder_id

        return await self._with_retry(
            "create_folder", self._create_folder_impl, folder_name, parent_id
        )

    async def _create_folder_impl(
        self, folder_name: str, parent_id: str | None
    ) -> str | None:
        """Internal folder creation via Drive API."""
        if not self._service:
            logger.error("Google Drive client not authenticated")
            return None

        try:
            # Check if folder already exists
            safe_name = folder_name.replace("'", "\\'")
            query = f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._service.files()
                .list(q=query, spaces="drive", fields="files(id, name)")
                .execute(),
            )

            existing = results.get("files", [])
            if existing:
                logger.info(
                    "Google Drive folder '%s' already exists (ID: %s)",
                    folder_name,
                    existing[0]["id"],
                )
                return existing[0]["id"]

            # Create new folder
            file_metadata: dict[str, Any] = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                file_metadata["parents"] = [parent_id]

            folder = await loop.run_in_executor(
                None,
                lambda: self._service.files()
                .create(body=file_metadata, fields="id")
                .execute(),
            )

            folder_id = folder.get("id")
            logger.info(
                "Created Google Drive folder '%s' (ID: %s)", folder_name, folder_id
            )
            return folder_id
        except Exception:
            logger.error(
                "Failed to create Google Drive folder '%s'",
                folder_name,
                exc_info=True,
            )
            raise

    async def upload_file(self, local_path: str, folder_id: str) -> str | None:
        """Upload a file to Google Drive.

        Args:
            local_path: Path to the local file.
            folder_id: Google Drive folder ID to upload into.

        Returns:
            The file's ID, or None on failure.
        """
        if not os.path.exists(local_path):
            logger.error("File not found for Google Drive upload: %s", local_path)
            return None

        if self._mock_mode:
            file_name = Path(local_path).name
            file_id = f"mock-gdrive-file-{file_name}"
            logger.info(
                "Mock: Uploaded '%s' to Google Drive folder %s", file_name, folder_id
            )
            return file_id

        return await self._with_retry(
            "upload_file", self._upload_file_impl, local_path, folder_id
        )

    async def _upload_file_impl(self, local_path: str, folder_id: str) -> str | None:
        """Internal file upload via Drive API."""
        if not self._service:
            logger.error("Google Drive client not authenticated")
            return None

        try:
            from googleapiclient.http import MediaFileUpload

            file_name = Path(local_path).name
            suffix = Path(local_path).suffix.lower()
            mime_type = _MIME_TYPES.get(suffix, "application/octet-stream")

            file_metadata: dict[str, Any] = {
                "name": file_name,
                "parents": [folder_id],
            }
            media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute(),
            )

            file_id = result.get("id")
            logger.info(
                "Uploaded '%s' to Google Drive (ID: %s)", file_name, file_id
            )
            return file_id
        except Exception:
            logger.error(
                "Failed to upload '%s' to Google Drive", local_path, exc_info=True
            )
            raise

    async def create_share_link(self, file_id: str) -> str | None:
        """Generate a sharing link for the uploaded file.

        Args:
            file_id: Google Drive file ID.

        Returns:
            Share URL string, or None on failure.
        """
        if self._mock_mode:
            url = f"https://drive.google.com/mock/d/{file_id}/view"
            logger.info("Mock: Created share link for %s: %s", file_id, url)
            return url

        return await self._with_retry(
            "create_share_link", self._create_share_link_impl, file_id
        )

    async def _create_share_link_impl(self, file_id: str) -> str | None:
        """Internal share link creation via Drive API."""
        if not self._service:
            logger.error("Google Drive client not authenticated")
            return None

        try:
            loop = asyncio.get_event_loop()

            # Create 'anyone with link' permission
            permission = {"type": "anyone", "role": "reader"}
            await loop.run_in_executor(
                None,
                lambda: self._service.permissions()
                .create(fileId=file_id, body=permission, fields="id")
                .execute(),
            )

            # Get the web view link
            result = await loop.run_in_executor(
                None,
                lambda: self._service.files()
                .get(fileId=file_id, fields="webViewLink")
                .execute(),
            )

            link = result.get("webViewLink")
            logger.info("Created share link for file %s", file_id)
            return link
        except Exception:
            logger.error(
                "Failed to create share link for file %s", file_id, exc_info=True
            )
            raise

    async def upload_report(
        self,
        owner_name: str,
        moshav_name: str,
        files: dict[str, str],
    ) -> dict[str, str]:
        """Upload all report files to a client folder.

        Same interface as OneDriveClient.upload_report.

        Args:
            owner_name: Client name for folder.
            moshav_name: Settlement name for folder.
            files: Mapping of file type to local path.

        Returns:
            Mapping of file type to share URL. Missing entries indicate upload failure.
        """
        folder_name = f"{owner_name} - {moshav_name}"
        folder_id = await self.create_folder(folder_name)

        if not folder_id:
            logger.error(
                "Failed to create Google Drive folder '%s', skipping uploads",
                folder_name,
            )
            return {}

        results: dict[str, str] = {}

        for file_type, local_path in files.items():
            file_id = await self.upload_file(local_path, folder_id)
            if file_id:
                share_url = await self.create_share_link(file_id)
                if share_url:
                    results[file_type] = share_url
                else:
                    logger.warning(
                        "Uploaded '%s' but failed to create share link", file_type
                    )
            else:
                logger.warning("Failed to upload '%s' (%s)", file_type, local_path)

        logger.info(
            "Google Drive upload complete for '%s': %d/%d files",
            folder_name,
            len(results),
            len(files),
        )
        return results

    async def _with_retry(
        self,
        operation: str,
        func: Any,
        *args: Any,
    ) -> Any:
        """Execute an operation with exponential backoff retry.

        Args:
            operation: Name of the operation (for logging).
            func: Async callable to execute.
            *args: Arguments to pass to func.

        Returns:
            The result of func(), or None if all attempts failed.
        """
        for attempt in range(_MAX_RETRIES):
            try:
                return await func(*args)
            except Exception:
                wait_time = _BASE_BACKOFF_SECONDS**attempt
                logger.warning(
                    "Google Drive %s failed (attempt %d/%d), retrying in %ds",
                    operation,
                    attempt + 1,
                    _MAX_RETRIES,
                    wait_time,
                    exc_info=True,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait_time)

        logger.error(
            "Google Drive %s failed after %d attempts",
            operation,
            _MAX_RETRIES,
        )
        return None
