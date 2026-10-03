"""
DBSCAN & Euclidean Multi-Building Instance Clustering
Segments classified building points into discrete individual building physical space units.
"""

import numpy as np
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any, Tuple


def cluster_building_instances(
    points: np.ndarray,
    building_mask: np.ndarray,
    eps: float = 3.5,
    min_samples: int = 15,
    min_points_per_building: int = 40
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Groups building points into distinct spatial clusters (Building Towers / Blocks).
    
    Args:
        points: (N, 3) point coordinates
        building_mask: boolean mask where True indicates Class 6 (Building)
        eps: DBSCAN neighborhood radius (meters)
        min_samples: Core point threshold
        min_points_per_building: Minimum points to qualify as a valid cadastral building
        
    Returns:
        cluster_labels: array of cluster IDs (-1 for noise, 0..K-1 for building instances)
        building_clusters: list of building metadata dicts
    """
    full_cluster_labels = np.full(points.shape[0], -1, dtype=int)
    building_indices = np.where(building_mask)[0]

    if len(building_indices) < min_samples:
        return full_cluster_labels, []

    # Cluster in 2D/3D (Z-scaled to preserve vertical tower cohesion)
    building_pts = points[building_indices, :3].copy()
    # Apply spatial scaling on Z so tall towers stay cohesive
    clustering_pts = np.column_stack([
        building_pts[:, 0],
        building_pts[:, 1],
        building_pts[:, 2] * 0.4
    ])

    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(clustering_pts)

    unique_labels = set(labels) - {-1}
    building_clusters = []
    valid_instance_id = 0

    for lbl in sorted(unique_labels):
        member_mask = (labels == lbl)
        count = int(np.sum(member_mask))
        if count < min_points_per_building:
            continue

        instance_pts = building_pts[member_mask]
        instance_indices = building_indices[member_mask]
        full_cluster_labels[instance_indices] = valid_instance_id

        min_bounds = np.min(instance_pts, axis=0)
        max_bounds = np.max(instance_pts, axis=0)
        centroid = np.mean(instance_pts, axis=0)

        building_clusters.append({
            "instance_id": valid_instance_id,
            "point_count": count,
            "centroid": [round(float(c), 3) for c in centroid],
            "min_bounds": [round(float(b), 3) for b in min_bounds],
            "max_bounds": [round(float(b), 3) for b in max_bounds],
            "height_m": round(float(max_bounds[2] - min_bounds[2]), 2),
            "estimated_floors": max(1, int(round((max_bounds[2] - min_bounds[2]) / 3.2)))
        })
        valid_instance_id += 1

    return full_cluster_labels, building_clusters
