/**
 * Frontend Configuration & API Constants
 */
const CONFIG = {
  API_BASE_URL: window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
    ? ""
    : "",

  // Populated from .env with live server fallback
  CESIUM_ION_TOKEN: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjYybXUwUk5Jejg5NUc5MDAiLCJqdGkiOiI0MzllNTI0YS1hNmIyLTQ0M2MtYjk1OS0yMTY0OWQ0ZjY3NjIiLCJpZCI6NTAwMzU3LCJzdWIiOiIyNDA3MDU3OSIsImlzcyI6Imh0dHBzOi8vYXBpLmNlc2l1bS5jb20iLCJhdWQiOiJ2S2FybWEiLCJpYXQiOjE3ODk3NTg0Mzl9.y2ZVklxqJOT0Jf4ZRbbvXBygLHLuDEhyp60Cb-UcAEw",
  HAS_OPENTOPOGRAPHY_KEY: true,
  
  SPACE_TYPE_COLORS: {
    'A': { label: 'Apartment / Flat', color: 0x3b82f6, hex: '#3b82f6' },      // Blue
    'C': { label: 'Corridor (Right of Way)', color: 0x94a3b8, hex: '#94a3b8' }, // Slate
    'S': { label: 'Staircase / Fire Core', color: 0xD96B32, hex: '#D96B32' },   // Amber
    'M': { label: 'Common Area / Sky Deck', color: 0x18A7A8, hex: '#18A7A8' }, // Emerald
    'P': { label: 'Parking Bay (Basement)', color: 0x52677D, hex: '#52677D' },  // Steel
    'U': { label: 'Utility / Subsurface', color: 0x0B1F33, hex: '#0B1F33' },    // Sky Blue
    'B': { label: 'Physical Shell', color: 0x475569, hex: '#475569' },          // Gray
    'R': { label: 'Air-Rights (+15m)', color: 0x20D9E6, hex: '#20D9E6' }        // Cyan
  },

  STATUS_COLORS: {
    'Clear Freehold': 0x3b82f6,
    'Bank Mortgaged': 0x8b5cf6,
    'Under Legal Dispute / Encroachment': 0xef4444,
    'Public / Common Utility': 0x18A7A8,
    'Pending RERA Approval': 0xf59e0b
  }
};

/**
 * Loads server-side configuration (Cesium token, feature flags).
 * Must be called before Cesium viewer initialization.
 */
async function loadServerConfig() {
  try {
    const resp = await fetch('/api/config');
    if (resp.ok) {
      const data = await resp.json();
      CONFIG.CESIUM_ION_TOKEN = data.cesium_ion_token || CONFIG.CESIUM_ION_TOKEN;
      CONFIG.HAS_OPENTOPOGRAPHY_KEY = data.has_opentopography_key || false;
      if (typeof Cesium !== 'undefined' && Cesium.Ion && CONFIG.CESIUM_ION_TOKEN) {
        Cesium.Ion.defaultAccessToken = CONFIG.CESIUM_ION_TOKEN;
      }
    }
  } catch (err) {
    console.warn("Could not load server config:", err);
  }
}

// Set token immediately if Cesium is already in scope
if (typeof Cesium !== 'undefined' && Cesium.Ion && CONFIG.CESIUM_ION_TOKEN) {
  Cesium.Ion.defaultAccessToken = CONFIG.CESIUM_ION_TOKEN;
}
