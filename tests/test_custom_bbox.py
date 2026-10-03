"""
Unit tests for custom bounding box area processing and multi-building cadastral generation.
"""

import numpy as np
import pytest
from backend.mock_data.pilot_tiles import generate_synthetic_lidar_point_cloud
from backend.pipeline.pipeline_orchestrator import run_full_3d_cadastral_pipeline
from backend.ladm.cadastral_db import cadastre_db


def test_procedural_multi_building_pointcloud():
    """Verify point cloud can generate arbitrary numbers of buildings across custom box dimensions."""
    # Test with 12 buildings in a 350m x 300m box
    num_blds = 12
    bw, bh = 350.0, 300.0
    pts = generate_synthetic_lidar_point_cloud(
        num_buildings=num_blds,
        box_width_m=bw,
        box_height_m=bh,
        point_density_per_sqm=2.0
    )
    assert len(pts) > 10000
    # Coordinates should be strictly contained within bounding box envelope
    assert np.min(pts[:, 0]) >= -bw / 2 - 2.0
    assert np.max(pts[:, 0]) <= bw / 2 + 2.0
    assert np.min(pts[:, 1]) >= -bh / 2 - 2.0
    assert np.max(pts[:, 1]) <= bh / 2 + 2.0


def test_custom_bounding_box_pipeline_processing():
    """Verify pipeline detects multiple buildings and places them strictly inside the user's custom bbox."""
    # Pune Hinjawadi bounding box: [min_lat, min_lng, max_lat, max_lng]
    min_lat, min_lng = 18.5800, 73.7300
    max_lat, max_lng = 18.5860, 73.7360
    base_lat = (min_lat + max_lat) / 2.0
    base_lng = (min_lng + max_lng) / 2.0

    bw = abs(max_lng - min_lng) * 111111.0 * np.cos(np.radians(base_lat))
    bh = abs(max_lat - min_lat) * 111111.0

    target_buildings = 9
    pts = generate_synthetic_lidar_point_cloud(
        num_buildings=target_buildings,
        box_width_m=bw,
        box_height_m=bh
    )

    result = run_full_3d_cadastral_pipeline(
        raw_points=pts,
        pincode="411057",
        area_name="Pune Hinjawadi Phase 1",
        base_lat=base_lat,
        base_lng=base_lng,
        has_dispute_scenario=False
    )

    assert result["status"] == "SUCCESS"
    buildings = result["buildings"]

    # Verify multiple buildings (not just 8 or 3)
    assert len(buildings) >= 6, f"Expected multiple buildings, got {len(buildings)}"

    # Verify all buildings are positioned accurately inside the custom bounding box
    for b in buildings:
        lat = b["centroid_lat"]
        lng = b["centroid_lng"]
        assert min_lat <= lat <= max_lat, f"Building latitude {lat} outside [{min_lat}, {max_lat}]"
        assert min_lng <= lng <= max_lng, f"Building longitude {lng} outside [{min_lng}, {max_lng}]"
        assert b["pincode"] == "411057"
        assert "Pune Hinjawadi" in b["building_name"]
        assert len(b["legal_units"]) > 0

        # Verify 3D ULPINs are minted for this specific area
        for u in b["legal_units"]:
            assert u["ulpin"].startswith("411057-")

    # Verify active cadastre database contains these buildings, not old seeded ones
    active_blds = cadastre_db.list_all_buildings()
    assert len(active_blds) == len(buildings)
    assert all("Pune Hinjawadi" in b["building_name"] for b in active_blds)
