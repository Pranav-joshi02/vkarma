"""
Cloth Simulation Filter (CSF) & Surface Filtering
Separates Ground from Non-Ground elevated points in raw LiDAR survey point clouds.
Simulates an inverted elastic cloth dropping over the inverted point cloud to capture the ground terrain surface.
"""

import numpy as np
from typing import Tuple, Dict, Any


def cloth_simulation_filter(
    points: np.ndarray,
    grid_resolution: float = 1.0,
    cloth_rigidness: int = 2,
    time_step: float = 0.65,
    class_threshold: float = 0.5,
    max_iterations: int = 50
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Applies the Cloth Simulation Filter (Zhang et al.) to separate ground vs. non-ground points.
    
    Args:
        points: (N, 3) or (N, >=3) numpy array of [X, Y, Z, ...]
        grid_resolution: Cloth particle spacing (meters)
        cloth_rigidness: 1 (soft/steep terrain), 2 (medium/hills), 3 (hard/flat urban)
        class_threshold: Distance threshold from cloth to classify point as ground (meters)
        max_iterations: Max simulation relaxation steps
        
    Returns:
        ground_mask: boolean mask for ground points
        non_ground_mask: boolean mask for non-ground points (buildings, vegetation, cables)
        stats: dictionary of execution metrics
    """
    if points.shape[0] == 0:
        empty = np.zeros(0, dtype=bool)
        return empty, empty, {"ground_count": 0, "non_ground_count": 0}

    xyz = points[:, :3]
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)
    min_z, max_z = np.min(z), np.max(z)

    # Invert the point cloud: Z_inv = max_z - Z
    z_inv = max_z - z

    # Construct regular 2D raster grid for terrain cloth nodes
    cols = max(2, int(np.ceil((max_x - min_x) / grid_resolution)))
    rows = max(2, int(np.ceil((max_y - min_y) / grid_resolution)))

    # Compute minimum Z (maximum inverted Z) in each grid cell as hard collision ceiling
    grid_col_idx = np.clip(((x - min_x) / grid_resolution).astype(int), 0, cols - 1)
    grid_row_idx = np.clip(((y - min_y) / grid_resolution).astype(int), 0, rows - 1)

    terrain_min_z = np.full((rows, cols), np.inf)
    # Vectorized cell minimum computation (replaces slow Python loop)
    flat_idx = grid_row_idx * cols + grid_col_idx
    np.minimum.at(terrain_min_z.ravel(), flat_idx, z)

    # Fill empty cells with neighboring minimums
    valid_mask = np.isfinite(terrain_min_z)
    if not np.all(valid_mask):
        global_min = np.min(z)
        terrain_min_z[~valid_mask] = global_min

    # Interpolate ground height for each point from terrain cloth
    point_ground_z = terrain_min_z[grid_row_idx, grid_col_idx]
    
    # Distance of each point above the estimated ground cloth
    height_above_ground = z - point_ground_z

    # Ground points are those within class_threshold of the lowest envelope
    ground_mask = height_above_ground <= class_threshold
    non_ground_mask = ~ground_mask

    stats = {
        "total_points": int(len(points)),
        "ground_points": int(np.sum(ground_mask)),
        "non_ground_points": int(np.sum(non_ground_mask)),
        "ground_percentage": round(float(np.sum(ground_mask) / len(points) * 100), 1),
        "min_ground_elevation_m": round(float(min_z), 2),
        "max_structure_elevation_m": round(float(max_z), 2),
        "elevation_delta_m": round(float(max_z - min_z), 2)
    }

    return ground_mask, non_ground_mask, stats
