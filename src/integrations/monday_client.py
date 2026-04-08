"""Monday.com integration for workflow status tracking.

Uses Monday.com GraphQL API v2 via httpx.
CRITICAL: Monday.com failures NEVER block the main workflow.
All calls are fire-and-forget with retry queue.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"

# Valid workflow statuses (from agent_workflow_flow.md step 14.2)
VALID_STATUSES: set[str] = {
    "בבדיקה",
    "ניתוח תב\"ע הושלם",
    "מיפוי מבנים הושלם",
    "טיוטה מוכנה",
    "בבקרה",
    "מאושר",
    "לתיקונים",
    "חסר מידע - ממתין ללקוח",
    "נכשל - דורש טיפול ידני",
}


@dataclass
class FailedOperation:
    """A Monday.com operation that failed and should be retried later."""

    operation: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    attempts: int = 0


class MondayClient:
    """Monday.com client for nachla workflow status tracking.

    Status flow (from workflow step 14.2):
    - בבדיקה (intake started)
    - ניתוח תב"ע הושלם (taba analysis done)
    - מיפוי מבנים הושלם (building mapping done)
    - טיוטה מוכנה (draft report ready)
    - בבקרה (under review)
    - מאושר (approved) / לתיקונים (needs fixes)
    - חסר מידע - ממתין ללקוח (waiting for client)
    - נכשל - דורש טיפול ידני (failed)
    """

    def __init__(
        self,
        api_token: str | None = None,
        board_id: str | None = None,
        *,
        mock_mode: bool = False,
    ) -> None:
        self._api_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        self._board_id = board_id or os.getenv("MONDAY_BOARD_ID", "")
        self._mock_mode = mock_mode
        self._failed_queue: deque[FailedOperation] = deque(maxlen=1000)
        self._status_column_id = os.getenv("MONDAY_STATUS_COLUMN_ID", "status")

    @property
    def is_configured(self) -> bool:
        """Check if Monday.com credentials are available."""
        return bool(self._api_token and self._board_id)

    @property
    def failed_queue_size(self) -> int:
        """Number of operations waiting for retry."""
        return len(self._failed_queue)

    async def _graphql(self, query: str, variables: dict | None = None) -> dict[str, Any]:
        """Execute a GraphQL query against Monday.com API.

        Args:
            query: GraphQL query string.
            variables: Optional query variables.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On HTTP errors.
            ValueError: On GraphQL errors.
        """
        headers = {
            "Authorization": self._api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        }
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(MONDAY_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data and data["errors"]:
            error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
            raise ValueError(f"Monday.com GraphQL error: {error_msg}")

        return data.get("data", {})

    async def read_item(self, item_id: str) -> dict[str, Any] | None:
        """Read client data from a Monday.com item."""

        async def _do_read() -> dict[str, Any] | None:
            if self._mock_mode:
                return {
                    "id": item_id,
                    "owner_name": "mock_owner",
                    "moshav_name": "mock_moshav",
                    "gush": 0,
                    "helka": 0,
                }
            query = """
                query ($ids: [ID!]!) {
                    items(ids: $ids) {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                        }
                    }
                }
            """
            data = await self._graphql(query, {"ids": [item_id]})
            items = data.get("items", [])
            if not items:
                return None

            item = items[0]
            columns = {cv["id"]: cv["text"] for cv in item.get("column_values", [])}
            return {
                "id": item["id"],
                "name": item.get("name", ""),
                "columns": columns,
            }

        return await self._execute_with_retry("read_item", _do_read)

    async def update_status(self, item_id: str, status: str) -> bool:
        """Update item status column value."""
        if status not in VALID_STATUSES:
            logger.error("Invalid Monday.com status '%s'. Valid: %s", status, VALID_STATUSES)
            return False

        async def _do_update() -> bool:
            if self._mock_mode:
                logger.info("Mock: Updated item %s status to '%s'", item_id, status)
                return True
            import json
            query = """
                mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
                    change_column_value(
                        board_id: $boardId
                        item_id: $itemId
                        column_id: $columnId
                        value: $value
                    ) { id }
                }
            """
            value = json.dumps({"label": status})
            await self._graphql(query, {
                "boardId": self._board_id,
                "itemId": item_id,
                "columnId": self._status_column_id,
                "value": value,
            })
            logger.info("Monday.com: Updated item %s status to '%s'", item_id, status)
            return True

        result = await self._execute_with_retry("update_status", _do_update)
        return result is True

    async def post_update(self, item_id: str, message: str) -> bool:
        """Post a progress update note on the item."""

        async def _do_post() -> bool:
            if self._mock_mode:
                logger.info("Mock: Posted update on item %s: '%s'", item_id, message)
                return True
            query = """
                mutation ($itemId: ID!, $body: String!) {
                    create_update(item_id: $itemId, body: $body) { id }
                }
            """
            await self._graphql(query, {"itemId": item_id, "body": message})
            logger.info("Monday.com: Posted update on item %s", item_id)
            return True

        result = await self._execute_with_retry("post_update", _do_post)
        return result is True

    async def attach_file(self, item_id: str, file_path: str) -> bool:
        """Attach a generated report file to the item via multipart upload."""
        if not os.path.exists(file_path):
            logger.error("File not found for Monday.com attachment: %s", file_path)
            return False

        async def _do_attach() -> bool:
            if self._mock_mode:
                logger.info("Mock: Attached file '%s' to item %s", file_path, item_id)
                return True

            query = 'mutation ($file: File!) { add_file_to_column(item_id: %s, column_id: "files", file: $file) { id } }' % item_id
            headers = {
                "Authorization": self._api_token,
                "API-Version": "2024-10",
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(file_path, "rb") as f:
                    filename = os.path.basename(file_path)
                    resp = await client.post(
                        MONDAY_API_URL + "/file",
                        headers=headers,
                        data={"query": query},
                        files={"variables[file]": (filename, f)},
                    )
                    resp.raise_for_status()

            logger.info("Monday.com: Attached file '%s' to item %s", file_path, item_id)
            return True

        result = await self._execute_with_retry("attach_file", _do_attach)
        return result is True

    async def _execute_with_retry(
        self,
        operation: str,
        func: Any,
        *,
        max_retries: int = 3,
    ) -> Any:
        """Execute with retry and exponential backoff.

        NEVER raises -- Monday.com failures must not block the workflow.
        """
        if not self.is_configured and not self._mock_mode:
            logger.debug("Monday.com %s: skipped (not configured)", operation)
            return None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception:
                wait_time = 2**attempt
                logger.warning(
                    "Monday.com %s failed (attempt %d/%d), retrying in %ds",
                    operation, attempt + 1, max_retries, wait_time,
                    exc_info=True,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

        logger.error(
            "Monday.com %s failed after %d attempts. Queued for later retry.",
            operation, max_retries,
        )
        self._queue_failed_update(operation, ())
        return None

    def _queue_failed_update(self, operation: str, args: tuple[Any, ...]) -> None:
        """Queue a failed update for later retry."""
        self._failed_queue.append(
            FailedOperation(operation=operation, args=args, kwargs={})
        )
        logger.info(
            "Queued failed Monday.com operation '%s'. Queue size: %d",
            operation, len(self._failed_queue),
        )

    async def retry_failed_operations(self) -> int:
        """Attempt to retry all queued failed operations."""
        if not self._failed_queue:
            return 0

        retried = 0
        remaining: deque[FailedOperation] = deque()

        while self._failed_queue:
            op = self._failed_queue.popleft()
            op.attempts += 1
            if op.attempts > 10:
                logger.warning(
                    "Dropping Monday.com operation '%s' after %d attempts",
                    op.operation, op.attempts,
                )
                continue
            remaining.append(op)

        self._failed_queue = remaining
        return retried
