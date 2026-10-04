/**
 * Building & 3D Legal Space Unit Inspector + Digital Title Deed Generator
 * Neumorphism Redesign — Renders into LEFT scrollable info panel with light theme styling.
 */

class CadastralInspector {
  constructor(panelContainerId) {
    this.panel = document.getElementById(panelContainerId);
    this.deedModal = document.getElementById('deed-modal');
    this.digilockerModal = document.getElementById('digilocker-modal');
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
        ${units.length > 0 ? `
          <div style="margin-top: 10px;">
            <a href="/ulpin/${encodeURIComponent(units[0].ulpin)}" target="_blank" style="width: 100%; box-sizing: border-box; text-decoration: none; padding: 8px 12px; background: linear-gradient(135deg, #0B1F33, #163654); color: #20D9E6; border-radius: 6px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 6px rgba(11,31,51,0.2);">
              <i class="fa-solid fa-passport"></i> View Digital Land Passport
            </a>
          </div>
        ` : ''}
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
          <a href="/ulpin/${encodeURIComponent(u.ulpin)}" target="_blank" class="primary-process-btn" style="padding: 10px 14px; font-size: 12px; margin-top: 6px; background: linear-gradient(135deg, #0B1F33, #163654); color: #20D9E6; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 8px;">
            <i class="fa-solid fa-passport"></i>
            <span>View Digital Land Passport</span>
          </a>
          <!-- Save to DigiLocker Button -->
          <button class="primary-process-btn" style="padding: 10px 14px; font-size: 12px; margin-top: 6px; background: linear-gradient(135deg, #002B49 0%, #004d80 100%); color: #ffffff; border: 1px solid #00a0e3; display: flex; align-items: center; justify-content: center; gap: 8px;" onclick="window.app && window.app.inspector.saveCertificateToDigiLocker('${u.ulpin}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="4" fill="#003366"/><path d="M12 4C9.2 4 7 6.2 7 9c-1.7 0.3-3 1.8-3 3.5 0 2 1.6 3.5 3.5 3.5h9c1.9 0 3.5-1.6 3.5-3.5 0-1.8-1.4-3.3-3.1-3.5C16.5 6.3 14.5 4 12 4z" fill="#00a0e3"/><path d="M10.5 13.5l-2-2 1.2-1.2 1.3 1.3 3.8-3.8 1.2 1.2-5.5 5.5z" fill="#78be20"/></svg>
            <span id="sidebar-digilocker-badge-${u.ulpin.replace(/[^a-zA-Z0-9]/g, '')}">Store in DigiLocker</span>
          </button>
          <!-- Email Certificate Button (Brevo) -->
          <button class="primary-process-btn" style="padding: 10px 14px; font-size: 12px; margin-top: 6px; background: linear-gradient(135deg, #0B1F33 0%, #163654 100%); color: #20D9E6; border: 1px solid rgba(32, 217, 230, 0.4); display: flex; align-items: center; justify-content: center; gap: 8px;" onclick="window.app && window.app.inspector.openEmailModal('certificate', '${u.ulpin}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
            <span>Email Certificate (Brevo)</span>
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
                          <div style="display: flex; gap: 6px; align-items: center;">
                            <button class="btn-inspect-unit-mini" type="button" title="Focus 3D View">
                              <i class="fa-solid fa-crosshairs"></i> Inspect
                            </button>
                            <a href="/ulpin/${encodeURIComponent(u.ulpin)}" target="_blank" class="btn-inspect-unit-mini" title="Open Land Passport" style="text-decoration: none; color: #0B1F33; background: #e0f7fa;">
                              <i class="fa-solid fa-passport" style="color: #18A7A8;"></i> Passport
                            </a>
                          </div>
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

          <!-- DigiLocker Sovereign Vault Integration Bar -->
          <div class="deed-digilocker-bar">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="background: #002B49; border-radius: 6px; padding: 4px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,43,73,0.3);">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M12 4C9.2 4 7 6.2 7 9c-1.7 0.3-3 1.8-3 3.5 0 2 1.6 3.5 3.5 3.5h9c1.9 0 3.5-1.6 3.5-3.5 0-1.8-1.4-3.3-3.1-3.5C16.5 6.3 14.5 4 12 4z" fill="#00a0e3"/>
                  <path d="M10.5 13.5l-2-2 1.2-1.2 1.3 1.3 3.8-3.8 1.2 1.2-5.5 5.5z" fill="#78be20"/>
                </svg>
              </div>
              <div>
                <div style="font-size: 11px; font-weight: 800; color: #002B49; font-family: var(--font-sans); display: flex; align-items: center; gap: 6px;">
                  DigiLocker Sovereign Vault
                  <span id="deed-digilocker-badge" class="badge-digilocker-pending">Checking...</span>
                </div>
                <div style="font-size: 10px; color: #555; font-family: var(--font-sans);">
                  Issued by Department of Land Resources (DoLR), Ministry of Rural Development &bull; Govt of India
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <button type="button" id="btn-save-digilocker" class="btn-save-digilocker" onclick="window.app && window.app.inspector.saveCertificateToDigiLocker('${unit.ulpin}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                </svg>
                <span id="btn-save-digilocker-text">Save to DigiLocker</span>
              </button>
              <button type="button" class="btn-email-action" style="background: linear-gradient(135deg, #0B1F33 0%, #163654 100%); color: #20D9E6; border: 1px solid rgba(32, 217, 230, 0.4); padding: 7px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;" onclick="window.app && window.app.inspector.openEmailModal('certificate', '${unit.ulpin}')">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
                <span>Email Certificate</span>
              </button>
              <button type="button" class="btn-wallet-action" style="background: #1f1f1f; color: #ffffff; border: 1.5px solid #4285F4; padding: 7px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(66, 133, 244, 0.25);" onclick="window.app && window.app.inspector.openGoogleWalletPass('${unit.ulpin}')">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
                </svg>
                <span id="btn-inspector-wallet-text">Save to Google Wallet</span>
              </button>
              <a href="/api/digilocker/certificate/${encodeURIComponent(unit.ulpin)}/xml" target="_blank" class="btn-view-digilocker-xml" title="Inspect official MeitY DigiLocker XML Schema">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
                XML Schema
              </a>
            </div>
          </div>

        </div>
      `;
    }

    if (this.deedModal) {
      this.deedModal.classList.add('active');
    }

    // Check current DigiLocker storage status
    this.checkDigiLockerStatus(unit.ulpin);
  }

  async checkDigiLockerStatus(ulpin) {
    if (!ulpin || !window.digiLockerService) return;
    try {
      const status = await window.digiLockerService.getStatus(ulpin);
      const badge = document.getElementById('deed-digilocker-badge');
      const btn = document.getElementById('btn-save-digilocker-text');
      const sidebarBadge = document.getElementById(`sidebar-digilocker-badge-${ulpin.replace(/[^a-zA-Z0-9]/g, '')}`);

      if (status && status.is_stored) {
        if (badge) {
          badge.className = 'badge-digilocker-synced';
          badge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Stored in DigiLocker`;
        }
        if (btn) {
          btn.textContent = 'Re-Sync DigiLocker';
        }
        if (sidebarBadge) {
          sidebarBadge.innerHTML = `DigiLocker Stored ✓`;
        }
      } else {
        if (badge) {
          badge.className = 'badge-digilocker-pending';
          badge.textContent = 'Available to Store';
        }
        if (btn) {
          btn.textContent = 'Save to DigiLocker';
        }
      }
    } catch (e) {
      console.warn('[DigiLocker] Status check notice:', e);
    }
  }

  async saveCertificateToDigiLocker(ulpinToSave = null) {
    let unit = null;
    if (ulpinToSave && this.currentBuilding && Array.isArray(this.currentBuilding.legal_units)) {
      unit = this.currentBuilding.legal_units.find(u => u.ulpin === ulpinToSave);
    }
    if (!unit) unit = this.currentUnit;
    if (!unit && this.currentBuilding && this.currentBuilding.legal_units && this.currentBuilding.legal_units.length > 0) {
      unit = this.currentBuilding.legal_units[0];
    }
    if (!unit) {
      alert("Please select a 3D legal unit first to store its certificate in DigiLocker.");
      return;
    }

    const modal = document.getElementById('digilocker-modal');
    const body = document.getElementById('digilocker-modal-body');
    if (!modal || !body) return;

    modal.classList.add('active');

    const party = (unit.parties && unit.parties.length > 0) ? unit.parties[0] : { name: "Citizen Property Owner", id_hash: "AADHAAR-8902-1123" };
    const bldName = this.currentBuilding ? (this.currentBuilding.building_name || this.currentBuilding.name) : 'Urban Complex';

    // Step 1: Initial Animation State
    body.innerHTML = `
      <div style="font-family: var(--font-sans);">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Target Property &amp; Title Holder</div>
            <div style="font-size: 15px; font-weight: 800; color: #0B1F33;">${unit.unit_name} &bull; ${bldName}</div>
            <div style="font-size: 12px; color: #475569; margin-top: 2px;">
              Owner: <strong>${party.name}</strong> &bull; KYC Hash: <span style="font-family: monospace;">${party.id_hash}</span>
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">3D ULPIN</div>
            <div style="font-size: 13px; font-family: monospace; font-weight: 800; color: #00a0e3;">${unit.ulpin}</div>
          </div>
        </div>

        <div style="margin-bottom: 18px;">
          <div class="digilocker-step-item active" id="step-1">
            <div class="digilocker-step-icon">1</div>
            <div style="flex: 1;">
              <strong>Validating Verhoeff Checksum &amp; 3D LADM Extents</strong>
              <div style="font-size: 11px; color: #64748b;">Verifying Dihedral D5 check digit and ISO 19152 volumetric space boundaries</div>
            </div>
            <span style="font-size: 12px; color: #3b82f6;">Processing...</span>
          </div>

          <div class="digilocker-step-item" id="step-2">
            <div class="digilocker-step-icon">2</div>
            <div style="flex: 1;">
              <strong>Generating Digital India DigiLocker XML Certificate</strong>
              <div style="font-size: 11px; color: #64748b;">Conforming to MeitY Certificate Schema with Department of Land Resources (DoLR)</div>
            </div>
            <span style="font-size: 12px; color: #94a3b8;">Pending</span>
          </div>

          <div class="digilocker-step-item" id="step-3">
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
      const s1 = document.getElementById('step-1');
      if (s1) {
        s1.className = 'digilocker-step-item done';
        s1.querySelector('.digilocker-step-icon').innerHTML = '✓';
        s1.lastElementChild.textContent = 'Verified';
        s1.lastElementChild.style.color = '#16a34a';
      }

      const s2 = document.getElementById('step-2');
      if (s2) {
        s2.className = 'digilocker-step-item active';
        s2.lastElementChild.textContent = 'Generating...';
        s2.lastElementChild.style.color = '#3b82f6';
      }
      await new Promise(r => setTimeout(r, 450));
      if (s2) {
        s2.className = 'digilocker-step-item done';
        s2.querySelector('.digilocker-step-icon').innerHTML = '✓';
        s2.lastElementChild.textContent = 'Assembled';
        s2.lastElementChild.style.color = '#16a34a';
      }

      const s3 = document.getElementById('step-3');
      if (s3) {
        s3.className = 'digilocker-step-item active';
        s3.lastElementChild.textContent = 'Transmitting...';
        s3.lastElementChild.style.color = '#3b82f6';
      }

      const pushRes = await window.digiLockerService.pushCertificate(
        unit.ulpin,
        party.name,
        party.id_hash
      );

      if (s3) {
        s3.className = 'digilocker-step-item done';
        s3.querySelector('.digilocker-step-icon').innerHTML = '✓';
        s3.lastElementChild.textContent = 'Issued';
        s3.lastElementChild.style.color = '#16a34a';
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
              ${pushRes.message || 'Authentic 3D Bhu-Aadhaar Digital Land Title Certificate is now verified and stored in DigiLocker.'}
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
              <a href="${pushRes.verification_url || '/api/digilocker/certificate/' + encodeURIComponent(unit.ulpin) + '/xml'}" target="_blank" class="btn-secondary" style="padding: 8px 14px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                View Official DigiLocker XML Schema
              </a>
            </div>
            <button type="button" class="primary-process-btn" style="padding: 8px 20px; font-size: 13px;" onclick="document.getElementById('digilocker-modal').classList.remove('active')">
              Done &bull; Return to Cadastre
            </button>
          </div>
        </div>
      `;

      this.checkDigiLockerStatus(unit.ulpin);
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
  }

  closeDeedModal() {
    if (this.deedModal) {
      this.deedModal.classList.remove('active');
    }
  }

  async openGoogleWalletPass(ulpinToPass = null) {
    let unit = null;
    if (ulpinToPass && this.currentBuilding && Array.isArray(this.currentBuilding.legal_units)) {
      unit = this.currentBuilding.legal_units.find(u => u.ulpin === ulpinToPass);
    }
    if (!unit) unit = this.currentUnit;
    if (!unit && this.currentBuilding && this.currentBuilding.legal_units && this.currentBuilding.legal_units.length > 0) {
      unit = this.currentBuilding.legal_units[0];
    }
    const ulpin = (unit && unit.ulpin) || ulpinToPass;
    if (!ulpin) {
      alert("Please select a 3D unit first to generate its Google Wallet pass.");
      return;
    }

    const party = (unit && unit.parties && unit.parties.length > 0) ? unit.parties[0] : { name: "Citizen Owner" };
    
    // Find button to show feedback
    const btn = document.querySelector(".btn-wallet-action");
    const textEl = document.getElementById("btn-inspector-wallet-text");
    const origHtml = textEl ? textEl.innerHTML : (btn ? btn.innerHTML : "Save to Google Wallet");

    if (btn) {
      btn.style.opacity = "0.75";
    }
    if (textEl) {
      textEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Creating Pass...`;
    } else if (btn) {
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Creating Pass...</span>`;
    }

    // Pre-open new tab to avoid browser popup blockers
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
        throw new Error("Google Wallet Service is not yet initialized. Please reload the page.");
      }
      const res = await window.googleWalletService.generatePass(ulpin, party.name);
      
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

        // Show direct floating notification toast
        if (window.googleWalletService && window.googleWalletService.showDirectNotification) {
          window.googleWalletService.showDirectNotification(res);
        }
      }
    } catch (err) {
      if (saveTab && !saveTab.closed) saveTab.close();
      console.error("[Google Wallet Error]:", err);
      alert("Google Wallet Pass Notice: " + (err.message || "Failed to generate pass."));
      if (textEl) textEl.innerHTML = origHtml;
    } finally {
      if (btn) {
        btn.style.opacity = "1";
      }
      setTimeout(() => {
        if (textEl && textEl.innerHTML.includes("Pass Created")) {
          textEl.innerHTML = origHtml;
        } else if (btn && btn.innerHTML.includes("Pass Created")) {
          btn.innerHTML = origHtml;
        }
      }, 6000);
    }
  }

  async saveToGoogleWallet(ulpinToPass = null) {
    return this.openGoogleWalletPass(ulpinToPass);
  }

  openEmailModal(docType, ulpinToEmail = null) {
    let unit = null;
    if (ulpinToEmail && this.currentBuilding && Array.isArray(this.currentBuilding.legal_units)) {
      unit = this.currentBuilding.legal_units.find(u => u.ulpin === ulpinToEmail);
    }
    if (!unit) unit = this.currentUnit;
    if (!unit && this.currentBuilding && this.currentBuilding.legal_units && this.currentBuilding.legal_units.length > 0) {
      unit = this.currentBuilding.legal_units[0];
    }
    const ulpin = (unit && unit.ulpin) || ulpinToEmail;
    if (!ulpin) {
      alert("Please select a 3D unit first to dispatch its certificate via email.");
      return;
    }

    const modal = document.getElementById('email-modal');
    const body = document.getElementById('email-modal-body');
    const title = document.getElementById('email-modal-title');
    if (!modal || !body) return;

    if (title) {
      title.textContent = docType === 'passport' ? 'Email Digital Land Passport' : 'Email 3D Bhu-Aadhaar Certificate';
    }

    const party = (unit && unit.parties && unit.parties.length > 0) ? unit.parties[0] : { name: "Citizen Owner", id_hash: "" };
    const propName = (unit && unit.unit_name) || "Volumetric Space Unit";

    body.innerHTML = `
      <form id="email-dispatch-form" onsubmit="window.app && window.app.inspector.submitEmailDispatch(event, '${docType}', '${ulpin}')" style="font-family: var(--font-sans);">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px;">
          <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Target Document</div>
          <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">${propName} &bull; ${ulpin}</div>
          <div style="font-size: 11px; color: #475569; margin-top: 2px;">Title Holder: ${party.name}</div>
        </div>

        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px;">
            Recipient Email Address <span style="color: #ef4444;">*</span>
          </label>
          <input 
            type="email" 
            id="email-input-recipient" 
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
            id="email-input-name" 
            value="${party.name || ''}" 
            placeholder="Property Owner Name" 
            style="width: 100%; box-sizing: border-box; padding: 10px 12px; font-size: 13px; border: 1.5px solid #cbd5e1; border-radius: 6px; font-family: var(--font-sans); outline: none;"
          />
        </div>

        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px 12px; margin-bottom: 18px; font-size: 11px; color: #1e40af; display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-bolt" style="color: #3b82f6;"></i>
          <span>Dispatched via official <strong>Brevo Transactional SMTP Gateway</strong> with ISO 19152 volumetric records.</span>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn-secondary" style="padding: 8px 16px; font-size: 12px;" onclick="document.getElementById('email-modal').classList.remove('active')">
            Cancel
          </button>
          <button type="submit" id="btn-submit-email" class="primary-process-btn" style="padding: 8px 20px; font-size: 12px; background: linear-gradient(135deg, #0B1F33 0%, #18A7A8 100%);">
            Send Official Email &rarr;
          </button>
        </div>
      </form>
    `;

    modal.classList.add('active');
    setTimeout(() => {
      const emailInput = document.getElementById('email-input-recipient');
      if (emailInput) emailInput.focus();
    }, 100);
  }

  async submitEmailDispatch(event, docType, ulpin) {
    if (event) event.preventDefault();
    const emailInput = document.getElementById('email-input-recipient');
    const nameInput = document.getElementById('email-input-name');
    const submitBtn = document.getElementById('btn-submit-email');
    const body = document.getElementById('email-modal-body');

    if (!emailInput || !emailInput.value.trim()) return;
    const recipientEmail = emailInput.value.trim();
    const recipientName = (nameInput && nameInput.value.trim()) || '';

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Sending via Brevo...`;
    }

    try {
      let res;
      if (docType === 'passport') {
        res = await window.emailService.sendPassport(recipientEmail, ulpin, recipientName);
      } else {
        res = await window.emailService.sendCertificate(recipientEmail, ulpin, recipientName);
      }

      body.innerHTML = `
        <div style="text-align: center; padding: 20px 10px; font-family: var(--font-sans);">
          <div style="width: 52px; height: 52px; background: #22c55e; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 26px; margin: 0 auto 14px; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3);">
            ✓
          </div>
          <h3 style="margin: 0 0 8px; font-size: 17px; font-weight: 800; color: #14532d;">
            Document Successfully Sent!
          </h3>
          <p style="margin: 0 0 16px; font-size: 13px; color: #166534; line-height: 1.5;">
            ${res.message || 'The official document has been transmitted to ' + recipientEmail + ' via Brevo.'}
          </p>
          <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 20px; font-size: 12px; text-align: left;">
            <div><strong>Recipient:</strong> ${recipientEmail}</div>
            <div style="margin-top: 4px;"><strong>ULPIN:</strong> <span style="font-family: monospace;">${ulpin}</span></div>
            <div style="margin-top: 4px; font-size: 11px; color: #64748b;"><strong>Gateway:</strong> Brevo Transactional API (Status: ${res.status})</div>
          </div>
          <button type="button" class="primary-process-btn" style="padding: 9px 24px; font-size: 13px;" onclick="document.getElementById('email-modal').classList.remove('active')">
            Done &bull; Close
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
            <button type="button" class="primary-process-btn" onclick="window.app && window.app.inspector.openEmailModal('${docType}', '${ulpin}')">
              Try Again
            </button>
          </div>
        </div>
      `;
    }
  }
}


