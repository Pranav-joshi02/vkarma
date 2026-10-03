"""
Tests for the Overture Maps + OSM Building Discovery System.

Tests cover:
  1. Overture building with real name
  2. OSM building with real name
  3. Building with no real name (synthetic naming)
  4. Mixed real + synthetic results
  5. New area resets numbering to 01
  6. Different areas produce different locality prefixes
  7. Locality cannot be determined → fallback to "Selected Area"
  8. Name priority order (Overture > OSM name > name:en > official_name > addr:housename)
  9. API endpoint integration
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.pipeline.building_discovery import (
    discover_buildings_in_bbox,
    _assign_names_and_build_output,
    _merge_overture_with_osm,
    _build_from_osm_only,
    _extract_osm_name,
    _detect_area_name,
    _haversine_distance_m,
)


# ---------------------------------------------------------------------------
# Helper: Create mock Overture and OSM building entries
# ---------------------------------------------------------------------------

def _make_overture_building(overture_id, name=None, lat=18.5904, lng=73.7389):
    """Create a mock Overture building entry."""
    poly = [
        (lat - 0.0001, lng - 0.0001),
        (lat - 0.0001, lng + 0.0001),
        (lat + 0.0001, lng + 0.0001),
        (lat + 0.0001, lng - 0.0001),
    ]
    return {
        "_source_api": "overture",
        "_overture_id": str(overture_id),
        "_overture_name": name,
        "_poly_coords": poly,
        "_centroid": (round(lat, 6), round(lng, 6)),
        "_height": None,
        "_levels": None,
        "_props": {},
    }


def _make_osm_building(osm_id, tags=None, lat=18.5904, lng=73.7389):
    """Create a mock OSM building entry."""
    if tags is None:
        tags = {"building": "yes"}
    poly = [
        (lat - 0.0001, lng - 0.0001),
        (lat - 0.0001, lng + 0.0001),
        (lat + 0.0001, lng + 0.0001),
        (lat + 0.0001, lng - 0.0001),
    ]
    return {
        "_source_api": "osm",
        "_osm_id": str(osm_id),
        "_tags": tags,
        "_poly_coords": poly,
        "_centroid": (round(lat, 6), round(lng, 6)),
    }


# ---------------------------------------------------------------------------
# 1. Overture building with real name
# ---------------------------------------------------------------------------

def test_overture_building_with_real_name():
    """An Overture building with names.primary should use that as the real name."""
    overture = [_make_overture_building("ov-001", name="Infosys Limited")]
    osm = []

    unified = _merge_overture_with_osm(overture, osm)
    result = _assign_names_and_build_output(unified, "Hinjawadi")

    assert len(result) == 1
    assert result[0]["name"] == "Infosys Limited"
    assert result[0]["name_source"] == "overture"
    assert result[0]["has_real_osm_name"] is True


# ---------------------------------------------------------------------------
# 2. OSM building with real name
# ---------------------------------------------------------------------------

def test_osm_building_with_real_name():
    """An OSM building with a 'name' tag should use that as the real name."""
    overture = [_make_overture_building("ov-001", name=None)]
    osm = [_make_osm_building("osm-001", tags={"building": "yes", "name": "Persistent Systems"})]

    unified = _merge_overture_with_osm(overture, osm)
    result = _assign_names_and_build_output(unified, "Hinjawadi")

    assert len(result) == 1
    assert result[0]["name"] == "Persistent Systems"
    assert result[0]["name_source"] == "osm"
    assert result[0]["has_real_osm_name"] is True


# ---------------------------------------------------------------------------
# 3. Building with no real name (synthetic naming)
# ---------------------------------------------------------------------------

def test_building_with_no_real_name():
    """A building with no real name should get a synthetic area-based name."""
    overture = [_make_overture_building("ov-001", name=None)]
    osm = [_make_osm_building("osm-001", tags={"building": "yes"})]

    unified = _merge_overture_with_osm(overture, osm)
    result = _assign_names_and_build_output(unified, "Hinjawadi")

    assert len(result) == 1
    assert result[0]["name"] == "Hinjawadi Building 01"
    assert result[0]["name_source"] == "synthetic"
    assert result[0]["has_real_osm_name"] is False


# ---------------------------------------------------------------------------
# 4. Mixed real + synthetic results
# ---------------------------------------------------------------------------

def test_mixed_real_and_synthetic_names():
    """
    Mixed scenario:
      Building A → Infosys Limited (Overture name)
      Building B → no real name
      Building C → Persistent Systems (OSM name)
      Building D → no real name
      Building E → no real name

    Expected:
      Infosys Limited
      Hinjawadi Building 01
      Persistent Systems
      Hinjawadi Building 02
      Hinjawadi Building 03
    """
    overture = [
        _make_overture_building("ov-001", name="Infosys Limited", lat=18.590),
        _make_overture_building("ov-002", name=None, lat=18.591),
        _make_overture_building("ov-003", name=None, lat=18.592),
        _make_overture_building("ov-004", name=None, lat=18.593),
        _make_overture_building("ov-005", name=None, lat=18.594),
    ]
    osm = [
        _make_osm_building("osm-003", tags={"building": "yes", "name": "Persistent Systems"}, lat=18.592),
    ]

    unified = _merge_overture_with_osm(overture, osm)
    result = _assign_names_and_build_output(unified, "Hinjawadi")

    names = [b["name"] for b in result]
    sources = [b["name_source"] for b in result]

    assert "Infosys Limited" in names
    assert "Persistent Systems" in names
    assert "Hinjawadi Building 01" in names
    assert "Hinjawadi Building 02" in names
    assert "Hinjawadi Building 03" in names

    # Verify correct name sources
    for b in result:
        if b["name"] == "Infosys Limited":
            assert b["name_source"] == "overture"
        elif b["name"] == "Persistent Systems":
            assert b["name_source"] == "osm"
        elif "Building" in b["name"]:
            assert b["name_source"] == "synthetic"

    # Verify synthetic numbering is sequential (01, 02, 03)
    synthetic_names = sorted([b["name"] for b in result if b["name_source"] == "synthetic"])
    assert synthetic_names == [
        "Hinjawadi Building 01",
        "Hinjawadi Building 02",
        "Hinjawadi Building 03",
    ]


# ---------------------------------------------------------------------------
# 5. New area resets numbering to 01
# ---------------------------------------------------------------------------

def test_new_area_resets_numbering():
    """When processing a new area, synthetic numbering should restart at 01."""
    # First area: Hinjawadi
    overture_1 = [
        _make_overture_building("ov-001", name=None, lat=18.590),
        _make_overture_building("ov-002", name=None, lat=18.591),
    ]
    unified_1 = _merge_overture_with_osm(overture_1, [])
    result_1 = _assign_names_and_build_output(unified_1, "Hinjawadi")
    assert result_1[0]["name"] == "Hinjawadi Building 01"
    assert result_1[1]["name"] == "Hinjawadi Building 02"

    # Second area: Baner (should restart at 01)
    overture_2 = [
        _make_overture_building("ov-003", name=None, lat=18.560),
        _make_overture_building("ov-004", name=None, lat=18.561),
        _make_overture_building("ov-005", name=None, lat=18.562),
    ]
    unified_2 = _merge_overture_with_osm(overture_2, [])
    result_2 = _assign_names_and_build_output(unified_2, "Baner")
    assert result_2[0]["name"] == "Baner Building 01"
    assert result_2[1]["name"] == "Baner Building 02"
    assert result_2[2]["name"] == "Baner Building 03"


# ---------------------------------------------------------------------------
# 6. Different areas produce different locality prefixes
# ---------------------------------------------------------------------------

def test_different_areas_different_prefixes():
    """Different areas should produce different locality prefixes."""
    overture = [_make_overture_building("ov-001", name=None)]

    unified_h = _merge_overture_with_osm(overture, [])
    result_h = _assign_names_and_build_output(unified_h, "Hinjawadi")
    assert result_h[0]["name"] == "Hinjawadi Building 01"

    unified_b = _merge_overture_with_osm(overture, [])
    result_b = _assign_names_and_build_output(unified_b, "Baner")
    assert result_b[0]["name"] == "Baner Building 01"

    unified_k = _merge_overture_with_osm(overture, [])
    result_k = _assign_names_and_build_output(unified_k, "Kothrud")
    assert result_k[0]["name"] == "Kothrud Building 01"

    unified_w = _merge_overture_with_osm(overture, [])
    result_w = _assign_names_and_build_output(unified_w, "Wakad")
    assert result_w[0]["name"] == "Wakad Building 01"


# ---------------------------------------------------------------------------
# 7. Locality cannot be determined → fallback to "Selected Area"
# ---------------------------------------------------------------------------

def test_locality_fallback_selected_area():
    """When locality can't be determined, 'Selected Area' should be used."""
    overture = [
        _make_overture_building("ov-001", name=None, lat=18.590),
        _make_overture_building("ov-002", name=None, lat=18.591),
    ]
    unified = _merge_overture_with_osm(overture, [])
    result = _assign_names_and_build_output(unified, "Selected Area")

    assert result[0]["name"] == "Selected Area Building 01"
    assert result[1]["name"] == "Selected Area Building 02"


# ---------------------------------------------------------------------------
# 8. Name priority order
# ---------------------------------------------------------------------------

def test_name_priority_overture_over_osm():
    """Overture names.primary should take priority over OSM name."""
    overture = [_make_overture_building("ov-001", name="Overture Name")]
    osm = [_make_osm_building("osm-001", tags={"building": "yes", "name": "OSM Name"})]

    unified = _merge_overture_with_osm(overture, osm)
    result = _assign_names_and_build_output(unified, "TestArea")

    assert result[0]["name"] == "Overture Name"
    assert result[0]["name_source"] == "overture"


def test_osm_name_priority():
    """OSM name fields should follow priority: name > name:en > official_name > addr:housename."""
    # name takes priority
    name = _extract_osm_name({"name": "Primary Name", "name:en": "English Name", "official_name": "Official"})
    assert name == "Primary Name"

    # name:en when name is missing
    name = _extract_osm_name({"name:en": "English Name", "official_name": "Official"})
    assert name == "English Name"

    # official_name when name and name:en are missing
    name = _extract_osm_name({"official_name": "Official Name"})
    assert name == "Official Name"

    # addr:housename as last resort
    name = _extract_osm_name({"addr:housename": "House Name"})
    assert name == "House Name"

    # None when no name fields
    name = _extract_osm_name({"building": "yes"})
    assert name is None


# ---------------------------------------------------------------------------
# Synthetic numbering: numbers only unnamed buildings
# ---------------------------------------------------------------------------

def test_synthetic_numbering_skips_named_buildings():
    """
    Synthetic numbering should only count unnamed buildings.
    Named buildings should NOT consume a number.
    """
    unified = [
        {"_poly_coords": [(18.59, 73.73), (18.59, 73.74), (18.60, 73.74), (18.60, 73.73)],
         "_centroid": (18.595, 73.735), "_overture_name": "Infosys Limited",
         "_osm_name": None, "_osm_tags": {"building": "yes"}, "_overture_id": "ov-1",
         "_osm_id": None, "_height": None, "_levels": None, "_props": {}},

        {"_poly_coords": [(18.60, 73.73), (18.60, 73.74), (18.61, 73.74), (18.61, 73.73)],
         "_centroid": (18.605, 73.735), "_overture_name": None,
         "_osm_name": None, "_osm_tags": {"building": "yes"}, "_overture_id": "ov-2",
         "_osm_id": None, "_height": None, "_levels": None, "_props": {}},

        {"_poly_coords": [(18.61, 73.73), (18.61, 73.74), (18.62, 73.74), (18.62, 73.73)],
         "_centroid": (18.615, 73.735), "_overture_name": None,
         "_osm_name": "Persistent Systems", "_osm_tags": {"building": "yes", "name": "Persistent Systems"},
         "_overture_id": "ov-3", "_osm_id": None, "_height": None, "_levels": None, "_props": {}},

        {"_poly_coords": [(18.62, 73.73), (18.62, 73.74), (18.63, 73.74), (18.63, 73.73)],
         "_centroid": (18.625, 73.735), "_overture_name": None,
         "_osm_name": None, "_osm_tags": {"building": "yes"}, "_overture_id": "ov-4",
         "_osm_id": None, "_height": None, "_levels": None, "_props": {}},

        {"_poly_coords": [(18.63, 73.73), (18.63, 73.74), (18.64, 73.74), (18.64, 73.73)],
         "_centroid": (18.635, 73.735), "_overture_name": None,
         "_osm_name": None, "_osm_tags": {"building": "yes"}, "_overture_id": "ov-5",
         "_osm_id": None, "_height": None, "_levels": None, "_props": {}},
    ]

    result = _assign_names_and_build_output(unified, "Hinjawadi")
    names = [b["name"] for b in result]

    assert names == [
        "Infosys Limited",
        "Hinjawadi Building 01",
        "Persistent Systems",
        "Hinjawadi Building 02",
        "Hinjawadi Building 03",
    ]


# ---------------------------------------------------------------------------
# Zero-padded numbering
# ---------------------------------------------------------------------------

def test_zero_padded_numbering():
    """Synthetic building numbers should be zero-padded: 01, 02, ..., 09, 10, 11."""
    overture = [
        _make_overture_building(f"ov-{i:03d}", name=None, lat=18.59 + i * 0.001)
        for i in range(12)
    ]
    unified = _merge_overture_with_osm(overture, [])
    result = _assign_names_and_build_output(unified, "TestArea")

    expected_nums = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    for i, b in enumerate(result):
        assert b["name"] == f"TestArea Building {expected_nums[i]}"


# ---------------------------------------------------------------------------
# _detect_area_name tests
# ---------------------------------------------------------------------------

def test_detect_area_name_from_provided_name():
    """Provided area name should be used if it's specific enough."""
    assert _detect_area_name(18.59, 73.73, "Hinjawadi") == "Hinjawadi"
    assert _detect_area_name(18.59, 73.73, "Baner, Pune") == "Baner"


def test_detect_area_name_skips_generic():
    """Generic names like 'Survey Area' should be skipped in favor of geocoding."""
    with patch("backend.pipeline.building_discovery.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "address": {
                "suburb": "Hinjawadi",
                "city": "Pune",
                "postcode": "411057",
            }
        }
        mock_get.return_value = mock_resp

        result = _detect_area_name(18.59, 73.73, "Survey Area")
        assert result == "Hinjawadi"


def test_detect_area_name_nominatim_failure_fallback():
    """If Nominatim fails and no specific area name provided, fall back to 'Selected Area'."""
    with patch("backend.pipeline.building_discovery.requests.get", side_effect=Exception("Connection error")):
        result = _detect_area_name(18.59, 73.73, None)
        assert result == "Selected Area"


# ---------------------------------------------------------------------------
# Output structure validation
# ---------------------------------------------------------------------------

def test_output_structure():
    """Verify each building in the output has the required fields."""
    overture = [_make_overture_building("ov-001", name="Test Building")]
    unified = _merge_overture_with_osm(overture, [])
    result = _assign_names_and_build_output(unified, "TestArea")

    assert len(result) == 1
    b = result[0]

    required_fields = [
        "id", "name", "name_source", "centroid", "centroid_lat", "centroid_lng",
        "footprint_coordinates", "footprint_polygon", "footprint_local",
        "width_m", "length_m", "floors", "height_m", "type", "building_type",
        "pincode", "has_real_osm_name", "source",
    ]
    for field in required_fields:
        assert field in b, f"Missing required field: {field}"

    assert b["name_source"] in ("overture", "osm", "synthetic")
    assert isinstance(b["centroid"], list)
    assert len(b["centroid"]) == 2


# ---------------------------------------------------------------------------
# Spatial matching
# ---------------------------------------------------------------------------

def test_haversine_distance():
    """Haversine distance should be roughly correct."""
    # Same point
    assert _haversine_distance_m(18.59, 73.73, 18.59, 73.73) == 0.0

    # ~111m for 0.001 degree latitude
    dist = _haversine_distance_m(18.590, 73.730, 18.591, 73.730)
    assert 100 < dist < 120


def test_osm_only_builds_correctly():
    """When only OSM data is available, buildings should still be created properly."""
    osm = [
        _make_osm_building("osm-001", tags={"building": "yes", "name": "Named Building"}),
        _make_osm_building("osm-002", tags={"building": "yes"}, lat=18.591),
    ]
    unified = _build_from_osm_only(osm)
    result = _assign_names_and_build_output(unified, "Wakad")

    assert len(result) == 2
    names = [b["name"] for b in result]
    assert "Named Building" in names
    assert "Wakad Building 01" in names


# ---------------------------------------------------------------------------
# Full discover_buildings_in_bbox with mocked APIs
# ---------------------------------------------------------------------------

def test_discover_buildings_mocked():
    """Full end-to-end test with mocked Overture and OSM APIs."""
    mock_overture = [
        _make_overture_building("ov-001", name="Infosys Limited", lat=18.590),
        _make_overture_building("ov-002", name=None, lat=18.591),
        _make_overture_building("ov-003", name=None, lat=18.592),
    ]
    mock_osm = [
        _make_osm_building("osm-002", tags={"building": "yes", "name": "Tech Park"}, lat=18.591),
    ]

    with patch("backend.pipeline.building_discovery._fetch_overture_buildings", return_value=mock_overture), \
         patch("backend.pipeline.building_discovery._fetch_osm_buildings_overpass", return_value=mock_osm), \
         patch("backend.pipeline.building_discovery._detect_area_name", return_value="Hinjawadi"):

        result = discover_buildings_in_bbox(18.585, 73.730, 18.595, 73.740, area_name="Hinjawadi")

        assert len(result) > 0
        names = [b["name"] for b in result]
        assert "Infosys Limited" in names
        assert "Tech Park" in names
        # The unnamed building should get synthetic name
        synthetic_names = [b["name"] for b in result if b["name_source"] == "synthetic"]
        assert any("Hinjawadi Building" in n for n in synthetic_names)


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------

def test_api_area_buildings_endpoint():
    """Test the /api/area/buildings endpoint with the new building discovery."""
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)

    mock_buildings = [
        {
            "id": "ov-001",
            "name": "Test Building",
            "name_source": "overture",
            "centroid": [18.59, 73.73],
            "centroid_lat": 18.59,
            "centroid_lng": 73.73,
            "footprint_coordinates": [],
            "footprint_polygon": [],
            "footprint_local": [],
            "width_m": 24.0,
            "length_m": 22.0,
            "floors": 7,
            "height_m": 22.4,
            "type": "Commercial",
            "building_type": "Commercial",
            "pincode": "",
            "has_real_osm_name": True,
            "source": "overture+osm",
        },
        {
            "id": "ov-002",
            "name": "Hinjawadi Building 01",
            "name_source": "synthetic",
            "centroid": [18.591, 73.731],
            "centroid_lat": 18.591,
            "centroid_lng": 73.731,
            "footprint_coordinates": [],
            "footprint_polygon": [],
            "footprint_local": [],
            "width_m": 24.0,
            "length_m": 22.0,
            "floors": 7,
            "height_m": 22.4,
            "type": "Commercial",
            "building_type": "Commercial",
            "pincode": "",
            "has_real_osm_name": False,
            "source": "overture+osm",
        },
    ]

    with patch("backend.pipeline.building_discovery.discover_buildings_in_bbox", return_value=mock_buildings):
        resp = client.post("/api/area/buildings", json={
            "bbox": [18.585, 73.730, 18.595, 73.740],
            "area_name": "Hinjawadi",
            "pincode": "411057"
        })

        assert resp.status_code == 200
        data = resp.json()

        assert data["total_found"] == 2
        assert data["real_named_count"] == 1
        assert data["synthetic_named_count"] == 1
        assert data["source"] == "overture+osm"
        assert len(data["buildings"]) == 2

        # Verify building structure
        b0 = data["buildings"][0]
        assert "name" in b0
        assert "name_source" in b0
        assert b0["name_source"] in ("overture", "osm", "synthetic")
