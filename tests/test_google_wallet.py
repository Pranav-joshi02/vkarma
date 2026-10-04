"""
Unit & Integration Tests for Google Wallet Generic Pass Service
"""

import pytest
from fastapi.testclient import TestClient
from backend.wallet.google_wallet_service import google_wallet_service
from backend.app import app


def test_google_wallet_ids():
    class_id = google_wallet_service.get_class_id()
    assert "vkarma_3d_land_passport_class" in class_id
    assert class_id.startswith(google_wallet_service.issuer_id)

    obj_id = google_wallet_service.get_object_id("560103-A-60YLMDPD-2")
    assert "560103_A_60YLMDPD_2" in obj_id
    assert obj_id.startswith(google_wallet_service.issuer_id)


def test_build_generic_class():
    gclass = google_wallet_service.build_generic_class()
    assert gclass["id"] == google_wallet_service.get_class_id()
    assert "issuerName" in gclass
    assert "classTemplateInfo" in gclass


def test_build_generic_object():
    test_ulpin = "560103-A-60YLMDPD-2"
    gobj = google_wallet_service.build_generic_object(test_ulpin, recipient_name="Pranav Joshi")
    
    assert gobj["id"] == google_wallet_service.get_object_id(test_ulpin)
    assert gobj["header"]["defaultValue"]["value"] == test_ulpin
    assert gobj["subheader"]["defaultValue"]["value"] == "Pranav Joshi"
    assert gobj["barcode"]["type"] == "QR_CODE"
    assert "https://vkarma.in/ulpin/" in gobj["barcode"]["value"]
    
    # Check text modules
    modules = {m["id"]: m["body"] for m in gobj["textModulesData"]}
    assert "space_type" in modules
    assert "floor_level" in modules
    assert "carpet_area" in modules
    assert "volume" in modules
    assert "z_bounds" in modules


def test_create_google_wallet_pass_sandbox():
    test_ulpin = "560103-A-60YLMDPD-2"
    res = google_wallet_service.create_google_wallet_pass(test_ulpin, "Pranav Joshi")
    
    assert res["success"] is True
    assert res["status"] in ("LIVE", "SANDBOX")
    assert res["ulpin"] == test_ulpin
    assert "save_url" in res
    assert res["save_url"].startswith("https://pay.google.com/gp/v/save/")
    assert len(res["jwt"]) > 100
    assert res["pass_object"]["subheader"]["defaultValue"]["value"] == "Pranav Joshi"


def test_invalid_ulpin_raises_error():
    with pytest.raises(ValueError):
        google_wallet_service.create_google_wallet_pass("INVALID-ULPIN-999")


def test_fastapi_wallet_endpoints():
    client = TestClient(app)

    # 1. Config
    resp = client.get("/api/wallet/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "issuer_id" in cfg
    assert "class_id" in cfg
    assert "service_account" in cfg

    # 2. Generate Pass
    payload = {
        "ulpin": "560103-A-60YLMDPD-2",
        "recipient_name": "Test Citizen"
    }
    resp = client.post("/api/wallet/google-pass", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["save_url"].startswith("https://pay.google.com/gp/v/save/")
    assert data["owner_name"] == "Test Citizen"

    # 3. Bad Request Validation
    bad_payload = {
        "ulpin": "bad-ulpin-format"
    }
    resp = client.post("/api/wallet/google-pass", json=bad_payload)
    assert resp.status_code == 400
