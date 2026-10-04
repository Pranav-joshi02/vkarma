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
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel
from backend.digilocker import (
    digilocker_service,
    DigiLockerPushRequest,
    DigiLockerPullUriRequest,
    DigiLockerPullDocRequest
)
from backend.email_service import brevo_email_service
from backend.wallet.google_wallet_service import google_wallet_service

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
    title="3D Cadastral Registry & 3D ULPIN System",
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
    """Fast check to verify if the configured Redis broker (local or cloud) is actively reachable."""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
        import redis
        client = redis.from_url(redis_url, socket_timeout=0.6, socket_connect_timeout=0.6)
        return bool(client.ping())
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
    bld_dict = bld.to_dict()
    if not bld_dict.get("image_url"):
        from backend.pipeline.building_images import get_building_realistic_image
        bld_dict["image_url"] = get_building_realistic_image(
            building_name=bld.building_name,
            total_floors=bld.total_floors,
            building_id=bld.building_id
        )
    return bld_dict


@app.get("/api/ulpin/lookup/{ulpin}")
def lookup_ulpin(ulpin: str):
    """
    Resolves a 3D ULPIN or Building ID to its full ISO 19152 ownership record, geometry, and legal documents.
    """
    from backend.pipeline.building_images import get_building_realistic_image

    # Check if query is actually a building_id
    bld_match = cadastre_db.get_building(ulpin)
    if bld_match and bld_match.legal_units:
        unit = bld_match.legal_units[0]
        building = bld_match
    else:
        unit = cadastre_db.get_unit_by_ulpin(ulpin)
        building = cadastre_db.get_building(unit.building_id) if (unit and unit.building_id) else None

    if not unit:
        # Validate format even if not in current memory DB
        val = parse_and_validate_ulpin(ulpin)
        if not val["is_valid"]:
            raise HTTPException(status_code=400, detail=val.get("error", "Invalid ULPIN format"))
        synth_img = get_building_realistic_image(
            space_type=val.get("space_type"),
            building_id=ulpin
        )
        return {
            "found_in_active_db": False,
            "ulpin_validation": val,
            "image_url": synth_img,
            "message": "ULPIN structure and check digit are valid, but unit is not registered in current session's active pilot tile."
        }

    val = parse_and_validate_ulpin(unit.ulpin)
    unit_dict = unit.to_dict()
    bld_dict = building.to_dict() if building else None

    # Guarantee realistic building image is present
    bld_name = building.building_name if building else unit.unit_name
    floors = building.total_floors if building else 5
    space_t = unit.space_type.value if hasattr(unit.space_type, "value") else str(unit.space_type)
    realistic_img = unit_dict.get("image_url") or (bld_dict and bld_dict.get("image_url")) or get_building_realistic_image(
        building_name=bld_name,
        total_floors=floors,
        space_type=space_t,
        building_id=unit.building_id
    )
    unit_dict["image_url"] = realistic_img
    if bld_dict:
        bld_dict["image_url"] = realistic_img

    return {
        "found_in_active_db": True,
        "ulpin_validation": val,
        "unit": unit_dict,
        "building": bld_dict,
        "image_url": realistic_img
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


# --- DIGILOCKER ISSUER & CITIZEN PUSH API ROUTES ---

@app.get("/api/digilocker/config")
def get_digilocker_config():
    """Returns public DigiLocker Issuer configuration and sandbox status."""
    return {
        "issuer_id": digilocker_service.issuer_id,
        "issuer_name": digilocker_service.issuer_name,
        "doc_type": digilocker_service.doc_type,
        "doc_title": digilocker_service.doc_title,
        "is_sandbox": digilocker_service.is_sandbox,
        "gateway_connected": not digilocker_service.is_sandbox
    }


@app.post("/api/digilocker/push-certificate")
def push_digilocker_certificate(req: DigiLockerPushRequest):
    """
    Citizen 'Save to DigiLocker' flow:
    Issues, digitally signs, and stores the 3D Bhu-Aadhaar Certificate into citizen's DigiLocker vault.
    """
    try:
        res = digilocker_service.push_certificate_to_digilocker(req)
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to issue DigiLocker certificate: {str(e)}")


@app.get("/api/digilocker/status/{ulpin}")
def get_digilocker_status(ulpin: str):
    """Checks whether a 3D ULPIN certificate has already been issued to DigiLocker."""
    return digilocker_service.get_status(ulpin)


@app.get("/api/digilocker/certificate/{ulpin}/xml")
def get_digilocker_xml(ulpin: str):
    """Fetches the official DigiLocker XML document conforming to MeitY Certificate schema."""
    val = parse_and_validate_ulpin(ulpin)
    if not val.get("is_valid", False):
        raise HTTPException(status_code=400, detail="Invalid ULPIN format")
    xml_content = digilocker_service.generate_digilocker_xml(ulpin)
    return Response(content=xml_content, media_type="application/xml")


@app.post("/api/digilocker/pull-uri")
def digilocker_pull_uri(req: DigiLockerPullUriRequest):
    """
    Government DigiLocker Issuer Gateway: Pull URI Endpoint
    Called by national DigiLocker gateway to discover 3D Bhu-Aadhaar certificate URI.
    """
    return digilocker_service.pull_uri_gateway(req)


@app.post("/api/digilocker/pull-doc")
def digilocker_pull_doc(req: DigiLockerPullDocRequest):
    """
    Government DigiLocker Issuer Gateway: Pull Doc Endpoint
    Called by national DigiLocker gateway to retrieve signed document content (XML/PDF).
    """
    res = digilocker_service.pull_doc_gateway(req)
    if res.response_status == 0:
        raise HTTPException(status_code=404, detail=res.error_message or "Document not found")
    return res


@app.get("/api/digilocker/docs")
def list_digilocker_docs():
    """Lists all certificates issued into DigiLocker."""
    docs = digilocker_service.list_all_issued()
    return {
        "count": len(docs),
        "documents": docs
    }


# --- BREVO TRANSACTIONAL EMAIL API ROUTES ---

class EmailDispatchRequest(BaseModel):
    recipient_email: str
    recipient_name: Optional[str] = None
    ulpin: str


@app.get("/api/email/config")
def get_email_config():
    """Returns Brevo email gateway configuration status."""
    return {
        "is_configured": brevo_email_service.is_configured,
        "sender_email": brevo_email_service.sender_email,
        "sender_name": brevo_email_service.sender_name
    }


@app.post("/api/email/send-certificate")
def send_certificate_email(req: EmailDispatchRequest):
    """
    Sends the official 3D Bhu-Aadhaar Digital Land Title Certificate
    directly to citizen email using Brevo.
    """
    try:
        res = brevo_email_service.send_certificate_email(
            to_email=req.recipient_email,
            to_name=req.recipient_name,
            ulpin=req.ulpin
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email dispatch error: {str(exc)}")


@app.post("/api/email/send-passport")
def send_passport_email(req: EmailDispatchRequest):
    """
    Sends the executive Digital Land Passport directly to citizen email using Brevo.
    """
    try:
        res = brevo_email_service.send_passport_email(
            to_email=req.recipient_email,
            to_name=req.recipient_name,
            ulpin=req.ulpin
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email dispatch error: {str(exc)}")


# --- GOOGLE WALLET PASS API ROUTES ---

class GoogleWalletPassRequest(BaseModel):
    ulpin: str
    recipient_name: Optional[str] = None
    origin: Optional[str] = None


@app.get("/api/wallet/config")
def get_wallet_config():
    """Returns Google Wallet gateway status and issuer information."""
    return {
        "is_configured": google_wallet_service.is_live_configured,
        "issuer_id": google_wallet_service.issuer_id,
        "class_id": google_wallet_service.get_class_id(),
        "service_account": google_wallet_service.service_account_email
    }


@app.post("/api/wallet/google-pass")
def generate_google_wallet_pass(req: GoogleWalletPassRequest):
    """
    Generates an official Google Wallet Generic Pass for a 3D Bhu-Aadhaar Land Passport.
    Returns signed JWT and direct Google Pay Save URL (https://pay.google.com/gp/v/save/{jwt}).
    """
    try:
        res = google_wallet_service.create_google_wallet_pass(
            ulpin=req.ulpin,
            recipient_name=req.recipient_name,
            origin=req.origin
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Google Wallet pass generation error: {str(exc)}")


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

    @app.api_route("/health", methods=["GET", "HEAD"])
    @app.api_route("/healthz", methods=["GET", "HEAD"])
    def health_check():
        return {"status": "ok", "service": "vkarma-3d-cadastre"}

    @app.api_route("/", methods=["GET", "HEAD"])
    def serve_landing_page():
        landing_file = os.path.join(frontend_dir, "landing.html")
        if os.path.exists(landing_file):
            return FileResponse(landing_file)
        return FileResponse(os.path.join(frontend_dir, "console.html"))

    @app.api_route("/console", methods=["GET", "HEAD"])
    @app.api_route("/app", methods=["GET", "HEAD"])
    def serve_console_service():
        console_file = os.path.join(frontend_dir, "console.html")
        if os.path.exists(console_file):
            return FileResponse(console_file)
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.api_route("/ulpin", methods=["GET", "HEAD"])
    @app.api_route("/ulpin/{ulpin_code}", methods=["GET", "HEAD"])
    def serve_ulpin_passport_page(ulpin_code: Optional[str] = None):
        return FileResponse(os.path.join(frontend_dir, "ulpin.html"))

    @app.api_route("/about", methods=["GET", "HEAD"])
    def serve_about_page():
        return FileResponse(os.path.join(frontend_dir, "about.html"))


if __name__ == "__main__":
    import uvicorn
    run_port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=run_port)


