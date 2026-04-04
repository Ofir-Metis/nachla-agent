"""External service integrations.

- Monday.com: workflow status tracking via @mondaycom/mcp
- OneDrive: file upload via msgraph-sdk (official Microsoft SDK)
- Google Drive: file upload via google-api-python-client (official Google SDK)
- Govmap: govmap.gov.il scraping (Phase 4, manual fallback in Phase 3)
"""

from integrations.gdrive_client import GoogleDriveClient
from integrations.govmap_scraper import GovmapClient
from integrations.monday_client import MondayClient
from integrations.onedrive_client import OneDriveClient

__all__ = [
    "GoogleDriveClient",
    "GovmapClient",
    "MondayClient",
    "OneDriveClient",
]
