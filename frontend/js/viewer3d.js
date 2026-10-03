/**
 * 3D Cadastral Digital Twin WebGL Viewer (CesiumJS)
 * Compliant with LADM 3D Spatial Units & 3D ULPIN registry.
 * Uses terrain-only tile providers (no satellite imagery).
 */

class CadastralViewer3D {
  constructor(containerId = 'cesium-container') {
    this.containerId = containerId;
    this.viewer = null;
    this.buildingEntities = new Map(); // buildingId -> Array of Entities
    this.unitEntities = new Map();     // unitId -> Entity
    
    this.selectedUnitEntity = null;
    this.selectedBuildingId = null;
    
    this.colorMode = 'type'; // 'type', 'status', 'xray'
    this.pointCloudVisible = false;
    
    this.onUnitSelectCallback = null;
    this.onBuildingSelectCallback = null;
    
    this.initCesium();
  }

  initCesium() {
    // Set Cesium Ion access token if provided
    if (CONFIG.CESIUM_ION_TOKEN) {
      Cesium.Ion.defaultAccessToken = CONFIG.CESIUM_ION_TOKEN;
    }

    // Prevent Cesium from defaulting to Ion World Imagery
    const viewerOptions = {
      baseLayer: false,
      animation: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: true,
      timeline: false,
      navigationHelpButton: false,
      scene3DOnly: true,
      creditContainer: document.createElement('div'),
      terrainProvider: new Cesium.EllipsoidTerrainProvider()
    };

    // Initialize Cesium Viewer
    this.viewer = new Cesium.Viewer(this.containerId, viewerOptions);

    // TERRAIN-ONLY: Use Esri World Topo Map (no satellite imagery)
    try {
      const topoProvider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
        credit: 'Esri World Topo Map'
      });
      const topoLayer = this.viewer.imageryLayers.addImageryProvider(topoProvider);
      if (topoLayer) {
        topoLayer.brightness = 1.05;
        topoLayer.contrast = 1.0;
        topoLayer.saturation = 0.85;
      }
    } catch (e) {
      console.warn("Terrain topo layer initialization warning:", e);
      // Fallback to OpenStreetMap terrain
      try {
        const osmProvider = new Cesium.UrlTemplateImageryProvider({
          url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          subdomains: 'abc',
          maximumLevel: 19,
          credit: 'OpenStreetMap'
        });
        this.viewer.imageryLayers.addImageryProvider(osmProvider);
      } catch (e2) {
        console.warn("OSM fallback layer warning:", e2);
      }
    }

    // Suppress Cesium Ion dialog alerts
    if (this.viewer.cesiumWidget && this.viewer.cesiumWidget.showErrorPanel) {
      this.viewer.cesiumWidget.showErrorPanel = function(title, message, error) {
        console.warn("Cesium internal notice:", title, message);
      };
    }

    // Scene lighting for terrain visibility
    this.viewer.scene.globe.enableLighting = true;
    this.viewer.scene.highDynamicRange = false;

    // Lighter sky atmosphere for neumorphic light theme
    if (this.viewer.scene.skyAtmosphere) {
      this.viewer.scene.skyAtmosphere.brightnessShift = 0.2;
    }

    // Handle picking (clicking on 3D units)
    this.viewer.screenSpaceEventHandler.setInputAction((click) => {
      const pickedObject = this.viewer.scene.pick(click.position);
      if (Cesium.defined(pickedObject) && pickedObject.id) {
        const entity = pickedObject.id;
        if (entity.userData && entity.userData.unit) {
          this.selectUnit(entity.userData.unit.unit_id, true);
        } else if (entity.userData && entity.userData.building) {
          this.selectBuilding(entity.userData.building.building_id);
        }
      } else {
        // Deselect
        if (this.selectedUnitEntity) {
          this.selectedUnitEntity.polygon.material = this.selectedUnitEntity.userData.originalColor;
          this.selectedUnitEntity = null;
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  loadCadastralData(buildingsData) {
    this.clearCadastre();
    if (!buildingsData || buildingsData.length === 0) return;

    let targetLat = 12.9352;
    let targetLng = 77.6946;

    buildingsData.forEach((bld) => {
      const bldEntities = [];
      targetLat = bld.centroid_lat;
      targetLng = bld.centroid_lng;
      
      const groundRef = bld.ground_elevation_m || 920.0;
      const units = bld.legal_units || [];

      // Building centroid label — dark text for light terrain map
      const pinEntity = this.viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(bld.centroid_lng, bld.centroid_lat, (bld.height_m || 30.0) + 8.0),
        label: {
          text: `${bld.building_name || bld.building_id}\n(${units.length || bld.legal_unit_count || 0} Units)`,
          font: 'bold 12px Inter, sans-serif',
          fillColor: Cesium.Color.fromCssColorString('#1a1a2e'),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 1800.0)
        }
      });
      pinEntity.userData = { building: bld };
      bldEntities.push(pinEntity);

      units.forEach(unit => {
        const bbox = unit.bbox || { min_x: -2, max_x: 2, min_y: -2, max_y: 2, min_z: 920, max_z: 923 };
        const minHeight = Math.max(0.0, bbox.min_z - groundRef);
        const extrudedHeight = Math.max(minHeight + 1.2, bbox.max_z - groundRef);
        
        // Accurate local meter coordinates to WGS84 degree offsets
        const latOffsetMin = (bbox.min_y / 111111.0);
        const latOffsetMax = (bbox.max_y / 111111.0);
        const lngMetersPerDeg = 111111.0 * Math.cos((bld.centroid_lat * Math.PI) / 180.0);
        const lngOffsetMin = (bbox.min_x / lngMetersPerDeg);
        const lngOffsetMax = (bbox.max_x / lngMetersPerDeg);
        
        const positions = Cesium.Cartesian3.fromDegreesArray([
          bld.centroid_lng + lngOffsetMin, bld.centroid_lat + latOffsetMin,
          bld.centroid_lng + lngOffsetMax, bld.centroid_lat + latOffsetMin,
          bld.centroid_lng + lngOffsetMax, bld.centroid_lat + latOffsetMax,
          bld.centroid_lng + lngOffsetMin, bld.centroid_lat + latOffsetMax
        ]);

        const color = this.getUnitColorCesium(unit);
        const isDisputed = unit.status && unit.status.includes("Dispute");
        
        const entity = this.viewer.entities.add({
          polygon: {
            hierarchy: positions,
            height: minHeight,
            extrudedHeight: extrudedHeight,
            material: color.withAlpha(unit.space_type === 'R' ? 0.35 : 0.88),
            outline: true,
            outlineColor: isDisputed ? Cesium.Color.RED : Cesium.Color.fromCssColorString('#1a1a2e'),
            outlineWidth: 1.5,
            closeTop: true,
            closeBottom: true
          }
        });
        
        entity.userData = {
          unit: unit,
          building: bld,
          originalColor: color.withAlpha(unit.space_type === 'R' ? 0.35 : 0.88)
        };

        bldEntities.push(entity);
        this.unitEntities.set(unit.unit_id, entity);
      });

      this.buildingEntities.set(bld.building_id, bldEntities);
    });

    // Fly camera smoothly to focus on the 3D cadastre
    setTimeout(() => {
      if (this.viewer.entities.values.length > 0) {
        this.viewer.flyTo(this.viewer.entities, {
          duration: 1.8,
          offset: new Cesium.HeadingPitchRange(
            Cesium.Math.toRadians(25.0),
            Cesium.Math.toRadians(-32.0),
            240.0
          )
        });
      } else {
        this.viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(targetLng, targetLat - 0.002, 350.0),
          orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-35.0),
          },
          duration: 1.5
        });
      }
    }, 100);
  }

  flyToCoordinates(lat, lng, altitude = 400.0) {
    this.viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lng, lat - 0.002, altitude),
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-35.0),
      },
      duration: 1.5
    });
  }

  getUnitColorCesium(unit) {
    if (this.colorMode === 'status') {
      if (unit.status && unit.status.includes('Dispute')) return Cesium.Color.fromCssColorString('#ef4444');
      if (unit.status && unit.status.includes('Mortgaged')) return Cesium.Color.fromCssColorString('#8b5cf6');
      if (unit.status && (unit.status.includes('Common') || unit.status.includes('Public'))) return Cesium.Color.fromCssColorString('#18A7A8');
      return Cesium.Color.fromCssColorString('#3b82f6');
    }
    const colors = {
      'A': '#3b82f6',
      'P': '#52677D',
      'S': '#D96B32',
      'M': '#18A7A8',
      'U': '#0B1F33',
      'R': '#20D9E6'
    };
    return Cesium.Color.fromCssColorString(colors[unit.space_type] || '#3b82f6');
  }

  setExplodedSeparation(val) {
    const factor = parseFloat(val) * 7.0; 
    
    this.unitEntities.forEach(entity => {
      const fl = entity.userData.unit.floor_level || 0;
      const bbox = entity.userData.unit.bbox;
      const groundRef = entity.userData.building.ground_elevation_m || 920.0;
      
      const baseMin = Math.max(0.0, bbox.min_z - groundRef);
      const baseMax = Math.max(baseMin + 1.2, bbox.max_z - groundRef);
      
      entity.polygon.height = baseMin + (fl * factor);
      entity.polygon.extrudedHeight = baseMax + (fl * factor);
    });
  }

  setColorMode(mode) {
    this.colorMode = mode;
    this.unitEntities.forEach(entity => {
      const unit = entity.userData.unit;
      if (mode === 'xray') {
        entity.polygon.material = Cesium.Color.fromCssColorString('#39FF14').withAlpha(0.25);
      } else {
        entity.polygon.material = this.getUnitColorCesium(unit).withAlpha(unit.space_type === 'R' ? 0.35 : 0.88);
      }
    });
  }

  selectUnit(unitId, flyTo = false) {
    const entity = this.unitEntities.get(unitId);
    if (!entity) return;

    if (this.selectedUnitEntity && this.selectedUnitEntity !== entity) {
      this.selectedUnitEntity.polygon.material = this.selectedUnitEntity.userData.originalColor;
    }

    this.selectedUnitEntity = entity;
    entity.polygon.material = Cesium.Color.fromCssColorString('#39FF14').withAlpha(0.92);

    const unit = entity.userData.unit;
    const bld = entity.userData.building;

    // Fly camera to the selected unit
    if (flyTo && bld) {
      this.viewer.flyTo(entity, {
        duration: 1.2,
        offset: new Cesium.HeadingPitchRange(
          Cesium.Math.toRadians(0.0),
          Cesium.Math.toRadians(-28.0),
          65.0
        )
      });
    }

    if (this.onUnitSelectCallback) {
      this.onUnitSelectCallback(unit, bld);
    }
  }

  selectBuilding(buildingId) {
    this.selectedBuildingId = buildingId;
    const bldEntities = this.buildingEntities.get(buildingId);
    if (!bldEntities || bldEntities.length === 0) return;

    const bld = bldEntities[0].userData.building;
    if (this.onBuildingSelectCallback) {
      this.onBuildingSelectCallback(bld);
    }
    
    this.viewer.flyTo(bldEntities, {
      duration: 1.4,
      offset: new Cesium.HeadingPitchRange(
        Cesium.Math.toRadians(15.0),
        Cesium.Math.toRadians(-30.0),
        110.0
      )
    });
  }

  togglePointCloud(visible) {
    this.pointCloudVisible = visible;
    if (this.pointCloudObj) {
      this.pointCloudObj.show = visible;
    }
  }

  clearCadastre() {
    this.viewer.entities.removeAll();
    this.buildingEntities.clear();
    this.unitEntities.clear();
    this.selectedUnitEntity = null;
  }
}
