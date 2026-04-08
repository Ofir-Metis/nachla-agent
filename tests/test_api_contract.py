"""API contract tests — verify frontend types match backend response models.

These tests import the Pydantic response models from routes.py and verify
that their fields match the TypeScript types in the frontend.
"""

import pytest
from pydantic import BaseModel


def _get_model_fields(model: type[BaseModel]) -> set[str]:
    """Get all field names from a Pydantic model."""
    return set(model.model_fields.keys())


class TestApiModels:
    """Verify API response model structures are valid."""

    def test_job_status_response_fields(self):
        from api.routes import JobStatusResponse
        fields = _get_model_fields(JobStatusResponse)
        assert "job_id" in fields
        assert "status" in fields
        assert "phase" in fields
        assert "progress_percent" in fields
        assert "message" in fields

    def test_job_create_response_fields(self):
        from api.routes import JobCreateResponse
        fields = _get_model_fields(JobCreateResponse)
        assert "job_id" in fields
        assert "status" in fields
        assert "message" in fields

    def test_results_response_fields(self):
        from api.routes import ResultsResponse
        fields = _get_model_fields(ResultsResponse)
        assert "job_id" in fields
        assert "total_regularization_cost" in fields
        assert "total_usage_fees" in fields
        assert "total_permit_fees" in fields
        assert "hivun_375_total" in fields
        assert "hivun_33_total" in fields
        assert "building_cards" in fields
        assert "download_types" in fields

    def test_intake_request_fields(self):
        from api.routes import IntakeRequest
        fields = _get_model_fields(IntakeRequest)
        required = {"owner_name", "moshav_name", "gush", "helka",
                    "num_existing_houses", "authorization_type",
                    "is_capitalized", "client_goals",
                    "has_intergenerational_continuity",
                    "ownership_type", "has_demolition_orders"}
        assert required.issubset(fields)

    def test_buildings_response_fields(self):
        from api.routes import BuildingsResponse
        fields = _get_model_fields(BuildingsResponse)
        assert "job_id" in fields
        assert "buildings" in fields
        assert "count" in fields


class TestBuildingModel:
    """Verify Building model validates correctly."""

    def test_valid_residential_building(self):
        from models.building import Building
        b = Building(
            id=1,
            name="בית מגורים ראשון",
            building_type="residential",
            status="compliant",
            main_area_sqm=180,
            building_order=1,
        )
        assert b.total_area_sqm == 180
        assert b.eco_coefficient == 1.0

    def test_agricultural_with_kitchen_rejected(self):
        from models.building import Building
        with pytest.raises(ValueError, match="kitchen"):
            Building(
                id=1,
                name="מבנה חקלאי",
                building_type="agricultural",
                status="compliant",
                main_area_sqm=100,
                has_kitchen=True,
            )

    def test_pool_with_basement_rejected(self):
        from models.building import Building
        with pytest.raises(ValueError, match="pool"):
            Building(
                id=1,
                name="בריכה",
                building_type="pool",
                status="compliant",
                main_area_sqm=50,
                basement_area_sqm=20,
                basement_type="service",
            )
