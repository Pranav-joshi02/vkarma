/**
 * Universal 3D ULPIN Search, Lookup & Tamper Validator
 */

class ULPINPortal {
  constructor() {
    this.searchInput = document.getElementById('ulpin-search-input');
    this.initSearch();
  }

  initSearch() {
    if (!this.searchInput) return;

    this.searchInput.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        const query = this.searchInput.value.trim();
        if (!query) return;
        await this.searchAndResolve(query);
      }
    });
  }

  async searchAndResolve(ulpinStr) {
    try {
      const resp = await fetch(`/api/ulpin/lookup/${encodeURIComponent(ulpinStr)}`);
      const data = await resp.json();

      if (!resp.ok) {
        alert(`ULPIN Verification Warning: ${data.detail || 'Invalid ULPIN'}`);
        return;
      }

      if (data.found_in_active_db) {
        const unit = data.unit;
        // Fly camera to unit in 3D viewer and inspect
        if (window.app && window.app.viewer3d) {
          window.app.viewer3d.selectUnit(unit.unit_id, true);
        }
      } else {
        alert(`ULPIN Syntax & Verhoeff Check Digit are VALID!\n(Note: Unit belongs to a different pilot tile than currently loaded).`);
      }

    } catch (err) {
      console.error(err);
      alert(`Search error: ${err.message}`);
    }
  }

  async verifyCustomULPIN(ulpinStr) {
    const resp = await fetch('/api/ulpin/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ulpin: ulpinStr })
    });
    return await resp.json();
  }
}
