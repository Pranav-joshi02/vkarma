# 🏛️ vKarma: 3D Cadastral Digital Registry & 3D ULPIN Platform
### National 3D Land Record Digital Twin & Automated Geospatial Processing Pipeline
#### Compliant with ISO 19152 Land Administration Domain Model (LADM) & Government of India DILRMP / Bhu-Aadhaar

[![Live Production](https://img.shields.io/badge/Live%20Demo-vkarma.onrender.com-00C7B7?style=for-the-badge&logo=render&logoColor=white)](https://vkarma.onrender.com)
[![Standard](https://img.shields.io/badge/Standard-ISO%2019152%20LADM-0052CC.svg)](https://www.iso.org/standard/51206.html)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.142-009688.svg)](https://fastapi.tiangolo.com/)
[![CesiumJS](https://img.shields.io/badge/3D%20Engine-CesiumJS%20WebGL-blue.svg)](https://cesium.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20PostGIS%20%2F%20Supabase-3ECF8E.svg)](https://supabase.com/)
[![Google Wallet](https://img.shields.io/badge/Google%20Wallet-Generic%20Passes%20API-4285F4.svg)](https://developers.google.com/wallet)
[![DigiLocker](https://img.shields.io/badge/DigiLocker-MeitY%20Document%20Gateway-FF9933.svg)](https://digitallocker.gov.in)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌐 Live Production Deployment

vKarma is deployed and running live on Render:

| Portal | URL | Description |
| :--- | :--- | :--- |
| **Official Sovereign Portal** | [https://vkarma.onrender.com](https://vkarma.onrender.com) | Sovereign landing portal with pilot zone launcher |
| **3D WebGIS Console** | [https://vkarma.onrender.com/console](https://vkarma.onrender.com/console) | Interactive 3D Cadastral Digital Twin, Dispute Scanner & Pipeline |
| **3D ULPIN Passport Portal** | [https://vkarma.onrender.com/ulpin](https://vkarma.onrender.com/ulpin) | Citizen Bhu-Aadhaar verification, deed download & Google Wallet pass |
| **System Architecture Guide** | [https://vkarma.onrender.com/about](https://vkarma.onrender.com/about) | In-depth ISO 19152, pipeline, and security specifications |
| **Interactive OpenAPI Docs** | [https://vkarma.onrender.com/docs](https://vkarma.onrender.com/docs) | Swagger UI for exploring and testing all REST APIs |
| **ReDoc Documentation** | [https://vkarma.onrender.com/redoc](https://vkarma.onrender.com/redoc) | Clean, responsive API documentation |
| **Uptime Health Check** | [https://vkarma.onrender.com/health](https://vkarma.onrender.com/health) | Uptime and service status monitor (returns HTTP 200 OK) |

---

## 📖 Executive Summary & Core Mission

### The Critical Limitation of 2D Cadastres
Traditional land registries operate on **two-dimensional (2D) parcel boundaries**. In modern high-density vertical cities, residential towers, commercial complexes, subterranean transit corridors, underground utility conduits, and elevated air rights all occupy the exact same horizontal footprint. A conventional 2D cadastre cannot disambiguate:
- **Vertical Ownership**: Who owns apartment 1402 on the 14th floor versus apartment 202 on the 2nd floor directly beneath it.
- **Common Property Boundaries**: Where private ownership ends and undivided common property (corridors, elevator shafts, structural columns, fire escapes) begins.
- **Topological Disputes**: Encroachments into shared amenities, illegal balcony extensions, or overlapping deed claims between adjacent units.
- **Subterranean & Air Rights**: Underground metro tunnels, high-voltage utility vaults, basements, and +15m overhead air-rights buffers.

### The vKarma Solution
**vKarma** delivers a sovereign **3D Cadastral Digital Twin & Land Administration System** aligned with the international **ISO 19152 Land Administration Domain Model (LADM)** and India's **Digital India Land Records Modernization Programme (DILRMP) / Bhu-Aadhaar** initiative.

The system ingests raw spatial data (aerial LiDAR point clouds, satellite building footprints from Overture Maps / OSM, and architectural floor plans), runs them through an automated **10-stage AI/ML pipeline**, extrudes **real polygonal building contours**, mints cryptographically verified **3D ULPIN identifiers**, and issues official land titles via **DigiLocker XML** and **Google Wallet Mobile Passes**.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph DataSources["1. Multi-Sensor Spatial Ingestion"]
        LIDAR["LiDAR Point Clouds (.las / .laz)"]
        OVERTURE["Overture Maps & OpenStreetMap Polygons"]
        RERA["RERA Architectural Floor Plans"]
        DEM["Digital Elevation Models (OpenTopography / USGS 3DEP)"]
    end

    subgraph Pipeline["2. 10-Stage Geospatial Processing Pipeline"]
        S1["Stage 1: Multi-Sensor Ingestion & Streaming"]
        S2["Stage 2: Cloth Simulation Filter (CSF Ground Extraction)"]
        S3["Stage 3: Multi-Scale Covariance Point Classifier"]
        S4["Stage 4: DBSCAN Building Instance Segmentation"]
        S5["Stage 5: Real Footprint Contour Extrusion (Shapely)"]
        S6["Stage 6: Floor Plan & Elevation Volumetric Fusion"]
        S7["Stage 7: Watertight 3D B-Rep Mesh Generation"]
        S8["Stage 8: ISO 19152 Legal Space Subdivision"]
        S9["Stage 9: Feistel FPE + Verhoeff Dihedral 3D ULPIN Minting"]
        S10["Stage 10: Topological Conflict & Encroachment Scanner"]
        
        S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8 --> S9 --> S10
    end

    subgraph Persistence["3. Storage & Distributed Tasks"]
        POSTGRES["PostgreSQL + PostGIS (Supabase Cloud)"]
        REDIS["Redis Message Broker (Upstash / Local)"]
        WORKER["Celery Worker / Resilient In-Memory ThreadPool"]
    end

    subgraph ServiceLayer["4. API & Application Gateways"]
        FASTAPI["FastAPI REST & Static WebGIS Server"]
        DIGILOCKER["DigiLocker Gateway (MeitY / DoLR XML Title Issuer)"]
        GWALLET["Google Wallet Generic Passes API (RS256 JWT)"]
        BREVO["Brevo Transactional Email Gateway"]
        DELIVERY["Address-as-a-Service (3D Drone & Delivery Coordinates)"]
        DISPUTE["Topological Dispute & Encroachment Scanner"]
    end

    subgraph Presentation["5. 3D WebGIS Presentation Layer"]
        CESIUM["CesiumJS 3D WebGL Engine (Terrain Topo Model)"]
        LEAFLET["Leaflet 2D GIS Interactive Bounding Box Selector"]
        EXPLODED["Exploded Floor-by-Floor Volumetric Inspector"]
        CERT["Printable 3D Bhu-Aadhaar Certificate Generator"]
        WALLET_MODAL["Google Wallet 3D Land Pass Dialog"]
    end

    DataSources --> S1
    S10 --> POSTGRES
    FASTAPI <--> POSTGRES
    FASTAPI <--> WORKER
    WORKER <--> REDIS
    FASTAPI --> CESIUM
    FASTAPI --> DIGILOCKER
    FASTAPI --> GWALLET
    FASTAPI --> BREVO
    FASTAPI --> DELIVERY
    FASTAPI --> DISPUTE
    CESIUM <--> LEAFLET
    CESIUM <--> EXPLODED
    CESIUM --> CERT
    CESIUM --> WALLET_MODAL
```

---

## 🔬 The 10-Stage Geospatial AI/ML & Cadastral Pipeline

Raw geospatial surveys are processed through a deterministic, high-throughput 10-stage pipeline:

| Stage | Name | Technical Implementation | Purpose & Output |
|---|---|---|---|
| **1** | **Multi-Sensor Ingestion** | `laspy` + `lazrs` streaming parser | Ingests dense point clouds (LAZ 1.4), geospatial metadata, and coordinate reference frames (WGS84 / EPSG:4326). |
| **2** | **CSF Ground Filtering** | Cloth Simulation Filter (Zhang et al.) | Inverts point cloud and simulates a physical cloth draped under gravity to mathematically separate bare-earth terrain from above-ground objects. |
| **3** | **Multi-Scale Point Classifier** | Normal estimation & geometric saliency | Computes eigenvalues ($\lambda_1, \lambda_2, \lambda_3$) of local covariance matrices to classify planar facades (walls), horizontal planes (roofs), and vegetation. |
| **4** | **Building Clustering** | Density-Based Spatial Clustering (DBSCAN) | Groups structural points into discrete building instances based on euclidean distance ($\epsilon$) and minimum neighbor density. |
| **5** | **Real Footprint Contour Extrusion** | Shapely Geometric Contour Polygonization | Preserves authentic multi-corner boundaries (L-shapes, angled wings, trapezoids) from Overture Maps / OSM instead of generic cuboids. |
| **6** | **Floor Plan & Elevation Fusion** | Iterative Closest Point (ICP) + Height Slicing | Combines vertical LiDAR height bounds with RERA structural floor heights ($3.2\text{m}$ standard) to generate vertical floor boundaries. |
| **7** | **Watertight 3D Mesh Generation** | Boundary Representation (B-Rep) | Constructs closed, watertight polyhedra for each legal volume ensuring Euler characteristic $\chi = V - E + F = 2$. |
| **8** | **ISO 19152 Legal Space Subdivision** | LADM Part 2 Schema Mapping | Subdivides building physical space into legal space units: Apartments (`A`), Parking Bays (`P`), Staircases (`S`), Utility Shafts (`U`), Common Sky Terraces (`M`), and Air-Rights (`R`). |
| **9** | **3D ULPIN Minting** | 32-bit Balanced Feistel Cipher + Verhoeff Dihedral $D_5$ | Mints unique, non-sequential, pseudorandom 16-character alphanumeric identifiers with guaranteed single-digit and transposition error detection. |
| **10** | **Topological Conflict Scanner** | 3D Intersection & Volumetric Overlap Analysis | Scans cadastre using boundary collision detection (Jaljolie et al.) to identify encroachments, overlaps, and easement violations in real time. |

---

## 📐 Real Footprint Contour Extrusion

Unlike conventional cadastral prototypes that force all buildings into identical rectangular boxes, **vKarma** implements **Real Footprint Contour Extrusion**:

1. **Authentic Boundary Geometry**: Ingests multi-vertex polygon contours from Overture Maps and OpenStreetMap (preserving L-shapes, T-wings, courtyards, angled towers, and custom polygons).
2. **Polygon-Clipped Units**: Floor units are partitioned using Shapely 2D polygon intersection (`building_poly.intersection(quadrant_box)`). Every unit's exterior boundary precisely matches the building's authentic architectural outline.
3. **Multi-Vertex Rooftop & Air-Rights**: Sky Terraces (`M`) and Air-Rights envelopes (`R`) conform to the full multi-vertex building perimeter.
4. **Architectural Wireframe Shell**: In CesiumJS, every building is enveloped in an extruded cyan architectural wireframe (`#20D9E6`) spanning from ground elevation to total structural height.

---

## 🔐 3D ULPIN Cryptographic Architecture

India's 2D Bhu-Aadhaar assigns a 14-digit centroid code. In vertical cities, dozens of property owners share the exact same 2D coordinate. **vKarma** establishes the **3D ULPIN Standard**:

$$\mathbf{PPPPPP}\text{ - }\mathbf{T}\text{ - }\mathbf{RRRRRRRR}\text{ - }\mathbf{C}$$

```text
 560103  -  A  -  G011E73B  -  8
└──┬───┘   └┬┘   └───┬────┘   └┬┘
   │        │        │         └── Verhoeff Dihedral (D5) Checksum Digit
   │        │        └──────────── 32-Bit Balanced Feistel Obfuscated Token (Base32)
   │        └───────────────────── ISO 19152 Space Type Code
   └────────────────────────────── 6-Digit Postal Index Number (Pincode)
```

### ISO 19152 Space Type Codes:
- `A` — Private Apartment / Residential Flat
- `C` — Shared Corridor (Right of Way)
- `S` — Fire Staircase & Elevator Core
- `M` — Sky Terrace / Rooftop Common Deck
- `P` — Subsurface Parking Bay
- `U` — Subsurface Utility Vault / Energy Transformer
- `B` — Physical Building Outer Shell
- `R` — Air-Rights Envelope (+15m Vertical Sky Buffer)

### Cryptographic Properties:
1. **Feistel Cipher Obfuscation**: The serial integer is transformed via a 3-round balanced Feistel cipher with SHA-256 round keys, preventing enumeration attacks or sequential deed tampering.
2. **Verhoeff Dihedral $D_5$ Check Digit**: Evaluated over the non-abelian Dihedral group $D_5$, detecting 100% of single-digit substitution errors and 100% of adjacent transposition errors.

---

## 🇮🇳 Government & Digital Identity Integrations

### 1. DigiLocker Document Exchange (MeitY / DILRMP)
- **DoLR DILRMP Standard Schema**: Issues official XML certificates (`BHUCR`) conforming to MeitY circulars with digital signatures and IPFS hashes.
- **Sovereign Cloud Vault**: Citizens can view, verify, and pull authentic digital title deeds into their DigiLocker account.
- **Sandbox Simulation**: Operates out-of-the-box in sandbox mode with zero external dependencies.

### 2. Google Wallet Generic Passes API
- **Digital Land Passport**: Issues native Google Wallet Passes for Android and WearOS.
- **RS256 JWT Signing**: Signed using Google Cloud Service Account credentials (`vkarma-service@vkarma-wallet.iam.gserviceaccount.com`).
- **Complete Self-Contained JWT**: Includes both `genericClasses` and `genericObjects` with QR code deep links back to the 3D digital twin.
- **Direct Save Link**: Generates a standard `https://pay.google.com/gp/v/save/{JWT}` button directly in the browser.

### 3. Brevo Transactional Email Gateway
- **Official Delivery**: Dispatches 3D Bhu-Aadhaar Land Title Certificates and Executive Passports directly to citizen email addresses.
- **Free Tier Integration**: 300 free emails per day with zero setup cost.

### 4. Address-as-a-Service (AaaS) & 3D Drone Navigation
- **Floor-Accurate Coordinates**: Provides exact 3D dispatch coordinates (`latitude, longitude, altitude_agl, floor_level`).
- **Autonomous Drone Delivery**: Enables rooftop and balcony landing coordinates for automated aerial logistics.

---

## ☁️ 100% Free Cloud Deployment Architecture

The entire platform runs on **100% free cloud services**:

| Service | Provider | Free Plan Quota | Configured Role |
| :--- | :--- | :--- | :--- |
| **Web Service & APIs** | [Render](https://render.com) | 512MB RAM, Free SSL, Auto-Deploy on `git push` | Serves FastAPI REST APIs & 3D WebGIS frontend |
| **Spatial Database** | [Supabase](https://supabase.com) | 500MB PostgreSQL, PostGIS, Connection Pooler | Stores spatial units, legal deeds, and parties |
| **Async Task Worker** | Built-in ThreadPool / [Upstash](https://upstash.com) | Zero-cost in-process / 10,000 req/day Redis | Executes 10-stage AI pipeline asynchronously |
| **3D Topo Terrain** | [Cesium Ion](https://ion.cesium.com) | 5GB 3D asset storage, 75GB/month streaming | Renders WebGL global 3D viewer |
| **LiDAR Aerial Survey** | [OpenTopography](https://portal.opentopography.org) | Free registered developer key | Ingests real point cloud survey data |
| **Transactional Email** | [Brevo](https://www.brevo.com) | 300 free emails/day forever | Sends digital land certificates |
| **Mobile Land Pass** | [Google Cloud Platform](https://pay.google.com/business/console) | Free Generic Passes API (0 cost) | Issues Google Wallet cards |

---

## 📂 Repository Structure

```text
vkarma/
├── backend/
│   ├── app.py                         # FastAPI web application, API routes, and static mounts
│   ├── celery_worker.py               # Celery async worker configuration
│   ├── email_service.py               # Brevo transactional email dispatcher
│   ├── run_server.py                  # Local development launcher with dynamic PORT binding
│   ├── tasks.py                       # Celery / ThreadPool async pipeline tasks
│   ├── database/
│   │   ├── repository.py              # Supabase PostGIS spatial data access layer
│   │   ├── migration_runner.py        # Automated SQL schema migrator
│   │   └── supabase_client.py         # Resilient Supabase client with in-memory fallback
│   ├── digilocker/
│   │   ├── issuer_service.py          # MeitY / DoLR DILRMP XML certificate generator
│   │   └── models.py                  # DigiLocker document data schemas
│   ├── ladm/
│   │   ├── cadastral_db.py            # ISO 19152 cadastral database manager
│   │   ├── schema.py                  # LADM Part 2 core classes (LA_SpatialUnit, LA_RRR, etc.)
│   │   ├── seed_cadastre.py           # Pilot city cadastre seeder (Bengaluru, Mumbai, Delhi)
│   │   └── topological_validator.py   # 3D spatial overlap and collision engine
│   ├── pipeline/
│   │   ├── building_discovery.py      # Overture Maps & OpenStreetMap polygon discovery
│   │   ├── building_images.py         # Realistic architectural facade imagery
│   │   ├── clustering.py              # DBSCAN building instance clustering
│   │   ├── csf_filter.py              # Cloth Simulation Filter bare-earth ground separation
│   │   ├── extrusion_engine.py        # Real footprint contour extrusion & unit partitioning
│   │   ├── footprint_extractor.py     # Alpha-shape & concave hull polygon extraction
│   │   ├── lidar_fetcher.py           # OpenTopography LAZ point cloud stream fetcher
│   │   ├── pipeline_orchestrator.py   # 10-stage sequential pipeline coordinator
│   │   └── point_classifier.py        # Covariance eigenvalue geometric point classifier
│   ├── ulpin/
│   │   ├── feistel_fpe.py             # 32-bit balanced Feistel cipher implementation
│   │   ├── ulpin_generator.py         # Complete 3D ULPIN parser and generator
│   │   └── verhoeff.py                # Dihedral group D5 checksum algorithm
│   └── wallet/
│       └── google_wallet_service.py   # Google Wallet Generic Passes API & RS256 JWT signer
├── frontend/
│   ├── index.html                     # 3D WebGIS Console (redirect target)
│   ├── landing.html                   # Sovereign national landing page
│   ├── console.html                   # Interactive 3D Digital Twin & Dispute Scanner
│   ├── ulpin.html                     # Citizen Bhu-Aadhaar Verification & Wallet Portal
│   ├── about.html                     # Technical architecture & compliance specifications
│   ├── css/
│   │   └── styles.css                 # Premium dark-mode glassmorphic design system
│   └── js/
│       ├── viewer3d.js                # CesiumJS 3D WebGL renderer & polygon visualizer
│       ├── console_ui.js              # 3D GIS interactive dashboard and dispute tools
│       ├── bounding_box_selector.js   # Leaflet 2D geospatial bounding box picker
│       └── ulpin_portal.js            # Bhu-Aadhaar lookup, deed download & wallet pass logic
├── tests/                             # 59 automated unit and integration tests
├── Dockerfile                         # Production Docker container definition
├── docker-compose.yml                 # Local container orchestration
├── render.yaml                        # Infrastructure-as-code for Render cloud deployment
├── requirements.txt                   # Production Python dependencies
└── .env.example                       # Documented environment variable template
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Clone Repository
```bash
git clone https://github.com/Pranav-joshi02/vkarma.git
cd vkarma
```

### 3. Create Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configure your environment settings (all external APIs have built-in resilient in-memory fallbacks):
```ini
# Server Configuration
PORT=8000
PUBLIC_URL=http://localhost:8000

# 3D Geospatial Providers (Optional)
CESIUM_ION_TOKEN=your_cesium_ion_token
OPENTOPOGRAPHY_API_KEY=your_opentopo_key

# Supabase PostGIS Database (Optional - in-memory fallback included)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres

# DigiLocker Gateway
DIGILOCKER_SANDBOX_MODE=true

# Brevo Transactional Email (Optional)
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=your_email@domain.com

# Google Wallet Generic Passes API
GOOGLE_WALLET_ISSUER_ID=3388000000023198169
GOOGLE_WALLET_SA_EMAIL=vkarma-service@vkarma-wallet.iam.gserviceaccount.com
GOOGLE_WALLET_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

### 6. Launch Application
```bash
python run_server.py
```

Access the application locally:
- Landing Page: `http://localhost:8000`
- 3D WebGIS Console: `http://localhost:8000/console`
- Bhu-Aadhaar Portal: `http://localhost:8000/ulpin`
- OpenAPI Swagger: `http://localhost:8000/docs`

---

## 🐳 Docker Deployment

Build and run the containerized application locally:

```bash
# Build Docker image
docker build -t vkarma:latest .

# Run container mapping port 8000 to internal container port 10000
docker run -p 8000:10000 -e PORT=10000 --env-file .env vkarma:latest
```

Or using Docker Compose:
```bash
docker-compose up --build
```

---

## ☁️ Deploying to Render (Free Tier)

vKarma is pre-configured for zero-configuration deployment on Render using `render.yaml`:

1. Fork or push this repository to GitHub.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint** and connect your repository (or create a **Web Service** with Environment `Docker`).
4. Set the following required environment variables in the Render Dashboard:
   - `PORT` = `10000`
   - `PUBLIC_URL` = `https://vkarma.onrender.com`
   - `GOOGLE_WALLET_ISSUER_ID` = `3388000000023198169`
   - `GOOGLE_WALLET_SA_EMAIL` = `vkarma-service@vkarma-wallet.iam.gserviceaccount.com`
   - `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON` = Single-line minified JSON string of your Google Cloud service account key
5. Ensure your Health Check Path is set to `/health`.
6. Click **Deploy**. Render will build the Docker container and start the service with full dynamic port binding.

### Google Wallet Demo Mode Note
When using the Google Wallet Generic Passes API in **Demo Mode**:
- Any Google Account attempting to save passes must be registered in the **Google Pay & Wallet Console** under **Test Accounts**.
- Alternatively, request production publishing access directly from the Google Wallet Console.

---

## 📡 REST API Reference

### Geospatial Pipeline & Cadastre
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/regions` | Returns pre-configured urban pilot survey regions (Bengaluru, Mumbai, Delhi). |
| `POST` | `/api/area/buildings` | Discovers real buildings in bounding box via Overture Maps + OSM. |
| `POST` | `/api/pipeline/run` | Submits the 10-stage AI pipeline for asynchronous processing. |
| `GET` | `/api/pipeline/status/{task_id}` | Polls pipeline execution stage, percentage, and results. |
| `GET` | `/api/buildings` | Lists all registered 3D spatial building models. |
| `GET` | `/api/buildings/{id}` | Returns watertight 3D meshes, footprint polygon, and legal units. |

### 3D ULPIN, Disputes & Navigation
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/ulpin/lookup/{ulpin}` | Returns complete ISO 19152 legal profile, RRR records, and deed links. |
| `POST` | `/api/ulpin/verify` | Validates Verhoeff Dihedral $D_5$ checksum and Feistel structure. |
| `POST` | `/api/disputes/scan` | Scans cadastral space for topological overlaps and encroachments. |
| `GET` | `/api/delivery/resolve/{ulpin}` | Address-as-a-Service floor and drone coordinates resolver. |
| `GET` | `/api/pointcloud/sample` | Streams classified LiDAR points for WebGL rendering. |

### DigiLocker, Google Wallet & Communication Gateways
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/digilocker/push-certificate` | Issues official 3D land title certificate into citizen DigiLocker vault. |
| `GET` | `/api/digilocker/certificate/{ulpin}/xml` | Returns MeitY-compliant XML certificate conforming to DoLR DILRMP. |
| `POST` | `/api/wallet/google-pass` | Generates official Google Wallet Generic Pass (RS256 JWT & Save URL). |
| `GET` | `/api/wallet/config` | Returns Google Wallet issuer status and public configuration. |
| `POST` | `/api/email/send-certificate` | Dispatches official 3D land deed via Brevo Transactional SMTP. |
| `POST` | `/api/email/send-passport` | Dispatches executive Digital Land Passport via Brevo Transactional SMTP. |
| `GET` | `/health` / `/healthz` | System liveness probe returning HTTP 200 OK. |

---

## 🧪 Automated Testing Suite

The repository contains 59 automated unit and integration tests covering the cryptographic engine, pipeline stages, schema validation, and external gateways:

```bash
python -m pytest tests/ -v
```

```text
======================= 59 passed, 2 warnings in 27.65s =======================
tests/test_building_discovery_selection.py ...................  [ 32%]
tests/test_building_realistic_images.py    .....                [ 40%]
tests/test_custom_bbox.py                  ..                   [ 44%]
tests/test_database.py                     ....                 [ 50%]
tests/test_digilocker.py                   ......               [ 61%]
tests/test_email_service.py                .....                [ 69%]
tests/test_feistel.py                      ..                   [ 72%]
tests/test_google_wallet.py                ......               [ 83%]
tests/test_ladm.py                         ...                  [ 88%]
tests/test_pipeline.py                     ...                  [ 93%]
tests/test_verhoeff.py                     ....                 [100%]
```

---

## 📜 Compliance & Standards

- **ISO 19152:2012 / 2024**: Geographic information — Land Administration Domain Model (LADM) Part 2 (Land Registration & 3D Spatial Units).
- **OGC 3D Portrayal Service**: Open Geospatial Consortium standards for WebGL volumetric GIS rendering.
- **MeitY / DILRMP Guidelines**: Digital India Land Records Modernization Programme, Department of Land Resources (DoLR), Ministry of Rural Development, Government of India.
- **National Geospatial Policy 2022**: Department of Science and Technology, Government of India.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
