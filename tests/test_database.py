"""
Unit tests for Supabase & PostgreSQL Database Layer and Migration Runner.
Verifies graceful fallback, status reporting, and repository methods.
"""

import pytest
from backend.database.supabase_client import get_database_status, is_supabase_connected
from backend.database.migration_runner import run_all_migrations
from backend.database.repository import CadastralRepository
from backend.ladm.cadastral_db import CadastralDatabase
from backend.ladm.schema import LA_SpatialUnit


def test_database_status_structure():
    """Verify get_database_status returns complete diagnostic structure."""
    status = get_database_status()
    assert isinstance(status, dict)
    assert "is_connected" in status
    assert "mode" in status
    assert "has_supabase_url" in status
    assert "has_supabase_key" in status
    assert "has_database_url" in status
    assert "table_counts" in status


def test_migration_runner_without_url():
    """Verify migration runner skips gracefully when DATABASE_URL is not set."""
    res = run_all_migrations(database_url="")
    assert res["status"] == "SKIPPED"
    assert "DATABASE_URL not configured" in res["message"]


def test_cadastral_db_fallback_save():
    """Verify CadastralDatabase register_building works seamlessly in fallback mode."""
    db = CadastralDatabase()
    bld = LA_SpatialUnit(
        building_id="TEST-BLD-001",
        building_name="Test Tower",
        pincode="560103",
        total_floors=5,
        basement_floors=1,
        height_m=18.0,
        ground_elevation_m=920.0,
        centroid_lat=12.935,
        centroid_lng=77.694,
        footprint_polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
        legal_units=[]
    )
    # Should not raise any error even with no database configured
    db.register_building(bld, persist=True)
    assert db.get_building("TEST-BLD-001") is not None
    assert db.get_building("TEST-BLD-001").building_name == "Test Tower"


def test_cadastral_db_load_from_database_fallback():
    """Verify load_from_database returns count and does not fail when DB is unconfigured."""
    db = CadastralDatabase()
    loaded = db.load_from_database()
    assert isinstance(loaded, int)
    assert loaded >= 0
