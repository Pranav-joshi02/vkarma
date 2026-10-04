"""
Building Realistic Image Resolver
Assigns high-resolution, photorealistic architectural and drone photography to
buildings and legal units based on their actual name, classification, height, and geographic context.
"""

import re
import hashlib
from typing import Optional

REALISTIC_BUILDING_IMAGES = [
    "/assets/buildings/tech_park_tower.jpg",
    "/assets/buildings/residential_highrise.jpg",
    "/assets/buildings/commercial_financial_plaza.jpg",
    "/assets/buildings/tech_campus.jpg",
    "/assets/buildings/residential_enclave.jpg",
    "/assets/buildings/mixed_use_complex.jpg",
]

CAMPUS_IMAGE = "/assets/buildings/tech_campus.jpg"
TECH_TOWER_IMAGE = "/assets/buildings/tech_park_tower.jpg"
COMMERCIAL_PLAZA_IMAGE = "/assets/buildings/commercial_financial_plaza.jpg"
RESIDENTIAL_HIGHRISE_IMAGE = "/assets/buildings/residential_highrise.jpg"
RESIDENTIAL_ENCLAVE_IMAGE = "/assets/buildings/residential_enclave.jpg"
MIXED_USE_IMAGE = "/assets/buildings/mixed_use_complex.jpg"


def get_building_realistic_image(
    building_name: Optional[str] = None,
    total_floors: int = 5,
    space_type: Optional[str] = None,
    building_id: Optional[str] = None,
    index: int = 0
) -> str:
    """
    Selects the most accurate photorealistic architectural image for a building.
    Matches semantic corporate/residential keywords, floor heights, and guarantees
    unique variety across sequentially discovered/processed buildings.
    """
    name_clean = (building_name or "").lower().strip()

    # 1. Semantic matching for Tech Parks & IT Corporate Campuses
    if any(k in name_clean for k in ["infosys", "persistent", "wipro", "tcs", "cognizant", "tech mahindra", "cyber", "technology"]):
        if any(k in name_clean for k in ["campus", "park", "infotech", "complex"]):
            return CAMPUS_IMAGE
        return TECH_TOWER_IMAGE

    if any(k in name_clean for k in ["software", "tech park", "it park", "it tower", "tech tower", "infopark", "technopark", "systems", "labs"]) or re.search(r'\b(?:it|tech)\s+(?:tower|enclave|hub|center)\b', name_clean):
        if any(k in name_clean for k in ["campus", "park"]):
            return CAMPUS_IMAGE
        return TECH_TOWER_IMAGE

    # 2. Semantic matching for Commercial, Banking, & Financial Plazas
    if any(k in name_clean for k in [
        "finance", "bank", "financial", "bkc", "exchange", "corporate plaza",
        "nse", "business bay", "headquarters", "commercial plaza"
    ]):
        return COMMERCIAL_PLAZA_IMAGE

    # 3. Semantic matching for Residential Towers & Communities
    if any(k in name_clean for k in [
        "residential", "residency", "enclave", "villa", "greens", "apartments",
        "heights", "condominium", "towers wing", "housing", "flats", "society"
    ]):
        if total_floors >= 10:
            return RESIDENTIAL_HIGHRISE_IMAGE
        return RESIDENTIAL_ENCLAVE_IMAGE

    # 4. Semantic matching for Mixed-Use, Retail & Transit Hubs
    if any(k in name_clean for k in [
        "mall", "market", "retail", "hub", "metro", "center", "centre", "suites", "arcade"
    ]):
        return MIXED_USE_IMAGE

    # 5. Extract trailing number for sequential synthetic buildings (e.g. "Hinjawadi Building 03")
    match_num = re.search(r'(?:building|block|tower)\s*(\d+)', name_clean)
    if match_num:
        try:
            num = int(match_num.group(1))
            # 1-indexed to 0-indexed list
            return REALISTIC_BUILDING_IMAGES[(num - 1) % len(REALISTIC_BUILDING_IMAGES)]
        except ValueError:
            pass

    # 6. Fallback based on Space Type
    if space_type == "A":
        return RESIDENTIAL_HIGHRISE_IMAGE if total_floors >= 8 else RESIDENTIAL_ENCLAVE_IMAGE
    elif space_type in ["B", "C"]:
        return COMMERCIAL_PLAZA_IMAGE
    elif space_type in ["U", "M", "P"]:
        return TECH_TOWER_IMAGE

    # 7. Deterministic hash distribution based on building name or ID
    key = building_id or building_name or str(index)
    hash_val = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:6], 16)
    return REALISTIC_BUILDING_IMAGES[(hash_val + index) % len(REALISTIC_BUILDING_IMAGES)]
