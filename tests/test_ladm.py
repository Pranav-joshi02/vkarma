"""
Unit Tests for ISO 19152 LADM Schema & Topological Validation
"""

import pytest
from backend.ladm.schema import (
    LA_LegalSpaceBuildingUnit, BoundingBox3D, LegalSpaceType, UnitStatus, LA_Party, LA_RRR, RRRType
)
from backend.ladm.topological_validator import validate_cadastral_topology, check_3d_bbox_intersection
from backend.ulpin.ulpin_generator import generate_3d_ulpin


def test_3d_bbox_non_intersecting():
    b1 = BoundingBox3D(0, 0, 0, 10, 10, 3)
    b2 = BoundingBox3D(12, 0, 0, 22, 10, 3)
    is_inter, vol, bounds = check_3d_bbox_intersection(b1, b2)
    assert is_inter is False
    assert vol == 0.0


def test_3d_bbox_intersecting():
    b1 = BoundingBox3D(0, 0, 0, 10, 10, 3)
    b2 = BoundingBox3D(8, 0, 0, 18, 10, 3)
    is_inter, vol, bounds = check_3d_bbox_intersection(b1, b2)
    assert is_inter is True
    assert vol == 60.0  # 2 * 10 * 3


def test_topological_conflict_detection():
    u1 = generate_3d_ulpin("560103", "A", 101)
    u2 = generate_3d_ulpin("560103", "A", 102)

    unit1 = LA_LegalSpaceBuildingUnit(
        unit_id="U1", building_id="B1", unit_name="Flat 101",
        space_type=LegalSpaceType.APARTMENT, ulpin=u1.ulpin, floor_level=1,
        bbox=BoundingBox3D(0, 0, 0, 10, 10, 3), status=UnitStatus.CLEAR_FREEHOLD
    )
    unit2 = LA_LegalSpaceBuildingUnit(
        unit_id="U2", building_id="B1", unit_name="Flat 102 (Overlapping)",
        space_type=LegalSpaceType.APARTMENT, ulpin=u2.ulpin, floor_level=1,
        bbox=BoundingBox3D(8, 0, 0, 18, 10, 3), status=UnitStatus.DISPUTED
    )

    report = validate_cadastral_topology([unit1, unit2])
    assert report["is_topologically_valid"] is False
    assert report["total_conflicts_detected"] == 1
    assert report["conflicts"][0]["type"] == "VOLUMETRIC_ENCROACHMENT"
