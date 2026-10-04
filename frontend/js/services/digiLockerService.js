/**
 * DigiLocker Client Service Layer
 * Interfaces with MeitY / DILRMP DigiLocker Document Exchange API.
 * Provides Citizen Push flow, status queries, and certificate XML retrieval.
 */

const DIGILOCKER_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Pushes / stores a 3D Bhu-Aadhaar Certificate into citizen's DigiLocker cloud vault.
   * @param {string} ulpin - Unique 3D Land Parcel Identification Number
   * @param {string} [citizenName] - Optional citizen legal owner name
   * @param {string} [aadhaarHash] - Optional Aadhaar / KYC identification hash
   * @returns {Promise<Object>} DigiLocker issuance receipt with doc_uri, sha256_hash, etc.
   */
  async function pushCertificate(ulpin, citizenName = null, aadhaarHash = null) {
    if (!ulpin) throw new Error("A valid ULPIN is required for DigiLocker issuance.");
    
    const payload = {
      ulpin: ulpin.trim().toUpperCase(),
      citizen_name: citizenName,
      citizen_aadhaar_hash: aadhaarHash
    };

    const response = await fetch(`${API_BASE}/api/digilocker/push-certificate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to store certificate in DigiLocker.");
    }

    return await response.json();
  }

  /**
   * Checks whether a 3D ULPIN certificate is currently issued/stored in DigiLocker.
   * @param {string} ulpin
   * @returns {Promise<Object>} Status object { is_stored, digilocker_uri, doc_id, issued_at }
   */
  async function getStatus(ulpin) {
    if (!ulpin) return { is_stored: false };
    try {
      const clean = encodeURIComponent(ulpin.trim().toUpperCase());
      const response = await fetch(`${API_BASE}/api/digilocker/status/${clean}`);
      if (!response.ok) return { is_stored: false };
      return await response.json();
    } catch (e) {
      console.warn("[DigiLocker] Status check warning:", e);
      return { is_stored: false };
    }
  }

  /**
   * Fetches DigiLocker configuration (issuer ID, sandbox mode status).
   */
  async function getConfig() {
    try {
      const res = await fetch(`${API_BASE}/api/digilocker/config`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("[DigiLocker] Config warning:", e);
    }
    return {
      issuer_id: "in.gov.dilrmp",
      issuer_name: "Department of Land Resources (DoLR), Ministry of Rural Development",
      doc_type: "BHUCR",
      is_sandbox: true
    };
  }

  function getXmlUrl(ulpin) {
    return `${API_BASE}/api/digilocker/certificate/${encodeURIComponent(ulpin.trim().toUpperCase())}/xml`;
  }

  return {
    pushCertificate,
    getStatus,
    getConfig,
    getXmlUrl
  };
})();

// Attach globally
window.digiLockerService = DIGILOCKER_SERVICE;
