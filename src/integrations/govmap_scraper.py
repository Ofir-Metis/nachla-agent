"""govmap.gov.il integration (Phase 4).

For Phase 3: manual taba data input only.
Phase 4: Playwright-based scraping of govmap ArcGIS REST APIs.

Per expert review #20: govmap scraping deferred to Phase 3+.
The current code provides a manual fallback.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class GovmapClient:
    """Govmap data retrieval -- manual input fallback for Phase 3."""

    async def get_tabas_for_plot(
        self, gush: int, helka: int
    ) -> list[dict] | None:
        """Attempt to retrieve taba data for a plot.

        Phase 3: Returns None (manual input required).
        Phase 4: Will use Playwright to scrape govmap.gov.il.

        Args:
            gush: Block number (gush).
            helka: Parcel number (helka).

        Returns:
            None in Phase 3 (manual input mode).
        """
        logger.info(
            "Govmap scraping not available (Phase 3). "
            "Manual taba input required for gush=%d, helka=%d",
            gush,
            helka,
        )
        return None

    def is_available(self) -> bool:
        """Check if govmap scraping is available.

        Returns:
            False in Phase 3 (manual input mode).
        """
        return False
