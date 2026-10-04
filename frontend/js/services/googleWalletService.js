/**
 * vKarma Google Wallet Service
 * Generates and displays official Google Wallet Generic Passes for 3D Land Passports.
 */

const GOOGLE_WALLET_SERVICE = (function () {
  const API_BASE = window.CONFIG && window.CONFIG.API_BASE_URL !== undefined 
    ? window.CONFIG.API_BASE_URL 
    : "";

  /**
   * Generates a Google Wallet Pass for a 3D ULPIN.
   * @param {string} ulpin - 3D ULPIN
   * @param {string} [name] - Citizen / Owner name
   * @returns {Promise<Object>} API response
   */
  async function generatePass(ulpin, name = "") {
    if (!ulpin) {
      throw new Error("ULPIN is required to generate Google Wallet Pass.");
    }

    const payload = {
      ulpin: ulpin.trim().toUpperCase(),
      recipient_name: name.trim() || undefined,
      origin: window.location.origin
    };

    const response = await fetch(`${API_BASE}/api/wallet/google-pass`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate Google Wallet pass.");
    }

    return await response.json();
  }

  /**
   * Opens the interactive Google Wallet preview modal.
   * @param {Object} passData - Pass data returned from generatePass
   */
  function showWalletModal(passData) {
    const modal = document.getElementById("wallet-modal");
    const body = document.getElementById("wallet-modal-body");
    if (!modal || !body) return;

    const pass = passData.pass_object || {};
    const textModules = pass.textModulesData || [];
    const ulpin = passData.ulpin || "";
    const ownerName = passData.owner_name || "Citizen Owner";
    const saveUrl = passData.save_url || "#";

    const getField = (id, fallback = "—") => {
      const item = textModules.find(m => m.id === id);
      return item ? item.body : fallback;
    };

    const spaceType = getField("space_type", "Air Rights (A)");
    const floor = getField("floor_level", "Level 1");
    const carpetArea = getField("carpet_area", "—");
    const volume = getField("volume", "—");
    const zBounds = getField("z_bounds", "—");
    const standard = getField("iso_standard", "ISO 19152 LADM");

    // QR code generation using quickchart or google chart qr api
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent('https://vkarma.in/ulpin/' + ulpin)}&color=002244`;

    body.style.overflowY = "auto";
    body.style.maxHeight = "calc(90vh - 70px)";
    body.style.overscrollBehavior = "contain";

    body.innerHTML = `
      <div style="font-family: var(--font-sans); display: flex; flex-direction: column; align-items: center; width: 100%;">
        
        <!-- Primary Action Banner (Prominent at Top) -->
        <div style="width: 100%; max-width: 360px; margin-bottom: 16px;">
          <a href="${saveUrl}" target="_blank" rel="noopener noreferrer" style="display: flex; align-items: center; justify-content: center; gap: 10px; background: #131314; color: #ffffff; text-decoration: none; padding: 13px 20px; border-radius: 28px; font-size: 14px; font-weight: 700; box-shadow: 0 6px 20px rgba(0,0,0,0.4); border: 1.5px solid #444746; transition: all 0.2s ease;">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
            </svg>
            <span>Save to Google Wallet &rarr;</span>
          </a>
          <div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 6px;">
            Click to save live to your Google Account and sync to phone
          </div>
        </div>

        <!-- Google Wallet Card Simulation -->
        <div style="width: 100%; max-width: 360px; background: linear-gradient(145deg, #00172e 0%, #002b54 60%, #0B1F33 100%); border-radius: 18px; box-shadow: 0 16px 40px rgba(0, 34, 68, 0.4), 0 2px 6px rgba(0,0,0,0.2); color: #fff; overflow: hidden; border: 1.5px solid rgba(255, 215, 0, 0.35); position: relative;">
          
          <!-- Top Accent Hologram Ribbon -->
          <div style="background: linear-gradient(90deg, #FF9933 0%, #FFFFFF 50%, #138808 100%); height: 4px; width: 100%;"></div>

          <!-- Card Header -->
          <div style="padding: 14px 18px 12px 18px; display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255,255,255,0.08);">
            <div>
              <div style="font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; color: #94a3b8;">Sovereign 3D Cadastre</div>
              <div style="font-size: 15px; font-weight: 900; color: #ffffff; letter-spacing: -0.2px; margin-top: 2px;">vKarma Pass</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.12); padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; color: #facc15; border: 1px solid rgba(250, 204, 21, 0.4); display: flex; align-items: center; gap: 4px;">
              <i class="fa-brands fa-google"></i> Wallet
            </div>
          </div>

          <!-- Card Body: Property & ULPIN -->
          <div style="padding: 14px 18px;">
            <div style="font-size: 10px; text-transform: uppercase; color: #94a3b8; font-weight: 700; letter-spacing: 0.5px;">Title Holder</div>
            <div style="font-size: 16px; font-weight: 900; color: #ffffff; margin-top: 1px;">${ownerName}</div>

            <div style="margin-top: 10px; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 6px 10px;">
              <div style="font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: 800; letter-spacing: 0.8px;">3D Bhu-Aadhaar ULPIN</div>
              <div style="font-size: 12px; font-weight: 900; color: #38bdf8; font-family: monospace; letter-spacing: 0.5px; margin-top: 2px; word-break: break-all;">
                ${ulpin}
              </div>
            </div>

            <!-- Spatial Attributes Grid -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
              <div style="background: rgba(255,255,255,0.05); padding: 6px 8px; border-radius: 6px;">
                <div style="font-size: 8px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">Space Type</div>
                <div style="font-size: 11px; font-weight: 800; color: #f1f5f9; margin-top: 1px;">${spaceType}</div>
              </div>
              <div style="background: rgba(255,255,255,0.05); padding: 6px 8px; border-radius: 6px;">
                <div style="font-size: 8px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">Floor Level</div>
                <div style="font-size: 11px; font-weight: 800; color: #f1f5f9; margin-top: 1px;">${floor}</div>
              </div>
              <div style="background: rgba(255,255,255,0.05); padding: 6px 8px; border-radius: 6px;">
                <div style="font-size: 8px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">Carpet Area</div>
                <div style="font-size: 11px; font-weight: 800; color: #f1f5f9; margin-top: 1px;">${carpetArea}</div>
              </div>
              <div style="background: rgba(255,255,255,0.05); padding: 6px 8px; border-radius: 6px;">
                <div style="font-size: 8px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">3D Volume</div>
                <div style="font-size: 11px; font-weight: 800; color: #f1f5f9; margin-top: 1px;">${volume}</div>
              </div>
            </div>

            <div style="margin-top: 8px; font-size: 9px; color: #94a3b8; display: flex; justify-content: space-between;">
              <span>Z: <strong style="color: #cbd5e1;">${zBounds}</strong></span>
              <span><strong style="color: #22c55e;"><i class="fa-solid fa-shield-halved"></i> Verhoeff D5</strong></span>
            </div>
          </div>

          <!-- QR Code Section -->
          <div style="background: #ffffff; padding: 12px 16px; text-align: center; border-top: 2px dashed rgba(255,255,255,0.2);">
            <div style="display: inline-block; background: #fff; padding: 6px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
              <img src="${qrUrl}" alt="Google Wallet QR" style="width: 110px; height: 110px; display: block;" />
            </div>
            <div style="font-size: 10px; font-weight: 700; color: #002244; margin-top: 4px;">
              Scan to Verify 3D Title on Mobile
            </div>
            <div style="font-size: 8px; color: #64748b; margin-top: 1px;">
              ${standard} &bull; Sovereign Digital India
            </div>
          </div>

        </div>

        <!-- Modal Action Buttons (No Copy Link) -->
        <div style="margin-top: 14px; width: 100%; max-width: 360px; display: flex; gap: 8px;">
          <a href="${saveUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="flex: 1; text-align: center; text-decoration: none; padding: 11px; font-size: 13px; font-weight: 700; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; background: linear-gradient(135deg, #002244 0%, #005A9C 100%);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
            </svg>
            <span>Open Google Wallet &rarr;</span>
          </a>
          <button type="button" class="btn-secondary" style="padding: 11px 18px; font-size: 12px; border-radius: 8px; cursor: pointer;" onclick="document.getElementById('wallet-modal').classList.remove('active')">
            Close
          </button>
        </div>

      </div>
    `;

    modal.classList.add("active");
  }

  /**
   * Helper to show direct Google Wallet notification toast banner
   */
  function showDirectNotification(passData) {
    if (!passData || !passData.save_url) return;

    let existing = document.getElementById("wallet-direct-notification");
    if (existing) existing.remove();

    const container = document.createElement("div");
    container.id = "wallet-direct-notification";
    container.style.cssText = "position: fixed; bottom: 24px; right: 24px; z-index: 10001; background: #0B1F33; border: 1.5px solid #4285F4; border-radius: 14px; padding: 16px 20px; box-shadow: 0 16px 40px rgba(0,0,0,0.6); color: #fff; max-width: 400px; display: flex; flex-direction: column; gap: 10px; animation: slideUp 0.3s ease-out;";

    container.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 8px; color: #60a5fa;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
          </svg>
          <span>Google Wallet Pass Created!</span>
        </div>
        <button onclick="this.closest('#wallet-direct-notification').remove()" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 16px; padding: 2px;">✕</button>
      </div>
      <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
        Direct Google Wallet save opened in a new tab. Click <strong>Save</strong> in Google Wallet to sync your 3D Land Passport to your phone.
      </div>
      <div style="display: flex; gap: 8px; margin-top: 4px;">
        <a href="${passData.save_url}" target="_blank" rel="noopener noreferrer" style="flex: 1; text-align: center; background: #4285F4; color: #ffffff; font-size: 12px; font-weight: 700; padding: 9px 12px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 12px rgba(66, 133, 244, 0.4);">
          <span>Open Wallet &rarr;</span>
        </a>
        <button type="button" id="btn-toast-view-card" style="background: rgba(255,255,255,0.12); color: #f8fafc; border: 1px solid rgba(255,255,255,0.25); font-size: 12px; font-weight: 600; padding: 9px 12px; border-radius: 8px; cursor: pointer;">
          View Pass Card / QR
        </button>
      </div>
    `;

    document.body.appendChild(container);

    const viewCardBtn = container.querySelector("#btn-toast-view-card");
    if (viewCardBtn) {
      viewCardBtn.onclick = () => {
        showWalletModal(passData);
      };
    }

    setTimeout(() => {
      if (container && container.parentNode) {
        container.remove();
      }
    }, 15000);
  }

  /**
   * Directly creates and opens the Google Wallet pass in a new tab.
   * @param {string} ulpin - 3D ULPIN
   * @param {string} [name] - Citizen / Owner name
   */
  async function saveDirectly(ulpin, name = "") {
    const res = await generatePass(ulpin, name);
    if (res && res.save_url) {
      window.open(res.save_url, "_blank");
      showDirectNotification(res);
    }
    return res;
  }

  return {
    generatePass,
    showWalletModal,
    showDirectNotification,
    saveDirectly
  };
})();

// Global registration
window.googleWalletService = GOOGLE_WALLET_SERVICE;
