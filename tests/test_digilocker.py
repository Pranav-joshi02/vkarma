"""
Unit Tests for DigiLocker Issuer Service & Document Exchange
"""

import pytest
from backend.digilocker.issuer_service import digilocker_service
from backend.digilocker.models import (
    DigiLockerPushRequest,
    DigiLockerPullUriRequest,
    DigiLockerPullDocRequest
)


def test_digilocker_uri_generation():
    test_ulpin = "560103-A-60YLMDPD-2"
    uri = digilocker_service.generate_doc_uri(test_ulpin)
    assert uri == "in.gov.dilrmp-BHUCR-560103A60YLMDPD2"
    assert "in.gov.dilrmp" in uri
    assert "BHUCR" in uri


def test_digilocker_xml_generation():
    test_ulpin = "560103-A-60YLMDPD-2"
    xml = digilocker_service.generate_digilocker_xml(test_ulpin)
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert "<Certificate" in xml
    assert "<DocType>BHUCR</DocType>" in xml
    assert f"<ULPIN>{test_ulpin}</ULPIN>" in xml
    assert "Digital India Land Records Modernization Programme" in xml
    assert "SHA256withRSA" in xml
    assert "VerhoeffTamperCheck" in xml


def test_push_certificate_to_digilocker():
    test_ulpin = "560103-A-60YLMDPD-2"
    req = DigiLockerPushRequest(
        ulpin=test_ulpin,
        citizen_name="Vikramaditya S. Rathore",
        citizen_aadhaar_hash="AADHAAR-8902-1123"
    )
    res = digilocker_service.push_certificate_to_digilocker(req)
    assert res.success is True
    assert res.status in ("ISSUED", "ALREADY_ISSUED")
    assert res.digilocker_uri == "in.gov.dilrmp-BHUCR-560103A60YLMDPD2"
    assert res.owner_name == "Vikramaditya S. Rathore"
    assert "SHA256:" in res.sha256_hash

    # Check status
    status = digilocker_service.get_status(test_ulpin)
    assert status.is_stored is True
    assert status.digilocker_uri == res.digilocker_uri


def test_pull_uri_gateway():
    test_ulpin = "560103-A-60YLMDPD-2"
    req = DigiLockerPullUriRequest(ulpin=test_ulpin)
    res = digilocker_service.pull_uri_gateway(req)
    assert res.response_status == 1
    assert res.status_code == "SUCCESS"
    assert res.doc_details["uri"] == "in.gov.dilrmp-BHUCR-560103A60YLMDPD2"


def test_pull_doc_gateway():
    test_ulpin = "560103-A-60YLMDPD-2"
    uri = digilocker_service.generate_doc_uri(test_ulpin)
    req = DigiLockerPullDocRequest(uri=uri)
    res = digilocker_service.pull_doc_gateway(req)
    assert res.response_status == 1
    assert res.doc_content != ""
    assert res.doc_type == "BHUCR"
    assert "SHA256:" in res.sha256_digest


def test_fastapi_digilocker_endpoints():
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)

    # 1. Config endpoint
    resp = client.get("/api/digilocker/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["doc_type"] == "BHUCR"
    assert "issuer_id" in cfg

    # 2. Push certificate endpoint
    push_payload = {
        "ulpin": "560103-A-60YLMDPD-2",
        "citizen_name": "Vikramaditya S. Rathore",
        "citizen_aadhaar_hash": "AADHAAR-8902-1123"
    }
    resp = client.post("/api/digilocker/push-certificate", json=push_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "in.gov.dilrmp-BHUCR-" in data["digilocker_uri"]

    # 3. Status endpoint
    resp = client.get("/api/digilocker/status/560103-A-60YLMDPD-2")
    assert resp.status_code == 200
    st = resp.json()
    assert st["is_stored"] is True
    assert st["digilocker_uri"] == data["digilocker_uri"]

    # 4. XML endpoint
    resp = client.get("/api/digilocker/certificate/560103-A-60YLMDPD-2/xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "<Certificate" in resp.text
    assert "<DocType>BHUCR</DocType>" in resp.text

    # 5. Gateway pull-uri endpoint
    resp = client.post("/api/digilocker/pull-uri", json={"ulpin": "560103-A-60YLMDPD-2"})
    assert resp.status_code == 200
    uri_res = resp.json()
    assert uri_res["response_status"] == 1

    # 6. Gateway pull-doc endpoint
    resp = client.post("/api/digilocker/pull-doc", json={"uri": data["digilocker_uri"]})
    assert resp.status_code == 200
    doc_res = resp.json()
    assert doc_res["response_status"] == 1
    assert doc_res["doc_content"] != ""

