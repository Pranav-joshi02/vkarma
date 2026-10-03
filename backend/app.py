"""
3D Cadastral Registry & 3D ULPIN System - FastAPI Application
Provides RESTful APIs for:
- 10-Stage Geospatial Processing Pipeline
- 3D Cadastral Digital Twin & LADM ISO 19152 Queries
- Cryptographic 3D ULPIN Minting & Tamper Verification
- Topological Dispute & Encroachment Scanner (Jaljolie et al.)
- Address-as-a-Service (UPI for 3D Addresses / Logistics)
- Static WebGIS Frontend
"""

import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv, find_dotenv

# Ensure environment variables are loaded
load_dotenv(find_dotenv())
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.mock_data.pilot_tiles import (
    PILOT_REGIONS, get_pilot_region_by_id, generate_synthetic_lidar_point_cloud
)
from backend.pipeline.pipeline_orchestrator import run_full_3d_cadastral_pipeline
from backend.ladm.cadastral_db import cadastre_db
from backend.ulpin.ulpin_generator import parse_and_validate_ulpin, generate_3d_ulpin, SPACE_TYPE_NAMES
from backend.ladm.schema import LegalSpaceType
from backend.tasks import run_cadastral_pipeline_task
from celery.result import AsyncResult
from backend.celery_worker import celery_app

app = FastAPI(
    title="3D Cadastral Registry & 3D ULPIN System (ISO 19152 LADM)",
    description="Automated pipeline converting geospatial point cloud survey data into verifiable 3D land records.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Cache for latest pipeline output & point cloud
latest_pipeline_state: Dict[str, Any] = {}
latest_raw_points: Optional[np.ndarray] = None


from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=3)
in_memory_tasks: Dict[str, Dict[str, Any]] = {}


class PipelineRunRequest(BaseModel):
    region_id: Optional[str] = "blr_orr_560103"
    custom_bbox: Optional[List[float]] = None  # [min_lat, min_lng, max_lat, max_lng]
    selected_building_id: Optional[str] = None
    selected_building_name: Optional[str] = None
    selected_building_footprint: Optional[List[List[float]]] = None
    selected_building_floors: Optional[int] = None
    selected_building_height: Optional[float] = None
    target_single_building: Optional[bool] = None
    base_lat: Optional[float] = None
    base_lng: Optional[float] = None
    area_name: Optional[str] = None
    pincode: Optional[str] = None
    num_buildings: Optional[int] = None
    point_density: Optional[float] = 2.5
    include_dispute_scenario: Optional[bool] = True


class AreaBuildingsRequest(BaseModel):
    custom_bbox: Optional[List[float]] = None
    bbox: Optional[List[float]] = None
    area_name: Optional[str] = "Survey Area"
    pincode: Optional[str] = "560103"


class ULPINVerifyRequest(BaseModel):
    ulpin: str


@app.on_event("startup")
async def startup_db_sync():
    """Syncs existing 3D cadastral records from Supabase/PostgreSQL into memory on startup."""
    try:
        loaded = cadastre_db.load_from_database()
        if loaded:
            print(f"[Supabase] Successfully loaded {loaded} building(s) from persistent database.")
    except Exception as e:
        print(f"[Supabase] Startup database sync notice: {e}")


# --- API ROUTES ---

@app.get("/api/config")
def get_frontend_config():
    """Returns public frontend configuration including Cesium Ion token."""
    return {
        "cesium_ion_token": os.environ.get("CESIUM_ION_TOKEN", ""),
        "has_opentopography_key": bool(os.environ.get("OPENTOPOGRAPHY_API_KEY", "")),
        "has_supabase": bool(os.environ.get("SUPABASE_URL", "") or os.environ.get("DATABASE_URL", ""))
    }


@app.get("/api/database/status")
def get_db_status():
    """Returns current Supabase/PostgreSQL connection, migration status, and table record counts."""
    from backend.database.supabase_client import get_database_status
    return get_database_status()


@app.post("/api/database/migrate")
def trigger_migrations():
    """Executes all pending SQL migrations against Supabase/PostgreSQL."""
    from backend.database.migration_runner import run_all_migrations
    res = run_all_migrations()
    if res.get("status") == "SUCCESS":
        cadastre_db.load_from_database()
    return res


@app.get("/api/regions")
def get_regions():
    return {"regions": PILOT_REGIONS}


@app.post("/api/area/buildings")
def get_area_buildings(req: AreaBuildingsRequest):
    """
    Discovers all real buildings present in the specified bounding box using
    Overture Maps + OpenStreetMap, with real names where available and
    area-based synthetic names for unnamed buildings.
    """
    raw_bbox = req.custom_bbox or req.bbox
    if not raw_bbox or len(raw_bbox) != 4:
        raise HTTPException(status_code=400, detail="Bounding box must be [min_lat, min_lng, max_lat, max_lng]")
    from backend.pipeline.building_discovery import discover_buildings_in_bbox
    min_lat, min_lng, max_lat, max_lng = raw_bbox
    buildings = discover_buildings_in_bbox(
        min_lat, min_lng, max_lat, max_lng,
        area_name=req.area_name,
    )
    has_real = any(b.get("source") in ("osm", "overture+osm") for b in buildings)
    real_count = sum(1 for b in buildings if b.get("name_source") != "synthetic")
    synthetic_count = sum(1 for b in buildings if b.get("name_source") == "synthetic")
    return {
        "area_name": req.area_name or "Survey Area",
        "total_found": len(buildings),
        "total_buildings": len(buildings),
        "real_named_count": real_count,
        "synthetic_named_count": synthetic_count,
        "source": "overture+osm" if has_real else "estimated",
        "buildings": buildings
    }


def is_celery_broker_ready() -> bool:
    """Fast non-blocking check to verify if Redis broker is actively listening on port 6379."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.25)
        res = s.connect_ex(('127.0.0.1', 6379))
        s.close()
        return res == 0
    except Exception:
        return False


@app.post("/api/pipeline/run")
def run_pipeline(req: PipelineRunRequest):
    """
    Submits the 10-stage AI/ML & Cadastral Pipeline.
    Uses Celery worker if available, otherwise falls back to resilient in-process background worker.
    """
    req_dict = req.dict()
    import uuid
    task_id = str(uuid.uuid4())

    # Try Celery dispatch only if Redis broker is actively reachable
    if is_celery_broker_ready():
        try:
            from backend.tasks import run_cadastral_pipeline_task
            task = run_cadastral_pipeline_task.apply_async(args=[req_dict], task_id=task_id)
            return {"task_id": task_id, "status": "PROCESSING"}
        except Exception:
            pass

    in_memory_tasks[task_id] = {
        "state": "PROGRESS",
        "stage": "Initializing Pipeline",
        "progress": 5,
        "result": None,
        "error": None
    }

    class InProcessTaskContext:
        def __init__(self, t_id):
            self.id = t_id
            self.request = type('Req', (), {'id': t_id})()

        def update_state(self, state='PROGRESS', meta=None):
            meta = meta or {}
            in_memory_tasks[self.id].update({
                "state": state,
                "stage": meta.get("stage", ""),
                "progress": meta.get("progress", 0)
            })

    def run_in_thread():
        ctx = InProcessTaskContext(task_id)
        try:
            from backend.tasks import execute_pipeline_job
            res = execute_pipeline_job(ctx, req_dict)
            in_memory_tasks[task_id].update({
                "state": "SUCCESS",
                "stage": "Completed!",
                "progress": 100,
                "result": {"result": res}
            })
            # Sync active cadastre memory
            global latest_raw_points
            latest_pipeline_state.clear()
            latest_pipeline_state.update(res)
            if "buildings" in res:
                cadastre_db.register_buildings_from_dicts(res["buildings"], clear_first=False, persist=True)
            try:
                from backend.database.repository import cadastral_repo
                cadastral_repo.log_pipeline_run(task_id, res)
            except Exception:
                pass
        except Exception as err:
            import traceback
            traceback.print_exc()
            in_memory_tasks[task_id].update({
                "state": "FAILURE",
                "stage": "Error",
                "status": str(err),
                "error": str(err)
            })

    executor.submit(run_in_thread)
    return {"task_id": task_id, "status": "PROCESSING"}


@app.post("/api/pipeline/upload")
async def upload_pipeline(file: UploadFile = File(...)):
    """
    Accepts a .las/.laz file upload and queues the pipeline task.
    """
    from backend.pipeline.lidar_fetcher import save_uploaded_file
    content = await file.read()
    file_path = save_uploaded_file(content, file.filename)
    
    req_dict = {
        "file_path": file_path,
        "pincode": "UPLOAD",
        "area_name": file.filename,
        "base_lat": 12.9352,
        "base_lng": 77.6946,
        "include_dispute_scenario": True
    }
    
    import uuid
    task_id = str(uuid.uuid4())
    try:
        from backend.tasks import run_cadastral_pipeline_task
        task = run_cadastral_pipeline_task.apply_async(args=[req_dict], task_id=task_id)
        return {"task_id": task_id, "status": "PROCESSING"}
    except Exception:
        pass

    in_memory_tasks[task_id] = {
        "state": "PROGRESS",
        "stage": "Processing Uploaded LiDAR",
        "progress": 10,
        "result": None,
        "error": None
    }

    class UploadTaskContext:
        def __init__(self, t_id):
            self.id = t_id
            self.request = type('Req', (), {'id': t_id})()

        def update_state(self, state='PROGRESS', meta=None):
            meta = meta or {}
            in_memory_tasks[self.id].update({
                "state": state,
                "stage": meta.get("stage", ""),
                "progress": meta.get("progress", 0)
            })

    def run_upload_in_thread():
        ctx = UploadTaskContext(task_id)
        try:
            from backend.tasks import execute_pipeline_job
            res = execute_pipeline_job(ctx, req_dict)
            in_memory_tasks[task_id].update({
                "state": "SUCCESS",
                "stage": "Completed!",
                "progress": 100,
                "result": {"result": res}
            })
            global latest_raw_points
            latest_pipeline_state.clear()
            latest_pipeline_state.update(res)
            if "buildings" in res:
                cadastre_db.register_buildings_from_dicts(res["buildings"], clear_first=False, persist=True)
            try:
                from backend.database.repository import cadastral_repo
                cadastral_repo.log_pipeline_run(task_id, res)
            except Exception:
                pass
        except Exception as err:
            in_memory_tasks[task_id].update({
                "state": "FAILURE",
                "stage": "Error",
                "status": str(err),
                "error": str(err)
            })

    executor.submit(run_upload_in_thread)
    return {"task_id": task_id, "status": "PROCESSING"}


@app.get("/api/pipeline/status/{task_id}")
def get_pipeline_status(task_id: str):
    """
    Polls the status and progress of the pipeline task (in-process or Celery).
    """
    # 1. In-process task tracking
    if task_id in in_memory_tasks:
        info = in_memory_tasks[task_id]
        state = info.get("state", "PENDING")
        if state == "SUCCESS":
            res_data = info.get("result", {}).get("result", {})
            return {
                "state": "SUCCESS",
                "stage": "Completed!",
                "progress": 100,
                "result": res_data
            }
        elif state == "FAILURE":
            return {
                "state": "FAILURE",
                "status": info.get("status", info.get("error", "Task execution failed"))
            }
        else:
            return {
                "state": state,
                "stage": info.get("stage", "Processing..."),
                "progress": info.get("progress", 0)
            }

    # 2. Celery AsyncResult fallback
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'status': 'Pending in queue...'
        }
    elif task_result.state != 'FAILURE':
        response = {
            'state': task_result.state,
            'stage': task_result.info.get('stage', '') if isinstance(task_result.info, dict) else '',
            'progress': task_result.info.get('progress', 0) if isinstance(task_result.info, dict) else 0,
        }
        if task_result.state == 'SUCCESS':
            res_data = task_result.result.get('result', {}) if isinstance(task_result.result, dict) else {}
            response['result'] = res_data
            if res_data:
                global latest_raw_points
                latest_pipeline_state.clear()
                latest_pipeline_state.update(res_data)
                if "buildings" in res_data:
                    cadastre_db.register_buildings_from_dicts(res_data["buildings"], clear_first=False, persist=True)
                try:
                    from backend.database.repository import cadastral_repo
                    cadastral_repo.log_pipeline_run(task_id, res_data)
                except Exception:
                    pass
    else:
        response = {
            'state': task_result.state,
            'status': str(task_result.info),
        }
    return response


@app.get("/api/cadastre/status")
def get_cadastre_status():
    """Returns current active cadastral digital twin summary."""
    buildings = cadastre_db.list_all_buildings()
    total_units = len(cadastre_db.legal_units_by_id)
    return {
        "is_active": len(buildings) > 0,
        "total_buildings": len(buildings),
        "total_legal_units": total_units,
        "latest_pipeline_summary": latest_pipeline_state.get("summary", {})
    }


@app.get("/api/buildings")
def list_buildings():
    """Lists all registered 3D spatial building shells."""
    return {"buildings": cadastre_db.list_all_buildings()}


@app.get("/api/buildings/{building_id}")
def get_building_detail(building_id: str):
    """Fetches full 3D building model, floor subdivisions, and legal units."""
    bld = cadastre_db.get_building(building_id)
    if not bld:
        raise HTTPException(status_code=404, detail=f"Building '{building_id}' not found in active cadastre.")
    return bld.to_dict()


@app.get("/api/ulpin/lookup/{ulpin}")
def lookup_ulpin(ulpin: str):
    """
    Resolves a 3D ULPIN to its full ISO 19152 ownership record, geometry, and legal documents.
    """
    unit = cadastre_db.get_unit_by_ulpin(ulpin)
    if not unit:
        # Validate format even if not in current memory DB
        val = parse_and_validate_ulpin(ulpin)
        if not val["is_valid"]:
            raise HTTPException(status_code=400, detail=val.get("error", "Invalid ULPIN format"))
        return {
            "found_in_active_db": False,
            "ulpin_validation": val,
            "message": "ULPIN structure and check digit are valid, but unit is not registered in current session's active pilot tile."
        }

    val = parse_and_validate_ulpin(ulpin)
    return {
        "found_in_active_db": True,
        "ulpin_validation": val,
        "unit": unit.to_dict()
    }


@app.post("/api/ulpin/verify")
def verify_ulpin(req: ULPINVerifyRequest):
    """
    Cryptographic verification endpoint for 3D ULPINs (Verhoeff check digit & Feistel reverse decryption).
    """
    res = parse_and_validate_ulpin(req.ulpin)
    return res


@app.post("/api/disputes/scan")
def scan_disputes(building_id: Optional[str] = None):
    """
    Runs 3D topological collision and encroachment detection across all units or a specific building.
    """
    report = cadastre_db.run_conflict_scan(building_id)
    return report


@app.get("/api/delivery/resolve/{ulpin}")
def resolve_delivery_address(ulpin: str):
    """
    Address-as-a-Service (UPI for 3D Addresses):
    Resolves a 3D ULPIN into precise 3D delivery coordinates and dispatch instructions for drones / couriers.
    """
    unit = cadastre_db.get_unit_by_ulpin(ulpin)
    if not unit:
        raise HTTPException(status_code=404, detail=f"ULPIN '{ulpin}' not found in registry.")

    bld = cadastre_db.get_building(unit.building_id)
    b_name = bld.building_name if bld else "Urban Tower"
    b_lat = bld.centroid_lat if bld else 12.9352
    b_lng = bld.centroid_lng if bld else 77.6946

    # Unit center in local/world coords
    bbox = unit.bbox
    cx = (bbox.min_x + bbox.max_x) / 2
    cy = (bbox.min_y + bbox.max_y) / 2
    cz = (bbox.min_z + bbox.max_z) / 2
    altitude_agl = round(cz - (bld.ground_elevation_m if bld else 920.0), 2)

    return {
        "ulpin": ulpin,
        "unit_name": unit.unit_name,
        "space_type": unit.space_type.value,
        "space_type_name": SPACE_TYPE_NAMES.get(unit.space_type.value, "Residential"),
        "formatted_postal_address": f"{unit.unit_name}, {b_name}, Pincode: {unit.ulpin.split('-')[0]}, India",
        "precision_3d_coordinates": {
            "latitude": round(b_lat + (cx * 0.000009), 6),
            "longitude": round(b_lng + (cy * 0.000009), 6),
            "altitude_agl_m": altitude_agl,
            "floor_level": unit.floor_level,
            "subsurface_depth_m": abs(altitude_agl) if altitude_agl < 0 else 0.0
        },
        "logistics_dispatch_routing": {
            "wing_quadrant": "North-West" if cx < 0 and cy > 0 else ("North-East" if cx >= 0 and cy > 0 else ("South-West" if cx < 0 else "South-East")),
            "elevator_core_recommended": f"Core Core-1 (Floor {unit.floor_level})",
            "drone_dropoff_available": unit.floor_level >= 5 or unit.space_type.value in ('M', 'R'),
            "drone_landing_point": {
                "latitude": round(b_lat, 6),
                "longitude": round(b_lng, 6),
                "altitude_agl_m": round(altitude_agl + 1.2, 2)
            }
        }
    }


@app.get("/api/pointcloud/sample")
def get_pointcloud_sample(max_points: int = Query(6000, le=15000)):
    """
    Returns a subsampled point cloud with classification labels and coordinates for WebGL rendering.
    """
    global latest_raw_points
    if latest_raw_points is None or len(latest_raw_points) == 0:
        latest_raw_points = generate_synthetic_lidar_point_cloud(num_buildings=3)

    pts = latest_raw_points
    n = len(pts)
    step = max(1, n // max_points)
    sample = pts[::step]

    # Quick classify for sample rendering
    ground_z = float(np.min(sample[:, 2]))
    ground_mask = (sample[:, 2] - ground_z) < 1.0

    return {
        "total_points": n,
        "sample_points_count": len(sample),
        "points": [
            {
                "x": round(float(p[0]), 2),
                "y": round(float(p[1]), 2),
                "z": round(float(p[2]), 2),
                "class": 2 if (p[2] - ground_z) < 1.0 else (6 if (p[2] - ground_z) > 4.0 else 5)
            }
            for p in sample
        ]
    }


# API route for featured / sample 3D ULPINs
@app.get("/api/ulpin/featured")
def get_featured_ulpins():
    """Returns curated featured 3D ULPINs for instant demonstration."""
    return {
        "featured": [
            {
                "ulpin": "560103-A-60YLMDPD-2",
                "label": "Unit 702 (Tower A - Residential)",
                "location": "Bengaluru Tech Corridor (Outer Ring Road)",
                "status": "Clear Freehold"
            },
            {
                "ulpin": "560103-A-G011E73B-8",
                "label": "Sky Villa Penthouse 1201",
                "location": "Bengaluru Tech Corridor",
                "status": "Bank Mortgaged"
            },
            {
                "ulpin": "560103-P-K9VF9HU8-9",
                "label": "Parking Bay B2-14 (Basement 2)",
                "location": "Basement Level Subsurface",
                "status": "Clear Freehold"
            },
            {
                "ulpin": "560103-R-0Y8L1W9X-0",
                "label": "Air-Rights Sky Deck (+15m)",
                "location": "Bengaluru Outer Ring Road",
                "status": "Drone & Solar Right"
            },
            {
                "ulpin": "400051-B-RG0LN1X6-7",
                "label": "Commercial Suite 1401",
                "location": "Bandra-Kurla Complex (Mumbai BKC)",
                "status": "Grade-A Commercial"
            }
        ]
    }


# Serve static frontend files and routes
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_landing_page():
        landing_file = os.path.join(frontend_dir, "landing.html")
        if os.path.exists(landing_file):
            return FileResponse(landing_file)
        return FileResponse(os.path.join(frontend_dir, "console.html"))

    @app.get("/console")
    @app.get("/app")
    def serve_console_service():
        console_file = os.path.join(frontend_dir, "console.html")
        if os.path.exists(console_file):
            return FileResponse(console_file)
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/ulpin")
    @app.get("/ulpin/{ulpin_code}")
    def serve_ulpin_passport_page(ulpin_code: Optional[str] = None):
        return FileResponse(os.path.join(frontend_dir, "ulpin.html"))

    @app.get("/about")
    def serve_about_page():
        return FileResponse(os.path.join(frontend_dir, "about.html"))

