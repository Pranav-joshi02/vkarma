/**
 * Address-as-a-Service (UPI for 3D Addresses) Logistics API Tester
 */

class DeliveryAPIDemo {
  constructor() {
    this.modal = document.getElementById('delivery-modal');
  }

  async openDeliveryResolver(ulpin) {
    if (!ulpin) {
      const activeText = document.getElementById('active-unit-ulpin');
      ulpin = activeText ? activeText.innerText.trim() : '560103-A-5ZS90BBJ-8';
    }

    try {
      const resp = await fetch(`/api/delivery/resolve/${encodeURIComponent(ulpin)}`);
      const data = await resp.json();

      const bodyEl = document.getElementById('delivery-modal-body');
      if (bodyEl) {
        bodyEl.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div style="background: var(--accent-green-dim); border: 2px solid rgba(32, 217, 230, 0.35); border-radius: var(--radius-md); padding: 14px; box-shadow: var(--neu-flat);">
              <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Resolved 3D ULPIN</span>
              <div style="font-family: var(--font-mono); font-size: 16px; font-weight: 800; color: var(--text-primary);">${data.ulpin}</div>
              <div style="font-size: 13px; color: #18A7A8; margin-top: 2px; font-weight: 700;">${data.formatted_postal_address}</div>
            </div>

            <div class="details-grid">
              <div class="detail-item">
                <span class="detail-label">Latitude & Longitude</span>
                <span class="detail-value" style="font-family: var(--font-mono); font-size: 11px;">
                  ${data.precision_3d_coordinates.latitude}, ${data.precision_3d_coordinates.longitude}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Altitude (AGL)</span>
                <span class="detail-value highlight">+${data.precision_3d_coordinates.altitude_agl_m} m</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Floor & Wing Quadrant</span>
                <span class="detail-value">Floor ${data.precision_3d_coordinates.floor_level} (${data.logistics_dispatch_routing.wing_quadrant})</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Recommended Core</span>
                <span class="detail-value">${data.logistics_dispatch_routing.elevator_core_recommended}</span>
              </div>
            </div>

            <div class="panel-card">
              <div class="panel-title">
                <span>Autonomous Drone / Courier Dropoff Payload</span>
                <span class="panel-title-badge">JSON Response</span>
              </div>
              <pre style="font-family: var(--font-mono); font-size: 11px; color: #18A7A8; background: var(--bg-deep); box-shadow: var(--neu-concave); padding: 12px; border-radius: var(--radius-sm); overflow-x: auto;">
${JSON.stringify(data, null, 2)}
              </pre>
            </div>
          </div>
        `;
      }

      if (this.modal) this.modal.classList.add('active');

    } catch (err) {
      console.error(err);
      alert(`Delivery API error: ${err.message}`);
    }
  }

  closeModal() {
    if (this.modal) this.modal.classList.remove('active');
  }
}
