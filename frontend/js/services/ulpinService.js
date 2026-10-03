/**
 * ULPIN & Land Passport API Service Layer
 * Clean abstraction handling all ULPIN verification, passport resolution,
 * and logistics routing endpoints.
 */

const ULPIN_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Fetches full Land Passport and 3D Cadastral Unit metadata for a ULPIN.
   * @param {string} ulpin - Unique Land Parcel Identification Number
   * @returns {Promise<Object>} Formatted passport record with ISO 19152 unit details
   */
  async function getLandPassport(ulpin) {
    if (!ulpin || typeof ulpin !== "string") {
      throw new Error("A valid ULPIN string is required.");
    }

    const cleanUlpin = ulpin.trim().toUpperCase();
    const endpoint = `${API_BASE}/api/ulpin/lookup/${encodeURIComponent(cleanUlpin)}`;

    const response = await fetch(endpoint, {
      headers: { "Accept": "application/json" }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const errorMsg = errData.detail || "Land passport could not be retrieved.";
      const error = new Error(errorMsg);
      error.status = response.status;
      throw error;
    }

    const data = await response.json();
    return data;
  }

  /**
   * Verifies cryptographic integrity of a 3D ULPIN (Verhoeff checksum + Feistel token decryption).
   * @param {string} ulpin
   * @returns {Promise<Object>} Validation result
   */
  async function verifyUlpin(ulpin) {
    const cleanUlpin = ulpin.trim().toUpperCase();
    const response = await fetch(`${API_BASE}/api/ulpin/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({ ulpin: cleanUlpin })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to verify ULPIN checksum.");
    }

    return await response.json();
  }

  /**
   * Fetches precision 3D coordinates and drone/courier dispatch routing.
   * @param {string} ulpin
   * @returns {Promise<Object>}
   */
  async function resolveDeliveryAddress(ulpin) {
    const cleanUlpin = ulpin.trim().toUpperCase();
    const response = await fetch(`${API_BASE}/api/delivery/resolve/${encodeURIComponent(cleanUlpin)}`);

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Delivery coordinates could not be resolved.");
    }

    return await response.json();
  }

  /**
   * Returns list of featured / sample ULPINs for fast interactive demonstration.
   */
  async function getFeaturedPassports() {
    try {
      const res = await fetch(`${API_BASE}/api/ulpin/featured`);
      if (res.ok) {
        const json = await res.json();
        return json.featured;
      }
    } catch (e) {
      console.warn("Using fallback featured ULPINs:", e);
    }

    // High-fidelity fallback presets matching seeded pilot data
    return [
      {
        ulpin: "560103-A-60YLMDPD-2",
        label: "Unit 702 (Tower A - Residential)",
        location: "Bengaluru Tech Corridor (Outer Ring Road)",
        status: "Clear Freehold"
      },
      {
        ulpin: "560103-A-G011E73B-8",
        label: "Sky Villa Penthouse 1201",
        location: "Bengaluru Tech Corridor",
        status: "Bank Mortgaged"
      },
      {
        ulpin: "560103-P-K9VF9HU8-9",
        label: "Parking Bay B2-14 (Basement 2)",
        location: "Basement Level Subsurface",
        status: "Clear Freehold"
      },
      {
        ulpin: "560103-R-0Y8L1W9X-0",
        label: "Air-Rights Sky Deck (+15m)",
        location: "Bengaluru Outer Ring Road",
        status: "Drone & Solar Right"
      },
      {
        ulpin: "400051-B-RG0LN1X6-7",
        label: "Commercial Suite 1401",
        location: "Bandra-Kurla Complex (Mumbai BKC)",
        status: "Grade-A Commercial"
      }
    ];
  }

  return {
    getLandPassport,
    verifyUlpin,
    resolveDeliveryAddress,
    getFeaturedPassports
  };
})();

// Attach to window for global access
window.ulpinService = ULPIN_SERVICE;
