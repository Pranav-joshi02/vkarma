/**
 * Main Application Coordinator — Neumorphism Redesign
 * Connects Leaflet 2D GIS, CesiumJS 3D WebGL Digital Twin,
 * LADM Cadastral Registry, and 10-Stage Pipeline Runner.
 * 
 * Layout: LEFT = Info Panel (building details, certificates)
 *         RIGHT = Action Hub (selection, pipeline, controls)
 */

class App {
  constructor() {
    this.viewer3d = null;
    this.mapSelector = null;
    this.pipelineRunner = null;
    this.inspector = null;
    this.ulpinPortal = null;
    this.disputeScanner = null;
    this.deliveryApi = null;

    this.regions = [];
    this.selectedRegion = null;
    this.cadastreData = null;
    this.stagedFile = null;

    this.discoveredBuildings = [];
    this.selectedBuildingToProcess = null;
    this.isFetchingAreaBuildings = false;

    this.init();
  }

  async init() {
    // 0. Load server configuration (Cesium token, OpenTopography key)
    await loadServerConfig();

    // 1. Initialize Sub-modules
    this.viewer3d = new CadastralViewer3D('cesium-container');
    this.pipelineRunner = new PipelineRunner();
    // Inspector now renders into the LEFT info panel
    this.inspector = new CadastralInspector('sidebar-info-content');
    this.ulpinPortal = new ULPINPortal();
    this.disputeScanner = new DisputeScanner();
    this.deliveryApi = new DeliveryAPIDemo();

    this.mapSelector = new MapAreaSelector('map-2d-container', (areaData) => {
      this.onAreaSelected(areaData);
    });

    // Wire selection callbacks — populate LEFT info panel
    this.viewer3d.onUnitSelectCallback = (unit, building) => {
      this.inspector.showUnitDetails(unit, building);
    };

    this.viewer3d.onBuildingSelectCallback = (building) => {
      this.inspector.showBuildingDetails(building);
    };

    // 2. Set default active view mode to 3D Digital Twin
    this.setViewMode('3d');

    // 3. Fetch Regions and Initial Cadastre
    await this.fetchRegions();
    await this.loadInitialCadastre();

    // 4. Bind UI Controls
    this.bindUIEvents();

    // 5. Initialize left sidebar resize + collapse
    this.initSidebarResize();

    // 6. Initialize ripple effects on all neumorphic buttons
    this.initRippleEffects();
  }

  initSidebarResize() {
    const panel = document.getElementById('sidebar-panel');
    const handle = document.getElementById('sidebar-resize-handle');
    const toggle = document.getElementById('sidebar-toggle-btn');
    if (!panel || !handle || !toggle) return;

    const MIN_W = 300;
    const MAX_W = 560;

    const savedW = parseInt(localStorage.getItem('sidebarWidth'), 10);
    if (savedW >= MIN_W && savedW <= MAX_W) panel.style.width = savedW + 'px';
    const savedCollapsed = localStorage.getItem('sidebarCollapsed');
    if (savedCollapsed === '1' || (savedCollapsed === null && window.innerWidth < 900)) {
      panel.classList.add('collapsed');
    }

    toggle.addEventListener('click', () => {
      panel.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', panel.classList.contains('collapsed') ? '1' : '0');
      this.refreshViewports();
    });

    handle.addEventListener('mousedown', (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const startW = panel.getBoundingClientRect().width;
      document.body.classList.add('sidebar-resizing');

      const onMove = (ev) => {
        const w = Math.min(MAX_W, Math.max(MIN_W, startW + ev.clientX - startX));
        panel.style.width = w + 'px';
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.body.classList.remove('sidebar-resizing');
        localStorage.setItem('sidebarWidth', String(Math.round(panel.getBoundingClientRect().width)));
        this.refreshViewports();
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  refreshViewports() {
    requestAnimationFrame(() => {
      window.dispatchEvent(new Event('resize'));
      if (this.viewer3d && this.viewer3d.viewer) this.viewer3d.viewer.resize();
      if (this.mapSelector && this.mapSelector.map) this.mapSelector.map.invalidateSize();
    });
  }

  async fetchRegions() {
    try {
      const resp = await fetch('/api/regions');
      const data = await resp.json();
      this.regions = data.regions || [];
      this.renderRegionList();
      if (this.regions.length > 0) {
        this.selectRegion(this.regions[0].id, false);
      }
    } catch (err) {
      console.error("Failed to load regions:", err);
    }
  }

  renderRegionList() {
    const container = document.getElementById('region-list');
    if (!container) return;

    container.innerHTML = this.regions.map(r => `
      <div class="region-card ${this.selectedRegion && this.selectedRegion.id === r.id ? 'active' : ''}" data-region-id="${r.id}">
        <div class="region-header">
          <span class="region-name">${r.name}</span>
          <span class="region-pincode">${r.pincode}</span>
        </div>
        <p class="region-desc">${r.description}</p>
        <div class="region-meta">
          <span>
            <svg viewBox="0 0 16 16" fill="currentColor" width="10" height="10" style="vertical-align: middle; margin-right: 3px;">
              <path d="M3 2a1 1 0 011 1v10H3V3a1 1 0 011-1zm3 2a1 1 0 011 1v8H6V5a1 1 0 011-1zm3-1a1 1 0 011 1v9H9V4a1 1 0 011-1z"/>
            </svg>
            ${r.buildings_count || 4} Registered Structures
          </span>
          <span>
            <svg viewBox="0 0 16 16" fill="currentColor" width="10" height="10" style="vertical-align: middle; margin-right: 3px;">
              <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L7 8.586 5.707 7.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            Verified
          </span>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.region-card').forEach(el => {
      el.addEventListener('click', () => {
        const rId = el.getAttribute('data-region-id');
        this.selectRegion(rId, true);
      });
    });
  }

  selectRegion(regionId, shouldFly = true) {
    const reg = this.regions.find(r => r.id === regionId);
    if (!reg) return;

    this.selectedRegion = reg;
    this.selectedBuildingToProcess = null;
    this.updateTargetIndicator(null);
    const buildingsSec = document.getElementById('area-buildings-section');
    if (buildingsSec) buildingsSec.style.display = 'none';

    this.renderRegionList();
    this.mapSelector.setRegion(reg);

    // Update HUD indicator
    const hudArea = document.getElementById('hud-area-name');
    if (hudArea) hudArea.innerText = reg.name;

    if (shouldFly && this.currentViewMode === '3d') {
      this.viewer3d.flyToCoordinates(reg.lat, reg.lng, 420.0);
    }
  }

  async loadInitialCadastre() {
    try {
      const resp = await fetch('/api/buildings');
      if (resp.ok) {
        const data = await resp.json();
        const buildings = data.buildings || [];
        if (buildings.length > 0) {
          this.cadastreData = { buildings };
          this.viewer3d.loadCadastralData(buildings);
          this.mapSelector.renderBuildingFootprints(buildings, (bld) => {
            this.setViewMode('3d');
            this.viewer3d.selectBuilding(bld.building_id);
          });

          // Update HUD count
          let totalUnits = 0;
          buildings.forEach(b => {
            totalUnits += (b.legal_units ? b.legal_units.length : (b.legal_unit_count || 0));
          });
          const statsBadge = document.getElementById('hud-units-count');
          if (statsBadge) {
            statsBadge.innerHTML = `<strong>${totalUnits}</strong> 3D ULPINs Active`;
          }

          // Show first building info in LEFT panel
          this.inspector.showBuildingDetails(buildings[0]);
        }
      }
    } catch (err) {
      console.warn("Could not load initial cadastre:", err);
    }
  }

  onAreaSelected(areaData) {
    if (areaData.is_custom) {
      // Clear active region card selection
      this.selectedRegion = null;
      this.renderRegionList();

      // Switch to custom tab
      this.switchAreaTab('custom');

      const locName = areaData.location ? areaData.location.area_name : 'Custom Area';
      const hudArea = document.getElementById('hud-area-name');
      if (hudArea) hudArea.innerText = `${locName} (${areaData.areaSqKm.toFixed(3)} km²)`;

      // Query real buildings in this bounding box
      this.fetchAreaBuildings(areaData);
    }
  }

  switchAreaTab(tab) {
    document.querySelectorAll('.area-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tab);
    });

    const panePredefined = document.getElementById('tab-pane-predefined');
    const paneCustom = document.getElementById('tab-pane-custom');
    const paneUpload = document.getElementById('tab-pane-upload');

    if (panePredefined) panePredefined.style.display = (tab === 'predefined') ? 'block' : 'none';
    if (paneCustom) paneCustom.style.display = (tab === 'custom') ? 'block' : 'none';
    if (paneUpload) paneUpload.style.display = (tab === 'upload') ? 'block' : 'none';

    if (tab === 'custom') {
      this.setViewMode('2d');
    }
  }

  bindUIEvents() {
    // 2D / 3D Mode Switch
    document.getElementById('nav-btn-3d')?.addEventListener('click', () => this.setViewMode('3d'));
    document.getElementById('nav-btn-2d')?.addEventListener('click', () => this.setViewMode('2d'));

    // Area Switcher Tabs
    document.querySelectorAll('.area-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        this.switchAreaTab(tab);
      });
    });

    // Draw Bounding Box
    document.getElementById('btn-draw-bbox')?.addEventListener('click', () => {
      this.setViewMode('2d');
      this.mapSelector.startDrawingBoundingBox();
    });

    // Clear Bounding Box
    document.getElementById('btn-clear-bbox')?.addEventListener('click', () => {
      this.clearAllSelections();
    });

    // Clear Building Selection / Redraw
    document.getElementById('btn-clear-building-selection')?.addEventListener('click', () => {
      this.clearAllSelections();
    });

    // Process Selected Building (Generate 3D Cadastre)
    document.getElementById('btn-process-selected-building')?.addEventListener('click', () => {
      this.runPipelineForActiveSelection();
    });

    // Process All Buildings
    document.getElementById('btn-process-all-buildings')?.addEventListener('click', () => {
      this.selectedBuildingToProcess = null;
      this.updateTargetIndicator(null);
      this.runPipelineForActiveSelection();
    });

    // Floating 2D Map Bottom Process Button
    document.getElementById('map-btn-process-target')?.addEventListener('click', () => {
      this.runPipelineForActiveSelection();
    });

    // Floating 2D Map Bottom Process All
    document.getElementById('map-btn-process-all')?.addEventListener('click', () => {
      this.selectedBuildingToProcess = null;
      this.updateTargetIndicator(null);
      this.runPipelineForActiveSelection();
    });

    // Run Pipeline Button (Main Action Panel)
    document.getElementById('btn-run-pipeline')?.addEventListener('click', () => {
      this.runPipelineForActiveSelection();
    });

    // Upload LiDAR Dropzone & File Input
    const dropzone = document.getElementById('upload-dropzone');
    const uploadInput = document.getElementById('file-upload-input');
    const fileStatus = document.getElementById('upload-file-status');
    const filenameDisplay = document.getElementById('upload-filename-display');
    const removeFileBtn = document.getElementById('btn-remove-file');

    if (dropzone && uploadInput) {
      dropzone.addEventListener('click', () => uploadInput.click());

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
          this.stagedFile = e.dataTransfer.files[0];
          if (filenameDisplay) filenameDisplay.innerText = this.stagedFile.name;
          if (fileStatus) fileStatus.style.display = 'flex';
          dropzone.style.display = 'none';
        }
      });

      uploadInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          this.stagedFile = e.target.files[0];
          if (filenameDisplay) filenameDisplay.innerText = this.stagedFile.name;
          if (fileStatus) fileStatus.style.display = 'flex';
          dropzone.style.display = 'none';
        }
      });
    }

    if (removeFileBtn) {
      removeFileBtn.addEventListener('click', () => {
        this.stagedFile = null;
        if (uploadInput) uploadInput.value = '';
        if (fileStatus) fileStatus.style.display = 'none';
        if (dropzone) dropzone.style.display = 'flex';
      });
    }

    // Exploded View Slider
    const explodeSlider = document.getElementById('exploded-slider');
    const explodeVal = document.getElementById('exploded-val');
    if (explodeSlider) {
      explodeSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (explodeVal) explodeVal.innerText = `${Math.round(val * 100)}%`;
        this.viewer3d.setExplodedSeparation(val);
      });
    }

    // View Toolbar Buttons
    document.getElementById('tool-btn-type')?.addEventListener('click', () => {
      this.viewer3d.setColorMode('type');
      this.setActiveToolBtn('tool-btn-type');
    });

    document.getElementById('tool-btn-status')?.addEventListener('click', () => {
      this.viewer3d.setColorMode('status');
      this.setActiveToolBtn('tool-btn-status');
    });

    document.getElementById('tool-btn-xray')?.addEventListener('click', () => {
      this.viewer3d.setColorMode('xray');
      this.setActiveToolBtn('tool-btn-xray');
    });

    document.getElementById('tool-btn-pointcloud')?.addEventListener('click', () => {
      const btn = document.getElementById('tool-btn-pointcloud');
      const isVisible = !this.viewer3d.pointCloudVisible;
      this.viewer3d.togglePointCloud(isVisible);
      btn.classList.toggle('active', isVisible);
    });

    // Dispute Scanner
    document.getElementById('btn-dispute-scan')?.addEventListener('click', () => {
      this.disputeScanner.runDisputeScan();
    });

    // Delivery API
    document.getElementById('btn-delivery-api')?.addEventListener('click', () => {
      this.deliveryApi.openDeliveryResolver();
    });
  }

  setActiveToolBtn(btnId) {
    ['tool-btn-type', 'tool-btn-status', 'tool-btn-xray'].forEach(id => {
      document.getElementById(id)?.classList.toggle('active', id === btnId);
    });
  }

  setViewMode(mode) {
    this.currentViewMode = mode;
    const cesiumEl = document.getElementById('cesium-container');
    const mapEl = document.getElementById('map-2d-container');
    const floatingSearchEl = document.getElementById('map-floating-search');
    const btn3D = document.getElementById('nav-btn-3d');
    const btn2D = document.getElementById('nav-btn-2d');

    if (mode === '2d') {
      if (cesiumEl) {
        cesiumEl.classList.add('hidden');
        cesiumEl.classList.remove('active');
      }
      if (mapEl) {
        mapEl.classList.remove('hidden');
        mapEl.classList.add('active');
      }
      if (floatingSearchEl) {
        floatingSearchEl.style.display = 'flex';
      }
      btn2D?.classList.add('active');
      btn3D?.classList.remove('active');
      setTimeout(() => this.mapSelector.map.invalidateSize(), 150);
    } else {
      if (mapEl) {
        mapEl.classList.add('hidden');
        mapEl.classList.remove('active');
      }
      if (floatingSearchEl) {
        floatingSearchEl.style.display = 'none';
      }
      if (cesiumEl) {
        cesiumEl.classList.remove('hidden');
        cesiumEl.classList.add('active');
      }
      const mapBottomBar = document.getElementById('map-target-bottom-bar');
      if (mapBottomBar) mapBottomBar.style.display = 'none';
      btn3D?.classList.add('active');
      btn2D?.classList.remove('active');
    }
    if (mode === '2d' && this.selectedBuildingToProcess) {
      const mapBottomBar = document.getElementById('map-target-bottom-bar');
      if (mapBottomBar) mapBottomBar.style.display = 'flex';
    }
  }

  async runPipelineForActiveSelection() {
    // 1. If a local file is uploaded, run file pipeline
    if (this.stagedFile) {
      await this.uploadAndProcessLas(this.stagedFile);
      return;
    }

    // 2. Otherwise run bounding box or selected region
    const req = {};

    if (this.selectedBuildingToProcess) {
      const bld = this.selectedBuildingToProcess;
      req.selected_building_id = bld.id || bld.building_id;
      req.selected_building_name = bld.name || bld.building_name;
      req.selected_building_footprint = bld.footprint_coordinates || bld.footprint_polygon || [];
      req.selected_building_footprint_local = bld.footprint_local || [];
      req.selected_building_width_m = bld.width_m || 24.0;
      req.selected_building_length_m = bld.length_m || 22.0;
      req.selected_building_floors = bld.floors || bld.total_floors || 3;
      req.selected_building_height = bld.height_m || (req.selected_building_floors * 3.2);
      req.target_single_building = true;
      req.num_buildings = 1;

      const cLat = (bld.centroid && bld.centroid[0]) != null ? bld.centroid[0] : bld.centroid_lat;
      const cLng = (bld.centroid && bld.centroid[1]) != null ? bld.centroid[1] : bld.centroid_lng;
      if (cLat != null && cLng != null) {
        req.base_lat = parseFloat(cLat);
        req.base_lng = parseFloat(cLng);
      }
      if (this.mapSelector.customBBox) {
        req.custom_bbox = this.mapSelector.customBBox;
      }
      const resLoc = this.mapSelector.resolvedLocation || {};
      req.area_name = resLoc.area_name || bld.area_name || "Survey Area";
      req.pincode = resLoc.pincode || bld.pincode || "560103";
    } else if (this.mapSelector.customBBox) {
      req.custom_bbox = this.mapSelector.customBBox;
      const resLoc = this.mapSelector.resolvedLocation || {};
      const center = this.mapSelector.lastCenter || {
        lat: (req.custom_bbox[0] + req.custom_bbox[2]) / 2.0,
        lng: (req.custom_bbox[1] + req.custom_bbox[3]) / 2.0
      };
      req.base_lat = center.lat;
      req.base_lng = center.lng;
      req.area_name = resLoc.area_name || "Custom Survey Area";
      req.pincode = resLoc.pincode || "560103";
      req.num_buildings = resLoc.estBuildings || Math.max(4, Math.min(32, Math.round((this.mapSelector.lastAreaSqKm || 0.1) * 45)));
    } else if (this.selectedRegion) {
      req.region_id = this.selectedRegion.id;
      req.area_name = this.selectedRegion.name;
      req.pincode = this.selectedRegion.pincode;
      req.base_lat = this.selectedRegion.lat;
      req.base_lng = this.selectedRegion.lng;
      req.num_buildings = this.selectedRegion.buildings_count || 4;
    } else {
      alert("Please select a survey zone, draw a boundary box, or import LiDAR data.");
      return;
    }

    req.include_dispute_scenario = true;

    await this.pipelineRunner.executePipeline(req, async (result) => {
      await this.handlePipelineSuccess(result);
    });
  }

  async uploadAndProcessLas(file) {
    const formData = new FormData();
    formData.append("file", file);
    
    this.pipelineRunner.showModal();
    this.pipelineRunner.statusText.innerText = "Uploading .LAS/.LAZ survey file...";
    
    try {
      const response = await fetch('/api/pipeline/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error("Upload failed");
      
      const { task_id } = await response.json();
      this.pipelineRunner.pollTaskStatus(task_id, async (result) => {
        await this.handlePipelineSuccess(result);
      });
    } catch (err) {
      console.error(err);
      alert("File upload failed: " + err.message);
      this.pipelineRunner.hideModal();
    }
  }

  async handlePipelineSuccess(result) {
    if (!result) return;

    // 1. Fetch updated buildings directly from Supabase via backend API
    try {
      const dbResp = await fetch('/api/buildings');
      if (dbResp.ok) {
        const dbData = await dbResp.json();
        if (dbData.buildings && dbData.buildings.length > 0) {
          this.cadastreData = { buildings: dbData.buildings };
        }
      }
    } catch (e) {
      console.warn("Could not reload buildings from Supabase:", e);
    }

    // Fallback merge if API fetch failed
    if (!this.cadastreData || !this.cadastreData.buildings) {
      this.cadastreData = result;
    } else if (result.buildings && result.buildings.length > 0) {
      result.buildings.forEach(newB => {
        const idx = this.cadastreData.buildings.findIndex(b => b.building_id === newB.building_id);
        if (idx >= 0) {
          this.cadastreData.buildings[idx] = newB;
        } else {
          this.cadastreData.buildings.push(newB);
        }
      });
    }

    // Target building from latest result
    const targetBld = (result.buildings && result.buildings.length > 0) 
      ? result.buildings[0] 
      : (this.cadastreData.buildings && this.cadastreData.buildings[0]);

    if (!targetBld) return;

    // Sync with discoveredBuildings cards in right panel
    if (this.discoveredBuildings && this.discoveredBuildings.length > 0) {
      const targetName = (targetBld.building_name || targetBld.name || '').trim().toLowerCase();
      this.discoveredBuildings.forEach(d => {
        const dName = (d.name || d.building_name || '').trim().toLowerCase();
        const dId = String(d.id || d.building_id || '');
        const tId = String(targetBld.building_id || targetBld.id || '');
        if (dName === targetName || (this.selectedBuildingToProcess && String(d.id) === String(this.selectedBuildingToProcess.id)) || (dId && tId && dId === tId)) {
          d.is_processed = true;
          d.building_id = targetBld.building_id;
          d.legal_units = targetBld.legal_units;
          d.legal_unit_count = targetBld.legal_units ? targetBld.legal_units.length : (targetBld.legal_unit_count || 0);
        }
      });
      this.renderDetectedBuildingsList(this.discoveredBuildings);
    }

    // Update active selection reference
    this.selectedBuildingToProcess = targetBld;
    this.updateTargetIndicator(targetBld);

    // 2. Load 3D WebGL meshes in Cesium
    if (this.cadastreData.buildings && this.cadastreData.buildings.length > 0) {
      this.viewer3d.loadCadastralData(this.cadastreData.buildings);

      // 3. Render 2D Footprint Markers
      this.mapSelector.renderBuildingFootprints(this.cadastreData.buildings, (bld) => {
        this.setViewMode('3d');
        this.viewer3d.selectBuilding(bld.building_id);
      });

      // 4. Switch to 3D mode & populate LEFT info panel
      this.setViewMode('3d');
      this.viewer3d.selectBuilding(targetBld.building_id);
      this.inspector.showBuildingDetails(targetBld);
    }

    // 5. Update summary metrics in HUD
    let totalUnits = 0;
    if (this.cadastreData.buildings) {
      this.cadastreData.buildings.forEach(b => {
        totalUnits += (b.legal_units ? b.legal_units.length : (b.legal_unit_count || 0));
      });
    }
    const statsBadge = document.getElementById('hud-units-count');
    if (statsBadge) {
      statsBadge.innerHTML = `<strong>${totalUnits}</strong> 3D ULPINs Active`;
    }
  }

  async fetchAreaBuildings(areaData) {
    const container = document.getElementById('area-buildings-section');
    const listEl = document.getElementById('detected-buildings-list');
    const countBadge = document.getElementById('detected-buildings-count');

    if (container) container.style.display = 'flex';
    if (listEl) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 22px 10px; color: var(--text-secondary); font-size: 11px;">
          <svg viewBox="0 0 24 24" fill="none" stroke="#18A7A8" stroke-width="2" width="24" height="24" style="display: block; margin: 0 auto 8px; animation: spinSlow 2s linear infinite;">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          Querying Overture Maps + OpenStreetMap for buildings...
        </div>
      `;
    }
    if (countBadge) countBadge.innerText = 'Scanning...';

    try {
      // Use the locality name from reverse geocoding for area-based synthetic naming
      const loc = areaData.location || {};
      const areaNameForApi = loc.locality || loc.area_name || "Selected Area";

      const resp = await fetch('/api/area/buildings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bbox: areaData.bbox,
          area_name: areaNameForApi,
          pincode: loc.pincode || "560103"
        })
      });

      if (!resp.ok) throw new Error("Failed to scan buildings in area");
      const data = await resp.json();

      this.discoveredBuildings = data.buildings || [];
      const realCount = data.real_named_count || 0;
      const synthCount = data.synthetic_named_count || 0;

      if (countBadge) {
        countBadge.innerText = `${this.discoveredBuildings.length} found (${realCount} named, ${synthCount} auto-named)`;
      }

      this.renderDetectedBuildingsList(this.discoveredBuildings);

      // Render building polygons on Leaflet terrain map
      this.mapSelector.renderDiscoveredBuildings(this.discoveredBuildings, (bld) => {
        this.selectBuildingToProcess(bld);
      });

      // Default select the first building if any
      if (this.discoveredBuildings.length > 0) {
        this.selectBuildingToProcess(this.discoveredBuildings[0]);
      } else {
        this.selectBuildingToProcess(null);
      }
    } catch (err) {
      console.warn("Error discovering buildings in area:", err);
      if (listEl) {
        listEl.innerHTML = `
          <div style="text-align: center; padding: 14px; color: var(--accent-crimson); font-size: 11px;">
            <i class="fa-solid fa-triangle-exclamation"></i> Could not query buildings: ${err.message}
          </div>
        `;
      }
    }
  }

  renderDetectedBuildingsList(buildings) {
    const listEl = document.getElementById('detected-buildings-list');
    if (!listEl) return;

    if (!buildings || buildings.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 16px; color: var(--text-muted); font-size: 11px;">
          No buildings discovered in this bounding box.
        </div>
      `;
      return;
    }

    listEl.innerHTML = buildings.map(b => {
      const bId = String(b.id || b.building_id || '');
      const selId = this.selectedBuildingToProcess 
        ? String(this.selectedBuildingToProcess.id || this.selectedBuildingToProcess.building_id || '') 
        : '';
      const isSelected = selId && (selId === bId);

      const hasUnits = b.is_processed || (b.legal_units && b.legal_units.length > 0);
      const unitCount = b.legal_unit_count || (b.legal_units ? b.legal_units.length : 0);
      const isSynthetic = b.name_source === 'synthetic';
      const buildingName = b.name || b.building_name || 'Building';

      return `
        <div class="detected-building-card ${isSelected ? 'active' : ''} ${hasUnits ? 'surveyed' : ''}" data-bld-id="${b.id || b.building_id}">
          <div class="detected-bld-icon">
            <i class="fa-solid fa-building"></i>
          </div>
          <div class="detected-bld-body">
            <div class="detected-bld-name${isSynthetic ? ' synthetic-name' : ''}" title="${buildingName}">${buildingName}</div>
            ${hasUnits ? `<div class="detected-bld-badges"><span class="bld-badge" style="background: #DFF7FA; color: #18A7A8; font-weight: 800; border: 1px solid rgba(24,167,168,0.35);"><i class="fa-solid fa-cube"></i> ${unitCount} 3D Units</span></div>` : ''}
          </div>
          <div class="detected-bld-check">
            <svg viewBox="0 0 16 16" fill="currentColor" width="16" height="16">
              <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L7 8.586 5.707 7.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>
      `;
    }).join('');

    listEl.querySelectorAll('.detected-building-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-bld-id');
        const bld = this.discoveredBuildings.find(b => String(b.id || b.building_id) === String(id));
        if (bld) {
          this.selectBuildingToProcess(bld);
        }
      });
    });
  }

  clearAllSelections() {
    this.selectedBuildingToProcess = null;
    this.discoveredBuildings = [];
    this.updateTargetIndicator(null);
    const bSec = document.getElementById('area-buildings-section');
    if (bSec) bSec.style.display = 'none';
    const mapBottomBar = document.getElementById('map-target-bottom-bar');
    if (mapBottomBar) mapBottomBar.style.display = 'none';
    if (this.mapSelector) this.mapSelector.clearBoundingBox();
  }

  selectBuildingToProcess(building) {
    this.selectedBuildingToProcess = building;

    const bId = building ? String(building.id || building.building_id || '') : '';
    const bName = building ? (building.name || building.building_name || '').trim().toLowerCase() : '';

    // Update active class on cards
    const cards = document.querySelectorAll('.detected-building-card');
    cards.forEach(c => {
      const cId = c.getAttribute('data-bld-id');
      const isMatch = bId && (String(cId) === bId);
      c.classList.toggle('active', !!isMatch);
    });

    // Highlight on Leaflet map
    if (building && this.mapSelector) {
      this.mapSelector.highlightDiscoveredBuilding(building.id || building.building_id);
    }

    // Populate the LEFT info panel with this building's data
    if (building && this.inspector) {
      let fullBld = building;
      if (this.cadastreData && this.cadastreData.buildings) {
        const match = this.cadastreData.buildings.find(b => {
          const matchId = String(b.building_id || b.id || '');
          const matchName = (b.building_name || b.name || '').trim().toLowerCase();
          return (bId && matchId && bId === matchId) || (bName && matchName && bName === matchName);
        });
        if (match) {
          fullBld = match;
          this.selectedBuildingToProcess = match;
        }
      }
      this.inspector.showBuildingDetails(fullBld);
    }

    this.updateTargetIndicator(this.selectedBuildingToProcess);

    // Ensure action panel is smoothly visible
    const actionsEl = document.getElementById('building-selection-actions');
    if (actionsEl) {
      actionsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  updateTargetIndicator(building) {
    const indicator = document.getElementById('selected-building-indicator');
    const nameEl = document.getElementById('selected-target-bld-name');
    const metaEl = document.getElementById('selected-target-bld-meta');
    const btnLabel = document.getElementById('btn-run-pipeline-label');

    // Section Action Panel
    const bannerName = document.getElementById('selected-bld-banner-name');
    const bannerSub = document.getElementById('selected-bld-banner-sub');
    const directBtnLabel = document.getElementById('btn-process-selected-label');

    // Floating Map Bottom Bar
    const mapBottomBar = document.getElementById('map-target-bottom-bar');
    const mapTargetName = document.getElementById('map-target-bld-name');
    const mapTargetDetails = document.getElementById('map-target-bld-details');

    if (building) {
      const bName = building.name || building.building_name || 'Selected Building';
      const bFloors = building.floors || building.total_floors || 3;
      const bHeight = (building.height_m || (bFloors * 3.2)).toFixed(1);
      const bType = building.type || 'Commercial';
      const metaText = `${bFloors} Floors • ${bHeight}m Height • ${bType}`;

      if (indicator) indicator.style.display = 'flex';
      if (nameEl) nameEl.innerText = bName;
      if (metaEl) metaEl.innerText = metaText;
      if (btnLabel) btnLabel.innerText = `Process: ${bName}`;

      if (bannerName) bannerName.innerText = bName;
      if (bannerSub) bannerSub.innerText = metaText;
      if (directBtnLabel) directBtnLabel.innerText = `Generate 3D Cadastre: ${bName}`;

      if (mapBottomBar && this.currentViewMode === '2d') {
        mapBottomBar.style.display = 'flex';
        if (mapTargetName) mapTargetName.innerText = bName;
        if (mapTargetDetails) mapTargetDetails.innerText = metaText;
      }
    } else {
      if (indicator) indicator.style.display = 'none';
      if (btnLabel) btnLabel.innerText = `Generate 3D Cadastre`;

      if (bannerName) bannerName.innerText = 'Select a building above';
      if (bannerSub) bannerSub.innerText = 'Click a building in the list or on the map';
      if (directBtnLabel) directBtnLabel.innerText = `Generate 3D Cadastre`;

      if (mapBottomBar) mapBottomBar.style.display = 'none';
    }
  }

  /**
   * Neumorphic Ripple Effect on Buttons
   * Adds a green ripple animation on click for all neumorphic action buttons.
   */
  initRippleEffects() {
    const rippleButtons = document.querySelectorAll(
      '.btn-run-pipeline, .primary-process-btn, .bbox-btn, .nav-pill, .tool-btn, .map-btn-process, .hud-action-btn'
    );

    rippleButtons.forEach(btn => {
      btn.classList.add('ripple-container');
      btn.addEventListener('click', (e) => {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        const rect = btn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
      });
    });
  }
}

// Global bootstrap
window.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
