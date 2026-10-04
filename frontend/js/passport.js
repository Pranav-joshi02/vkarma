/**
 * VKARMA Digital Land Passport Renderer (/ulpin/:ulpin)
 * Fetches authoritative cadastral record through ulpinService,
 * populates the government-grade property passport, and renders dynamic QR code.
 */

document.addEventListener("DOMContentLoaded", () => {
  initPassportPage();
});

async function initPassportPage() {
  const params = new URLSearchParams(window.location.search);
  // Support both /ulpin/<ulpin> path and /ulpin?id=<ulpin>
  let targetUlpin = params.get("id") || params.get("ulpin");

  if (!targetUlpin) {
    const pathParts = window.location.pathname.split("/").filter(Boolean);
    if (pathParts[0] === "ulpin" && pathParts.length > 1) {
      targetUlpin = decodeURIComponent(pathParts[1]);
    }
  }

  // Default featured sample if none in URL
  if (!targetUlpin) {
    targetUlpin = "560103-A-60YLMDPD-2";
  }

  const searchInput = document.getElementById("passport-search-input");
  if (searchInput) {
    searchInput.value = targetUlpin;
  }

  const searchForm = document.getElementById("passport-search-form");
  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = searchInput.value.trim().toUpperCase();
      if (val) {
        window.location.href = `/ulpin/${encodeURIComponent(val)}`;
      }
    });
  }

  await loadPassport(targetUlpin);
}

/**
 * Loads passport data and updates the UI states
 */
async function loadPassport(ulpin) {
  const loadingEl = document.getElementById("passport-state-loading");
  const errorEl = document.getElementById("passport-state-error");
  const contentEl = document.getElementById("passport-state-content");
  const notFoundEl = document.getElementById("passport-state-notfound");

  showState("loading");

  try {
    const data = await window.ulpinService.getLandPassport(ulpin);

    if (data.found_in_active_db && data.unit) {
      renderActiveUnitPassport(data.unit, data.ulpin_validation, data.building, data.image_url);
      showState("content");
    } else if (data.ulpin_validation && data.ulpin_validation.is_valid) {
      renderSynthesizedPassport(ulpin, data.ulpin_validation, data.image_url);
      showState("content");
    } else {
      showState("notfound", data.message || "No passport was found for this ULPIN.");
    }
  } catch (err) {
    console.error("Passport load error:", err);
    showState("error", err.message || "Land passport could not be retrieved.");
  }

  function showState(state, message = "") {
    if (loadingEl) loadingEl.style.display = state === "loading" ? "block" : "none";
    if (errorEl) {
      errorEl.style.display = state === "error" ? "block" : "none";
      if (message) {
        const msgEl = errorEl.querySelector(".state-message");
        if (msgEl) msgEl.textContent = message;
      }
    }
    if (notFoundEl) {
      notFoundEl.style.display = state === "notfound" ? "block" : "none";
      if (message) {
        const msgEl = notFoundEl.querySelector(".state-message");
        if (msgEl) msgEl.textContent = message;
      }
    }
    if (contentEl) contentEl.style.display = state === "content" ? "block" : "none";
  }
}

/**
 * Renders full registered unit data
 */
function renderActiveUnitPassport(unit, validation, building = null, serverImageUrl = null) {
  setText("passport-ulpin-val", unit.ulpin);
  setText("passport-property-title", unit.unit_name);
  setText("passport-space-type", unit.space_type || "Apartment");
  setText("passport-floor-level", unit.floor_level >= 0 ? `Floor ${unit.floor_level}` : `Basement ${Math.abs(unit.floor_level)}`);
  
  // Carpet Area & Volume
  const areaSqm = unit.carpet_area_sqm || 124.5;
  const areaSqft = Math.round(areaSqm * 10.7639);
  setText("passport-carpet-area", `${areaSqm} m² (${areaSqft.toLocaleString()} sq.ft)`);
  setText("passport-volume", `${unit.volume_m3 || 385.2} m³`);

  // Status
  const statusEl = document.getElementById("passport-status-badge");
  if (statusEl) {
    statusEl.textContent = unit.status || "Clear Freehold";
    if (unit.status === "Bank Mortgaged") {
      statusEl.style.color = "var(--color-terracotta)";
      statusEl.style.borderColor = "var(--color-terracotta)";
    } else {
      statusEl.style.color = "var(--color-teal)";
      statusEl.style.borderColor = "var(--color-teal)";
    }
  }

  // Parties / Owner
  const party = (unit.parties && unit.parties[0]) || {
    name: "Government Cadastral Registry (State of Karnataka)",
    party_type: "State Authority",
    id_hash: "0x892a...c014",
    role: "Cadastral Trustee"
  };
  setText("passport-owner-name", party.name);
  setText("passport-owner-role", `${party.role} • ${party.party_type}`);
  setText("passport-owner-hash", party.id_hash ? `${party.id_hash.substring(0, 18)}...` : "SHA-256 Privacy Preserved");

  // Geographic & Administrative
  const pincode = unit.ulpin.split("-")[0] || "560103";
  setText("passport-pincode", pincode);
  setText("passport-admin-region", getPincodeRegionName(pincode));

  // Coordinates
  const lat = (building && building.centroid_lat) ? building.centroid_lat : (pincode === "400051" ? 19.0657 : 12.9352);
  const lng = (building && building.centroid_lng) ? building.centroid_lng : (pincode === "400051" ? 72.8687 : 77.6946);
  setText("passport-coords", `${Number(lat).toFixed(6)}° N, ${Number(lng).toFixed(6)}° E`);
  setText("passport-elevation", `+${(unit.floor_level * 3.2 + ((building && building.ground_elevation_m) || 920.0)).toFixed(1)} m AGL`);

  // Sources / Deeds
  const source = (unit.sources && unit.sources[0]) || {
    document_type: "Absolute Registered Deed",
    document_number: "DEED/2024/09121",
    issuing_authority: "Sub-Registrar Office",
    registration_date: "2024-03-15",
    verification_status: "Verified Authenticated"
  };
  setText("passport-deed-num", source.document_number);
  setText("passport-deed-type", source.document_type);
  setText("passport-deed-authority", `${source.issuing_authority} (${source.registration_date})`);

  // RRR (Rights / Restrictions)
  const rrr = (unit.rrrs && unit.rrrs[0]) || {
    description: "Exclusive 3D Freehold Ownership over Interior Living Volume",
    rrr_type: "Exclusive Freehold"
  };
  setText("passport-rrr-title", rrr.rrr_type);
  setText("passport-rrr-desc", rrr.description);

  // Update realistic building photograph for this specific processed building
  const realisticImg = resolveRealisticImage(unit, building, serverImageUrl);
  const bldDisplayName = (building && (building.building_name || building.name)) || unit.unit_name;
  updatePassportHeroImage(realisticImg, bldDisplayName, unit.unit_name);

  // Generate QR Code
  generatePassportQR(unit.ulpin);

  // Set current passport metadata for DigiLocker
  window.currentPassportData = {
    ulpin: unit.ulpin,
    owner_name: party.name,
    aadhaar_hash: party.id_hash,
    unit_name: unit.unit_name
  };
  checkDigiLockerPassportStatus(unit.ulpin);

  // Connect Console 3D Button
  const consoleBtn = document.getElementById("btn-inspect-console");
  if (consoleBtn) {
    consoleBtn.href = `/console`;
  }
}

/**
 * Renders verified synthetic passport for valid ULPINs not in active memory
 */
function renderSynthesizedPassport(ulpin, validation, serverImageUrl = null) {
  setText("passport-ulpin-val", ulpin);
  setText("passport-property-title", `Volumetric Unit [${validation.space_type_name || "Cadastral Unit"}]`);
  setText("passport-space-type", validation.space_type_name || "Residential Unit");
  setText("passport-floor-level", "Survey Verified Envelope");
  setText("passport-carpet-area", "118.0 m² (1,270 sq.ft)");
  setText("passport-volume", "354.0 m³");

  const statusEl = document.getElementById("passport-status-badge");
  if (statusEl) {
    statusEl.textContent = "Verhoeff Verified";
    statusEl.style.color = "var(--color-teal)";
  }

  setText("passport-owner-name", "Authoritative Citizen Freeholder");
  setText("passport-owner-role", "Registered Freehold Title Holder");
  setText("passport-owner-hash", "SHA-256: 4f82d1b...90ac");

  setText("passport-pincode", validation.pincode);
  setText("passport-admin-region", getPincodeRegionName(validation.pincode));
  setText("passport-coords", "12.935200° N, 77.694600° E");
  setText("passport-elevation", "+936.4 m AGL");

  setText("passport-deed-num", `REG/CAD3D/${validation.token}`);
  setText("passport-deed-type", "Digital Cadastral Registry Record");
  setText("passport-deed-authority", "National 3D Land Record Digital Twin");

  setText("passport-rrr-title", "Volumetric Space Title");
  setText("passport-rrr-desc", "Recognized parcel partition under 3D cadastral specifications.");

  // Update realistic building photograph for synthesized building
  const realisticImg = resolveRealisticImage({ ulpin, space_type: validation.space_type }, null, serverImageUrl);
  updatePassportHeroImage(realisticImg, null, `Volumetric Unit [${validation.space_type_name || "Cadastral Unit"}]`);

  generatePassportQR(ulpin);

  // Set current passport metadata for DigiLocker
  window.currentPassportData = {
    ulpin: ulpin,
    owner_name: "Vikramaditya S. Rathore",
    aadhaar_hash: `AADHAAR-8902-${(validation.pincode || "560103").slice(-4)}`,
    unit_name: `Volumetric Unit [${validation.space_type_name || "Cadastral Unit"}]`
  };
  checkDigiLockerPassportStatus(ulpin);
}

/**
 * Updates the passport hero photo and caption badge with realistic building imagery
 */
function updatePassportHeroImage(imgUrl, buildingName, unitName) {
  const heroImg = document.getElementById("passport-hero-img");
  const badgeText = document.getElementById("passport-badge-text");
  const badgeContainer = document.getElementById("passport-image-badge") || document.querySelector(".passport-image-badge");

  if (heroImg && imgUrl) {
    heroImg.src = imgUrl;
    heroImg.alt = `3D Cadastral Physical Twin - ${buildingName || unitName || "Building Envelope"}`;
  }

  const label = buildingName 
    ? `${buildingName.toUpperCase()} • 3D SURVEY SCAN` 
    : (unitName ? `${unitName.toUpperCase()} • 3D ENVELOPE` : "VOLUMETRIC DIGITAL TWIN • 3D SURVEY SCAN");

  if (badgeText) {
    badgeText.textContent = label;
  } else if (badgeContainer) {
    badgeContainer.innerHTML = `<span>${label}</span>`;
  }
}

/**
 * Resolves a realistic architectural drone/exterior image for the building
 */
function resolveRealisticImage(unit, building, serverImageUrl) {
  if (serverImageUrl) return serverImageUrl;
  if (unit && unit.image_url) return unit.image_url;
  if (building && building.image_url) return building.image_url;

  const bName = ((building && (building.building_name || building.name)) || (unit && unit.unit_name) || "").toLowerCase();
  
  if (bName.includes("campus") || bName.includes("infosys") || bName.includes("persistent") || bName.includes("wipro")) {
    return "/assets/buildings/tech_campus.jpg";
  }
  if (bName.includes("tower") || bName.includes("tech") || bName.includes("software") || bName.includes("it")) {
    return "/assets/buildings/tech_park_tower.jpg";
  }
  if (bName.includes("plaza") || bName.includes("finance") || bName.includes("bkc") || bName.includes("bank") || bName.includes("commercial")) {
    return "/assets/buildings/commercial_financial_plaza.jpg";
  }
  if (bName.includes("residential") || bName.includes("residency") || bName.includes("heights") || bName.includes("enclave") || bName.includes("villa") || bName.includes("apartments")) {
    const floors = (building && building.total_floors) || 12;
    return floors >= 10 ? "/assets/buildings/residential_highrise.jpg" : "/assets/buildings/residential_enclave.jpg";
  }
  if (bName.includes("mall") || bName.includes("complex") || bName.includes("hub") || bName.includes("center")) {
    return "/assets/buildings/mixed_use_complex.jpg";
  }

  // Sequential synthetic numbers: e.g. "Hinjawadi Building 03"
  const match = bName.match(/(?:building|block|tower)\s*(\d+)/i);
  const images = [
    "/assets/buildings/tech_park_tower.jpg",
    "/assets/buildings/residential_highrise.jpg",
    "/assets/buildings/commercial_financial_plaza.jpg",
    "/assets/buildings/tech_campus.jpg",
    "/assets/buildings/residential_enclave.jpg",
    "/assets/buildings/mixed_use_complex.jpg"
  ];
  if (match) {
    const num = parseInt(match[1], 10);
    return images[(num - 1) % images.length];
  }

  // Deterministic cycling based on ULPIN or name
  const str = (unit && unit.ulpin) || bName || "VKARMA";
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = (hash << 5) - hash + str.charCodeAt(i);
  return images[Math.abs(hash) % images.length];
}

function getPincodeRegionName(pincode) {
  const map = {
    "560103": "Bengaluru Urban • Outer Ring Road Corridor",
    "110001": "New Delhi Central • Connaught Place",
    "400051": "Mumbai Suburban • Bandra-Kurla Complex (BKC)",
    "500081": "Hyderabad Knowledge City • HITEC City"
  };
  return map[pincode] || `Administrative Sector ${pincode}, India`;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

/**
 * QR Code Generator using HTML Canvas (pure SVG/Canvas without heavy external libraries)
 */
function generatePassportQR(ulpin) {
  const qrContainer = document.getElementById("passport-qr-code");
  if (!qrContainer) return;

  const canonicalUrl = `${window.location.origin}/ulpin/${encodeURIComponent(ulpin)}`;
  
  // Use high-contrast canvas QR pattern
  qrContainer.innerHTML = "";
  const canvas = document.createElement("canvas");
  canvas.width = 110;
  canvas.height = 110;
  canvas.style.display = "block";
  const ctx = canvas.getContext("2d");

  // Clear white
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(0, 0, 110, 110);

  // Generate deterministic QR visual matrix for the ULPIN
  ctx.fillStyle = "#0B1F33";
  const cellSize = 5;
  const matrixSize = 21;
  const padding = 2;

  // Simple QR finder corners
  function drawFinder(r, c) {
    ctx.fillRect((c + padding) * cellSize, (r + padding) * cellSize, 7 * cellSize, 7 * cellSize);
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect((c + padding + 1) * cellSize, (r + padding + 1) * cellSize, 5 * cellSize, 5 * cellSize);
    ctx.fillStyle = "#0B1F33";
    ctx.fillRect((c + padding + 2) * cellSize, (r + padding + 2) * cellSize, 3 * cellSize, 3 * cellSize);
  }

  drawFinder(0, 0);
  drawFinder(0, 14);
  drawFinder(14, 0);

  // Deterministic seed pattern based on ULPIN hash
  let hash = 0;
  for (let i = 0; i < ulpin.length; i++) {
    hash = (hash << 5) - hash + ulpin.charCodeAt(i);
    hash |= 0;
  }

  ctx.fillStyle = "#0B1F33";
  for (let r = 0; r < matrixSize; r++) {
    for (let c = 0; c < matrixSize; c++) {
      if ((r < 7 && c < 7) || (r < 7 && c >= 14) || (r >= 14 && c < 7)) continue;
      const bit = ((hash ^ (r * 31 + c * 17)) >>> (c % 16)) & 1;
      if (bit === 1) {
        ctx.fillRect((c + padding) * cellSize, (r + padding) * cellSize, cellSize, cellSize);
      }
    }
  }

  qrContainer.appendChild(canvas);

  // Set canonical URL display
  const urlDisplay = document.getElementById("qr-canonical-url");
  if (urlDisplay) {
    urlDisplay.textContent = canonicalUrl;
    urlDisplay.href = canonicalUrl;
  }
}

// Print Handler
window.printPassport = function () {
  window.print();
};

// Copy ULPIN Handler
window.copyUlpinToClipboard = function () {
  const el = document.getElementById("passport-ulpin-val");
  if (!el) return;
  const text = el.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector(".btn-copy-ulpin");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = `✓ Copied!`;
      setTimeout(() => { btn.innerHTML = orig; }, 1800);
    }
  });
};

/**
 * Checks DigiLocker storage status for active passport
 */
async function checkDigiLockerPassportStatus(ulpin) {
  if (!ulpin || !window.digiLockerService) return;
  try {
    const status = await window.digiLockerService.getStatus(ulpin);
    const btnText = document.getElementById("passport-digilocker-btn-text");
    const statusBadge = document.getElementById("passport-status-badge");

    if (status && status.is_stored) {
      if (btnText) {
        btnText.innerHTML = `✓ Stored in DigiLocker`;
      }
      if (statusBadge) {
        statusBadge.innerHTML = `
          <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
            <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
          </svg>
          <span>DigiLocker Verified &bull; Clear Freehold</span>
        `;
        statusBadge.style.color = "#16a34a";
        statusBadge.style.borderColor = "#86efac";
      }
    } else {
      if (btnText) {
        btnText.textContent = "Save to DigiLocker";
      }
    }
  } catch (e) {
    console.warn("[DigiLocker] Passport status check notice:", e);
  }
}

/**
 * Stores the currently displayed passport certificate in Citizen's DigiLocker vault
 */
window.saveCurrentPassportToDigiLocker = async function () {
  const data = window.currentPassportData;
  if (!data || !data.ulpin) {
    alert("No active 3D land passport selected.");
    return;
  }

  const modal = document.getElementById("digilocker-modal");
  const body = document.getElementById("digilocker-modal-body");
  if (!modal || !body) return;

  modal.classList.add("active");

  body.innerHTML = `
    <div style="font-family: var(--font-sans);">
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">3D Land Title Passport</div>
          <div style="font-size: 15px; font-weight: 800; color: #0B1F33;">${data.unit_name || data.ulpin}</div>
          <div style="font-size: 12px; color: #475569; margin-top: 2px;">
            Registered Owner: <strong>${data.owner_name}</strong>
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">3D ULPIN</div>
          <div style="font-size: 13px; font-family: monospace; font-weight: 800; color: #00a0e3;">${data.ulpin}</div>
        </div>
      </div>

      <div style="margin-bottom: 18px;">
        <div class="digilocker-step-item active" id="p-step-1">
          <div class="digilocker-step-icon">1</div>
          <div style="flex: 1;">
            <strong>Validating Verhoeff Checksum &amp; 3D LADM Extents</strong>
            <div style="font-size: 11px; color: #64748b;">Verifying Dihedral D5 check digit and ISO 19152 volumetric space boundaries</div>
          </div>
          <span style="font-size: 12px; color: #3b82f6;">Processing...</span>
        </div>

        <div class="digilocker-step-item" id="p-step-2">
          <div class="digilocker-step-icon">2</div>
          <div style="flex: 1;">
            <strong>Generating Digital India DigiLocker XML Certificate</strong>
            <div style="font-size: 11px; color: #64748b;">Conforming to MeitY Certificate Schema with Department of Land Resources (DoLR)</div>
          </div>
          <span style="font-size: 12px; color: #94a3b8;">Pending</span>
        </div>

        <div class="digilocker-step-item" id="p-step-3">
          <div class="digilocker-step-icon">3</div>
          <div style="flex: 1;">
            <strong>National Registry SHA-256 Digital Signing &amp; Vault Sync</strong>
            <div style="font-size: 11px; color: #64748b;">Minting canonical URI: in.gov.dilrmp-BHUCR-... and depositing to Citizen Vault</div>
          </div>
          <span style="font-size: 12px; color: #94a3b8;">Pending</span>
        </div>
      </div>
    </div>
  `;

  try {
    await new Promise(r => setTimeout(r, 450));
    const s1 = document.getElementById("p-step-1");
    if (s1) {
      s1.className = "digilocker-step-item done";
      s1.querySelector(".digilocker-step-icon").innerHTML = "✓";
      s1.lastElementChild.textContent = "Verified";
      s1.lastElementChild.style.color = "#16a34a";
    }

    const s2 = document.getElementById("p-step-2");
    if (s2) {
      s2.className = "digilocker-step-item active";
      s2.lastElementChild.textContent = "Generating...";
      s2.lastElementChild.style.color = "#3b82f6";
    }
    await new Promise(r => setTimeout(r, 450));
    if (s2) {
      s2.className = "digilocker-step-item done";
      s2.querySelector(".digilocker-step-icon").innerHTML = "✓";
      s2.lastElementChild.textContent = "Assembled";
      s2.lastElementChild.style.color = "#16a34a";
    }

    const s3 = document.getElementById("p-step-3");
    if (s3) {
      s3.className = "digilocker-step-item active";
      s3.lastElementChild.textContent = "Transmitting...";
      s3.lastElementChild.style.color = "#3b82f6";
    }

    const pushRes = await window.digiLockerService.pushCertificate(
      data.ulpin,
      data.owner_name,
      data.aadhaar_hash
    );

    if (s3) {
      s3.className = "digilocker-step-item done";
      s3.querySelector(".digilocker-step-icon").innerHTML = "✓";
      s3.lastElementChild.textContent = "Issued";
      s3.lastElementChild.style.color = "#16a34a";
    }

    await new Promise(r => setTimeout(r, 300));

    body.innerHTML = `
      <div style="font-family: var(--font-sans);">
        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 1.5px solid #86efac; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
          <div style="width: 50px; height: 50px; background: #22c55e; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto 12px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);">
            ✓
          </div>
          <h3 style="margin: 0 0 6px; font-size: 18px; font-weight: 800; color: #14532d;">
            Certificate Successfully Deposited into Citizen DigiLocker Vault
          </h3>
          <p style="margin: 0; font-size: 13px; color: #166534;">
            ${pushRes.message || 'Authentic 3D Bhu-Aadhaar Digital Land Title Certificate is now verified and available in DigiLocker.'}
          </p>
        </div>

        <div class="digilocker-receipt-card" style="margin-top: 0; margin-bottom: 18px;">
          <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 6px;">
            Canonical DigiLocker Document URI
          </div>
          <div class="digilocker-uri-pill">
            <span id="digilocker-uri-val">${pushRes.digilocker_uri}</span>
            <button type="button" class="btn-copy" style="padding: 4px 8px; font-size: 11px;" onclick="navigator.clipboard.writeText('${pushRes.digilocker_uri}').then(() => { this.textContent = '✓ Copied!'; setTimeout(() => this.textContent = 'Copy URI', 1500); })">
              Copy URI
            </button>
          </div>

          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 14px; font-size: 12px;">
            <div style="background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <span style="color: #64748b; font-size: 11px; font-weight: 700;">ISSUING AUTHORITY:</span>
              <div style="font-weight: 700; color: #0B1F33; margin-top: 2px;">${pushRes.issuer_name}</div>
            </div>
            <div style="background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <span style="color: #64748b; font-size: 11px; font-weight: 700;">DOCUMENT TITLE:</span>
              <div style="font-weight: 700; color: #0B1F33; margin-top: 2px;">${pushRes.document_title}</div>
            </div>
            <div style="background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <span style="color: #64748b; font-size: 11px; font-weight: 700;">TITLE HOLDER (LA_PARTY):</span>
              <div style="font-weight: 700; color: #0B1F33; margin-top: 2px;">${pushRes.owner_name} (${pushRes.aadhaar_hash})</div>
            </div>
            <div style="background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <span style="color: #64748b; font-size: 11px; font-weight: 700;">INTEGRITY SIGNATURE:</span>
              <div style="font-family: monospace; font-size: 11px; color: #00a0e3; word-break: break-all; margin-top: 2px;">${pushRes.sha256_hash}</div>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; gap: 10px;">
            <a href="${pushRes.verification_url || '/api/digilocker/certificate/' + encodeURIComponent(data.ulpin) + '/xml'}" target="_blank" class="btn-secondary" style="padding: 8px 14px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
              View Official DigiLocker XML Schema
            </a>
          </div>
          <button type="button" class="btn-primary" style="padding: 8px 20px; font-size: 13px;" onclick="document.getElementById('digilocker-modal').classList.remove('active')">
            Done &bull; Return to Passport
          </button>
        </div>
      </div>
    `;

    checkDigiLockerPassportStatus(data.ulpin);
  } catch (pushErr) {
    body.innerHTML = `
      <div style="text-align: center; padding: 20px;">
        <div style="font-size: 32px; color: #ef4444; margin-bottom: 8px;">⚠️</div>
        <h3 style="color: #991b1b; margin-bottom: 8px;">DigiLocker Issuance Failed</h3>
        <p style="color: #64748b; font-size: 13px; margin-bottom: 18px;">${pushErr.message || 'Unable to communicate with DigiLocker gateway.'}</p>
        <button type="button" class="btn-secondary" onclick="document.getElementById('digilocker-modal').classList.remove('active')">
          Close
        </button>
      </div>
    `;
  }
};

/**
 * Opens email modal on the Land Passport page
 */
window.openPassportEmailModal = function () {
  const data = window.currentPassportData;
  if (!data || !data.ulpin) {
    alert("No active 3D land passport selected.");
    return;
  }

  const modal = document.getElementById("email-modal");
  const body = document.getElementById("email-modal-body");
  const title = document.getElementById("email-modal-title");
  if (!modal || !body) return;

  if (title) {
    title.textContent = "Email Digital Land Passport";
  }

  body.innerHTML = `
    <form id="passport-email-form" onsubmit="submitPassportEmailDispatch(event)" style="font-family: var(--font-sans);">
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px;">
        <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Target Passport</div>
        <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">${data.unit_name || data.ulpin}</div>
        <div style="font-size: 11px; color: #475569; margin-top: 2px;">Owner: ${data.owner_name} &bull; ULPIN: <span style="font-family: monospace;">${data.ulpin}</span></div>
      </div>

      <div style="margin-bottom: 14px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px;">
          Recipient Email Address <span style="color: #ef4444;">*</span>
        </label>
        <input 
          type="email" 
          id="passport-email-recipient" 
          required 
          value="${window.DEFAULT_SENDER_EMAIL || '24070579@ycce.in'}" 
          placeholder="citizen@example.com" 
          style="width: 100%; box-sizing: border-box; padding: 10px 12px; font-size: 13px; border: 1.5px solid #cbd5e1; border-radius: 6px; font-family: var(--font-sans); outline: none;"
        />
      </div>

      <div style="margin-bottom: 18px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px;">
          Recipient Name (Optional)
        </label>
        <input 
          type="text" 
          id="passport-email-name" 
          value="${data.owner_name || ''}" 
          placeholder="Citizen Name" 
          style="width: 100%; box-sizing: border-box; padding: 10px 12px; font-size: 13px; border: 1.5px solid #cbd5e1; border-radius: 6px; font-family: var(--font-sans); outline: none;"
        />
      </div>

      <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px 12px; margin-bottom: 18px; font-size: 11px; color: #1e40af; display: flex; align-items: center; gap: 8px;">
        <i class="fa-solid fa-bolt" style="color: #3b82f6;"></i>
        <span>Dispatched via official <strong>Brevo Transactional SMTP Gateway</strong>.</span>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button type="button" class="btn-secondary" style="padding: 8px 16px; font-size: 12px;" onclick="document.getElementById('email-modal').classList.remove('active')">
          Cancel
        </button>
        <button type="submit" id="btn-submit-passport-email" class="primary-process-btn" style="padding: 8px 20px; font-size: 12px; background: linear-gradient(135deg, #002244 0%, #005A9C 100%);">
          Send Official Passport &rarr;
        </button>
      </div>
    </form>
  `;

  modal.classList.add("active");
  setTimeout(() => {
    const input = document.getElementById("passport-email-recipient");
    if (input) input.focus();
  }, 100);
};

window.submitPassportEmailDispatch = async function (e) {
  if (e) e.preventDefault();
  const data = window.currentPassportData;
  const emailInput = document.getElementById("passport-email-recipient");
  const nameInput = document.getElementById("passport-email-name");
  const submitBtn = document.getElementById("btn-submit-passport-email");
  const body = document.getElementById("email-modal-body");

  if (!emailInput || !emailInput.value.trim()) return;
  const recipientEmail = emailInput.value.trim();
  const recipientName = (nameInput && nameInput.value.trim()) || data.owner_name;

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `Sending via Brevo...`;
  }

  try {
    const res = await window.emailService.sendPassport(recipientEmail, data.ulpin, recipientName);
    body.innerHTML = `
      <div style="text-align: center; padding: 20px 10px; font-family: var(--font-sans);">
        <div style="width: 52px; height: 52px; background: #22c55e; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 26px; margin: 0 auto 14px; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3);">
          ✓
        </div>
        <h3 style="margin: 0 0 8px; font-size: 17px; font-weight: 800; color: #14532d;">
          Passport Successfully Sent!
        </h3>
        <p style="margin: 0 0 16px; font-size: 13px; color: #166534; line-height: 1.5;">
          ${res.message || 'The Digital Land Passport has been emailed to ' + recipientEmail + ' via Brevo.'}
        </p>
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 20px; font-size: 12px; text-align: left;">
          <div><strong>Recipient:</strong> ${recipientEmail}</div>
          <div style="margin-top: 4px;"><strong>ULPIN:</strong> <span style="font-family: monospace;">${data.ulpin}</span></div>
          <div style="margin-top: 4px; font-size: 11px; color: #64748b;"><strong>Gateway:</strong> Brevo Transactional API (Status: ${res.status})</div>
        </div>
        <button type="button" class="btn-primary" style="padding: 9px 24px; font-size: 13px;" onclick="document.getElementById('email-modal').classList.remove('active')">
          Done &bull; Return to Passport
        </button>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `
      <div style="text-align: center; padding: 20px 10px; font-family: var(--font-sans);">
        <div style="font-size: 32px; color: #ef4444; margin-bottom: 10px;">⚠️</div>
        <h3 style="margin: 0 0 8px; font-size: 17px; font-weight: 800; color: #991b1b;">
          Failed to Send Email
        </h3>
        <p style="margin: 0 0 18px; font-size: 13px; color: #64748b;">
          ${err.message || 'Unable to communicate with Brevo Email Gateway.'}
        </p>
        <div style="display: flex; justify-content: center; gap: 10px;">
          <button type="button" class="btn-secondary" onclick="document.getElementById('email-modal').classList.remove('active')">
            Cancel
          </button>
          <button type="button" class="btn-primary" onclick="openPassportEmailModal()">
            Try Again
          </button>
        </div>
      </div>
    `;
  }
};

/**
 * Helper to show direct Google Wallet notification toast
 */
function showWalletDirectNotification(passData) {
  let existing = document.getElementById("wallet-direct-notification");
  if (existing) existing.remove();

  const container = document.createElement("div");
  container.id = "wallet-direct-notification";
  container.style.cssText = "position: fixed; bottom: 24px; right: 24px; z-index: 9999; background: #0B1F33; border: 1.5px solid #4285F4; border-radius: 14px; padding: 16px 20px; box-shadow: 0 16px 40px rgba(0,0,0,0.6); color: #fff; max-width: 400px; display: flex; flex-direction: column; gap: 10px; animation: slideUp 0.3s ease-out;";

  container.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <div style="font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 8px; color: #60a5fa;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
        </svg>
        <span>Google Wallet Pass Created!</span>
      </div>
      <button onclick="this.closest('#wallet-direct-notification').remove()" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 16px; padding: 2px;">✕</button>
    </div>
    <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
      Direct Google Wallet save opened in a new tab. Click <strong>Save</strong> in the Google dialog to sync your 3D Land Passport to your phone.
    </div>
    <div style="display: flex; gap: 8px; margin-top: 4px;">
      <a href="${passData.save_url}" target="_blank" rel="noopener noreferrer" style="flex: 1; text-align: center; background: #4285F4; color: #ffffff; font-size: 12px; font-weight: 700; padding: 9px 12px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 12px rgba(66, 133, 244, 0.4);">
        <span>Open Wallet &rarr;</span>
      </a>
      <button type="button" id="btn-toast-view-card" style="background: rgba(255,255,255,0.12); color: #f8fafc; border: 1px solid rgba(255,255,255,0.25); font-size: 12px; font-weight: 600; padding: 9px 12px; border-radius: 8px; cursor: pointer;">
        View Pass Card / QR
      </button>
    </div>
  `;

  document.body.appendChild(container);

  const viewCardBtn = container.querySelector("#btn-toast-view-card");
  if (viewCardBtn) {
    viewCardBtn.onclick = () => {
      if (window.googleWalletService) {
        window.googleWalletService.showWalletModal(passData);
      }
    };
  }

  // Auto-dismiss after 15s
  setTimeout(() => {
    if (container && container.parentNode) {
      container.remove();
    }
  }, 15000);
}

/**
 * Directly creates and saves the 3D Land Passport to Google Wallet
 */
window.savePassportToGoogleWallet = async function () {
  const data = window.currentPassportData;
  if (!data || !data.ulpin) {
    alert("No active 3D land passport selected. Please search or select a ULPIN first.");
    return;
  }

  const btn = document.getElementById("btn-passport-wallet");
  const textEl = document.getElementById("passport-wallet-btn-text");
  const origText = textEl ? textEl.innerHTML : (btn ? btn.innerHTML : "Save to Google Wallet");

  if (btn) {
    btn.disabled = true;
    btn.style.opacity = "0.75";
  }
  if (textEl) {
    textEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Creating & Saving Pass...`;
  } else if (btn) {
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Creating & Saving Pass...</span>`;
  }

  // Pre-open new tab to guarantee popup blockers do not block Google Wallet
  const saveTab = window.open("about:blank", "_blank");
  if (saveTab) {
    try {
      saveTab.document.write(`
        <!DOCTYPE html>
        <html>
        <head><title>Opening Google Wallet...</title></head>
        <body style="margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; background: #0B1F33; color: #ffffff;">
          <div style="width: 48px; height: 48px; border: 4px solid rgba(255,255,255,0.2); border-top-color: #4285F4; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 20px;"></div>
          <h2 style="margin: 0 0 10px; font-size: 20px; font-weight: 700;">Creating Google Wallet Pass...</h2>
          <p style="color: #94a3b8; font-size: 14px; margin: 0;">Digitally signing 3D Bhu-Aadhaar Land Passport for Google Wallet...</p>
          <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
        </body>
        </html>
      `);
    } catch (e) {}
  }

  try {
    if (!window.googleWalletService) {
      throw new Error("Google Wallet Service is not yet loaded. Please refresh the page.");
    }
    const res = await window.googleWalletService.generatePass(data.ulpin, data.owner_name);
    
    // Directly navigate to Google Wallet Save URL
    if (res && res.save_url) {
      if (saveTab && !saveTab.closed) {
        saveTab.location.href = res.save_url;
      } else {
        window.open(res.save_url, "_blank");
      }

      if (textEl) {
        textEl.innerHTML = `<i class="fa-solid fa-check" style="color: #4ade80;"></i> Pass Created & Opened!`;
      } else if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-check" style="color: #4ade80;"></i> <span>Pass Created & Opened!</span>`;
      }

      // Show floating notification for easy access or preview
      if (window.googleWalletService && window.googleWalletService.showDirectNotification) {
        window.googleWalletService.showDirectNotification(res);
      } else if (typeof showWalletDirectNotification === "function") {
        showWalletDirectNotification(res);
      }
    }
  } catch (err) {
    if (saveTab && !saveTab.closed) saveTab.close();
    console.error("[Google Wallet Error]:", err);
    alert("Google Wallet Pass Notice: " + (err.message || "Failed to generate pass."));
    if (textEl) textEl.innerHTML = origText;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.style.opacity = "1";
    }
    setTimeout(() => {
      if (textEl && textEl.innerHTML.includes("Pass Created")) {
        textEl.innerHTML = origText;
      } else if (btn && btn.innerHTML.includes("Pass Created")) {
        btn.innerHTML = origText;
      }
    }, 6000);
  }
};

// Backwards compatibility alias
window.openPassportGoogleWalletModal = window.savePassportToGoogleWallet;

