/**
 * VKARMA About & API Ecosystem Interactive Architecture Controller
 * Provides interactive node inspection for the tripartite API diagram
 * (Government, Commerce, Individual) and handles documentation tabs.
 */

document.addEventListener("DOMContentLoaded", () => {
  initApiDiagram();
  initPersonaTabs();
});

const NODE_DETAILS = {
  vkarma_core: {
    title: "VKARMA SPATIAL CORE",
    type: "Orchestration & LADM 3D Cadastral Engine",
    status: "Available",
    endpoint: "/api/pipeline/run • /api/cadastre/status",
    description: "The core engine processes multi-sensor LiDAR/drone point clouds, runs CSF ground separation, DBSCAN clustering, and extrudes volumetric 3D legal spaces compliant with ISO 19152.",
    specs: [
      { name: "Standard", val: "ISO 19152 (LADM 3D)" },
      { name: "Security", val: "Feistel Cipher Tokenization + Verhoeff D5 Checksum" },
      { name: "Performance", val: "Sub-second 3D topological intersection check" }
    ]
  },
  government: {
    title: "GOVERNMENT AUTHORITIES API",
    type: "Cadastral Administration & Spatial Justice",
    status: "Available",
    endpoint: "/api/disputes/scan • /api/ulpin/mint • /api/area/buildings",
    description: "Municipal corporations, survey departments, and state revenue ministries access verifiable 3D parcel boundaries, automated title dispute detection, and volumetric property tax assessments.",
    specs: [
      { name: "Topological Scanner", val: "Volumetric overlap & encroachment detection (Jaljolie et al.)" },
      { name: "RERA Deeds", val: "Direct attachment of RERA sanctioned building unit boundaries" },
      { name: "3D Property Tax", val: "Exact cubic meter volumetric tax base calculation" }
    ]
  },
  commerce: {
    title: "COMMERCE & LOGISTICS API",
    type: "Address-as-a-Service & Spatial Search",
    status: "Available",
    endpoint: "/api/delivery/resolve/{ulpin} • /api/area/buildings",
    description: "E-commerce retailers, quick-commerce couriers, and autonomous drone delivery networks resolve customer 3D ULPINs to exact high-rise floor levels, elevator core recommendations, and rooftop drop points.",
    specs: [
      { name: "Address Resolution", val: "UPI for 3D Addresses (3-second geocoding)" },
      { name: "Drone Flight Corridors", val: "Rooftop air-rights dropoff coordinates & vertical buffers" },
      { name: "Building Footprints", val: "Regularized building envelopes for map tile rendering" }
    ]
  },
  individual: {
    title: "INDIVIDUAL CITIZENS & BUYERS API",
    type: "Digital Land Passport & Property Verification",
    status: "Available",
    endpoint: "/api/ulpin/lookup/{ulpin} • /api/ulpin/verify",
    description: "Homebuyers, property owners, and legal evaluators search any apartment or parcel to instantly inspect registered deeds, mortgage hypothecations, and scan QR verification codes before transactions.",
    specs: [
      { name: "Digital Land Passport", val: "Tamper-proof volumetric property identity passport" },
      { name: "Mortgage Transparency", val: "Real-time bank lien and RERA compliance verification" },
      { name: "Cryptographic QR", val: "Instant field verification via mobile camera" }
    ]
  },
  gis_data: {
    title: "GIS & 3D POINT CLOUD LAYER",
    type: "Spatial Geometry & Point Cloud Services",
    status: "Available",
    endpoint: "/api/pointcloud/sample • /api/config",
    description: "Streaming subsampled LAS/LAZ point clouds, classified ground/building/vegetation returns, and 3D Tiles for CesiumJS WebGL visualization.",
    specs: [
      { name: "Streaming Format", val: "Subsampled WebGL Buffer / 3D Tiles" },
      { name: "Classification", val: "Ground (Class 2), High Veg (Class 5), Building (Class 6)" }
    ]
  },
  property_data: {
    title: "PROPERTY ATTRIBUTES & RRR LAYER",
    type: "LADM ISO 19152 Relational Registry",
    status: "Available",
    endpoint: "/api/buildings • /api/buildings/{id}",
    description: "Relational registry linking parties (owners, banks, state), rights (freeholds, undivided common shares), restrictions (liens, zoning), and legal documents.",
    specs: [
      { name: "Entity Model", val: "LA_Party, LA_RRR, LA_Source, LA_LegalSpaceUnit" },
      { name: "Persistence", val: "Supabase / PostgreSQL PostGIS with In-Memory Caching" }
    ]
  },
  ulpin_passport: {
    title: "3D ULPIN PASSPORT LAYER",
    type: "Cryptographic Identity & Verifiable Credentials",
    status: "Available",
    endpoint: "/api/ulpin/lookup/{ulpin} • /ulpin/{ulpin}",
    description: "Format-preserving Feistel encryption converts sequential unit registrations into non-sequential 8-character tokens, sealed with a Verhoeff Dihedral D5 check digit.",
    specs: [
      { name: "Syntax", val: "PPPPPP-T-RRRRRRRR-C (~17 characters)" },
      { name: "Error Detection", val: "100% single digit errors, 100% adjacent transpositions" }
    ]
  }
};

function initApiDiagram() {
  const nodes = document.querySelectorAll(".diagram-subnode, .diagram-node");
  const detailCard = document.getElementById("node-detail-panel");
  if (!detailCard) return;

  nodes.forEach((node) => {
    node.addEventListener("click", () => {
      nodes.forEach(n => n.classList.remove("active"));
      node.classList.add("active");

      const key = node.getAttribute("data-node-id");
      const info = NODE_DETAILS[key] || NODE_DETAILS.vkarma_core;
      renderNodeDetail(info);
    });
  });

  // Default selection
  renderNodeDetail(NODE_DETAILS.vkarma_core);
}

function renderNodeDetail(info) {
  const titleEl = document.getElementById("node-detail-title");
  const typeEl = document.getElementById("node-detail-type");
  const statusEl = document.getElementById("node-detail-status");
  const endpointEl = document.getElementById("node-detail-endpoint");
  const descEl = document.getElementById("node-detail-desc");
  const specsList = document.getElementById("node-detail-specs");

  if (titleEl) titleEl.textContent = info.title;
  if (typeEl) typeEl.textContent = info.type;
  if (statusEl) {
    statusEl.textContent = info.status;
    statusEl.className = `persona-badge badge-${info.status.toLowerCase()}`;
  }
  if (endpointEl) endpointEl.textContent = info.endpoint;
  if (descEl) descEl.textContent = info.description;

  if (specsList) {
    specsList.innerHTML = info.specs.map(s => `
      <li class="service-item">
        <span>${s.name}</span>
        <strong>${s.val}</strong>
      </li>
    `).join("");
  }
}

function initPersonaTabs() {
  const tabs = document.querySelectorAll(".persona-tab");
  const cards = document.querySelectorAll(".persona-card");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.getAttribute("data-persona");
      cards.forEach(card => {
        if (target === "all" || card.getAttribute("data-persona") === target) {
          card.style.display = "block";
        } else {
          card.style.display = "none";
        }
      });
    });
  });
}
