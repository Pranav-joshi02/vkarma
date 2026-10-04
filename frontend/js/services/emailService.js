/**
 * vKarma Email Dispatch Service (Brevo Integration)
 * Provides client methods to email official 3D Bhu-Aadhaar Certificates
 * and Digital Land Passports directly to property owners.
 */

const EMAIL_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Sends the 3D Bhu-Aadhaar Title Certificate to the specified email.
   * @param {string} email - Recipient email address
   * @param {string} ulpin - 3D ULPIN
   * @param {string} [name] - Citizen / owner name
   * @returns {Promise<Object>} API response
   */
  async function sendCertificate(email, ulpin, name = "") {
    if (!email || !ulpin) {
      throw new Error("Both email and ULPIN are required.");
    }

    const payload = {
      recipient_email: email.trim(),
      recipient_name: name.trim(),
      ulpin: ulpin.trim().toUpperCase()
    };

    const response = await fetch(`${API_BASE}/api/email/send-certificate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to dispatch certificate email.");
    }

    return await response.json();
  }

  /**
   * Sends the Digital Land Passport to the specified email.
   * @param {string} email - Recipient email address
   * @param {string} ulpin - 3D ULPIN
   * @param {string} [name] - Citizen / owner name
   * @returns {Promise<Object>} API response
   */
  async function sendPassport(email, ulpin, name = "") {
    if (!email || !ulpin) {
      throw new Error("Both email and ULPIN are required.");
    }

    const payload = {
      recipient_email: email.trim(),
      recipient_name: name.trim(),
      ulpin: ulpin.trim().toUpperCase()
    };

    const response = await fetch(`${API_BASE}/api/email/send-passport`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to dispatch passport email.");
    }

    return await response.json();
  }

  /**
   * Fetches the email gateway configuration from backend.
   * @returns {Promise<Object>}
   */
  async function getConfig() {
    try {
      const resp = await fetch(`${API_BASE}/api/email/config`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.sender_email) {
          window.DEFAULT_SENDER_EMAIL = data.sender_email;
        }
        return data;
      }
    } catch (e) {
      console.warn("[EmailService] Failed to load config:", e);
    }
    return { sender_email: "24070579@ycce.in", is_configured: true };
  }

  // Pre-fetch on load
  getConfig();

  return {
    sendCertificate,
    sendPassport,
    getConfig
  };
})();

// Attach globally
window.emailService = EMAIL_SERVICE;
