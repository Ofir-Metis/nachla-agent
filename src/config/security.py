"""Security module: RBAC roles, input sanitization, file upload security.

Roles:
- admin: full access (manage users, configure settings, all operations)
- analyst: create and view reports, upload files, confirm classifications
- viewer: view reports only (read-only access)
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from pathlib import PurePosixPath


class Role(StrEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Permission matrix: role -> set of allowed operations
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "create_job",
        "upload_files",
        "confirm_classification",
        "download_report",
        "list_jobs",
        "cancel_job",
        "manage_users",
        "configure",
    },
    Role.ANALYST: {
        "create_job",
        "upload_files",
        "confirm_classification",
        "download_report",
        "list_jobs",
    },
    Role.VIEWER: {
        "download_report",
        "list_jobs",
    },
}

# Endpoint-to-operation mapping for RBAC middleware
ENDPOINT_OPERATIONS: dict[str, str] = {
    "POST /api/v1/jobs": "create_job",
    "POST /api/v1/jobs/{job_id}/files": "upload_files",
    "POST /api/v1/jobs/{job_id}/classify/confirm": "confirm_classification",
    "GET /api/v1/jobs/{job_id}/download/{file_type}": "download_report",
    "GET /api/v1/jobs/{job_id}/status": "list_jobs",
}

# Maximum input text length (characters)
MAX_INPUT_LENGTH = 10_000

# Maximum filename length
MAX_FILENAME_LENGTH = 255

# Magic byte signatures for allowed file types
MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF",),
    "xlsx": (b"PK\x03\x04",),
    "docx": (b"PK\x03\x04",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpeg": (b"\xff\xd8\xff",),
    "tiff_le": (b"II\x2a\x00",),
    "tiff_be": (b"MM\x00\x2a",),
}


def check_permission(role: str, operation: str) -> bool:
    """Check if a role has permission for an operation.

    Args:
        role: The user role string.
        operation: The operation to check.

    Returns:
        True if the role has permission, False otherwise.
    """
    try:
        role_enum = Role(role)
    except ValueError:
        return False

    permissions = ROLE_PERMISSIONS.get(role_enum, set())
    return operation in permissions


def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Sanitize user input text.

    Strips control characters (except common whitespace), normalizes Unicode,
    and limits length.

    Args:
        text: Raw input text.
        max_length: Maximum allowed length after sanitization.

    Returns:
        Sanitized text string.
    """
    # Normalize Unicode to NFC form
    text = unicodedata.normalize("NFC", text)

    # Strip control characters except tab, newline, carriage return
    allowed_control = {"\t", "\n", "\r"}
    cleaned = []
    for ch in text:
        if unicodedata.category(ch).startswith("C") and ch not in allowed_control:
            continue
        cleaned.append(ch)
    text = "".join(cleaned)

    # Strip null bytes explicitly
    text = text.replace("\x00", "")

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def validate_file_magic_bytes(file_path: str) -> tuple[bool, str]:
    """Validate file type by checking magic bytes (not just extension).

    Checks the first few bytes of the file against known signatures for
    PDF, XLSX, DOCX, PNG, JPEG, and TIFF.

    Args:
        file_path: Path to the file to validate.

    Returns:
        Tuple of (is_valid, detected_type). detected_type is 'unknown'
        if no match found.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
    except (OSError, FileNotFoundError):
        return False, "unreadable"

    if not header:
        return False, "empty"

    # Check each signature
    if header.startswith(b"%PDF"):
        return True, "pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, "png"
    if header.startswith(b"\xff\xd8\xff"):
        return True, "jpeg"
    if header.startswith(b"II\x2a\x00") or header.startswith(b"MM\x00\x2a"):
        return True, "tiff"
    if header.startswith(b"PK\x03\x04"):
        # PK signature covers both XLSX and DOCX (ZIP-based Office formats)
        return True, "office_zip"

    return False, "unknown"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and injection.

    Removes path separators, parent directory references, null bytes,
    and other dangerous characters. Limits length to MAX_FILENAME_LENGTH.

    Args:
        filename: Raw filename string.

    Returns:
        Sanitized filename safe for filesystem use.
    """
    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Extract just the filename component (strip any path)
    filename = PurePosixPath(filename).name
    # Also handle Windows-style paths
    if "\\" in filename:
        filename = filename.rsplit("\\", 1)[-1]

    # Remove parent directory references
    filename = filename.replace("..", "")

    # Remove characters that are problematic on filesystems
    # Allow: alphanumeric, dot, hyphen, underscore, space, Hebrew chars
    filename = re.sub(r"[^\w\s.\-\u0590-\u05FF]", "", filename)

    # Collapse multiple dots (prevent hidden files tricks)
    filename = re.sub(r"\.{2,}", ".", filename)

    # Strip leading/trailing whitespace and dots
    filename = filename.strip(". \t")

    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        # Preserve extension
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            max_name = MAX_FILENAME_LENGTH - len(ext) - 1
            filename = f"{name[:max_name]}.{ext}"
        else:
            filename = filename[:MAX_FILENAME_LENGTH]

    # Fallback if filename is empty after sanitization
    if not filename:
        filename = "unnamed_file"

    return filename
