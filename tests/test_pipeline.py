"""
Unit Tests for AI/ML & 3D Cadastral Pipeline
"""

import pytest
import numpy as np
from backend.mock_data.pilot_tiles import generate_synthetic_lidar_point_cloud
from backend.pipeline.csf_filter import cloth_simulation_filter
from backend.pipeline.point_classifier import classify_point_cloud
from backend.pipeline.clustering import cluster_building_instances
from backend.pipeline.footprint_extractor import extract_regularized_footprint
from backend.pipeline.pipeline_orchestrator import run_full_3d_cadastral_pipeline


def test_synthetic_pointcloud_generator():
    pts = generate_synthetic_lidar_point_cloud(num_buildings=2, area_size=100.0)
    assert pts.shape[0] > 5000
    assert pts.shape[1] == 3


def test_csf_ground_separation():
    pts = generate_synthetic_lidar_point_cloud(num_buildings=2, area_size=100.0)
    g_mask, ng_mask, stats = cloth_simulation_filter(pts)
    assert np.sum(g_mask) > 0
    assert np.sum(ng_mask) > 0
    assert stats["ground_percentage"] > 20


def test_end_to_end_pipeline():
    pts = generate_synthetic_lidar_point_cloud(num_buildings=2, area_size=100.0)
    res = run_full_3d_cadastral_pipeline(pts, pincode="110001", area_name="Delhi CP", has_dispute_scenario=False)
    assert res["status"] == "SUCCESS"
    assert res["summary"]["buildings_detected"] >= 2
    assert res["summary"]["legal_space_units_minted"] > 0
    assert len(res["pipeline_stages"]) == 10
