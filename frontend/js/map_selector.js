/**
 * 2D GIS Map & Custom Area Bounding Box Selector (Leaflet)
 * Built for precision spatial cadastral pilot & custom area selection across India.
 * Powered 100% by open geospatial tile layers (Zero API keys required).
 */

class MapAreaSelector {
  constructor(mapContainerId, onAreaSelectedCallback) {
    this.containerId = mapContainerId;
    this.onAreaSelected = onAreaSelectedCallback;
    this.map = null;
    this.currentMarker = null;
    this.bboxLayer = null;
    this.previewLayer = null;
    this.searchMarker = null;
    this.buildingLayers = L.layerGroup();
    this.discoveredBuildingsLayer = L.layerGroup();
    this.buildingMarkerMap = {};
    this.selectedDiscoveredBuildingId = null;
    
    this.isDrawingBBox = false;
    this.drawStartLatLng = null;
    this.hasMovedAfterMouseDown = false;

    this.selectedRegion = null;
    this.customBBox = null;

    this.initMap();
  }

  initMap() {
    // Default center: Bengaluru Outer Ring Road
    this.map = L.map(this.containerId, {
      zoomControl: false,
      attributionControl: false,
      doubleClickZoom: false
    }).setView([12.9352, 77.6946], 15);

    L.control.zoom({ position: 'bottomright' }).addTo(this.map);

    // Terrain-Only Tile Layers (no satellite imagery)
    const esriTopo = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: '&copy; Esri World Topo Map &bull; Terrain Only'
    });

    const openTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17,
      attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
    });

    const osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    });

    // Default to Topographic Terrain view (no satellite imagery)
    esriTopo.addTo(this.map);

    // Layer Switcher: terrain-only options
    const baseMaps = {
      "Topographic Terrain": esriTopo,
      "Contours & Elevation": openTopo,
      "Street Map": osmStandard
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(this.map);

    this.discoveredBuildingsLayer.addTo(this.map);
    this.buildingLayers.addTo(this.map);

    this.initDrawingEvents();
    this.bindBannerEvents();
    this.initSearchAndQuickTools();
  }

  initSearchAndQuickTools() {
    // 1. Sidebar Search Input & Button
    const searchInput = document.getElementById('map-search-input');
    const searchBtn = document.getElementById('btn-map-search');
    
    if (searchBtn && searchInput) {
      searchBtn.addEventListener('click', () => {
        const val = searchInput.value.trim();
        if (val) this.searchLocation(val);
      });
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const val = searchInput.value.trim();
          if (val) this.searchLocation(val);
        }
      });
    }

    // 2. Viewport Floating Search Input & Button
    const viewportSearchInput = document.getElementById('map-viewport-search-input');
    const viewportSearchBtn = document.getElementById('btn-viewport-search');
    
    if (viewportSearchBtn && viewportSearchInput) {
      viewportSearchBtn.addEventListener('click', () => {
        const val = viewportSearchInput.value.trim();
        if (val) this.searchLocation(val);
      });
      viewportSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const val = viewportSearchInput.value.trim();
          if (val) this.searchLocation(val);
        }
      });
    }

    // 3. Select Current Map View Buttons
    const selectViewBtn = document.getElementById('btn-select-current-view');
    if (selectViewBtn) {
      selectViewBtn.addEventListener('click', () => this.selectCurrentView());
    }

    const hudSelectViewBtn = document.getElementById('btn-hud-select-view');
    if (hudSelectViewBtn) {
      hudSelectViewBtn.addEventListener('click', () => this.selectCurrentView());
    }

    // 4. Viewport Draw BBox Button
    const hudDrawBtn = document.getElementById('btn-hud-draw-bbox');
    if (hudDrawBtn) {
      hudDrawBtn.addEventListener('click', () => this.startDrawingBoundingBox());
    }
  }

  async searchLocation(query) {
    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=in&limit=1`
      );
      if (!resp.ok) throw new Error("Search service error");
      const results = await resp.json();

      if (!results || results.length === 0) {
        alert(`Location "${query}" not found in India. Try another place name or city.`);
        return;
      }

      const item = results[0];
      const lat = parseFloat(item.lat);
      const lon = parseFloat(item.lon);

      // Smoothly fly map to searched location
      this.map.flyTo([lat, lon], 16, { duration: 1.5 });

      // Add temporary marker with popup
      if (this.searchMarker) {
        this.map.removeLayer(this.searchMarker);
      }

      this.searchMarker = L.circleMarker([lat, lon], {
        radius: 10,
        fillColor: '#38bdf8',
        color: '#ffffff',
        weight: 3,
        opacity: 1,
        fillOpacity: 0.85
      }).addTo(this.map);

      this.searchMarker.bindPopup(`<b>${item.display_name.split(',')[0]}</b><br>${item.display_name}`).openPopup();

      // Update HUD text
      const hudArea = document.getElementById('hud-area-name');
      if (hudArea) hudArea.innerText = item.display_name.split(',')[0];

      // Sync input values
      const s1 = document.getElementById('map-search-input');
      const s2 = document.getElementById('map-viewport-search-input');
      if (s1) s1.value = item.display_name.split(',')[0];
      if (s2) s2.value = item.display_name.split(',')[0];

    } catch (err) {
      console.warn("Geocoding search failed:", err);
      alert(`Search failed: ${err.message}`);
    }
  }

  selectCurrentView() {
    const center = this.map.getCenter();
    // Create ~500m x 500m box around center (approx 0.25 sq km)
    const deltaLat = 0.0025;
    const deltaLng = 0.0025 / Math.cos((center.lat * Math.PI) / 180.0);

    const bounds = L.latLngBounds(
      [center.lat - deltaLat, center.lng - deltaLng],
      [center.lat + deltaLat, center.lng + deltaLng]
    );

    this.finishDrawingBoundingBoxFromBounds(bounds);
  }

  bindBannerEvents() {
    const cancelBtn = document.getElementById('btn-cancel-draw');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        this.cancelDrawingBoundingBox();
      });
    }

    const clearBtn = document.getElementById('btn-clear-bbox');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        this.clearBoundingBox();
      });
    }

    // Escape key cancels drawing
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isDrawingBBox) {
        this.cancelDrawingBoundingBox();
      }
    });
  }

  initDrawingEvents() {
    // 1. Mouse Down: anchor first corner
    this.map.on('mousedown', (e) => {
      if (!this.isDrawingBBox) return;

      if (!this.drawStartLatLng) {
        this.drawStartLatLng = e.latlng;
        this.hasMovedAfterMouseDown = false;
        
        if (this.previewLayer) {
          this.map.removeLayer(this.previewLayer);
          this.previewLayer = null;
        }

        this.updateBannerText("Move cursor and release/click at opposite corner...");
      }
    });

    // 2. Mouse Move: live rectangle preview & live area
    this.map.on('mousemove', (e) => {
      if (!this.isDrawingBBox || !this.drawStartLatLng) return;

      this.hasMovedAfterMouseDown = true;
      const bounds = L.latLngBounds(this.drawStartLatLng, e.latlng);
      const area = this.calculateAreaSqKm(bounds);

      if (this.previewLayer) {
        this.previewLayer.setBounds(bounds);
      } else {
        this.previewLayer = L.rectangle(bounds, {
          color: '#39FF14',
          weight: 2,
          fillColor: '#39FF14',
          fillOpacity: 0.2,
          dashArray: '6, 6'
        }).addTo(this.map);
      }

      this.updateBannerText(`Drawing Area: ${area.toFixed(3)} km² (Max 1.0 km²)`);
    });

    // 3. Mouse Up: completes drag mode if moved sufficiently
    this.map.on('mouseup', (e) => {
      if (!this.isDrawingBBox || !this.drawStartLatLng) return;

      const startPoint = this.map.latLngToLayerPoint(this.drawStartLatLng);
      const currentPoint = this.map.latLngToLayerPoint(e.latlng);
      const pixelDist = startPoint.distanceTo(currentPoint);

      if (pixelDist > 15) {
        const bounds = L.latLngBounds(this.drawStartLatLng, e.latlng);
        this.finishDrawingBoundingBoxFromBounds(bounds);
      }
    });

    // 4. Click: handles two-click corner selection
    this.map.on('click', (e) => {
      if (!this.isDrawingBBox) return;

      if (this.drawStartLatLng && !this.hasMovedAfterMouseDown) {
        return;
      }

      if (this.drawStartLatLng) {
        const startPoint = this.map.latLngToLayerPoint(this.drawStartLatLng);
        const currentPoint = this.map.latLngToLayerPoint(e.latlng);
        if (startPoint.distanceTo(currentPoint) > 15) {
          const bounds = L.latLngBounds(this.drawStartLatLng, e.latlng);
          this.finishDrawingBoundingBoxFromBounds(bounds);
        }
      }
    });
  }

  calculateAreaSqKm(bounds) {
    const southWest = bounds.getSouthWest();
    const northEast = bounds.getNorthEast();
    const distWidth = southWest.distanceTo(L.latLng(southWest.lat, northEast.lng));
    const distHeight = southWest.distanceTo(L.latLng(northEast.lat, southWest.lng));
    return (distWidth / 1000.0) * (distHeight / 1000.0);
  }

  startDrawingBoundingBox() {
    this.isDrawingBBox = true;
    this.drawStartLatLng = null;
    this.hasMovedAfterMouseDown = false;

    // Disable Leaflet map panning during draw mode
    this.map.dragging.disable();
    this.map.getContainer().classList.add('drawing-active');

    // Show drawing banner
    const banner = document.getElementById('drawing-mode-banner');
    if (banner) banner.style.display = 'flex';
    this.updateBannerText("Click & drag on the map (or click 2 corners) to define survey area");

    const btn = document.getElementById('btn-draw-bbox');
    if (btn) {
      btn.classList.add('drawing');
      btn.innerHTML = `<i class="fa-solid fa-crosshairs fa-spin"></i> Drawing active on map...`;
    }

    const hudBtn = document.getElementById('btn-hud-draw-bbox');
    if (hudBtn) hudBtn.classList.add('active');
  }

  stopDrawingBoundingBox() {
    this.isDrawingBBox = false;
    this.drawStartLatLng = null;
    this.hasMovedAfterMouseDown = false;

    // Re-enable map dragging
    this.map.dragging.enable();
    this.map.getContainer().classList.remove('drawing-active');

    // Hide banner
    const banner = document.getElementById('drawing-mode-banner');
    if (banner) banner.style.display = 'none';

    const btn = document.getElementById('btn-draw-bbox');
    if (btn) {
      btn.classList.remove('drawing');
      btn.innerHTML = `<i class="fa-solid fa-draw-polygon"></i> Redraw Bounding Box`;
    }

    const hudBtn = document.getElementById('btn-hud-draw-bbox');
    if (hudBtn) hudBtn.classList.remove('active');
  }

  cancelDrawingBoundingBox() {
    if (this.previewLayer) {
      this.map.removeLayer(this.previewLayer);
      this.previewLayer = null;
    }
    this.stopDrawingBoundingBox();
  }

  finishDrawingBoundingBoxFromBounds(bounds) {
    const areaSqKm = this.calculateAreaSqKm(bounds);

    if (this.previewLayer) {
      this.map.removeLayer(this.previewLayer);
      this.previewLayer = null;
    }

    if (areaSqKm > 1.0) {
      alert(`Selected area is ${areaSqKm.toFixed(2)} km², which exceeds the maximum limit of 1.0 km². Please select a smaller bounding box.`);
      this.cancelDrawingBoundingBox();
      return;
    }

    if (areaSqKm < 0.0001) {
      this.cancelDrawingBoundingBox();
      return;
    }

    const center = bounds.getCenter();
    this.lastCenter = center;
    this.lastAreaSqKm = areaSqKm;

    const southWest = bounds.getSouthWest();
    const northEast = bounds.getNorthEast();

    this.customBBox = [
      southWest.lat, southWest.lng,
      northEast.lat, northEast.lng
    ];

    // Dynamic building capacity proportional to area size (e.g. 4 to 32 buildings)
    const estBuildings = Math.max(4, Math.min(32, Math.round(areaSqKm * 45)));
    this.resolvedLocation = this.inferLocationDetails(center.lat, center.lng);
    this.resolvedLocation.estBuildings = estBuildings;
    this.reverseGeocode(center.lat, center.lng);

    // Persist bbox rectangle
    if (this.bboxLayer) {
      this.map.removeLayer(this.bboxLayer);
    }

    this.bboxLayer = L.rectangle(bounds, {
      color: '#39FF14',
      weight: 2,
      fillColor: '#39FF14',
      fillOpacity: 0.15
    }).addTo(this.map);

    this.stopDrawingBoundingBox();

    // Update UI Stats Pill
    const pill = document.getElementById('bbox-active-indicator');
    const coordsStat = document.getElementById('bbox-stat-coords');
    const areaStat = document.getElementById('bbox-stat-area');

    if (pill) pill.style.display = 'flex';
    if (coordsStat) coordsStat.innerText = `${southWest.lat.toFixed(4)}, ${southWest.lng.toFixed(4)}`;
    if (areaStat) areaStat.innerText = `${areaSqKm.toFixed(3)} km² • ~${estBuildings} Blds`;

    // Fly slightly to frame bounds
    this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17 });

    if (this.onAreaSelected) {
      this.onAreaSelected({
        is_custom: true,
        bbox: this.customBBox,
        center: center,
        areaSqKm: areaSqKm,
        estBuildings: estBuildings,
        location: this.resolvedLocation
      });
    }
  }

  inferLocationDetails(lat, lng) {
    if (lat >= 28.3 && lat <= 28.9 && lng >= 76.8 && lng <= 77.5) {
      return { area_name: "Delhi NCR / Central Zone", pincode: "110001" };
    }
    if (lat >= 18.8 && lat <= 19.3 && lng >= 72.7 && lng <= 73.1) {
      return { area_name: "Mumbai Metropolitan / BKC Zone", pincode: "400051" };
    }
    if (lat >= 18.4 && lat <= 18.7 && lng >= 73.7 && lng <= 74.0) {
      return { area_name: "Pune Tech Corridor / Hinjawadi", pincode: "411057" };
    }
    if (lat >= 12.8 && lat <= 13.1 && lng >= 77.4 && lng <= 77.8) {
      return { area_name: "Bengaluru Tech Corridor", pincode: "560103" };
    }
    if (lat >= 17.3 && lat <= 17.6 && lng >= 78.2 && lng <= 78.6) {
      return { area_name: "Hyderabad HITEC City", pincode: "500081" };
    }
    if (lat >= 12.9 && lat <= 13.2 && lng >= 80.1 && lng <= 80.3) {
      return { area_name: "Chennai OMR IT Corridor", pincode: "600096" };
    }
    if (lat >= 22.4 && lat <= 22.7 && lng >= 88.2 && lng <= 88.5) {
      return { area_name: "Kolkata Salt Lake Sector V", pincode: "700091" };
    }
    return { area_name: `Custom Survey Area (${lat.toFixed(3)}, ${lng.toFixed(3)})`, pincode: "560001" };
  }

  async reverseGeocode(lat, lng) {
    try {
      const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=16`);
      if (resp.ok) {
        const data = await resp.json();
        const addr = data.address || {};
        const suburb = addr.suburb || addr.neighbourhood || addr.city_district || addr.road || "Survey Area";
        const city = addr.city || addr.town || addr.county || "Urban Zone";
        const rawPin = addr.postcode || "";
        const cleanPin = rawPin.replace(/\D/g, '').slice(0, 6);
        if (suburb || city) {
          this.resolvedLocation.area_name = `${suburb}, ${city}`;
        }
        if (cleanPin && cleanPin.length === 6) {
          this.resolvedLocation.pincode = cleanPin;
        }
        const hudArea = document.getElementById('hud-area-name');
        if (hudArea) hudArea.innerText = `${this.resolvedLocation.area_name} (${this.lastAreaSqKm.toFixed(3)} km²)`;
      }
    } catch (e) {
      // Keep heuristic location
    }
  }

  clearBoundingBox() {
    if (this.bboxLayer) {
      this.map.removeLayer(this.bboxLayer);
      this.bboxLayer = null;
    }
    if (this.searchMarker) {
      this.map.removeLayer(this.searchMarker);
      this.searchMarker = null;
    }
    this.clearDiscoveredBuildings();
    this.customBBox = null;

    const pill = document.getElementById('bbox-active-indicator');
    if (pill) pill.style.display = 'none';

    const btn = document.getElementById('btn-draw-bbox');
    if (btn) {
      btn.innerHTML = `<svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14" style="vertical-align: middle; margin-right: 4px;"><path d="M8 1a1 1 0 011 1v1.6A4.5 4.5 0 0112.4 7H14a1 1 0 110 2h-1.6A4.5 4.5 0 019 12.4V14a1 1 0 11-2 0v-1.6A4.5 4.5 0 013.6 9H2a1 1 0 110-2h1.6A4.5 4.5 0 017 3.6V2a1 1 0 011-1z"/></svg> Draw Bounding Box`;
    }
  }

  clearDiscoveredBuildings() {
    if (this.discoveredBuildingsLayer) {
      this.discoveredBuildingsLayer.clearLayers();
    }
    this.buildingMarkerMap = {};
    this.selectedDiscoveredBuildingId = null;
  }

  renderDiscoveredBuildings(buildings, onSelectBuilding) {
    this.clearDiscoveredBuildings();

    if (!buildings || buildings.length === 0) return;

    buildings.forEach(bld => {
      let layer = null;
      const coords = bld.footprint_coordinates || [];

      if (coords && coords.length >= 3) {
        // Render exact polygon boundary on terrain map — neon green accent
        layer = L.polygon(coords, {
          color: '#0a8a4a',
          weight: 2,
          fillColor: '#39FF14',
          fillOpacity: 0.25
        });
      } else if (bld.centroid && bld.centroid.length === 2) {
        layer = L.circleMarker(bld.centroid, {
          radius: 9,
          color: '#0a8a4a',
          weight: 2,
          fillColor: '#39FF14',
          fillOpacity: 0.7
        });
      }

      if (layer) {
        const tooltipHtml = `
          <div style="font-family: 'Inter', sans-serif; font-size: 12px; line-height: 1.35; padding: 2px;">
            <div style="font-weight: 700; color: #0a8a4a;"><i class="fa-solid fa-building"></i> ${bld.name || 'Building'}</div>
            <div style="color: #555570; font-size: 11px; margin-top: 2px;">
              <span>${bld.floors || 3} Fl</span> &bull; 
              <span>${(bld.height_m || 12).toFixed(1)}m</span> &bull; 
              <span>${bld.type || 'Commercial'}</span>
            </div>
            <div style="color: #0a8a4a; font-size: 10px; margin-top: 3px; font-weight: 700;">
              Click to select for Cadastral
            </div>
          </div>
        `;
        layer.bindTooltip(tooltipHtml, { className: 'cadastral-tooltip', sticky: true });

        const popupContent = `
          <div style="font-family: 'Inter', sans-serif; font-size: 12px; line-height: 1.4; padding: 4px 2px; min-width: 190px;">
            <div style="font-weight: 800; color: #1a1a2e; font-size: 13px; margin-bottom: 2px;">
              <i class="fa-solid fa-building" style="color: #0a8a4a;"></i> ${bld.name || 'Building'}
            </div>
            <div style="color: #555570; font-size: 11px; margin-bottom: 8px;">
              <span>${bld.floors || 3} Floors</span> &bull; 
              <span>${(bld.height_m || 12).toFixed(1)}m</span> &bull; 
              <span>${bld.type || 'Commercial'}</span>
            </div>
            <button class="leaflet-popup-process-btn" type="button" onclick="window.app && window.app.runPipelineForActiveSelection()">
              Proceed for Cadastral
            </button>
          </div>
        `;
        layer.bindPopup(popupContent, { maxWidth: 260 });

        layer.on('click', () => {
          this.highlightDiscoveredBuilding(bld.id);
          if (onSelectBuilding) onSelectBuilding(bld);
          layer.openPopup();
        });

        layer.on('mouseover', () => {
          if (this.selectedDiscoveredBuildingId !== bld.id) {
            layer.setStyle({ weight: 3, color: '#39FF14', fillOpacity: 0.45 });
          }
        });

        layer.on('mouseout', () => {
          if (this.selectedDiscoveredBuildingId !== bld.id) {
            layer.setStyle({ weight: 2, color: '#0a8a4a', fillOpacity: 0.25 });
          }
        });

        this.discoveredBuildingsLayer.addLayer(layer);
        this.buildingMarkerMap[bld.id] = layer;
      }
    });
  }

  highlightDiscoveredBuilding(buildingId) {
    this.selectedDiscoveredBuildingId = buildingId;
    if (!this.buildingMarkerMap) return;

    for (const [id, layer] of Object.entries(this.buildingMarkerMap)) {
      if (id === buildingId) {
        layer.setStyle({
          color: '#39FF14',
          weight: 4,
          fillColor: '#39FF14',
          fillOpacity: 0.5
        });
        if (layer.bringToFront) layer.bringToFront();
      } else {
        layer.setStyle({
          color: '#0a8a4a',
          weight: 2,
          fillColor: '#39FF14',
          fillOpacity: 0.25
        });
      }
    }
  }

  updateBannerText(text) {
    const el = document.getElementById('drawing-banner-text');
    if (el) el.innerHTML = text;
  }

  setRegion(region) {
    this.selectedRegion = region;
    this.clearBoundingBox();
    this.map.flyTo([region.lat, region.lng], region.zoom || 16, { duration: 1.2 });

    const delta = 0.005;
    const bounds = [
      [region.lat - delta, region.lng - delta],
      [region.lat + delta, region.lng + delta]
    ];

    this.bboxLayer = L.rectangle(bounds, {
      color: '#39FF14',
      weight: 2,
      fillColor: '#39FF14',
      fillOpacity: 0.12
    }).addTo(this.map);
  }

  renderBuildingFootprints(buildings, onBuildingClick) {
    this.buildingLayers.clearLayers();

    if (!buildings || buildings.length === 0) return;

    buildings.forEach(bld => {
      const marker = L.circleMarker([bld.centroid_lat, bld.centroid_lng], {
        radius: 8,
        fillColor: '#39FF14',
        color: '#0a8a4a',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85
      });

      marker.bindTooltip(`<b>${bld.building_name || bld.building_id}</b><br>Floors: ${bld.total_floors} | Units: ${bld.legal_units ? bld.legal_units.length : (bld.legal_unit_count || 0)}`, {
        className: 'cadastral-tooltip'
      });

      marker.on('click', () => {
        if (onBuildingClick) onBuildingClick(bld);
      });

      this.buildingLayers.addLayer(marker);
    });
  }
}
