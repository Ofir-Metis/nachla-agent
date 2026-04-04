"""OneDrive integration via Microsoft Graph SDK.

Uses msgraph-sdk (official Microsoft SDK), NOT a hobby MCP server.
Per expert review #13: hobby MCP servers for cloud storage are not production-ready.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Retry constants
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2


class OneDriveClient:
    """OneDrive file upload and folder management.

    Creates client folders and uploads generated reports.
    Uses the official msgraph-sdk for all operations.
    """

    def __init__(
        self,
        client_id: str | None = None,
        tenant_id: str = "common",
        client_secret: str | None = None,
        *,
        mock_mode: bool = False,
    ) -> None:
        """Initialize with Microsoft app credentials.

        Args:
            client_id: Azure app client ID. Falls back to ONEDRIVE_CLIENT_ID env var.
            tenant_id: Azure tenant ID. Falls back to ONEDRIVE_TENANT_ID env var.
            client_secret: Azure app client secret. Falls back to ONEDRIVE_CLIENT_SECRET env var.
            mock_mode: If True, simulate all API calls.
        """
        self._client_id = client_id or os.getenv("ONEDRIVE_CLIENT_ID", "")
        self._tenant_id = tenant_id if tenant_id != "common" else os.getenv("ONEDRIVE_TENANT_ID", "common")
        self._client_secret = client_secret or os.getenv("ONEDRIVE_CLIENT_SECRET", "")
        self._mock_mode = mock_mode
        self._graph_client: Any = None
        self._authenticated = False

    async def authenticate(self, credential: Any = None) -> bool:
        """Authenticate with Microsoft Graph.

        Args:
            credential: An azure.identity credential object. If None and not in mock mode,
                        will attempt to create a ClientSecretCredential.

        Returns:
            True if authentication succeeded, False otherwise.
        """
        if self._mock_mode:
            self._authenticated = True
            logger.info("Mock: OneDrive authentication successful")
            return True

        try:
            if credential is None:
                from azure.identity import ClientSecretCredential

                credential = ClientSecretCredential(
                    tenant_id=self._tenant_id,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )

            from msgraph import GraphServiceClient

            self._graph_client = GraphServiceClient(
                credentials=credential,
                scopes=["https://graph.microsoft.com/.default"],
            )
            self._authenticated = True
            logger.info("OneDrive authentication successful")
            return True
        except ImportError:
            logger.error(
                "msgraph-sdk or azure-identity not installed. "
                "Install with: pip install msgraph-sdk azure-identity"
            )
            return False
        except Exception:
            logger.error("OneDrive authentication failed", exc_info=True)
            return False

    async def create_folder(
        self, folder_name: str, parent_path: str = "/"
    ) -> str | None:
        """Create a folder if it doesn't exist.

        Folder name format: "{owner_name} - {moshav_name}"

        Args:
            folder_name: Name for the new folder.
            parent_path: Parent folder path (default: root).

        Returns:
            Folder ID or None on failure.
        """
        if self._mock_mode:
            folder_id = f"mock-folder-{folder_name.replace(' ', '-')}"
            logger.info("Mock: Created OneDrive folder '%s' -> %s", folder_name, folder_id)
            return folder_id

        return await self._with_retry("create_folder", self._create_folder_impl, folder_name, parent_path)

    async def _create_folder_impl(self, folder_name: str, parent_path: str) -> str | None:
        """Internal folder creation via Graph API."""
        if not self._graph_client:
            logger.error("OneDrive client not authenticated")
            return None

        try:
            from msgraph.generated.models.drive_item import DriveItem
            from msgraph.generated.models.folder import Folder

            drive_item = DriveItem(
                name=folder_name,
                folder=Folder(),
                additional_data={"@microsoft.graph.conflictBehavior": "rename"},
            )

            if parent_path == "/":
                result = await self._graph_client.me.drive.root.children.post(drive_item)
            else:
                result = await self._graph_client.me.drive.root.item_with_path(
                    parent_path
                ).children.post(drive_item)

            if result and result.id:
                logger.info("Created OneDrive folder '%s' (ID: %s)", folder_name, result.id)
                return result.id
            return None
        except Exception:
            logger.error("Failed to create OneDrive folder '%s'", folder_name, exc_info=True)
            raise

    async def upload_file(self, local_path: str, remote_folder_id: str) -> str | None:
        """Upload a file to OneDrive.

        Args:
            local_path: Path to the local file.
            remote_folder_id: OneDrive folder ID to upload into.

        Returns:
            The file's ID, or None on failure.
        """
        if not os.path.exists(local_path):
            logger.error("File not found for OneDrive upload: %s", local_path)
            return None

        if self._mock_mode:
            file_name = Path(local_path).name
            file_id = f"mock-file-{file_name}"
            logger.info("Mock: Uploaded '%s' to OneDrive folder %s", file_name, remote_folder_id)
            return file_id

        return await self._with_retry("upload_file", self._upload_file_impl, local_path, remote_folder_id)

    async def _upload_file_impl(self, local_path: str, remote_folder_id: str) -> str | None:
        """Internal file upload via Graph API."""
        if not self._graph_client:
            logger.error("OneDrive client not authenticated")
            return None

        try:
            file_name = Path(local_path).name
            with open(local_path, "rb") as f:
                content = f.read()

            result = await self._graph_client.me.drive.items[remote_folder_id].item_with_path(
                file_name
            ).content.put(content)

            if result and result.id:
                logger.info("Uploaded '%s' to OneDrive (ID: %s)", file_name, result.id)
                return result.id
            return None
        except Exception:
            logger.error("Failed to upload '%s' to OneDrive", local_path, exc_info=True)
            raise

    async def create_share_link(self, file_id: str) -> str | None:
        """Generate a sharing link for the uploaded file.

        Args:
            file_id: OneDrive file ID.

        Returns:
            Share URL string, or None on failure.
        """
        if self._mock_mode:
            url = f"https://onedrive.mock/share/{file_id}"
            logger.info("Mock: Created share link for %s: %s", file_id, url)
            return url

        return await self._with_retry("create_share_link", self._create_share_link_impl, file_id)

    async def _create_share_link_impl(self, file_id: str) -> str | None:
        """Internal share link creation via Graph API."""
        if not self._graph_client:
            logger.error("OneDrive client not authenticated")
            return None

        try:
            from msgraph.generated.drives.item.items.item.create_link.create_link_post_request_body import (
                CreateLinkPostRequestBody,
            )

            body = CreateLinkPostRequestBody(type="view", scope="anonymous")
            result = await self._graph_client.me.drive.items[file_id].create_link.post(body)

            if result and result.link and result.link.web_url:
                logger.info("Created share link for file %s", file_id)
                return result.link.web_url
            return None
        except Exception:
            logger.error("Failed to create share link for file %s", file_id, exc_info=True)
            raise

    async def upload_report(
        self,
        owner_name: str,
        moshav_name: str,
        files: dict[str, str],
    ) -> dict[str, str]:
        """Upload all report files to a client folder.

        Creates a folder named "{owner_name} - {moshav_name}" and uploads
        all provided files, returning share links for each.

        Args:
            owner_name: Client name for folder.
            moshav_name: Settlement name for folder.
            files: Mapping of file type to local path, e.g.
                   {"word": "/path/to/report.docx", "excel": "/path/to/calc.xlsx"}

        Returns:
            Mapping of file type to share URL. Missing entries indicate upload failure.
        """
        folder_name = f"{owner_name} - {moshav_name}"
        folder_id = await self.create_folder(folder_name)

        if not folder_id:
            logger.error("Failed to create OneDrive folder '%s', skipping uploads", folder_name)
            return {}

        results: dict[str, str] = {}

        for file_type, local_path in files.items():
            file_id = await self.upload_file(local_path, folder_id)
            if file_id:
                share_url = await self.create_share_link(file_id)
                if share_url:
                    results[file_type] = share_url
                else:
                    logger.warning("Uploaded '%s' but failed to create share link", file_type)
            else:
                logger.warning("Failed to upload '%s' (%s)", file_type, local_path)

        logger.info(
            "OneDrive upload complete for '%s': %d/%d files",
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
                wait_time = _BASE_BACKOFF_SECONDS**attempt  # 1s, 2s, 4s
                logger.warning(
                    "OneDrive %s failed (attempt %d/%d), retrying in %ds",
                    operation,
                    attempt + 1,
                    _MAX_RETRIES,
                    wait_time,
                    exc_info=True,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait_time)

        logger.error(
            "OneDrive %s failed after %d attempts",
            operation,
            _MAX_RETRIES,
        )
        return None
