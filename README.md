# 3D Cadastral Registry & 3D ULPIN System (ISO 19152 LADM)
### National 3D Land Record Digital Twin & Automated Geospatial Processing Pipeline

An end-to-end, open-source 3D Cadastral Administration and Digital Twin platform built according to the **ISO 19152 (Land Administration Domain Model - LADM)** standard. It converts raw geospatial survey data (LiDAR point clouds, drone photogrammetry, satellite imagery, architectural floor plans) into structured, legally unambiguous 3D land records where every apartment, corridor, parking bay, utility shaft, and air-rights envelope receives its own secure, non-sequential, tamper-checked **3D ULPIN** (`PPPPPP-T-RRRRRRRR-C`).

---

## 🏛️ Core Features

1. **Interactive 2D/3D Geospatial Area Selector**:
   - Leaflet 2D GIS map supporting preset Indian urban pilot zones (Bengaluru Tech Corridor, New Delhi Connaught Place, Mumbai BKC, Hyderabad HITEC City).
   - **Interactive Bounding Box Tool**: Select any custom bounding box across India to generate and process a 3D cadastral digital twin on the fly.
2. **10-Stage Automated AI/ML & Cadastral Pipeline**:
   - **Stage 1**: Multi-Sensor Ingestion (LAS/LAZ point clouds, RERA floor plans).
   - **Stage 2**: Cloth Simulation Filter (CSF) Ground / Non-Ground separation.
   - **Stage 3**: Multi-Scale Geometric Point Classifier (Ground, Vegetation, Building Shell, Infrastructure).
   - **Stage 4**: DBSCAN Multi-Building Instance Clustering.
   - **Stage 5**: 2D Footprint Regularization (ABORE / Alpha-Shape).
   - **Stage 6**: LiDAR + Floor Plan ICP Volumetric Fusion.
   - **Stage 7**: 3D Physical Space Unit Mesh Generation.
   - **Stage 8**: ISO 19152 Legal Space Unit Subdivision (Apartments, Parking, Cores, Utilities, Air-Rights).
   - **Stage 9**: Cryptographic Feistel FPE + Verhoeff Dihedral $D_5$ 3D ULPIN Minting.
   - **Stage 10**: Topological Manifold & 3D Spatial Collision Validation (Jaljolie et al.).
3. **High-Fidelity 3D Cadastral WebGIS Digital Twin (Three.js)**:
   - Real-time 3D orbit, pan, zoom with realistic lighting and shadows.
   - **Exploded Floor-by-Floor View Slider**: Explodes building storeys vertically to inspect internal flats, corridors, and elevator shafts.
   - **Multi-View Modes**: Color by Space Type, Color by Ownership / Legal Status, X-Ray Wireframe Mode, and Classified Point Cloud particle toggle.
4. **Deep Legal Unit & 3D ULPIN Inspector**:
   - Click any building or flat to view its full LADM ISO 19152 profile:
     - 3D ULPIN (`PPPPPP-T-RRRRRRRR-C`) with 1-click copy & live Verhoeff validity check.
     - Dimensions ($m^2$ carpet area, $m^3$ 3D volume, 3D coordinate extents).
     - Verified Party (Owner name, Aadhaar/PAN hash).
     - RRR Breakdown (Freehold ownership, SBI/HDFC Bank hypothecation mortgage lien, Undivided Common Share).
     - Linked Source Legal Documents (Sale Deed, RERA Sanction Plan, Sub-Registrar stamp).
   - **3D Bhu-Aadhaar Digital Certificate Generator**: Official printable land title certificate with cryptographic QR code.
5. **Topological Dispute & Encroachment Scanner**:
   - 3D spatial collision detector identifying illegal common area encroachments or double-allocated parking slots in glowing red.
6. **Address-as-a-Service (UPI for 3D Delivery)**:
   - REST API resolving any 3D ULPIN into precision 3D navigation coordinates (Latitude, Longitude, Altitude AGL, Floor Level, Wing Quadrant, Drone Landing Altitude).

---

## 🔒 3D ULPIN Architecture

Format: `PPPPPP-T-RRRRRRRR-C` (17 characters)

- `PPPPPP`: 6-digit postal pincode (geographic partition key).
- `T`: 1-character space type code:
  - `A` = Apartment / Residential Unit
  - `C` = Common Corridor (Right of Way)
  - `S` = Staircase & Fire Evacuation Shaft
  - `M` = Common Amenities / Sky Deck / Terrace
  - `P` = Parking Bay (Basement / Surface)
  - `U` = Utility Shaft / Subsurface Infrastructure
  - `B` = Standalone Building Envelope
  - `R` = Air-Rights Envelope (+15m)
- `RRRRRRRR`: 8-character Format-Preserving Encryption (FPE) token generated using an 8-round Balanced Feistel Network with HMAC-SHA256 round function over base-34 space. Guarantees non-sequential, pseudorandom, non-enumerable IDs.
- `C`: 1-digit Verhoeff Check Digit (Dihedral group $D_5$ permutation matrix, identical to Aadhaar / UIDAI standard). Catches 100% of single-digit entry errors and adjacent transposition errors.

---

## 🚀 Quick Start

### 1. Run the Server
```bash
python run_server.py
```

Open your browser at:
`http://localhost:8000`

### 2. Run Automated Test Suite
```bash
pytest tests/
```

---

## 📡 API Endpoints

- `GET /api/regions`: List available pilot survey regions.
- `POST /api/pipeline/run`: Run 10-stage pipeline on selected region or custom bounding box.
- `GET /api/buildings`: List all registered 3D spatial building shells.
- `GET /api/buildings/{building_id}`: Fetch complete 3D building model and legal units.
- `GET /api/ulpin/lookup/{ulpin}`: Lookup full ISO 19152 ownership record by 3D ULPIN.
- `POST /api/ulpin/verify`: Cryptographic verification of 3D ULPIN.
- `POST /api/disputes/scan`: Run 3D topological collision and encroachment detection.
- `GET /api/delivery/resolve/{ulpin}`: UPI-for-addresses 3D logistics resolver.
- `GET /api/pointcloud/sample`: Stream classified LiDAR points for WebGL.
