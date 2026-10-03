-- ============================================================
-- 3D Cadastral Digital Registry & 3D ULPIN System
-- ISO 19152 (Land Administration Domain Model - LADM) Schema
-- Supabase / PostgreSQL Initial Migration
-- ============================================================

-- 1. Pilot Survey Regions Table
CREATE TABLE IF NOT EXISTS cadastral_regions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    state VARCHAR(100) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    zoom INTEGER DEFAULT 17,
    description TEXT,
    buildings_count INTEGER DEFAULT 0,
    features JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Physical 3D Building Shells (LA_SpatialUnit)
CREATE TABLE IF NOT EXISTS cadastral_buildings (
    building_id VARCHAR(64) PRIMARY KEY,
    building_name VARCHAR(255) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    total_floors INTEGER NOT NULL,
    basement_floors INTEGER DEFAULT 0,
    height_m DOUBLE PRECISION NOT NULL,
    ground_elevation_m DOUBLE PRECISION NOT NULL,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lng DOUBLE PRECISION NOT NULL,
    footprint_polygon JSONB NOT NULL DEFAULT '[]'::jsonb,
    point_count INTEGER DEFAULT 0,
    raw_las_filename VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Volumetric 3D Legal Space Units (LA_LegalSpaceBuildingUnit)
CREATE TABLE IF NOT EXISTS cadastral_units (
    unit_id VARCHAR(64) PRIMARY KEY,
    building_id VARCHAR(64) NOT NULL REFERENCES cadastral_buildings(building_id) ON DELETE CASCADE,
    unit_name VARCHAR(255) NOT NULL,
    space_type VARCHAR(10) NOT NULL,
    ulpin VARCHAR(32) UNIQUE NOT NULL,
    floor_level INTEGER NOT NULL,
    carpet_area_sqm DOUBLE PRECISION NOT NULL,
    volume_m3 DOUBLE PRECISION NOT NULL,
    status VARCHAR(64) NOT NULL,
    min_x DOUBLE PRECISION NOT NULL,
    max_x DOUBLE PRECISION NOT NULL,
    min_y DOUBLE PRECISION NOT NULL,
    max_y DOUBLE PRECISION NOT NULL,
    min_z DOUBLE PRECISION NOT NULL,
    max_z DOUBLE PRECISION NOT NULL,
    mesh_geometry JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Stakeholder Parties (LA_Party - Citizen, Bank, RWA, State)
CREATE TABLE IF NOT EXISTS cadastral_parties (
    party_id VARCHAR(64) PRIMARY KEY,
    unit_id VARCHAR(64) NOT NULL REFERENCES cadastral_units(unit_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    party_type VARCHAR(64) NOT NULL,
    id_hash VARCHAR(128) NOT NULL,
    contact_email VARCHAR(255),
    role VARCHAR(64) DEFAULT 'Owner',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Rights, Restrictions, and Responsibilities (LA_RRR)
CREATE TABLE IF NOT EXISTS cadastral_rrrs (
    rrr_id VARCHAR(64) PRIMARY KEY,
    unit_id VARCHAR(64) NOT NULL REFERENCES cadastral_units(unit_id) ON DELETE CASCADE,
    rrr_type VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    share_ratio VARCHAR(32) DEFAULT '1.0',
    beneficiary_party VARCHAR(255),
    amount_inr DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT TRUE,
    valid_from VARCHAR(32) DEFAULT '2024-01-01',
    valid_to VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Legal Deeds and Certifications (LA_Source)
CREATE TABLE IF NOT EXISTS cadastral_sources (
    source_id VARCHAR(64) PRIMARY KEY,
    unit_id VARCHAR(64) NOT NULL REFERENCES cadastral_units(unit_id) ON DELETE CASCADE,
    document_type VARCHAR(128) NOT NULL,
    document_number VARCHAR(128) NOT NULL,
    issuing_authority VARCHAR(255) NOT NULL,
    registration_date VARCHAR(32) NOT NULL,
    digital_signature VARCHAR(255) NOT NULL,
    ipfs_hash VARCHAR(128),
    verification_status VARCHAR(64) DEFAULT 'Verified Valid',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Topological Encroachments & 3D Disputes
CREATE TABLE IF NOT EXISTS cadastral_disputes (
    id SERIAL PRIMARY KEY,
    building_id VARCHAR(64) NOT NULL REFERENCES cadastral_buildings(building_id) ON DELETE CASCADE,
    conflict_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    unit_a_id VARCHAR(64) REFERENCES cadastral_units(unit_id) ON DELETE SET NULL,
    unit_a_name VARCHAR(255),
    unit_a_ulpin VARCHAR(32),
    unit_b_id VARCHAR(64) REFERENCES cadastral_units(unit_id) ON DELETE SET NULL,
    unit_b_name VARCHAR(255),
    unit_b_ulpin VARCHAR(32),
    overlap_volume_m3 DOUBLE PRECISION,
    message TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Pipeline Execution Telemetry Logs
CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL,
    area_name VARCHAR(255),
    pincode VARCHAR(10),
    points_processed INTEGER,
    buildings_detected INTEGER,
    units_minted INTEGER,
    disputes_flagged INTEGER,
    processing_time_s DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'SUCCESS',
    raw_summary JSONB DEFAULT '{}'::jsonb,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- --- INDEXES FOR O(1) LOOKUPS & SPATIAL QUERIES ---
CREATE INDEX IF NOT EXISTS idx_cadastral_units_ulpin ON cadastral_units(ulpin);
CREATE INDEX IF NOT EXISTS idx_cadastral_units_building_id ON cadastral_units(building_id);
CREATE INDEX IF NOT EXISTS idx_cadastral_units_floor ON cadastral_units(floor_level);
CREATE INDEX IF NOT EXISTS idx_cadastral_units_space_type ON cadastral_units(space_type);
CREATE INDEX IF NOT EXISTS idx_cadastral_buildings_pincode ON cadastral_buildings(pincode);
CREATE INDEX IF NOT EXISTS idx_cadastral_parties_unit ON cadastral_parties(unit_id);
CREATE INDEX IF NOT EXISTS idx_cadastral_rrrs_unit ON cadastral_rrrs(unit_id);
CREATE INDEX IF NOT EXISTS idx_cadastral_sources_unit ON cadastral_sources(unit_id);
CREATE INDEX IF NOT EXISTS idx_cadastral_disputes_building ON cadastral_disputes(building_id);

-- --- SEED DEFAULT PILOT REGIONS ---
INSERT INTO cadastral_regions (id, name, pincode, state, lat, lng, zoom, description, buildings_count, features)
VALUES 
('blr_orr_560103', 'Bengaluru Tech Corridor (Outer Ring Road)', '560103', 'Karnataka', 12.9352, 77.6946, 17, 'High-density mixed-use IT towers, residential high-rises, underground basement parking, and upcoming elevated metro line.', 3, '["Multi-Tower High-Rise", "2-Level Basement Parking", "Air-Rights Envelope", "Dispute Case 701"]'::jsonb),
('del_cp_110001', 'New Delhi Connaught Place / Barakhamba', '110001', 'Delhi NCR', 28.6315, 77.2167, 17, 'Central commercial business district with multi-level underground metro interchange, office towers, and heritage height zoning.', 4, '["Underground Metro Hub", "Commercial Condominiums", "Heritage Zoning Restriction", "Subsurface Utility Vaults"]'::jsonb),
('mum_bkc_400051', 'Mumbai BKC (Bandra-Kurla Complex)', '400051', 'Maharashtra', 19.0657, 72.8687, 17, 'India''s premier financial hub with luxury commercial skyscrapers, rooftop helipads, and high-security basement bullion vaults.', 3, '["Skyscraper 3D Cadastre", "3-Level Automated Parking", "Transferable Development Rights (TDR)", "Rooftop Air Rights"]'::jsonb),
('hyd_hitec_500081', 'Hyderabad HITEC City (Knowledge Park)', '500081', 'Telangana', 17.4435, 78.3772, 17, 'Special Economic Zone (SEZ) with multi-storey cloud tech campuses, shared sky-walks, and common solar microgrids.', 3, '["SEZ Commercial Rights", "Inter-Building Skywalks", "Solar Common Amenity Share", "Multi-Owner Freeholds"]'::jsonb)
ON CONFLICT (id) DO NOTHING;
