"""Monday.com integration for workflow status tracking.

Uses the official @mondaycom/mcp hosted at mcp.monday.com.
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

logger = logging.getLogger(__name__)

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
        """Initialize with Monday.com API token and board ID.

        Args:
            api_token: Monday.com API token. Falls back to MONDAY_API_TOKEN env var.
            board_id: Default board ID. Falls back to MONDAY_BOARD_ID env var.
            mock_mode: If True, simulate all API calls without contacting Monday.com.
        """
        self._api_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        self._board_id = board_id or os.getenv("MONDAY_BOARD_ID", "")
        self._mock_mode = mock_mode
        self._failed_queue: deque[FailedOperation] = deque(maxlen=1000)

    @property
    def failed_queue_size(self) -> int:
        """Number of operations waiting for retry."""
        return len(self._failed_queue)

    async def read_item(self, item_id: str) -> dict[str, Any] | None:
        """Read client data from a Monday.com item.

        Returns dict with keys: owner_name, moshav_name, gush, helka, or None on failure.
        """

        async def _do_read() -> dict[str, Any] | None:
            if self._mock_mode:
                return {
                    "id": item_id,
                    "owner_name": "mock_owner",
                    "moshav_name": "mock_moshav",
                    "gush": 0,
                    "helka": 0,
                }
            # MCP call: the monday MCP server exposes GraphQL queries.
            # In production, this would invoke the MCP tool to run:
            #   query { items(ids: [<item_id>]) { name column_values { id text value } } }
            # For now, structured as a placeholder for MCP integration.
            raise NotImplementedError(
                "MCP-based Monday.com read not yet wired. "
                "Use mock_mode=True for testing."
            )

        return await self._execute_with_retry("read_item", _do_read)

    async def update_status(self, item_id: str, status: str) -> bool:
        """Update item status (column value).

        Args:
            item_id: The Monday.com item ID.
            status: One of the valid workflow statuses.

        Returns:
            True if the update succeeded, False otherwise.
        """
        if status not in VALID_STATUSES:
            logger.error(
                "Invalid Monday.com status '%s'. Valid statuses: %s",
                status,
                VALID_STATUSES,
            )
            return False

        async def _do_update() -> bool:
            if self._mock_mode:
                logger.info("Mock: Updated item %s status to '%s'", item_id, status)
                return True
            # MCP call placeholder:
            #   mutation { change_column_value(
            #     board_id: <board_id>, item_id: <item_id>,
            #     column_id: "status", value: "{\"label\":\"<status>\"}"
            #   ) { id } }
            raise NotImplementedError(
                "MCP-based Monday.com update not yet wired. "
                "Use mock_mode=True for testing."
            )

        result = await self._execute_with_retry("update_status", _do_update)
        return result is True

    async def post_update(self, item_id: str, message: str) -> bool:
        """Post a progress update note on the item.

        Args:
            item_id: The Monday.com item ID.
            message: Hebrew text update, e.g. "ניתוח תב\"ע הושלם - 3 תב\"עות נמצאו"

        Returns:
            True if the post succeeded, False otherwise.
        """

        async def _do_post() -> bool:
            if self._mock_mode:
                logger.info("Mock: Posted update on item %s: '%s'", item_id, message)
                return True
            # MCP call placeholder:
            #   mutation { create_update(item_id: <item_id>, body: "<message>") { id } }
            raise NotImplementedError(
                "MCP-based Monday.com post not yet wired. "
                "Use mock_mode=True for testing."
            )

        result = await self._execute_with_retry("post_update", _do_post)
        return result is True

    async def attach_file(self, item_id: str, file_path: str) -> bool:
        """Attach a generated report file to the item.

        Args:
            item_id: The Monday.com item ID.
            file_path: Local path to the file to attach.

        Returns:
            True if the attachment succeeded, False otherwise.
        """
        if not os.path.exists(file_path):
            logger.error("File not found for Monday.com attachment: %s", file_path)
            return False

        async def _do_attach() -> bool:
            if self._mock_mode:
                logger.info(
                    "Mock: Attached file '%s' to item %s", file_path, item_id
                )
                return True
            # MCP call placeholder:
            #   mutation { add_file_to_column(
            #     item_id: <item_id>, column_id: "files", file: <file>
            #   ) { id } }
            raise NotImplementedError(
                "MCP-based Monday.com file attach not yet wired. "
                "Use mock_mode=True for testing."
            )

        result = await self._execute_with_retry("attach_file", _do_attach)
        return result is True

    async def _execute_with_retry(
        self,
        operation: str,
        func: Any,
        *,
        max_retries: int = 3,
    ) -> Any:
        """Execute Monday.com operation with retry and exponential backoff.

        If all retries fail, log the failure and return None.
        NEVER raises -- Monday.com failures must not block the workflow.

        Args:
            operation: Name of the operation (for logging).
            func: Async callable to execute.
            max_retries: Maximum retry attempts.

        Returns:
            The result of func(), or None if all attempts failed.
        """
        for attempt in range(max_retries):
            try:
                return await func()
            except NotImplementedError:
                # Not-yet-wired operations should not retry
                logger.warning(
                    "Monday.com %s: not implemented (MCP integration pending)",
                    operation,
                )
                return None
            except Exception:
                wait_time = 2**attempt  # 1s, 2s, 4s
                logger.warning(
                    "Monday.com %s failed (attempt %d/%d), retrying in %ds",
                    operation,
                    attempt + 1,
                    max_retries,
                    wait_time,
                    exc_info=True,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

        # All retries exhausted -- queue for later
        logger.error(
            "Monday.com %s failed after %d attempts. Queued for later retry.",
            operation,
            max_retries,
        )
        self._queue_failed_update(operation, ())
        return None

    def _queue_failed_update(self, operation: str, args: tuple[Any, ...]) -> None:
        """Queue a failed update for later retry.

        Args:
            operation: Name of the failed operation.
            args: Original arguments for the operation.
        """
        self._failed_queue.append(
            FailedOperation(operation=operation, args=args, kwargs={})
        )
        logger.info(
            "Queued failed Monday.com operation '%s'. Queue size: %d",
            operation,
            len(self._failed_queue),
        )

    async def retry_failed_operations(self) -> int:
        """Attempt to retry all queued failed operations.

        Returns:
            Number of operations successfully retried.
        """
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
                    op.operation,
                    op.attempts,
                )
                continue
            # For now, just re-queue since MCP is not wired
            remaining.append(op)

        self._failed_queue = remaining
        return retried
