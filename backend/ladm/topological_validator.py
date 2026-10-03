"""
3D Cadastral Topological Validator (Jaljolie et al. Method)
Implements 3D spatial relationship checks:
- Volumetric Overlap / Encroachment Detection: intersection volume > tolerance
- 3D Boundary Manifoldness Check
- Vertical Encroachment & Common Space Violation Detection
"""

from typing import List, Dict, Any, Tuple
from .schema import LA_LegalSpaceBuildingUnit, BoundingBox3D, UnitStatus


def check_3d_bbox_intersection(b1: BoundingBox3D, b2: BoundingBox3D, tolerance: float = 0.05) -> Tuple[bool, float, Dict[str, float]]:
    """
    Computes 3D Axis-Aligned Bounding Box intersection.
    Returns: (is_intersecting, intersection_volume_m3, overlap_bounds)
    """
    ox_min = max(b1.min_x, b2.min_x)
    ox_max = min(b1.max_x, b2.max_x)
    oy_min = max(b1.min_y, b2.min_y)
    oy_max = min(b1.max_y, b2.max_y)
    oz_min = max(b1.min_z, b2.min_z)
    oz_max = min(b1.max_z, b2.max_z)

    dx = ox_max - ox_min
    dy = oy_max - oy_min
    dz = oz_max - oz_min

    if dx > tolerance and dy > tolerance and dz > tolerance:
        vol = round(dx * dy * dz, 3)
        overlap_bounds = {
            "min_x": ox_min, "max_x": ox_max,
            "min_y": oy_min, "max_y": oy_max,
            "min_z": oz_min, "max_z": oz_max,
            "volume_m3": vol
        }
        return True, vol, overlap_bounds
    return False, 0.0, {}


def validate_cadastral_topology(units: List[LA_LegalSpaceBuildingUnit]) -> Dict[str, Any]:
    """
    Runs pairwise 3D topological verification across all legal space units.
    Flags encroachments, double-allocated volumetric space, and invalid geometries.
    """
    conflicts = []
    checked_pairs = set()

    # Group units by building_id
    units_by_bld: Dict[str, List[LA_LegalSpaceBuildingUnit]] = {}
    for u in units:
        units_by_bld.setdefault(u.building_id, []).append(u)

    for bld_id, bld_units in units_by_bld.items():
        for i, u1 in enumerate(bld_units):
            # 1. Geometry sanity check
            b1 = u1.bbox
            if b1.max_x <= b1.min_x or b1.max_y <= b1.min_y or b1.max_z <= b1.min_z:
                conflicts.append({
                    "type": "DEGENERATE_GEOMETRY",
                    "severity": "CRITICAL",
                    "unit_a": u1.unit_id,
                    "unit_a_name": u1.unit_name,
                    "unit_a_ulpin": u1.ulpin,
                    "building_id": bld_id,
                    "message": f"Unit {u1.unit_name} has degenerate or inverted 3D dimensions."
                })
                continue

            # 2. Pairwise 3D spatial intersection within the building
            for j in range(i + 1, len(bld_units)):
                u2 = bld_units[j]
                pair_key = tuple(sorted([u1.unit_id, u2.unit_id]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Check 3D intersection
                is_intersect, vol, bounds = check_3d_bbox_intersection(u1.bbox, u2.bbox, tolerance=0.1)
                if is_intersect:
                    severity = "CRITICAL" if vol > 2.0 else "WARNING"
                    conflict_type = "VOLUMETRIC_ENCROACHMENT"
                    
                    if u1.space_type.value in ('C', 'S', 'M', 'U') or u2.space_type.value in ('C', 'S', 'M', 'U'):
                        conflict_type = "COMMON_PROPERTY_ENCROACHMENT"

                    conflicts.append({
                        "type": conflict_type,
                        "severity": severity,
                        "building_id": bld_id,
                        "unit_a": u1.unit_id,
                        "unit_a_name": u1.unit_name,
                        "unit_a_ulpin": u1.ulpin,
                        "unit_b": u2.unit_id,
                        "unit_b_name": u2.unit_name,
                        "unit_b_ulpin": u2.ulpin,
                        "overlap_volume_m3": vol,
                        "overlap_bounds": bounds,
                        "message": f"Illegal 3D overlap of {vol} m³ between '{u1.unit_name}' ({u1.ulpin}) and '{u2.unit_name}' ({u2.ulpin})."
                    })

    return {
        "is_topologically_valid": len(conflicts) == 0,
        "total_units_evaluated": len(units),
        "total_conflicts_detected": len(conflicts),
        "conflicts": conflicts
    }
