"""
Unit & Integration Tests for Brevo Transactional Email Service
"""

import pytest
from backend.email_service import brevo_email_service
from fastapi.testclient import TestClient
from backend.app import app


def test_email_validation():
    assert brevo_email_service.is_valid_email("citizen@example.com") is True
    assert brevo_email_service.is_valid_email("test.user+tag@domain.co.in") is True
    assert brevo_email_service.is_valid_email("invalid-email") is False
    assert brevo_email_service.is_valid_email("") is False


def test_send_certificate_email_simulation(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "")
    test_ulpin = "560103-A-60YLMDPD-2"
    res = brevo_email_service.send_certificate_email(
        to_email="pranav@example.com",
        to_name="Pranav Joshi",
        ulpin=test_ulpin
    )
    assert res["success"] is True
    assert res["status"] == "SIMULATED"
    assert res["recipient"] == "pranav@example.com"


def test_send_passport_email_simulation(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "")
    test_ulpin = "560103-A-60YLMDPD-2"
    res = brevo_email_service.send_passport_email(
        to_email="pranav@example.com",
        to_name="Pranav Joshi",
        ulpin=test_ulpin
    )
    assert res["success"] is True
    assert res["status"] == "SIMULATED"
    assert res["recipient"] == "pranav@example.com"


def test_fastapi_email_endpoints(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "")
    client = TestClient(app)

    # 1. Config
    resp = client.get("/api/email/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "sender_email" in cfg
    assert "is_configured" in cfg

    # 2. Send Certificate
    payload = {
        "recipient_email": "test@vkarma.in",
        "recipient_name": "Test Citizen",
        "ulpin": "560103-A-60YLMDPD-2"
    }
    resp = client.post("/api/email/send-certificate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # 3. Send Passport
    resp = client.post("/api/email/send-passport", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # 4. Invalid Email Validation
    bad_payload = {
        "recipient_email": "not-an-email",
        "recipient_name": "Test Citizen",
        "ulpin": "560103-A-60YLMDPD-2"
    }
    resp = client.post("/api/email/send-certificate", json=bad_payload)
    assert resp.status_code == 400


def test_sender_and_receiver_identical_payload(monkeypatch):
    captured_payload = {}

    class MockResponse:
        status_code = 201
        def json(self):
            return {"messageId": "mock-identical-id"}

    def mock_post(url, json=None, headers=None):
        nonlocal captured_payload
        captured_payload = json
        return MockResponse()

    monkeypatch.setenv("BREVO_API_KEY", "test-live-key")
    monkeypatch.setattr("httpx.Client.post", lambda self, url, json=None, headers=None: mock_post(url, json=json, headers=headers))

    res = brevo_email_service.send_certificate_email(
        to_email="24070579@ycce.in",
        to_name="Citizen Pranav",
        ulpin="560103-A-60YLMDPD-2"
    )
    assert res["success"] is True
    assert captured_payload["sender"]["email"] == "24070579@ycce.in"
    assert captured_payload["to"][0]["email"] == "24070579@ycce.in"
    assert captured_payload["sender"]["email"] == captured_payload["to"][0]["email"]
