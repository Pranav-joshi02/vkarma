"""
ISO 19152 (Land Administration Domain Model - LADM) Schema
Defines the official standard data structures for 3D Cadastral records:
- LA_Party: Owners, Financial Institutions, Government Authorities
- LA_Source: Legal Deeds, RERA Sanction Plans, Survey Documents
- LA_RRR: Rights, Restrictions, and Responsibilities
- LA_SpatialUnit: Physical 3D building shells and structural elements
- LA_LegalSpaceBuildingUnit: Volumetric legal parcels (Flats, Parking, Air-Rights, etc.)
- LA_BAUnit: Basic Administrative Unit tying spatial units to legal rights
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
import uuid
import datetime


class RRRType(str, Enum):
    RIGHT_OWNERSHIP = "Exclusive Freehold Ownership"
    RIGHT_COMMON_SHARE = "Undivided Common Share (UDS)"
    RIGHT_AIR_RIGHTS = "Vertical Air Space Development Right"
    RIGHT_WAY_EASEMENT = "Right of Way / Corridor Access Easement"
    RESTRICTION_MORTGAGE = "Bank Mortgage / Financial Hypothecation Lien"
    RESTRICTION_GOVT_RESERVATION = "Municipal / Infrastructure Reservation"
    RESTRICTION_HERITAGE = "Heritage Conservation Height Restriction"
    RESPONSIBILITY_MAINTENANCE = "Condominium Maintenance Levy"
    RESPONSIBILITY_PROPERTY_TAX = "Municipal 3D Property Tax Assessment"


class LegalSpaceType(str, Enum):
    APARTMENT = "A"
    CORRIDOR = "C"
    STAIRCASE = "S"
    COMMON_AREA = "M"
    PARKING = "P"
    UTILITY_SHAFT = "U"
    STANDALONE_BUILDING = "B"
    AIR_RIGHTS = "R"


class UnitStatus(str, Enum):
    CLEAR_FREEHOLD = "Clear Freehold"
    MORTGAGED = "Bank Mortgaged"
    DISPUTED = "Under Legal Dispute / Encroachment"
    MUNICIPAL_COMMON = "Public / Common Utility"
    PENDING_REGISTRATION = "Pending RERA Approval"


@dataclass
class LA_Party:
    """ISO 19152 Party (Citizen, Developer, Bank, State)"""
    party_id: str
    name: str
    party_type: str  # "Natural Person", "Financial Institution", "Government Agency", "RWA"
    id_hash: str     # SHA-256 hash of Aadhaar/PAN/CIN for privacy-preserving verification
    contact_email: Optional[str] = None
    role: str = "Owner"


@dataclass
class LA_Source:
    """ISO 19152 Source Legal Document"""
    source_id: str
    document_type: str  # "Registered Sale Deed", "RERA Sanction Plan", "Bank Lien Notice", "Sub-Registrar Index-II"
    document_number: str
    issuing_authority: str
    registration_date: str
    digital_signature: str
    ipfs_hash: Optional[str] = None
    verification_status: str = "Verified Valid"


@dataclass
class LA_RRR:
    """ISO 19152 Rights, Restrictions, and Responsibilities"""
    rrr_id: str
    rrr_type: RRRType
    description: str
    share_ratio: Optional[str] = "1.0"  # e.g., "1/32" for undivided common share
    beneficiary_party: Optional[str] = None  # e.g. "State Bank of India"
    amount_inr: Optional[float] = None       # e.g. Mortgage loan amount 85,00,000 INR
    is_active: bool = True
    valid_from: str = "2024-01-01"
    valid_to: Optional[str] = None


@dataclass
class BoundingBox3D:
    """3D Extents in Local Survey / EPSG Coordinates"""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @property
    def volume_m3(self) -> float:
        return round((self.max_x - self.min_x) * (self.max_y - self.min_y) * (self.max_z - self.min_z), 2)

    @property
    def carpet_area_sqm(self) -> float:
        return round((self.max_x - self.min_x) * (self.max_y - self.min_y), 2)


@dataclass
class LA_LegalSpaceBuildingUnit:
    """
    ISO 19152 3D Legal Space Unit
    Represents an unambiguous volumetric parcel of ownership/rights.
    """
    unit_id: str
    building_id: str
    unit_name: str          # e.g., "Flat 702", "Parking Slot B2-14", "Corridor West"
    space_type: LegalSpaceType
    ulpin: str              # Format: PPPPPP-T-RRRRRRRR-C
    floor_level: int        # -2 (Basement 2), 0 (Ground), 7 (7th Floor), 99 (Roof/Air-Rights)
    bbox: BoundingBox3D
    status: UnitStatus
    parties: List[LA_Party] = field(default_factory=list)
    rrrs: List[LA_RRR] = field(default_factory=list)
    sources: List[LA_Source] = field(default_factory=list)
    mesh_geometry: Optional[Dict[str, Any]] = None  # 3D vertices/faces for WebGL visualization
    dispute_details: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None  # Realistic architectural/drone photographic scan
    polygon_coordinates: Optional[List[List[float]]] = None  # Exact real 2D contour polygon [[lat, lng], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "building_id": self.building_id,
            "unit_name": self.unit_name,
            "space_type": self.space_type.value,
            "ulpin": self.ulpin,
            "floor_level": self.floor_level,
            "carpet_area_sqm": self.bbox.carpet_area_sqm,
            "volume_m3": self.bbox.volume_m3,
            "status": self.status.value,
            "bbox": asdict(self.bbox),
            "parties": [asdict(p) for p in self.parties],
            "rrrs": [asdict(r) for r in self.rrrs],
            "sources": [asdict(s) for s in self.sources],
            "mesh_geometry": self.mesh_geometry,
            "dispute_details": self.dispute_details,
            "image_url": self.image_url,
            "polygon_coordinates": self.polygon_coordinates
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LA_LegalSpaceBuildingUnit":
        bbox_raw = d.get("bbox", {})
        bbox = BoundingBox3D(
            min_x=float(bbox_raw.get("min_x", 0.0)),
            min_y=float(bbox_raw.get("min_y", 0.0)),
            min_z=float(bbox_raw.get("min_z", 0.0)),
            max_x=float(bbox_raw.get("max_x", 0.0)),
            max_y=float(bbox_raw.get("max_y", 0.0)),
            max_z=float(bbox_raw.get("max_z", 0.0))
        )
        parties = [
            LA_Party(
                party_id=p["party_id"],
                name=p["name"],
                party_type=p.get("party_type", "Natural Person"),
                id_hash=p.get("id_hash", ""),
                contact_email=p.get("contact_email"),
                role=p.get("role", "Owner")
            ) for p in d.get("parties", [])
        ]
        rrrs = []
        for r in d.get("rrrs", []):
            try:
                rt = RRRType(r["rrr_type"]) if isinstance(r.get("rrr_type"), str) else RRRType.RIGHT_OWNERSHIP
            except ValueError:
                rt = RRRType.RIGHT_OWNERSHIP
            rrrs.append(LA_RRR(
                rrr_id=r["rrr_id"],
                rrr_type=rt,
                description=r.get("description", ""),
                share_ratio=r.get("share_ratio", "1.0"),
                beneficiary_party=r.get("beneficiary_party"),
                amount_inr=r.get("amount_inr"),
                is_active=r.get("is_active", True),
                valid_from=r.get("valid_from", "2024-01-01"),
                valid_to=r.get("valid_to")
            ))
        sources = [
            LA_Source(
                source_id=s["source_id"],
                document_type=s.get("document_type", "Registered Deed"),
                document_number=s.get("document_number", "DOC-001"),
                issuing_authority=s.get("issuing_authority", "Sub-Registrar"),
                registration_date=s.get("registration_date", "2024-01-01"),
                digital_signature=s.get("digital_signature", ""),
                ipfs_hash=s.get("ipfs_hash"),
                verification_status=s.get("verification_status", "Verified Valid")
            ) for s in d.get("sources", [])
        ]
        try:
            space_type = LegalSpaceType(d.get("space_type", "A"))
        except ValueError:
            space_type = LegalSpaceType.APARTMENT

        try:
            status = UnitStatus(d.get("status", "Clear Freehold"))
        except ValueError:
            status = UnitStatus.CLEAR_FREEHOLD

        return cls(
            unit_id=d["unit_id"],
            building_id=d["building_id"],
            unit_name=d["unit_name"],
            space_type=space_type,
            ulpin=d["ulpin"],
            floor_level=int(d.get("floor_level", 0)),
            bbox=bbox,
            status=status,
            parties=parties,
            rrrs=rrrs,
            sources=sources,
            mesh_geometry=d.get("mesh_geometry"),
            dispute_details=d.get("dispute_details"),
            image_url=d.get("image_url"),
            polygon_coordinates=d.get("polygon_coordinates")
        )


@dataclass
class LA_SpatialUnit:
    """Physical Building Shell (Geometry only, no ownership)"""
    building_id: str
    building_name: str
    pincode: str
    total_floors: int
    basement_floors: int
    height_m: float
    ground_elevation_m: float
    centroid_lat: float
    centroid_lng: float
    footprint_polygon: List[List[float]]  # 2D regularized polygon vertices [x, y]
    legal_units: List[LA_LegalSpaceBuildingUnit] = field(default_factory=list)
    point_count: int = 0
    raw_las_filename: Optional[str] = None
    image_url: Optional[str] = None  # Realistic photographic scan of the building

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "building_name": self.building_name,
            "pincode": self.pincode,
            "total_floors": self.total_floors,
            "basement_floors": self.basement_floors,
            "height_m": round(self.height_m, 2),
            "ground_elevation_m": round(self.ground_elevation_m, 2),
            "centroid_lat": self.centroid_lat,
            "centroid_lng": self.centroid_lng,
            "footprint_polygon": self.footprint_polygon,
            "legal_unit_count": len(self.legal_units),
            "legal_units": [u.to_dict() for u in self.legal_units],
            "point_count": self.point_count,
            "raw_las_filename": self.raw_las_filename,
            "image_url": self.image_url
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LA_SpatialUnit":
        units = [LA_LegalSpaceBuildingUnit.from_dict(u) for u in d.get("legal_units", [])]
        return cls(
            building_id=d["building_id"],
            building_name=d["building_name"],
            pincode=d.get("pincode", "560103"),
            total_floors=int(d.get("total_floors", 5)),
            basement_floors=int(d.get("basement_floors", 1)),
            height_m=float(d.get("height_m", 15.0)),
            ground_elevation_m=float(d.get("ground_elevation_m", 920.0)),
            centroid_lat=float(d.get("centroid_lat", 12.9352)),
            centroid_lng=float(d.get("centroid_lng", 77.6946)),
            footprint_polygon=d.get("footprint_polygon", []),
            legal_units=units,
            point_count=int(d.get("point_count", 0)),
            raw_las_filename=d.get("raw_las_filename"),
            image_url=d.get("image_url")
        )
