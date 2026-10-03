"""
Seed Data Generator for Default 3D Cadastre Records
Supplies authentic pilot buildings and ISO 19152 legal units with cryptographic 3D ULPINs.
"""

from typing import List, Dict, Any
from backend.ladm.schema import (
    LA_SpatialUnit, LA_LegalSpaceBuildingUnit, LA_Party, LA_Source,
    LA_RRR, RRRType, LegalSpaceType, UnitStatus, BoundingBox3D
)
from backend.ulpin.ulpin_generator import generate_3d_ulpin


def generate_seed_buildings() -> List[LA_SpatialUnit]:
    """Generates standard pilot buildings for the default pilot regions."""
    buildings: List[LA_SpatialUnit] = []

    # -------------------------------------------------------------
    # Building 1: Vanguard Orion Tech Tower (Bengaluru Outer Ring Road - 560103)
    # -------------------------------------------------------------
    b1_id = "BLR-ORR-BLD-01"
    b1_units: List[LA_LegalSpaceBuildingUnit] = []

    # Flat 702 - Residential 3BHK
    u1_ulpin = generate_3d_ulpin("560103", "A", 702)
    b1_units.append(LA_LegalSpaceBuildingUnit(
        unit_id="U-702",
        building_id=b1_id,
        unit_name="Unit 702 (Tower A - 3BHK Luxury)",
        space_type=LegalSpaceType.APARTMENT,
        ulpin=u1_ulpin.ulpin,
        floor_level=7,
        bbox=BoundingBox3D(min_x=-12.5, min_y=4.0, min_z=941.0, max_x=2.5, max_y=18.0, max_z=944.2),
        status=UnitStatus.CLEAR_FREEHOLD,
        parties=[
            LA_Party(
                party_id="P-IND-8841",
                name="Vikramaditya S. Rathore",
                party_type="Natural Person",
                id_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                contact_email="v.rathore@outlook.com",
                role="Sole Freehold Owner"
            )
        ],
        rrrs=[
            LA_RRR(
                rrr_id="RRR-OWN-702",
                rrr_type=RRRType.RIGHT_OWNERSHIP,
                description="Exclusive 3D Freehold Title Deed over Volumetric Interior Space",
                share_ratio="1.0",
                is_active=True,
                valid_from="2024-03-15"
            ),
            LA_RRR(
                rrr_id="RRR-UDS-702",
                rrr_type=RRRType.RIGHT_COMMON_SHARE,
                description="Undivided Common Share of Land & Tower Core Infrastructure (0.03125 fraction)",
                share_ratio="1/32",
                is_active=True,
                valid_from="2024-03-15"
            ),
            LA_RRR(
                rrr_id="RRR-TAX-702",
                rrr_type=RRRType.RESPONSIBILITY_PROPERTY_TAX,
                description="BBMP Municipal 3D Volumetric Property Tax Assessment",
                amount_inr=18450.0,
                is_active=True,
                valid_from="2024-04-01"
            )
        ],
        sources=[
            LA_Source(
                source_id="DOC-DEED-2024-702",
                document_type="Registered Absolute Sale Deed",
                document_number="KRN-BLR-SR-2024/88921",
                issuing_authority="Sub-Registrar Office, Bellandur / Bengaluru Urban",
                registration_date="2024-03-15",
                digital_signature="0x9a8f27b4e13cd781059fba428172c91834eaf651",
                ipfs_hash="QmZ4tDuvesekSs4qM5ZBKpXiZGun7S2CYtEZRB3DYXkjGx",
                verification_status="Verified Authenticated"
            ),
            LA_Source(
                source_id="DOC-RERA-702",
                document_type="Karnataka RERA Sanction Plan Approval",
                document_number="PRM/KA/RERA/1251/310/PR/190822/002819",
                issuing_authority="Karnataka Real Estate Regulatory Authority (K-RERA)",
                registration_date="2022-08-19",
                digital_signature="0x4b7891cf23e80a56214d0234a91bce74981ef402",
                ipfs_hash="QmNnooDuvesekSs4qM5ZBKpXiZGun7S2CYtEZRB3DYXkjGx",
                verification_status="Verified Valid"
            )
        ]
    ))

    # Unit 1201 - Executive Penthouse
    u2_ulpin = generate_3d_ulpin("560103", "A", 1201)
    b1_units.append(LA_LegalSpaceBuildingUnit(
        unit_id="U-1201",
        building_id=b1_id,
        unit_name="Unit 1201 (Tower A - Sky Villa Penthouse)",
        space_type=LegalSpaceType.APARTMENT,
        ulpin=u2_ulpin.ulpin,
        floor_level=12,
        bbox=BoundingBox3D(min_x=-15.0, min_y=-10.0, min_z=957.0, max_x=15.0, max_y=10.0, max_z=961.5),
        status=UnitStatus.MORTGAGED,
        parties=[
            LA_Party(
                party_id="P-IND-9021",
                name="Ananya Mehra & Siddharth Mehra",
                party_type="Natural Person (Joint)",
                id_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
                contact_email="siddharth.mehra@techcap.io",
                role="Joint Freehold Owners"
            ),
            LA_Party(
                party_id="P-BNK-0012",
                name="State Bank of India (Commercial RACPC Koramangala)",
                party_type="Financial Institution",
                id_hash="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
                contact_email="racpc.koramangala@sbi.co.in",
                role="Primary Mortgagee Bank"
            )
        ],
        rrrs=[
            LA_RRR(
                rrr_id="RRR-MORT-1201",
                rrr_type=RRRType.RESTRICTION_MORTGAGE,
                description="Hypothecation Lien against Housing Loan Facilities",
                share_ratio="1.0",
                beneficiary_party="State Bank of India",
                amount_inr=32500000.0,
                is_active=True,
                valid_from="2023-11-10"
            )
        ],
        sources=[
            LA_Source(
                source_id="DOC-MORT-2023-1201",
                document_type="Mortgage Deed / Memorandum of Deposit of Title Deeds",
                document_number="SBI-MODTD-2023/11092",
                issuing_authority="Sub-Registrar Office, Jayanagar",
                registration_date="2023-11-10",
                digital_signature="0x12c8e9b4e13cd781059fba428172c91834eaf651",
                verification_status="Active Bank Lien Recorded"
            )
        ]
    ))

    # Unit P-B214 - Basement Parking Bay
    u3_ulpin = generate_3d_ulpin("560103", "P", 214)
    b1_units.append(LA_LegalSpaceBuildingUnit(
        unit_id="U-P214",
        building_id=b1_id,
        unit_name="Parking Slot B2-14 (Basement 2)",
        space_type=LegalSpaceType.PARKING,
        ulpin=u3_ulpin.ulpin,
        floor_level=-2,
        bbox=BoundingBox3D(min_x=5.0, min_y=2.0, min_z=914.0, max_x=7.8, max_y=7.2, max_z=917.0),
        status=UnitStatus.CLEAR_FREEHOLD,
        parties=[
            LA_Party(
                party_id="P-IND-8841",
                name="Vikramaditya S. Rathore",
                party_type="Natural Person",
                id_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                role="Appurtenant Parking Allottee"
            )
        ],
        rrrs=[
            LA_RRR(
                rrr_id="RRR-PRK-B214",
                rrr_type=RRRType.RIGHT_OWNERSHIP,
                description="Designated Basement Volumetric Parking Bay Appurtenant to Flat 702",
                is_active=True,
                valid_from="2024-03-15"
            )
        ],
        sources=[]
    ))

    # Unit R-Deck - Air Rights & Helipad Sky Envelope
    u4_ulpin = generate_3d_ulpin("560103", "R", 801)
    b1_units.append(LA_LegalSpaceBuildingUnit(
        unit_id="U-R801",
        building_id=b1_id,
        unit_name="Sky Deck Air-Rights Envelope (+15m Vertical Buffer)",
        space_type=LegalSpaceType.AIR_RIGHTS,
        ulpin=u4_ulpin.ulpin,
        floor_level=99,
        bbox=BoundingBox3D(min_x=-15.0, min_y=-10.0, min_z=961.5, max_x=15.0, max_y=10.0, max_z=976.5),
        status=UnitStatus.CLEAR_FREEHOLD,
        parties=[
            LA_Party(
                party_id="P-RWA-001",
                name="Orion Towers Owners Resident Welfare Association",
                party_type="RWA / Society",
                id_hash="11a8b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9011",
                role="Collective Common Amenity Trustee"
            )
        ],
        rrrs=[
            LA_RRR(
                rrr_id="RRR-AIR-801",
                rrr_type=RRRType.RIGHT_AIR_RIGHTS,
                description="Designated Drone Logistics Corridor & Rooftop Solar Microgrid Right",
                share_ratio="1.0",
                is_active=True,
                valid_from="2024-01-01"
            )
        ],
        sources=[]
    ))

    bld1 = LA_SpatialUnit(
        building_id=b1_id,
        building_name="Vanguard Orion Tech Tower",
        pincode="560103",
        total_floors=14,
        basement_floors=2,
        height_m=48.5,
        ground_elevation_m=920.0,
        centroid_lat=12.9352,
        centroid_lng=77.6946,
        footprint_polygon=[
            [-15.0, -10.0], [15.0, -10.0], [15.0, 10.0], [-15.0, 10.0]
        ],
        legal_units=b1_units,
        point_count=28450
    )
    buildings.append(bld1)

    # -------------------------------------------------------------
    # Building 2: Aura Financial Plaza (Mumbai BKC - 400051)
    # -------------------------------------------------------------
    b2_id = "MUM-BKC-BLD-02"
    b2_units: List[LA_LegalSpaceBuildingUnit] = []

    u5_ulpin = generate_3d_ulpin("400051", "B", 101)
    b2_units.append(LA_LegalSpaceBuildingUnit(
        unit_id="U-BKC-101",
        building_id=b2_id,
        unit_name="Commercial Corporate Suite 1401 (Floor 14)",
        space_type=LegalSpaceType.STANDALONE_BUILDING,
        ulpin=u5_ulpin.ulpin,
        floor_level=14,
        bbox=BoundingBox3D(min_x=-20.0, min_y=-15.0, min_z=55.0, max_x=20.0, max_y=15.0, max_z=60.0),
        status=UnitStatus.CLEAR_FREEHOLD,
        parties=[
            LA_Party(
                party_id="P-CORP-4401",
                name="Nexus Capital Global Assets LLP",
                party_type="Corporate Entity",
                id_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                contact_email="legal@nexuscapital.com",
                role="Commercial Freehold Leaseholder"
            )
        ],
        rrrs=[
            LA_RRR(
                rrr_id="RRR-COM-1401",
                rrr_type=RRRType.RIGHT_OWNERSHIP,
                description="Grade-A Commercial Financial District Volumetric Title",
                share_ratio="1.0",
                is_active=True,
                valid_from="2023-06-01"
            )
        ],
        sources=[]
    ))

    bld2 = LA_SpatialUnit(
        building_id=b2_id,
        building_name="Aura Financial Plaza (Bandra-Kurla Complex)",
        pincode="400051",
        total_floors=22,
        basement_floors=3,
        height_m=76.2,
        ground_elevation_m=12.0,
        centroid_lat=19.0657,
        centroid_lng=72.8687,
        footprint_polygon=[
            [-22.0, -16.0], [22.0, -16.0], [22.0, 16.0], [-22.0, 16.0]
        ],
        legal_units=b2_units,
        point_count=42100
    )
    buildings.append(bld2)

    return buildings
