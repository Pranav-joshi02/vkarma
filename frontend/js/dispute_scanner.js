/**
 * 3D Topological Dispute & Encroachment Scanner (Jaljolie et al.)
 */

class DisputeScanner {
  constructor() {
    this.modal = document.getElementById('dispute-modal');
  }

  async runDisputeScan() {
    try {
      const resp = await fetch('/api/disputes/scan', { method: 'POST' });
      const report = await resp.json();

      this.displayDisputeReport(report);

      // Switch 3D view to status mode to highlight disputed units in red
      if (window.app && window.app.viewer3d) {
        window.app.viewer3d.setColorMode('status');
      }

    } catch (err) {
      console.error(err);
      alert(`Dispute scan error: ${err.message}`);
    }
  }

  displayDisputeReport(report) {
    const bodyEl = document.getElementById('dispute-modal-body');
    if (!bodyEl) return;

    if (report.total_conflicts_detected === 0) {
      bodyEl.innerHTML = `
        <div style="text-align: center; padding: 28px; color: #0a8a4a;">
          <svg viewBox="0 0 20 20" fill="#0a8a4a" width="40" height="40" style="display: block; margin: 0 auto 12px;">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <h3 style="color: var(--text-primary); font-weight: 800;">Zero 3D Volumetric Encroachments Detected</h3>
          <p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
            All ${report.total_units_evaluated} 3D Legal Space Units conform strictly to ISO 19152 manifold topological rules.
          </p>
        </div>
      `;
    } else {
      bodyEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="background: rgba(239, 68, 68, 0.08); border: 2px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius-md); padding: 14px; color: var(--accent-crimson); font-size: 13px; box-shadow: var(--neu-flat);">
            <strong>
              <svg viewBox="0 0 16 16" fill="#ef4444" width="14" height="14" style="vertical-align: middle; margin-right: 4px;">
                <path fill-rule="evenodd" d="M6.701 2.076c.58-1.035 2.018-1.035 2.598 0L14.466 11C15.04 12.023 14.341 13.3 13.167 13.3H2.833c-1.174 0-1.873-1.277-1.3-2.3L6.7 2.076z"/>
              </svg>
              ${report.total_conflicts_detected} Vertical Encroachment / Overlap Conflict(s) Detected!
            </strong>
            <p style="margin-top: 4px; font-size: 11px; color: var(--text-secondary);">
              The topological relationship engine detected illegal 3D intersections violating common fire escapes and shared boundaries.
            </p>
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px; max-height: 350px; overflow-y: auto;">
            ${report.conflicts.map(c => `
              <div class="panel-card" style="border-left: 4px solid #ef4444;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 12px; font-weight: 800; color: #ef4444;">${c.type}</span>
                  <span style="font-size: 11px; font-family: var(--font-mono); color: #0a8a4a; font-weight: 700;">${c.overlap_volume_m3} m³ Overlap</span>
                </div>
                <p style="font-size: 12px; color: var(--text-primary); margin-top: 4px;">${c.message}</p>
                <div style="display: flex; gap: 8px; margin-top: 6px;">
                  <button class="btn-copy" onclick="window.app.viewer3d.selectUnit('${c.unit_a}', true)">
                    <i class="fa-solid fa-eye"></i> View Unit A
                  </button>
                  <button class="btn-copy" onclick="window.app.viewer3d.selectUnit('${c.unit_b}', true)">
                    <i class="fa-solid fa-eye"></i> View Unit B
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (this.modal) this.modal.classList.add('active');
  }

  closeModal() {
    if (this.modal) this.modal.classList.remove('active');
  }
}
