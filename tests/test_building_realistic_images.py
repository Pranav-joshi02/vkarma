"""
Tests for Building Realistic Image Resolution & Land Passport Integration.
Validates:
1. get_building_realistic_image matches tech, campus, residential, and commercial keywords
2. get_building_realistic_image handles sequential synthetic buildings with unique cyclic images
3. LA_SpatialUnit and LA_LegalSpaceBuildingUnit preserve image_url in to_dict() and from_dict()
4. Extrusion engine assigns image_url to both physical shell and subdivided legal units
5. /api/ulpin/lookup/{ulpin} endpoint returns image_url and building details
6. Seed buildings include realistic image URLs
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.ladm.cadastral_db import cadastre_db
from backend.ladm.schema import (
    LA_SpatialUnit, LA_LegalSpaceBuildingUnit, BoundingBox3D,
    LegalSpaceType, UnitStatus
)
from backend.pipeline.building_images import (
    get_building_realistic_image,
    TECH_TOWER_IMAGE,
    CAMPUS_IMAGE,
    COMMERCIAL_PLAZA_IMAGE,
    RESIDENTIAL_HIGHRISE_IMAGE,
    RESIDENTIAL_ENCLAVE_IMAGE,
    MIXED_USE_IMAGE,
)
from backend.pipeline.extrusion_engine import extrude_and_partition_building


@pytest.fixture
def client():
    return TestClient(app)


def test_keyword_matching_images():
    # Tech campus
    assert get_building_realistic_image("Infosys Tech Campus Hinjawadi") == CAMPUS_IMAGE
    assert get_building_realistic_image("Persistent Systems Tech Park") == CAMPUS_IMAGE
    assert get_building_realistic_image("Wipro Software Campus") == CAMPUS_IMAGE

    # Tech tower
    assert get_building_realistic_image("Infosys Limited") == TECH_TOWER_IMAGE
    assert get_building_realistic_image("Apex IT Tower") == TECH_TOWER_IMAGE

    # Financial / Commercial plaza
    assert get_building_realistic_image("Aura Financial Plaza") == COMMERCIAL_PLAZA_IMAGE
    assert get_building_realistic_image("BKC Corporate Plaza") == COMMERCIAL_PLAZA_IMAGE
    assert get_building_realistic_image("State Bank Commercial Exchange") == COMMERCIAL_PLAZA_IMAGE

    # Residential
    assert get_building_realistic_image("Godrej Sky Heights", total_floors=18) == RESIDENTIAL_HIGHRISE_IMAGE
    assert get_building_realistic_image("Sobha Luxury Apartments", total_floors=14) == RESIDENTIAL_HIGHRISE_IMAGE
    assert get_building_realistic_image("Emerald Greens Residency", total_floors=4) == RESIDENTIAL_ENCLAVE_IMAGE
    assert get_building_realistic_image("Silver Oak Enclave", total_floors=5) == RESIDENTIAL_ENCLAVE_IMAGE

    # Mixed-use
    assert get_building_realistic_image("Central Mall & Multiplex") == MIXED_USE_IMAGE
    assert get_building_realistic_image("Metro Retail Hub") == MIXED_USE_IMAGE


def test_sequential_synthetic_buildings_variety():
    # Synthetic buildings should cycle through distinct realistic images
    img1 = get_building_realistic_image("Hinjawadi Building 01")
    img2 = get_building_realistic_image("Hinjawadi Building 02")
    img3 = get_building_realistic_image("Hinjawadi Building 03")
    img4 = get_building_realistic_image("Hinjawadi Building 04")
    img5 = get_building_realistic_image("Hinjawadi Building 05")
    img6 = get_building_realistic_image("Hinjawadi Building 06")

    # Ensure consecutive synthetic buildings don't share the same image
    assert img1 != img2
    assert img2 != img3
    assert img3 != img4
    assert img4 != img5
    assert img5 != img6


def test_schema_image_url_serialization():
    bbox = BoundingBox3D(0, 0, 0, 10, 10, 3)
    unit = LA_LegalSpaceBuildingUnit(
        unit_id="U-TEST-1",
        building_id="BLD-TEST-1",
        unit_name="Unit 101",
        space_type=LegalSpaceType.APARTMENT,
        ulpin="560103-A-ABCDEFGH-1",
        floor_level=1,
        bbox=bbox,
        status=UnitStatus.CLEAR_FREEHOLD,
        image_url="/assets/buildings/residential_highrise.jpg"
    )
    unit_dict = unit.to_dict()
    assert unit_dict["image_url"] == "/assets/buildings/residential_highrise.jpg"

    rehydrated_unit = LA_LegalSpaceBuildingUnit.from_dict(unit_dict)
    assert rehydrated_unit.image_url == "/assets/buildings/residential_highrise.jpg"

    spatial_bld = LA_SpatialUnit(
        building_id="BLD-TEST-1",
        building_name="Test Tower",
        pincode="560103",
        total_floors=5,
        basement_floors=1,
        height_m=18.0,
        ground_elevation_m=920.0,
        centroid_lat=12.9352,
        centroid_lng=77.6946,
        footprint_polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
        legal_units=[unit],
        image_url="/assets/buildings/tech_park_tower.jpg"
    )
    bld_dict = spatial_bld.to_dict()
    assert bld_dict["image_url"] == "/assets/buildings/tech_park_tower.jpg"

    rehydrated_bld = LA_SpatialUnit.from_dict(bld_dict)
    assert rehydrated_bld.image_url == "/assets/buildings/tech_park_tower.jpg"


def test_extrusion_engine_assigns_image_url():
    fp = [[-10.0, -10.0], [10.0, -10.0], [10.0, 10.0], [-10.0, 10.0]]
    bld = extrude_and_partition_building(
        instance_id=1,
        building_name="Persistent Systems Hinjawadi",
        pincode="411057",
        footprint=fp,
        ground_z=550.0,
        building_height=30.0,
        floors_count=8,
        basements_count=1,
        centroid_lat=18.59,
        centroid_lng=73.71,
        serial_start=10000,
        building_id="BLD-411057-PERSIST"
    )

    assert bld.image_url is not None
    assert bld.image_url.startswith("/assets/buildings/")
    assert len(bld.legal_units) > 0
    # Every legal unit should inherit the realistic building image
    for u in bld.legal_units:
        assert u.image_url == bld.image_url


def test_api_ulpin_lookup_returns_image_url(client):
    cadastre_db.ensure_seeded()
    # Check default seeded ULPIN (Unit 702 in Vanguard Orion Tech Tower)
    resp = client.get("/api/ulpin/lookup/560103-A-60YLMDPD-2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found_in_active_db"] is True
    assert "unit" in data
    assert "image_url" in data
    assert data["image_url"].startswith("/assets/buildings/")
    assert data["unit"]["image_url"].startswith("/assets/buildings/")
    assert "building" in data
    assert data["building"]["building_name"] == "Vanguard Orion Tech Tower"
