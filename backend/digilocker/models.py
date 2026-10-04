"""
DigiLocker Data Models conforming to MeitY (Digital India) Document Exchange Specification.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DigiLockerPushRequest(BaseModel):
    ulpin: str = Field(..., description="Unique 3D Land Parcel Identification Number (e.g. 560103-A-60YLMDPD-2)")
    citizen_aadhaar_hash: Optional[str] = Field(None, description="Citizen Aadhaar / KYC identification hash")
    citizen_name: Optional[str] = Field(None, description="Registered legal owner name")


class DigiLockerPushResponse(BaseModel):
    success: bool
    status: str
    digilocker_uri: str
    doc_id: str
    timestamp: str
    issuer_id: str
    issuer_name: str
    document_title: str
    owner_name: str
    aadhaar_hash: str
    sha256_hash: str
    verhoeff_checksum: str
    is_sandbox: bool
    verification_url: str
    message: str


class DigiLockerPullUriRequest(BaseModel):
    org_id: Optional[str] = Field("in.gov.dilrmp", description="DigiLocker Registered Issuer Org ID")
    doc_type: Optional[str] = Field("BHUCR", description="Document Type Code (BHUCR = 3D Bhu-Aadhaar Certificate)")
    ulpin: Optional[str] = Field(None, description="3D ULPIN parameter from DigiLocker citizen query")
    aadhaar_hash: Optional[str] = Field(None, description="Citizen Aadhaar / KYC token")
    pincode: Optional[str] = Field(None, description="Property pincode partition")
    name: Optional[str] = Field(None, description="Citizen name")


class DigiLockerPullUriResponse(BaseModel):
    response_status: int  # 1 = Success, 0 = Failed
    status_code: str      # "SUCCESS", "NOT_FOUND", "INVALID_PARAM"
    doc_details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class DigiLockerPullDocRequest(BaseModel):
    uri: str = Field(..., description="DigiLocker Canonical Document URI (e.g. in.gov.dilrmp-BHUCR-560103A60YLMDPD2)")
    format: Optional[str] = Field("xml", description="Requested document format: 'xml' or 'json' or 'pdf'")


class DigiLockerPullDocResponse(BaseModel):
    response_status: int
    uri: str
    doc_type: str
    doc_content: str  # Base64 encoded XML/PDF string
    format: str
    sha256_digest: str
    error_message: Optional[str] = None


class DigiLockerDocStatus(BaseModel):
    is_stored: bool
    ulpin: str
    issued_at: Optional[str] = None
    digilocker_uri: Optional[str] = None
    doc_id: Optional[str] = None
    sha256_hash: Optional[str] = None
    owner_name: Optional[str] = None
    aadhaar_hash: Optional[str] = None
    status: Optional[str] = None
