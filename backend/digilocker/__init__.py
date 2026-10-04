"""
VKARMA DigiLocker Integration Module
Compliant with Ministry of Electronics & IT (MeitY) and DILRMP National Land Records.
Provides:
- DigiLocker Issuer Gateway APIs (Pull URI & Pull Doc)
- Citizen "Save to DigiLocker" / Push Certificate Service
- Standardized ISO 19152 3D Bhu-Aadhaar XML Certificate Generation
- Cryptographic SHA-256 Digital Signing & Verhoeff Validation
"""

from .issuer_service import digilocker_service
from .models import (
    DigiLockerPushRequest,
    DigiLockerPushResponse,
    DigiLockerPullUriRequest,
    DigiLockerPullUriResponse,
    DigiLockerPullDocRequest,
    DigiLockerPullDocResponse,
    DigiLockerDocStatus
)

__all__ = [
    "digilocker_service",
    "DigiLockerPushRequest",
    "DigiLockerPushResponse",
    "DigiLockerPullUriRequest",
    "DigiLockerPullUriResponse",
    "DigiLockerPullDocRequest",
    "DigiLockerPullDocResponse",
    "DigiLockerDocStatus"
]
