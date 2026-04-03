"""Application settings and configuration loader.

Loads environment variables and regulatory rate constants from rates_config.json.
All regulatory constants must come from the config file, never hardcoded.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables and config files.

    API keys and secrets come from .env file. Regulatory rates and constants
    come from rates_config.json with effective date support.
    """

    # API keys
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    monday_api_token: str = ""
    monday_board_id: str = ""
    onedrive_client_id: str = ""
    onedrive_client_secret: str = ""
    onedrive_tenant_id: str = ""
    onedrive_redirect_uri: str = "http://localhost:8000/auth/callback"
    google_drive_credentials_path: str = ""

    # App config
    log_level: str = "INFO"

    # Rates config (loaded from JSON, not from env)
    rates_config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def load_rates_config(self) -> dict[str, Any]:
        """Load rates from rates_config.json.

        Returns:
            The loaded rates configuration dictionary.

        Raises:
            FileNotFoundError: If rates_config.json does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        config_path = Path(__file__).parent / "rates_config.json"
        with open(config_path, encoding="utf-8") as f:
            self.rates_config = json.load(f)
        return self.rates_config

    def get_rate(self, key: str, effective_date: str | None = None) -> float:
        """Get a rate value, optionally checking effective date.

        Supports dotted key paths like 'vat.rate' or 'usage_fees.residential'.

        Args:
            key: Dotted path to the rate value in rates_config.
            effective_date: ISO date string (YYYY-MM-DD) for date-dependent rates.

        Returns:
            The rate value as a float.

        Raises:
            KeyError: If the key path does not exist in the config.
            ValueError: If the value at the key path is not numeric.
        """
        if not self.rates_config:
            self.load_rates_config()

        # Navigate dotted path
        parts = key.split(".")
        current: Any = self.rates_config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Rate key '{key}' not found in rates_config.json")

        # Handle date-dependent rates (e.g., VAT changed from 17% to 18%)
        if effective_date and isinstance(current, dict) and "rate" in current:
            date = datetime.strptime(effective_date, "%Y-%m-%d").date()
            effective = current.get("effective_date")
            if effective:
                effective_dt = datetime.strptime(effective, "%Y-%m-%d").date()
                if date < effective_dt and "previous" in current:
                    return float(current["previous"]["rate"])
            return float(current["rate"])

        if isinstance(current, (int, float)):
            return float(current)

        raise ValueError(f"Rate key '{key}' resolved to non-numeric value: {current}")

    def get_priority_discount(self, priority_area: str, field: str) -> float | None:
        """Get a priority area discount value.

        Args:
            priority_area: Priority area code ('A', 'B', 'frontline', or 'none').
            field: The discount field name (e.g., 'permit_fee_discount', 'usage_fee_rate').

        Returns:
            The discount value, or None if the area has no discounts.
        """
        if not self.rates_config:
            self.load_rates_config()

        if priority_area == "none" or priority_area is None:
            return None

        discounts = self.rates_config.get("priority_area_discounts", {})
        area_config = discounts.get(priority_area, {})
        value = area_config.get(field)
        return float(value) if value is not None else None

    def check_data_freshness(self) -> tuple[bool, str]:
        """Check if rates_config data is within acceptable freshness window.

        Returns:
            Tuple of (is_fresh, message). is_fresh is False if data is stale.
        """
        if not self.rates_config:
            self.load_rates_config()

        last_updated = self.rates_config.get("_last_updated")
        if not last_updated:
            return False, "No _last_updated date found in rates_config.json"

        updated_date = datetime.strptime(last_updated, "%Y-%m-%d").date()
        days_old = (datetime.now().date() - updated_date).days
        warning_days = self.rates_config.get("data_freshness_warning_days", 90)

        if days_old > warning_days:
            return False, (
                f"rates_config.json was last updated {days_old} days ago ({last_updated}). "
                f"Data older than {warning_days} days may contain outdated rates."
            )

        return True, f"Rates data is current (last updated: {last_updated}, {days_old} days ago)"


# Module-level singleton for convenience
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get or create the application settings singleton.

    Returns:
        The AppSettings instance with rates loaded.
    """
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = AppSettings()
        _settings.load_rates_config()
    return _settings
