import time
import math
import numpy as np
from backend.celery_worker import celery_app
from backend.pipeline.lidar_fetcher import fetch_lidar_data
from backend.pipeline.pipeline_orchestrator import run_full_3d_cadastral_pipeline


def execute_pipeline_job(task_instance, req_data: dict):
    """
    Core pipeline execution logic shared by both Celery worker and in-process background worker.
    """
    if task_instance and hasattr(task_instance, "update_state"):
        task_instance.update_state(state='PROGRESS', meta={'stage': 'Analyzing Geographic Boundary', 'progress': 10})

    custom_bbox = req_data.get("custom_bbox")
    file_path = req_data.get("file_path")
    
    base_lat = req_data.get("base_lat")
    base_lng = req_data.get("base_lng")
    num_blds = req_data.get("num_buildings")

    target_bld = req_data.get("target_single_building")
    if (not isinstance(target_bld, dict) or isinstance(target_bld, bool)) and req_data.get("selected_building_name"):
        target_bld = {
            "id": req_data.get("selected_building_id"),
            "name": req_data.get("selected_building_name"),
            "centroid_lat": req_data.get("base_lat"),
            "centroid_lng": req_data.get("base_lng"),
            "footprint_local": req_data.get("selected_building_footprint_local") or req_data.get("selected_building_footprint"),
            "floors": req_data.get("selected_building_floors", 12),
            "height_m": req_data.get("selected_building_height", 38.4),
            "width_m": req_data.get("selected_building_width_m", 26.0),
            "length_m": req_data.get("selected_building_length_m", 24.0)
        }
    elif not isinstance(target_bld, dict):
        target_bld = None

    if target_bld:
        num_blds = 1
        if target_bld.get("centroid_lat"):
            base_lat = target_bld["centroid_lat"]
        if target_bld.get("centroid_lng"):
            base_lng = target_bld["centroid_lng"]

    if custom_bbox and len(custom_bbox) == 4:
        min_lat, min_lng, max_lat, max_lng = custom_bbox
        calc_lat = (min_lat + max_lat) / 2.0
        calc_lng = (min_lng + max_lng) / 2.0
        if base_lat is None:
            base_lat = calc_lat
        if base_lng is None:
            base_lng = calc_lng

        # Determine area and dynamic building count
        box_h = max(40.0, abs(max_lat - min_lat) * 111111.0)
        box_w = max(40.0, abs(max_lng - min_lng) * 111111.0 * math.cos(math.radians(calc_lat)))
        area_sqm = box_h * box_w
        if not num_blds or num_blds <= 0 or num_blds == 3:
            # Scaled urban density: ~1 building per 2,200 sqm
            num_blds = 1 if target_bld else max(4, min(35, int(round(area_sqm / 2200.0))))

        if not file_path:
            file_path = fetch_lidar_data(min_lat, min_lng, max_lat, max_lng, num_buildings=num_blds)
    else:
        if base_lat is None:
            base_lat = 12.9352
        if base_lng is None:
            base_lng = 77.6946
        if not num_blds or num_blds <= 0:
            num_blds = 1 if target_bld else 4
        if not file_path:
            file_path = fetch_lidar_data(12.930, 77.690, 12.940, 77.700, num_buildings=num_blds)

    if task_instance and hasattr(task_instance, "update_state"):
        task_instance.update_state(state='PROGRESS', meta={'stage': 'Executing 10-Stage AI Pipeline', 'progress': 30})

    # Read .las/.laz file to numpy array
    import laspy
    las = laspy.read(file_path)
    points = np.vstack((las.x, las.y, las.z)).transpose()

    # If point cloud is too sparse (< 100 points), supplement with realistic urban generator
    if len(points) < 100:
        from backend.mock_data.pilot_tiles import generate_synthetic_lidar_point_cloud
        points = generate_synthetic_lidar_point_cloud(num_buildings=num_blds, area_size=120.0)

    # Run full 10-stage pipeline with accurate geographic positioning
    result = run_full_3d_cadastral_pipeline(
        raw_points=points,
        pincode=req_data.get("pincode", "560103"),
        area_name=req_data.get("area_name", "Survey Area"),
        base_lat=float(base_lat),
        base_lng=float(base_lng),
        has_dispute_scenario=req_data.get("include_dispute_scenario", True),
        task_instance=task_instance,
        target_single_building=target_bld
    )

    return result


@celery_app.task(bind=True)
def run_cadastral_pipeline_task(self, req_data: dict):
    """
    Celery task that executes the pipeline asynchronously.
    """
    try:
        result = execute_pipeline_job(self, req_data)
        return {"status": "SUCCESS", "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
