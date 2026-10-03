import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.pipeline.building_discovery import discover_buildings_in_bbox

client = TestClient(app)

def test_discover_buildings_in_bbox():
    # Cessna Business Park, Bengaluru
    min_lat, min_lng = 12.9330, 77.6910
    max_lat, max_lng = 12.9370, 77.6970
    
    buildings = discover_buildings_in_bbox(min_lat, min_lng, max_lat, max_lng)
    assert len(buildings) > 0, "Should discover buildings in bounding box"
    
    first = buildings[0]
    assert "id" in first
    assert "name" in first
    assert "centroid" in first
    assert "footprint_coordinates" in first
    assert "floors" in first
    assert "height_m" in first
    assert "type" in first


def test_api_area_buildings_endpoint():
    resp = client.post("/api/area/buildings", json={
        "bbox": [12.9330, 77.6910, 12.9370, 77.6970],
        "area_name": "Bengaluru Outer Ring Road",
        "pincode": "560103"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_found"] > 0
    assert len(data["buildings"]) > 0
    assert data["source"] in ["osm", "estimated"]


def test_single_building_selection_pipeline():
    # Pick a building to process
    target_bld_name = "Aloft Bengaluru Cessna Business Park"
    req_payload = {
        "custom_bbox": [12.9330, 77.6910, 12.9370, 77.6970],
        "area_name": "Bengaluru Outer Ring Road",
        "pincode": "560103",
        "base_lat": 12.9370,
        "base_lng": 77.6950,
        "selected_building_id": "osm_347475248",
        "selected_building_name": target_bld_name,
        "selected_building_floors": 5,
        "selected_building_height": 16.0,
        "target_single_building": True,
        "num_buildings": 1,
        "include_dispute_scenario": False
    }
    
    run_resp = client.post("/api/pipeline/run", json=req_payload)
    assert run_resp.status_code == 200
    task_id = run_resp.json()["task_id"]
    
    # Wait for completion
    import time
    for _ in range(30):
        time.sleep(0.4)
        stat = client.get(f"/api/pipeline/status/{task_id}").json()
        if stat.get("state") == "SUCCESS":
            res = stat.get("result", {})
            buildings = res.get("buildings", [])
            assert len(buildings) == 1, f"Expected 1 building, got {len(buildings)}"
            assert target_bld_name in buildings[0]["building_name"]
            assert len(buildings[0]["legal_units"]) > 0
            return
        elif stat.get("state") == "FAILURE":
            pytest.fail(f"Pipeline failed: {stat}")
            
    pytest.fail("Pipeline did not finish in time")
