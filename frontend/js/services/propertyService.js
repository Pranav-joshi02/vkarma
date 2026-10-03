/**
 * Property & Spatial GIS Service Layer
 * Interacts with building discovery, pilot regions, and bounding box APIs.
 */

const PROPERTY_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Retrieves all pilot regions configured in the system.
   */
  async function getRegions() {
    const res = await fetch(`${API_BASE}/api/regions`);
    if (!res.ok) throw new Error("Could not retrieve pilot regions.");
    const data = await res.json();
    return data.regions || [];
  }

  /**
   * Discovers real buildings within a geographic bounding box [min_lat, min_lng, max_lat, max_lng].
   */
  async function getAreaBuildings(bbox, areaName = "Survey Area", pincode = "560103") {
    const res = await fetch(`${API_BASE}/api/area/buildings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        custom_bbox: bbox,
        area_name: areaName,
        pincode: pincode
      })
    });
    if (!res.ok) throw new Error("Could not discover buildings in bounding box.");
    return await res.json();
  }

  /**
   * Fetches full 3D building shell, floors, and legal units for a specific building.
   */
  async function getBuildingDetail(buildingId) {
    const res = await fetch(`${API_BASE}/api/buildings/${encodeURIComponent(buildingId)}`);
    if (!res.ok) throw new Error(`Building '${buildingId}' not found.`);
    return await res.json();
  }

  /**
   * Lists all active buildings in the cadastral registry.
   */
  async function listBuildings() {
    const res = await fetch(`${API_BASE}/api/buildings`);
    if (!res.ok) throw new Error("Could not list registered buildings.");
    const data = await res.json();
    return data.buildings || [];
  }

  return {
    getRegions,
    getAreaBuildings,
    getBuildingDetail,
    listBuildings
  };
})();

window.propertyService = PROPERTY_SERVICE;
