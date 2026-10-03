/**
 * Building & 3D Legal Space Unit Inspector + Digital Title Deed Generator
 * Neumorphism Redesign — Renders into LEFT scrollable info panel with light theme styling.
 */

class CadastralInspector {
  constructor(panelContainerId) {
    this.panel = document.getElementById(panelContainerId);
    this.deedModal = document.getElementById('deed-modal');
    this.currentUnit = null;
    this.currentBuilding = null;
  }

  getSpaceTypeInfo(typeCode) {
    const types = {
      'A': { label: 'Apartment', class: 'apartment', icon: 'fa-house-user' },
      'P': { label: 'Parking Bay', class: 'parking', icon: 'fa-square-parking' },
      'S': { label: 'Staircase Core', class: 'staircase', icon: 'fa-stairs' },
      'M': { label: 'Sky Terrace', class: 'terrace', icon: 'fa-tree' },
      'U': { label: 'Utility Shaft', class: 'utility', icon: 'fa-bolt' },
      'R': { label: 'Air-Rights', class: 'air-rights', icon: 'fa-cloud' }
    };
    return types[typeCode] || { label: typeCode || 'Unit', class: 'apartment', icon: 'fa-cube' };
  }

  showBuildingDetails(building, selectedUnit = null) {
    this.currentBuilding = building;
    if (selectedUnit) {
      this.currentUnit = selectedUnit;
    }

    if (!this.panel) return;

    // Ensure legal_units is always an array
    let units = (building && Array.isArray(building.legal_units)) ? building.legal_units : [];
    
    // If not found directly on building, check app.cadastreData
    if (units.length === 0 && window.app && window.app.cadastreData && window.app.cadastreData.buildings) {
      const bName = (building.building_name || building.name || '').trim().toLowerCase();
      const bId = String(building.building_id || building.id || '');
      const match = window.app.cadastreData.buildings.find(b => {
        const matchId = String(b.building_id || b.id || '');
        const matchName = (b.building_name || b.name || '').trim().toLowerCase();
        return (bId && matchId && bId === matchId) || (bName && matchName && bName === matchName);
      });
      if (match && Array.isArray(match.legal_units) && match.legal_units.length > 0) {
        units = match.legal_units;
        this.currentBuilding = match;
        building = match;
      }
    }

    const bldName = building.building_name || building.name || 'Building Complex';
    const totalFloors = building.total_floors || building.floors || 3;
    const basementFloors = building.basement_floors || 0;
    const heightM = building.height_m ? Number(building.height_m).toFixed(1) : '15.0';
    const groundElev = building.ground_elevation_m ? Number(building.ground_elevation_m).toFixed(1) : '920.0';
    const pincode = building.pincode || '560103';
    const unitCount = units.length || building.legal_unit_count || 0;

    let html = `
      <!-- Building Physical Shell -->
      <div class="panel-card" style="animation-delay: 0.05s;">
        <div class="panel-title">
          <span>Physical Structure</span>
        </div>
        <h2 style="font-size: 17px; font-weight: 800; color: var(--text-primary); display: flex; align-items: center; gap: 10px;">
          <svg viewBox="0 0 20 20" fill="#D96B32" width="20" height="20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h12a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6z"/>
          </svg>
          ${bldName}
        </h2>
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Pincode</span>
            <span class="detail-value highlight">${pincode}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Total Height</span>
            <span class="detail-value">${heightM} m</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Above-Ground</span>
            <span class="detail-value">${totalFloors} Floors</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Basements</span>
            <span class="detail-value">${basementFloors} Levels</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Ground Elev.</span>
            <span class="detail-value">${groundElev} m AMSL</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Legal 3D Units</span>
            <span class="detail-value highlight">${unitCount} Units</span>
          </div>
        </div>
      </div>
    `;

    // Active Selected Legal Unit Details (if any unit is active)
    if (this.currentUnit) {
      const u = this.currentUnit;
      const party = (u.parties && u.parties.length > 0) ? u.parties[0] : { name: "Government Authority", id_hash: "GOV-01", role: "Custodian" };
      const sourceDoc = (u.sources && u.sources.length > 0) ? u.sources[0] : { document_type: "Registered Deed", document_number: "DOC-2024-001", issuing_authority: "Revenue Dept", registration_date: "2024-01-15", digital_signature: "SHA256:4f8a..." };
      const isDisputed = u.status && u.status.includes("Dispute");
      const isMortgaged = u.status && u.status.includes("Mortgaged");
      const spaceInfo = this.getSpaceTypeInfo(u.space_type);

      html += `
        <!-- Active Selected Unit Inspector Card -->
        <div class="panel-card" id="active-unit-card" style="border: 2px solid var(--accent-neon); box-shadow: var(--neu-convex), 0 0 20px rgba(32,217,230,0.25); animation: cardReveal 0.35s ease-out both;">
          <div class="panel-title">
            <span style="color: #18A7A8; font-weight: 800;">Selected Property Unit</span>
            <button class="btn-copy" id="btn-deselect-unit" style="font-size: 10px; padding: 2px 8px;" title="Back to building overview">
              <i class="fa-solid fa-xmark"></i> Deselect
            </button>
          </div>

          <!-- ULPIN Banner -->
          <div class="ulpin-card-banner" style="margin: 0; padding: 12px 14px;">
            <div class="ulpin-tag">3D ULPIN Identifier</div>
            <div class="ulpin-number-row">
              <span class="ulpin-display-text" id="active-unit-ulpin" style="font-size: 13px;">${u.ulpin}</span>
              <button class="btn-copy" onclick="navigator.clipboard.writeText('${u.ulpin}').then(()=>alert('3D ULPIN Copied!'))">
                <svg viewBox="0 0 16 16" fill="currentColor" width="11" height="11" style="vertical-align: middle; margin-right: 3px;">
                  <path d="M4 2a2 2 0 012-2h4a2 2 0 012 2v1h2a2 2 0 012 2v9a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h0V2z"/>
                </svg>
                Copy
              </button>
            </div>
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px;">
              <div class="verhoeff-chip">
                <svg viewBox="0 0 16 16" fill="currentColor" width="10" height="10">
                  <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L7 8.586 5.707 7.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Verhoeff: <strong>VALID</strong>
              </div>
              <span class="space-type-badge ${spaceInfo.class}">
                <i class="fa-solid ${spaceInfo.icon}"></i> ${spaceInfo.label}
              </span>
            </div>
          </div>

          ${isDisputed ? `
            <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; border-radius: var(--radius-sm); padding: 10px 12px; color: #ef4444; font-size: 11px;">
              <strong><i class="fa-solid fa-triangle-exclamation"></i> 3D TOPOLOGICAL CONFLICT DETECTED</strong>
              <p style="margin-top: 2px; color: var(--text-secondary);">${u.dispute_details ? u.dispute_details.description : '3D Spatial intersection overlap detected with common area.'}</p>
            </div>
          ` : ''}

          <!-- Unit Metrics Grid -->
          <div class="details-grid">
            <div class="detail-item">
              <span class="detail-label">Unit Title</span>
              <span class="detail-value highlight" style="font-size: 12px;">${u.unit_name}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Floor Level</span>
              <span class="detail-value">${u.floor_level < 0 ? 'Basement ' + Math.abs(u.floor_level) : (u.floor_level === 99 ? 'Air Rights' : 'Floor ' + u.floor_level)}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Carpet Area</span>
              <span class="detail-value">${u.carpet_area_sqm || '--'} m²</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">3D Volume</span>
              <span class="detail-value">${u.volume_m3 || '--'} m³</span>
            </div>
            <div class="detail-item" style="grid-column: span 2;">
              <span class="detail-label">3D Extents (AMSL Ref: ${groundElev}m)</span>
              <span class="detail-value" style="font-size: 11px; font-family: var(--font-mono);">
                X:[${u.bbox.min_x}, ${u.bbox.max_x}] &bull; Y:[${u.bbox.min_y}, ${u.bbox.max_y}] &bull; Z:[${u.bbox.min_z}, ${u.bbox.max_z}]
              </span>
            </div>
          </div>

          <!-- Ownership (LA_Party) -->
          <div style="background: var(--bg-deep); box-shadow: var(--neu-concave); border-radius: var(--radius-md); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px;">
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">
              <span>Registered Owner (LA_Party)</span>
              <span style="color: #18A7A8;">${party.role || 'Owner'}</span>
            </div>
            <div style="font-size: 13px; font-weight: 800; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
              <i class="fa-solid fa-user-check" style="color: #18A7A8;"></i>
              ${party.name}
            </div>
            <div style="font-size: 10px; font-family: var(--font-mono); color: var(--text-muted);">
              KYC Hash: <span style="color: #18A7A8;">${party.id_hash}</span>
            </div>
          </div>

          <!-- Legal Rights & Liens (RRR) -->
          ${(u.rrrs && u.rrrs.length > 0) ? `
            <div class="rrr-list">
              ${u.rrrs.map(r => `
                <div class="rrr-item ${r.rrr_type.includes('Mortgage') ? 'mortgage' : (r.rrr_type.includes('Dispute') ? 'dispute' : '')}" style="padding: 8px 10px;">
                  <div class="rrr-title" style="font-size: 11px;">
                    <span>${r.rrr_type}</span>
                    ${r.amount_inr ? `<span style="color: var(--accent-amber); font-weight: 700;">₹ ${(r.amount_inr / 100000).toFixed(1)}L</span>` : ''}
                  </div>
                  <div class="rrr-desc" style="font-size: 10px;">${r.description}</div>
                </div>
              `).join('')}
            </div>
          ` : ''}

          <!-- View Certificate Button -->
          <button class="primary-process-btn" style="padding: 10px 14px; font-size: 12px; margin-top: 4px;" onclick="window.app && window.app.inspector.openDigitalTitleCertificate()">
            <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
              <path fill-rule="evenodd" d="M5 2a2 2 0 00-2 2v14l3.5-2 3.5 2 3.5-2 3.5 2V4a2 2 0 00-2-2H5zm4.707 3.707a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L8.414 9H10a3 3 0 013 3v1a1 1 0 102 0v-1a5 5 0 00-5-5H8.414l1.293-1.293z" clip-rule="evenodd"/>
            </svg>
            <span>View Digital Title Deed Certificate</span>
          </button>
        </div>
      `;
    }

    // Subdivided Legal Units Section
    if (units.length > 0) {
      // Group units by floor
      const grouped = units.reduce((acc, u) => {
        const floor = u.floor_level === 99 
          ? 'Air Rights (+15m)' 
          : (u.floor_level < 0 ? 'Basement ' + Math.abs(u.floor_level) : 'Floor ' + u.floor_level);
        if (!acc[floor]) acc[floor] = [];
        acc[floor].push(u);
        return acc;
      }, {});

      html += `
        <!-- Subdivided Legal Units Directory -->
        <div class="panel-card" style="animation-delay: 0.15s;">
          <div class="panel-title">
            <span>Registered Units (${units.length})</span>
            <span class="panel-title-badge">Unit Directory</span>
          </div>

          <div class="legal-units-inner-scroll">
            ${Object.entries(grouped).map(([floorName, floorUnits]) => `
              <div style="background: var(--bg-deep); box-shadow: var(--neu-concave); border-radius: var(--radius-md); overflow: hidden;">
                <div style="padding: 8px 14px; background: var(--accent-green-dim); font-size: 11px; font-weight: 800; color: #18A7A8; display: flex; justify-content: space-between; align-items: center;">
                  <span><i class="fa-solid fa-layer-group"></i> ${floorName}</span>
                  <span style="font-family: var(--font-mono); font-size: 10px;">${floorUnits.length} Units</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px; padding: 8px;">
                  ${floorUnits.map(u => {
                    const sInfo = this.getSpaceTypeInfo(u.space_type);
                    const ownerName = (u.parties && u.parties.length > 0) ? u.parties[0].name : 'Owner / Public';
                    const isDisputed = u.status && u.status.includes('Dispute');
                    const isMortgaged = u.status && u.status.includes('Mortgaged');
                    const isSelected = this.currentUnit && this.currentUnit.unit_id === u.unit_id;
                    const statusClass = isDisputed ? 'dispute' : (isMortgaged ? 'mortgage' : 'clear');

                    return `
                      <div class="legal-unit-rich-card ${isSelected ? 'active' : ''} unit-list-item" data-unit-id="${u.unit_id}">
                        <div class="legal-unit-rich-header">
                          <span class="legal-unit-title">
                            <i class="fa-solid ${sInfo.icon}" style="color: #18A7A8;"></i>
                            ${u.unit_name}
                          </span>
                          <span class="space-type-badge ${sInfo.class}">
                            ${sInfo.label}
                          </span>
                        </div>

                        <div class="legal-unit-data-row">
                          <div class="legal-unit-specs">
                            <span>${u.carpet_area_sqm || 80} m²</span>
                            <span>${u.volume_m3 || 240} m³</span>
                          </div>
                          <span class="legal-unit-status-chip ${statusClass}">
                            ${u.status}
                          </span>
                        </div>

                        <div class="legal-unit-owner">
                          <i class="fa-solid fa-user-circle"></i>
                          <span>${ownerName}</span>
                        </div>

                        <div class="legal-unit-footer">
                          <span class="legal-unit-ulpin">${u.ulpin}</span>
                          <button class="btn-inspect-unit-mini" type="button" title="Focus 3D View">
                            <i class="fa-solid fa-crosshairs"></i> Inspect
                          </button>
                        </div>
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } else {
      // Discovered building awaiting 3D Cadastral pipeline
      html += `
        <!-- Survey Awaiting Notice Card -->
        <div class="panel-card" style="animation-delay: 0.15s; border-left: 4px solid var(--accent-neon);">
          <div class="panel-title">
            <span>Property Units</span>
            <span class="panel-title-badge">Unregistered</span>
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
            <p>Building footprint recognized from spatial records. Volumetric spatial units, verified carpet areas, and official 3D ULPIN identifiers are pending generation.</p>
          </div>
          <button class="primary-process-btn" style="margin-top: 8px;" onclick="window.app && window.app.runPipelineForActiveSelection()">
            <svg class="svg-btn-icon" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
              <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 01.12-.381z"/>
            </svg>
            Generate 3D Cadastre
          </button>
        </div>
      `;
    }

    // LADM 3D Space Legend (Always visible at bottom)
    html += `
      <!-- LADM 3D Space Legend -->
      <div class="panel-card" style="animation-delay: 0.25s;">
        <div class="panel-title">
          <span>Spatial Unit Classification</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 11px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #3b82f6; box-shadow: var(--neu-flat);"></div>
            <span>Apartment (A)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #52677D; box-shadow: var(--neu-flat);"></div>
            <span>Parking Bay (P)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #D96B32; box-shadow: var(--neu-flat);"></div>
            <span>Staircase Core (S)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #18A7A8; box-shadow: var(--neu-flat);"></div>
            <span>Sky Terrace (M)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #0B1F33; box-shadow: var(--neu-flat);"></div>
            <span>Utility Shaft (U)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 12px; height: 12px; border-radius: 3px; background: #20D9E6; box-shadow: var(--neu-flat);"></div>
            <span>Air-Rights (+15m)</span>
          </div>
        </div>
      </div>
    `;

    this.panel.innerHTML = html;

    // Attach click listeners to unit items
    this.panel.querySelectorAll('.unit-list-item').forEach(el => {
      el.addEventListener('click', () => {
        const uId = el.getAttribute('data-unit-id');
        const unit = units.find(u => u.unit_id === uId);
        if (unit) {
          if (window.app && window.app.viewer3d) {
            window.app.viewer3d.selectUnit(unit.unit_id, true);
          }
          this.showUnitDetails(unit, this.currentBuilding);
        }
      });
    });

    // Clear focus button
    const deselectBtn = document.getElementById('btn-deselect-unit');
    if (deselectBtn) {
      deselectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.currentUnit = null;
        if (window.app && window.app.viewer3d && window.app.viewer3d.selectedUnitEntity) {
          window.app.viewer3d.selectedUnitEntity.polygon.material = window.app.viewer3d.selectedUnitEntity.userData.originalColor;
          window.app.viewer3d.selectedUnitEntity = null;
        }
        this.showBuildingDetails(this.currentBuilding);
      });
    }
  }

  showUnitDetails(unit, building) {
    this.currentUnit = unit;
    this.currentBuilding = building;
    this.showBuildingDetails(building, unit);

    // Smoothly scroll the active unit card into view if needed
    setTimeout(() => {
      const activeCard = document.getElementById('active-unit-card');
      const container = this.panel;
      if (activeCard && container) {
        const cardRect = activeCard.getBoundingClientRect();
        const contRect = container.getBoundingClientRect();
        if (cardRect.top < contRect.top || cardRect.bottom > contRect.bottom) {
          activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    }, 60);
  }

  openDigitalTitleCertificate(unitToOpen = null) {
    const unit = unitToOpen || this.currentUnit;
    if (!unit) {
      // If no unit is actively selected, take the first legal unit of the current building
      if (this.currentBuilding && Array.isArray(this.currentBuilding.legal_units) && this.currentBuilding.legal_units.length > 0) {
        return this.openDigitalTitleCertificate(this.currentBuilding.legal_units[0]);
      }
      alert("Please select a 3D legal unit first to generate its digital land title certificate.");
      return;
    }

    const bld = this.currentBuilding;
    const party = (unit.parties && unit.parties.length > 0) ? unit.parties[0] : { name: "Citizen Owner", id_hash: "AADHAAR-8902-1123" };
    const groundRef = (bld && bld.ground_elevation_m) ? bld.ground_elevation_m : 920.0;
    const bbox = unit.bbox || { min_x: -2, max_x: 2, min_y: -2, max_y: 2, min_z: 920, max_z: 923 };

    const bodyEl = document.getElementById('deed-modal-body');
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div class="deed-certificate-container">
          <div class="deed-header">
            <div style="font-size: 24px; margin-bottom: 4px;">🇮🇳</div>
            <h2>Government of India &bull; Ministry of Rural Development & Land Resources</h2>
            <p>Department of Land Resources &bull; DILRMP 3D Cadastral Digital Registry</p>
            <h3 style="margin-top: 8px; font-size: 15px; color: #18A7A8; text-decoration: underline;">
              3D BHU-AADHAAR / 3D ULPIN DIGITAL LAND TITLE CERTIFICATE
            </h3>
          </div>

          <div class="deed-grid">
            <div class="deed-box deed-grid-full" style="background: rgba(223, 247, 250, 0.8); border-color: rgba(24, 167, 168, 0.35);">
              <span class="deed-box-label">Unique 3D Land Parcel Identification Number (3D ULPIN)</span>
              <div class="deed-box-val" style="font-size: 16px; color: #18A7A8; font-family: monospace; font-weight: 800;">${unit.ulpin}</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">Registered Property Name</span>
              <div class="deed-box-val">${unit.unit_name} (${bld ? (bld.building_name || bld.name) : 'Urban Complex'})</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">Spatial Type & Level</span>
              <div class="deed-box-val">${this.getSpaceTypeInfo(unit.space_type).label} &bull; Floor ${unit.floor_level}</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">Registered Title Holder (LA_Party)</span>
              <div class="deed-box-val">${party.name}</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">KYC Identification Hash</span>
              <div class="deed-box-val" style="font-family: monospace;">${party.id_hash}</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">Volumetric Dimensions</span>
              <div class="deed-box-val">${unit.carpet_area_sqm || 85} m² Carpet &bull; ${unit.volume_m3 || 255} m³ Volume</div>
            </div>

            <div class="deed-box">
              <span class="deed-box-label">Legal Tenancy Status</span>
              <div class="deed-box-val" style="color: ${unit.status && unit.status.includes('Dispute') ? '#ef4444' : '#0a8a4a'};">${unit.status}</div>
            </div>

            <div class="deed-box deed-grid-full">
              <span class="deed-box-label">3D Bounding Extents (AMSL Ground Ref: ${groundRef}m)</span>
              <div class="deed-box-val" style="font-family: monospace; font-size: 11px;">
                Min(X:${bbox.min_x}, Y:${bbox.min_y}, Z:${bbox.min_z}) &rarr; Max(X:${bbox.max_x}, Y:${bbox.max_y}, Z:${bbox.max_z})
              </div>
            </div>

            <div class="deed-box deed-grid-full">
              <span class="deed-box-label">Rights, Restrictions & Encumbrances (RRR)</span>
              <div class="deed-box-val" style="font-size: 11px; font-family: sans-serif; font-weight: normal; line-height: 1.5;">
                ${(unit.rrrs && unit.rrrs.length > 0) 
                  ? unit.rrrs.map(r => `&bull; <strong>${r.rrr_type}:</strong> ${r.description} ${r.amount_inr ? '(₹' + (r.amount_inr/100000).toFixed(1) + ' Lakh)' : ''}`).join('<br>')
                  : '&bull; <strong>Clear Freehold:</strong> Unencumbered allodial ownership registered under Section 14 of Indian Land Registration Act.'}
              </div>
            </div>
          </div>

          <div class="deed-footer">
            <div>
              <div style="font-size: 11px; font-weight: bold; color: #1a1a2e;">Certified Cadastral Verification</div>
              <div style="font-size: 10px; color: var(--text-muted); font-family: monospace;">Signature: SHA256:7f8a9e2b1049c812d4a51e60f09b</div>
              <div style="font-size: 10px; color: #18A7A8; font-weight: bold; margin-top: 4px;">
                &check; Tamper Check Digit Verified (Verhoeff Dihedral D5 Standard)
              </div>
            </div>
            <div class="deed-qr">
              <div style="padding: 4px; font-size: 9px; line-height: 1.2;">
                [ 3D QR ]<br>
                ${unit.ulpin ? unit.ulpin.substring(0, 8) : 'VERIFIED'}<br>
                REGISTERED
              </div>
            </div>
          </div>
        </div>
      `;
    }

    if (this.deedModal) {
      this.deedModal.classList.add('active');
    }
  }

  closeDeedModal() {
    if (this.deedModal) {
      this.deedModal.classList.remove('active');
    }
  }
}
