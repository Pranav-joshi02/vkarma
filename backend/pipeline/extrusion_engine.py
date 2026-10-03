"""
3D Volumetric Extrusion, Floor Slicing, and LADM Legal Space Unit Subdivider
Generates 3D meshes, assigns ISO 19152 legal units, and mints cryptographically verified 3D ULPINs.
"""

import numpy as np
import uuid
import random
import math
from typing import List, Dict, Any, Tuple, Optional
from backend.ladm.schema import (
    LA_SpatialUnit, LA_LegalSpaceBuildingUnit, BoundingBox3D,
    LA_Party, LA_Source, LA_RRR, RRRType, LegalSpaceType, UnitStatus
)
from backend.ulpin.ulpin_generator import generate_3d_ulpin

SAMPLE_BANKS = ["State Bank of India (SBI)", "HDFC Bank Ltd.", "ICICI Bank", "Punjab National Bank", "Axis Bank"]
SAMPLE_OWNERS = [
    ("Aarav Sharma", "IND-PAN-ARVS8821K"),
    ("Priya Venkatesh", "IND-PAN-PVNK4419M"),
    ("Rajesh & Sunita Gupta (Joint)", "IND-PAN-RSGP9012A"),
    ("Mohammed Faizan", "IND-PAN-MFAZ7741P"),
    ("Deepak Deshmukh", "IND-PAN-DDSK3309Q"),
    ("Ananya Banerjee", "IND-PAN-ABNR6615T"),
    ("Vikram Singhania", "IND-PAN-VSNG5523R"),
    ("Kavita Mehra", "IND-PAN-KMHR1188B"),
    ("Sanjay & Ritu Reddy", "IND-PAN-SRRD2299Z"),
    ("Meera Kulkarni", "IND-PAN-MKLK7733E")
]


def convert_to_local_metric_footprint(
    footprint: List[List[float]],
    centroid_lat: float,
    centroid_lng: float
) -> Tuple[List[List[float]], List[List[float]], float, float]:
    """
    Normalizes footprint coordinates into:
    1. local_metric: [dx_m, dy_m] relative to centroid (0, 0) for Cesium 3D WebGL.
    2. geo_polygon: [[lat, lng], ...] for 2D Leaflet map overlay.
    Returns: (local_metric, geo_polygon, width_m, length_m)
    """
    meters_per_deg_lat = 111320.0
    meters_per_deg_lng = 111320.0 * math.cos(math.radians(centroid_lat))

    if not footprint or len(footprint) < 3:
        w = 26.0
        l = 24.0
        local = [[-w/2, -l/2], [w/2, -l/2], [w/2, l/2], [-w/2, l/2]]
        geo = [
            [centroid_lat + y / meters_per_deg_lat, centroid_lng + x / meters_per_deg_lng]
            for x, y in local
        ]
        return local, geo, w, l

    pts = np.array(footprint, dtype=float)

    # Detect if input coordinates are in geographic degrees (lat/lng typically > 5.0)
    is_degrees = np.any(np.abs(pts) > 3.0) and (
        np.all((np.abs(pts[:, 0]) < 90.0) & (np.abs(pts[:, 1]) < 180.0)) or
        np.all((np.abs(pts[:, 1]) < 90.0) & (np.abs(pts[:, 0]) < 180.0))
    )

    if is_degrees:
        # Determine column orientation: lat vs lng
        col0_mean_diff = np.mean(np.abs(pts[:, 0] - centroid_lat))
        col1_mean_diff = np.mean(np.abs(pts[:, 1] - centroid_lat))
        if col0_mean_diff <= col1_mean_diff:
            lats = pts[:, 0]
            lngs = pts[:, 1]
        else:
            lngs = pts[:, 0]
            lats = pts[:, 1]

        dx = (lngs - centroid_lng) * meters_per_deg_lng
        dy = (lats - centroid_lat) * meters_per_deg_lat
        local_pts = np.column_stack((dx, dy))
        geo_polygon = [[round(float(la), 6), round(float(ln), 6)] for la, ln in zip(lats, lngs)]
    else:
        local_pts = pts
        geo_polygon = [
            [
                round(centroid_lat + float(p[1]) / meters_per_deg_lat, 6),
                round(centroid_lng + float(p[0]) / meters_per_deg_lng, 6)
            ]
            for p in local_pts
        ]

    min_x, max_x = float(np.min(local_pts[:, 0])), float(np.max(local_pts[:, 0]))
    min_y, max_y = float(np.min(local_pts[:, 1])), float(np.max(local_pts[:, 1]))
    w = max_x - min_x
    l = max_y - min_y

    # Enforce realistic minimum dimensions (at least 18m x 16m) so units do not collapse
    if w < 16.0 or l < 16.0 or np.isnan(w) or np.isnan(l):
        target_w = max(20.0, w if not np.isnan(w) else 20.0)
        target_l = max(18.0, l if not np.isnan(l) else 18.0)
        c_x = (min_x + max_x) / 2.0 if not np.isnan(min_x) else 0.0
        c_y = (min_y + max_y) / 2.0 if not np.isnan(min_y) else 0.0
        local_pts = np.array([
            [c_x - target_w/2, c_y - target_l/2],
            [c_x + target_w/2, c_y - target_l/2],
            [c_x + target_w/2, c_y + target_l/2],
            [c_x - target_w/2, c_y + target_l/2]
        ])
        w, l = target_w, target_l

    return local_pts.tolist(), geo_polygon, round(w, 2), round(l, 2)


def generate_unit_mesh_geometry(bbox: BoundingBox3D, color_hex: str = "#3b82f6") -> Dict[str, Any]:
    """
    Generates 3D box vertices and face indices for WebGL rendering.
    """
    x0, y0, z0 = bbox.min_x, bbox.min_y, bbox.min_z
    x1, y1, z1 = bbox.max_x, bbox.max_y, bbox.max_z

    # 8 corner vertices
    vertices = [
        [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],  # Bottom face (0,1,2,3)
        [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]   # Top face (4,5,6,7)
    ]

    # 12 triangles (6 faces * 2)
    indices = [
        # Bottom
        0, 2, 1,  0, 3, 2,
        # Top
        4, 5, 6,  4, 6, 7,
        # Front (y0)
        0, 1, 5,  0, 5, 4,
        # Back (y1)
        3, 7, 6,  3, 6, 2,
        # Left (x0)
        0, 4, 7,  0, 7, 3,
        # Right (x1)
        1, 2, 6,  1, 6, 5
    ]

    return {
        "vertices": vertices,
        "indices": indices,
        "color_hex": color_hex,
        "opacity": 0.85
    }


def extrude_and_partition_building(
    instance_id: int,
    building_name: str,
    pincode: str,
    footprint: List[List[float]],
    ground_z: float,
    building_height: float,
    floors_count: int,
    basements_count: int = 1,
    centroid_lat: float = 12.9716,
    centroid_lng: float = 77.5946,
    serial_start: int = 1000,
    has_dispute_scenario: bool = False,
    building_id: Optional[str] = None
) -> LA_SpatialUnit:
    """
    Extrudes a 3D physical building shell and subdivides it into ISO 19152 Legal Space Units.
    Mints tamper-proof 3D ULPINs for every apartment, parking bay, and utility space.
    """
    local_footprint, geo_polygon, w, l = convert_to_local_metric_footprint(
        footprint, centroid_lat, centroid_lng
    )
    poly_pts = np.array(local_footprint)
    min_x, min_y = float(np.min(poly_pts[:, 0])), float(np.min(poly_pts[:, 1]))
    max_x, max_y = float(np.max(poly_pts[:, 0])), float(np.max(poly_pts[:, 1]))

    if not building_id:
        building_id = f"BLD-{pincode}-{instance_id:03d}"
    floor_height = 3.2  # 3.2 meters per floor
    basement_height = 3.0

    legal_units: List[LA_LegalSpaceBuildingUnit] = []
    current_serial = serial_start

    # Corridor and core dimensions
    core_w = w * 0.28
    core_l = l * 0.28
    core_min_x = min_x + (w - core_w) / 2
    core_max_x = core_min_x + core_w
    core_min_y = min_y + (l - core_l) / 2
    core_max_y = core_min_y + core_l

    # 1. BASEMENTS (Parking & Utilities)
    for b in range(basements_count):
        floor_num = -(b + 1)
        z_bottom = ground_z - (b + 1) * basement_height
        z_top = z_bottom + basement_height

        # 4 distinct outer Parking Quadrants (non-overlapping with central core [0.36, 0.64])
        parking_grid = [
            (min_x, min_y, min_x + w * 0.34, min_y + l * 0.34, f"Parking Bay B{b+1}-01"),
            (min_x + w * 0.66, min_y, max_x, min_y + l * 0.34, f"Parking Bay B{b+1}-02"),
            (min_x, min_y + l * 0.66, min_x + w * 0.34, max_y, f"Parking Bay B{b+1}-03"),
            (min_x + w * 0.66, min_y + l * 0.66, max_x, max_y, f"Parking Bay B{b+1}-04"),
        ]

        for px0, py0, px1, py1, bay_name in parking_grid:
            ulpin_res = generate_3d_ulpin(pincode, 'P', current_serial)
            current_serial += 1

            bbox = BoundingBox3D(round(px0, 2), round(py0, 2), round(z_bottom, 2), round(px1, 2), round(py1, 2), round(z_top, 2))
            assigned_owner = random.choice(SAMPLE_OWNERS)
            
            p_unit = LA_LegalSpaceBuildingUnit(
                unit_id=f"UNIT-{building_id}-B{b+1}-{bay_name.replace(' ', '')}",
                building_id=building_id,
                unit_name=bay_name,
                space_type=LegalSpaceType.PARKING,
                ulpin=ulpin_res.ulpin,
                floor_level=floor_num,
                bbox=bbox,
                status=UnitStatus.CLEAR_FREEHOLD,
                parties=[LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", assigned_owner[0], "Natural Person", assigned_owner[1])],
                rrrs=[LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_OWNERSHIP, "Exclusive Designated Parking Rights", "1.0")],
                sources=[LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "Registered Sale Deed Allotment", f"DOC-{pincode}-{random.randint(10000,99999)}", "Sub-Registrar Office", "2023-04-10", f"SIG-0x{uuid.uuid4().hex[:12]}")],
                mesh_geometry=generate_unit_mesh_geometry(bbox, "#64748b")
            )
            legal_units.append(p_unit)

        # Basement Central Utility & Transformer Shaft (occupies core_min_x to core_max_x)
        u_bbox = BoundingBox3D(round(core_min_x, 2), round(core_min_y, 2), round(z_bottom, 2), round(core_max_x, 2), round(core_max_y, 2), round(z_top, 2))
        u_ulpin = generate_3d_ulpin(pincode, 'U', current_serial)
        current_serial += 1
        u_unit = LA_LegalSpaceBuildingUnit(
            unit_id=f"UNIT-{building_id}-B{b+1}-TRANSFORMER",
            building_id=building_id,
            unit_name=f"Subsurface Utility & Transformer Vault B{b+1}",
            space_type=LegalSpaceType.UTILITY_SHAFT,
            ulpin=u_ulpin.ulpin,
            floor_level=floor_num,
            bbox=u_bbox,
            status=UnitStatus.MUNICIPAL_COMMON,
            parties=[LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", "State Electricity Board / Municipality", "Government Agency", "GOV-DISCOM-DL-01")],
            rrrs=[LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RESTRICTION_GOVT_RESERVATION, "Statutory Subsurface Energy Easement", "1.0")],
            sources=[LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "Municipal Utility Sanction", f"UTIL-{pincode}-99", "Municipal Corporation", "2022-01-15", f"SIG-0x{uuid.uuid4().hex[:12]}")],
            mesh_geometry=generate_unit_mesh_geometry(u_bbox, "#0284c7")
        )
        legal_units.append(u_unit)

    # 2. ABOVE-GROUND FLOORS (Flats, Corridors, Staircases)
    for fl in range(floors_count):
        floor_num = fl
        z_bottom = ground_z + fl * floor_height
        z_top = z_bottom + floor_height

        # Floor Staircase & Elevator Core (Space Type S)
        s_bbox = BoundingBox3D(round(core_min_x, 2), round(core_min_y, 2), round(z_bottom, 2), round(core_max_x, 2), round(core_max_y, 2), round(z_top, 2))
        s_ulpin = generate_3d_ulpin(pincode, 'S', current_serial)
        current_serial += 1
        s_unit = LA_LegalSpaceBuildingUnit(
            unit_id=f"UNIT-{building_id}-FL{fl}-CORE",
            building_id=building_id,
            unit_name=f"Fire Staircase & Lift Core (Floor {fl})",
            space_type=LegalSpaceType.STAIRCASE,
            ulpin=s_ulpin.ulpin,
            floor_level=floor_num,
            bbox=s_bbox,
            status=UnitStatus.MUNICIPAL_COMMON,
            parties=[LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", f"{building_name} Apartment Owners Association (AOA)", "RWA", "RWA-REG-2023-01")],
            rrrs=[LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_COMMON_SHARE, "Fire Safety Common Right of Way", f"1/{floors_count * 4}")],
            sources=[LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "Fire Safety Compliance NOC", f"FIRE-{pincode}-{fl}", "Directorate of Fire Services", "2023-05-12", f"SIG-0x{uuid.uuid4().hex[:12]}")],
            mesh_geometry=generate_unit_mesh_geometry(s_bbox, "#f59e0b")
        )
        legal_units.append(s_unit)

        # 4 Flats per floor (North-West, North-East, South-West, South-East)
        flats_config = [
            (min_x, min_y, core_min_x, core_min_y, f"Flat {fl}01 (SW)"),
            (core_max_x, min_y, max_x, core_min_y, f"Flat {fl}02 (SE)"),
            (min_x, core_max_y, core_min_x, max_y, f"Flat {fl}03 (NW)"),
            (core_max_x, core_max_y, max_x, max_y, f"Flat {fl}04 (NE)")
        ]

        for idx, (fx0, fy0, fx1, fy1, flat_name) in enumerate(flats_config):
            # Dispute injection scenario on specific unit if requested
            is_disputed = has_dispute_scenario and (fl == floors_count - 1) and (idx == 0)
            is_mortgaged = (fl + idx) % 2 == 1

            # If disputed, extend its bounding box into adjacent staircase core in both X and Y
            if is_disputed:
                fx1_mod = fx1 + 1.6  # Encroaches 1.6m in X
                fy1_mod = fy1 + 1.6  # Encroaches 1.6m in Y into central fire evacuation core
                status = UnitStatus.DISPUTED
                color = "#ef4444"  # Red
            else:
                fx1_mod = fx1
                fy1_mod = fy1
                status = UnitStatus.MORTGAGED if is_mortgaged else UnitStatus.CLEAR_FREEHOLD
                color = "#3b82f6" if status == UnitStatus.CLEAR_FREEHOLD else "#8b5cf6"  # Blue or Purple

            bbox = BoundingBox3D(round(fx0, 2), round(fy0, 2), round(z_bottom, 2), round(fx1_mod, 2), round(fy1_mod, 2), round(z_top, 2))
            ulpin_res = generate_3d_ulpin(pincode, 'A', current_serial)
            current_serial += 1

            owner_tuple = SAMPLE_OWNERS[(fl * 4 + idx) % len(SAMPLE_OWNERS)]
            parties = [LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", owner_tuple[0], "Natural Person", owner_tuple[1])]
            
            rrrs = [
                LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_OWNERSHIP, "Exclusive 100% Freehold Title", "1.0"),
                LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_COMMON_SHARE, "Undivided Share in Common Land & Amenities", f"1/{floors_count * 4}"),
                LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RESPONSIBILITY_MAINTENANCE, "Monthly Condominium Sinking Fund", "1.0", amount_inr=4500.0)
            ]

            if is_mortgaged:
                bank_name = SAMPLE_BANKS[(fl + idx) % len(SAMPLE_BANKS)]
                loan_val = float(random.randint(65, 140) * 100000)
                rrrs.append(LA_RRR(
                    f"RRR-{uuid.uuid4().hex[:8]}",
                    RRRType.RESTRICTION_MORTGAGE,
                    f"First charge lien hypothecated to {bank_name} for Housing Term Loan",
                    "1.0",
                    beneficiary_party=bank_name,
                    amount_inr=loan_val
                ))

            sources = [
                LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "Registered Sale Deed & Conveyance", f"DEED-{pincode}-{fl}{idx:02d}", "Sub-Registrar Division-IV", "2023-08-19", f"SIG-0x{uuid.uuid4().hex[:12]}"),
                LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "RERA Approved Building Sanction", f"RERA-PRM-KA-{random.randint(1000,9999)}", "Real Estate Regulatory Authority", "2022-11-04", f"SIG-0x{uuid.uuid4().hex[:12]}")
            ]

            dispute_meta = None
            if is_disputed:
                dispute_meta = {
                    "dispute_id": f"DISP-{uuid.uuid4().hex[:6]}",
                    "title": "Unauthorized Common Corridor Encroachment",
                    "description": f"{flat_name} has expanded 1.8m into the central fire escape corridor without RERA approval.",
                    "encroachment_volume_m3": 11.5,
                    "case_number": f"CIVIL/DEL/{random.randint(100,999)}/2024",
                    "court": "Hon'ble District Civil & Revenue Court"
                }

            flat_unit = LA_LegalSpaceBuildingUnit(
                unit_id=f"UNIT-{building_id}-FL{fl}-{idx+1}",
                building_id=building_id,
                unit_name=f"{flat_name} - {building_name}",
                space_type=LegalSpaceType.APARTMENT,
                ulpin=ulpin_res.ulpin,
                floor_level=floor_num,
                bbox=bbox,
                status=status,
                parties=parties,
                rrrs=rrrs,
                sources=sources,
                mesh_geometry=generate_unit_mesh_geometry(bbox, color),
                dispute_details=dispute_meta
            )
            legal_units.append(flat_unit)

    # 3. ROOFTOP & AIR-RIGHTS (Space Type M and R)
    roof_z_bottom = ground_z + floors_count * floor_height
    roof_z_top = roof_z_bottom + 1.5
    terrace_bbox = BoundingBox3D(round(min_x, 2), round(min_y, 2), round(roof_z_bottom, 2), round(max_x, 2), round(max_y, 2), round(roof_z_top, 2))
    terrace_ulpin = generate_3d_ulpin(pincode, 'M', current_serial)
    current_serial += 1
    terrace_unit = LA_LegalSpaceBuildingUnit(
        unit_id=f"UNIT-{building_id}-ROOF-TERRACE",
        building_id=building_id,
        unit_name=f"Common Sky Terrace & Solar Farm ({building_name})",
        space_type=LegalSpaceType.COMMON_AREA,
        ulpin=terrace_ulpin.ulpin,
        floor_level=floors_count,
        bbox=terrace_bbox,
        status=UnitStatus.MUNICIPAL_COMMON,
        parties=[LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", f"{building_name} Residents Welfare Association", "RWA", "RWA-PAN-90218")],
        rrrs=[LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_COMMON_SHARE, "Equitable Shared Rooftop & Green Energy Right", "1.0")],
        sources=[LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "RERA Sanctioned Common Area Plan", f"RERA-COMM-{pincode}-01", "RERA Authority", "2023-01-10", f"SIG-0x{uuid.uuid4().hex[:12]}")],
        mesh_geometry=generate_unit_mesh_geometry(terrace_bbox, "#10b981")
    )
    legal_units.append(terrace_unit)

    # Air-Rights (Sky Envelope up to 15m above roof)
    air_bbox = BoundingBox3D(round(min_x, 2), round(min_y, 2), round(roof_z_top, 2), round(max_x, 2), round(max_y, 2), round(roof_z_top + 15.0, 2))
    air_ulpin = generate_3d_ulpin(pincode, 'R', current_serial)
    current_serial += 1
    air_unit = LA_LegalSpaceBuildingUnit(
        unit_id=f"UNIT-{building_id}-AIR-RIGHTS",
        building_id=building_id,
        unit_name=f"Vertical Air-Rights Envelope (+15m)",
        space_type=LegalSpaceType.AIR_RIGHTS,
        ulpin=air_ulpin.ulpin,
        floor_level=99,
        bbox=air_bbox,
        status=UnitStatus.CLEAR_FREEHOLD,
        parties=[LA_Party(f"PTY-{uuid.uuid4().hex[:8]}", "Directorate General of Civil Aviation & Municipal Authority", "Government Agency", "DGCA-ZONING-01")],
        rrrs=[
            LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RIGHT_AIR_RIGHTS, "Transferable Development Rights (TDR) Quota", "1.0"),
            LA_RRR(f"RRR-{uuid.uuid4().hex[:8]}", RRRType.RESTRICTION_HERITAGE, "Maximum Airport Funnel Height Ceiling", "1.0")
        ],
        sources=[LA_Source(f"SRC-{uuid.uuid4().hex[:8]}", "AAI Height Clearance Certificate", f"AAI-NOC-{pincode}", "Airports Authority of India", "2023-03-01", f"SIG-0x{uuid.uuid4().hex[:12]}")],
        mesh_geometry=generate_unit_mesh_geometry(air_bbox, "#38bdf8")
    )
    legal_units.append(air_unit)

    # Construct LA_SpatialUnit Physical Shell
    spatial_unit = LA_SpatialUnit(
        building_id=building_id,
        building_name=building_name,
        pincode=pincode,
        total_floors=floors_count,
        basement_floors=basements_count,
        height_m=round(building_height, 2),
        ground_elevation_m=round(ground_z, 2),
        centroid_lat=centroid_lat,
        centroid_lng=centroid_lng,
        footprint_polygon=geo_polygon,
        legal_units=legal_units,
        point_count=floors_count * 1250,
        raw_las_filename=f"{building_id}_survey_tile.laz"
    )

    return spatial_unit
