"""
Geospatial Pilot Tiles & Synthetic LiDAR Point Cloud Generator
Supplies realistic 3D LiDAR point clouds for Indian urban pilot locations and on-demand custom map bounding boxes.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional


def generate_synthetic_lidar_point_cloud(
    num_buildings: Optional[int] = None,
    area_size: float = 120.0,
    box_width_m: Optional[float] = None,
    box_height_m: Optional[float] = None,
    point_density_per_sqm: float = 2.5,
    seed: int = 42,
    base_elevation: float = 920.0
) -> np.ndarray:
    """
    Generates realistic 3D LiDAR point cloud for any custom geographic bounding box:
    - Scaled to actual bounding box dimensions (width_m x height_m).
    - Procedural urban block layout with realistic setbacks (>10m street corridors for DBSCAN).
    - Diverse building envelopes (high-rises, commercial plazas, podiums, multi-tower enclaves).
    - Terrain undulation, rooftop parapets, facade walls, vegetation canopy, and infrastructure.
    """
    np.random.seed(seed)
    points_list = []

    # 1. Determine bounding box dimensions
    bw = float(box_width_m) if box_width_m and box_width_m > 30.0 else float(area_size)
    bh = float(box_height_m) if box_height_m and box_height_m > 30.0 else float(area_size)
    total_area_sqm = bw * bh

    # Dynamic building count if not specified
    if num_buildings is None or num_buildings <= 0:
        # Scale: ~1 building per 2,000 - 3,000 sqm
        num_buildings = max(3, min(35, int(round(total_area_sqm / 2400.0))))

    # 2. Ground terrain points
    # Cap total points reasonably for real-time WebGL and pipeline performance (25k - 80k pts)
    target_ground_pts = int(np.clip(total_area_sqm * point_density_per_sqm * 0.25, 12000, 70000))
    gx = np.random.uniform(-bw / 2, bw / 2, target_ground_pts)
    gy = np.random.uniform(-bh / 2, bh / 2, target_ground_pts)
    gz = base_elevation + 0.015 * gx + 0.012 * gy + np.random.normal(0, 0.08, target_ground_pts)
    points_list.append(np.column_stack([gx, gy, gz]))

    # 3. Procedural Urban Block Grid Layout
    # Determine grid rows and columns based on aspect ratio
    aspect = max(0.2, min(5.0, bw / bh))
    n_cols = max(1, int(np.ceil(np.sqrt(num_buildings * aspect))))
    n_rows = max(1, int(np.ceil(num_buildings / n_cols)))

    cell_w = bw / n_cols
    cell_h = bh / n_rows

    building_configs = []
    b_idx = 0

    # Height and floor templates for variety
    height_profiles = [
        {"floors": 16, "h": 51.2},  # High-rise tower
        {"floors": 12, "h": 38.4},  # Standard residential tower
        {"floors": 9,  "h": 28.8},  # Mid-rise block
        {"floors": 7,  "h": 22.4},  # Corporate office plaza
        {"floors": 5,  "h": 16.0},  # Retail & community hub
        {"floors": 20, "h": 64.0},  # Premium commercial skyscraper
        {"floors": 14, "h": 44.8},  # Mixed-use condo
        {"floors": 8,  "h": 25.6},  # Tech campus wing
    ]

    for r in range(n_rows):
        for c in range(n_cols):
            if b_idx >= num_buildings:
                break

            # Cell center in local coordinates [-bw/2..bw/2], [-bh/2..bh/2]
            cell_cx = -bw / 2 + (c + 0.5) * cell_w
            cell_cy = -bh / 2 + (r + 0.5) * cell_h

            # Jitter within cell (keep inside lot)
            max_jitter_x = max(0.0, (cell_w - 26.0) * 0.18)
            max_jitter_y = max(0.0, (cell_h - 26.0) * 0.18)
            cx = cell_cx + np.random.uniform(-max_jitter_x, max_jitter_x)
            cy = cell_cy + np.random.uniform(-max_jitter_y, max_jitter_y)

            # Ensure setback: road corridor >= 10m between neighboring building shells
            w = float(np.clip(cell_w * 0.62, 16.0, 42.0))
            l = float(np.clip(cell_h * 0.62, 16.0, 42.0))

            prof = height_profiles[b_idx % len(height_profiles)]
            h = prof["h"] + np.random.uniform(-2.0, 3.0)
            floors = prof["floors"]

            building_configs.append({
                "cx": cx, "cy": cy, "w": w, "l": l,
                "h": round(h, 1), "floors": floors, "id": b_idx + 1
            })
            b_idx += 1

    # 4. Generate Building Point Clouds (Roofs + Walls)
    for b in building_configs:
        cx, cy, w, l, h = b["cx"], b["cy"], b["w"], b["l"], b["h"]
        base_z = base_elevation + 0.015 * cx + 0.012 * cy
        top_z = base_z + h

        # Roof points
        n_roof = int(np.clip(w * l * 2.8, 180, 1400))
        rx = np.random.uniform(cx - w/2, cx + w/2, n_roof)
        ry = np.random.uniform(cy - l/2, cy + l/2, n_roof)
        rz = top_z + np.random.normal(0, 0.04, n_roof)
        points_list.append(np.column_stack([rx, ry, rz]))

        # Wall facade points (4 exterior facades)
        n_wall_pts = int(np.clip(2 * (w + l) * h * 0.65, 300, 2200))
        wall_pts_each = max(50, n_wall_pts // 4)

        # South wall: y = cy - l/2
        w1_x = np.random.uniform(cx - w/2, cx + w/2, wall_pts_each)
        w1_y = np.full(wall_pts_each, cy - l/2) + np.random.normal(0, 0.03, wall_pts_each)
        w1_z = np.random.uniform(base_z, top_z, wall_pts_each)
        points_list.append(np.column_stack([w1_x, w1_y, w1_z]))

        # North wall: y = cy + l/2
        w2_x = np.random.uniform(cx - w/2, cx + w/2, wall_pts_each)
        w2_y = np.full(wall_pts_each, cy + l/2) + np.random.normal(0, 0.03, wall_pts_each)
        w2_z = np.random.uniform(base_z, top_z, wall_pts_each)
        points_list.append(np.column_stack([w2_x, w2_y, w2_z]))

        # West wall: x = cx - w/2
        w3_y = np.random.uniform(cy - l/2, cy + l/2, wall_pts_each)
        w3_x = np.full(wall_pts_each, cx - w/2) + np.random.normal(0, 0.03, wall_pts_each)
        w3_z = np.random.uniform(base_z, top_z, wall_pts_each)
        points_list.append(np.column_stack([w3_x, w3_y, w3_z]))

        # East wall: x = cx + w/2
        w4_y = np.random.uniform(cy - l/2, cy + l/2, wall_pts_each)
        w4_x = np.full(wall_pts_each, cx + w/2) + np.random.normal(0, 0.03, wall_pts_each)
        w4_z = np.random.uniform(base_z, top_z, wall_pts_each)
        points_list.append(np.column_stack([w4_x, w4_y, w4_z]))

    # 5. Tree Clusters in Open Spaces
    num_tree_clusters = max(4, int(num_buildings * 1.5))
    for _ in range(num_tree_clusters):
        tx = np.random.uniform(-bw * 0.44, bw * 0.44)
        ty = np.random.uniform(-bh * 0.44, bh * 0.44)
        # Avoid placing inside a building
        in_bld = any(abs(tx - b["cx"]) < (b["w"]/2 + 2) and abs(ty - b["cy"]) < (b["l"]/2 + 2) for b in building_configs)
        if in_bld:
            continue

        n_tree = 90
        tz_base = base_elevation + 0.015 * tx + 0.012 * ty
        phi = np.random.uniform(0, 2*np.pi, n_tree)
        theta = np.random.uniform(0, np.pi, n_tree)
        r = np.random.uniform(0.8, 3.2, n_tree)
        px = tx + r * np.sin(theta) * np.cos(phi)
        py = ty + r * np.sin(theta) * np.sin(phi)
        pz = tz_base + 2.5 + r * np.cos(theta) * 0.75
        points_list.append(np.column_stack([px, py, pz]))

    # 6. Overhead transit/utility line across the block
    n_cable = 160
    cx_line = np.linspace(-bw/2, bw/2, n_cable)
    cy_line = np.full(n_cable, bh * 0.12)
    cz_line = base_elevation + 13.5 + 0.4 * np.sin(cx_line * 0.04)
    points_list.append(np.column_stack([cx_line, cy_line, cz_line]))

    all_points = np.vstack(points_list)
    return all_points


PILOT_REGIONS = [
    {
        "id": "blr_orr_560103",
        "name": "Bengaluru Tech Corridor (Outer Ring Road)",
        "pincode": "560103",
        "state": "Karnataka",
        "lat": 12.9352,
        "lng": 77.6946,
        "zoom": 17,
        "description": "High-density mixed-use IT towers, residential high-rises, underground basement parking, and upcoming elevated metro line.",
        "buildings_count": 3,
        "features": ["Multi-Tower High-Rise", "2-Level Basement Parking", "Air-Rights Envelope", "Dispute Case 701"]
    },
    {
        "id": "del_cp_110001",
        "name": "New Delhi Connaught Place / Barakhamba",
        "pincode": "110001",
        "state": "Delhi NCR",
        "lat": 28.6315,
        "lng": 77.2167,
        "zoom": 17,
        "description": "Central commercial business district with multi-level underground metro interchange, office towers, and heritage height zoning.",
        "buildings_count": 4,
        "features": ["Underground Metro Hub", "Commercial Condominiums", "Heritage Zoning Restriction", "Subsurface Utility Vaults"]
    },
    {
        "id": "mum_bkc_400051",
        "name": "Mumbai BKC (Bandra-Kurla Complex)",
        "pincode": "400051",
        "state": "Maharashtra",
        "lat": 19.0657,
        "lng": 72.8687,
        "zoom": 17,
        "description": "India's premier financial hub with luxury commercial skyscrapers, rooftop helipads, and high-security basement bullion vaults.",
        "buildings_count": 3,
        "features": ["Skyscraper 3D Cadastre", "3-Level Automated Parking", "Transferable Development Rights (TDR)", "Rooftop Air Rights"]
    },
    {
        "id": "hyd_hitec_500081",
        "name": "Hyderabad HITEC City (Knowledge Park)",
        "pincode": "500081",
        "state": "Telangana",
        "lat": 17.4435,
        "lng": 78.3772,
        "zoom": 17,
        "description": "Special Economic Zone (SEZ) with multi-storey cloud tech campuses, shared sky-walks, and common solar microgrids.",
        "buildings_count": 3,
        "features": ["SEZ Commercial Rights", "Inter-Building Skywalks", "Solar Common Amenity Share", "Multi-Owner Freeholds"]
    }
]


def get_pilot_region_by_id(region_id: str) -> Dict[str, Any]:
    for r in PILOT_REGIONS:
        if r["id"] == region_id:
            return r
    return PILOT_REGIONS[0]
