/**
 * Building & Topological Cadastre Service Layer
 * Interacts with dispute scanning, collision detection, and cadastre status.
 */

const BUILDING_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Runs topological collision & volumetric encroachment scan across units.
   */
  async function runDisputeScan(buildingId = null) {
    const url = buildingId 
      ? `${API_BASE}/api/disputes/scan?building_id=${encodeURIComponent(buildingId)}`
      : `${API_BASE}/api/disputes/scan`;

    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("Could not execute dispute scan.");
    return await res.json();
  }

  /**
   * Retrieves overall 3D cadastre active twin status.
   */
  async function getCadastreStatus() {
    const res = await fetch(`${API_BASE}/api/cadastre/status`);
    if (!res.ok) throw new Error("Could not get cadastre status.");
    return await res.json();
  }

  return {
    runDisputeScan,
    getCadastreStatus
  };
})();

window.buildingService = BUILDING_SERVICE;
