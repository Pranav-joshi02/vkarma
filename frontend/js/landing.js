/**
 * VKARMA Landing Page Controller
 * Handles ULPIN structure interactive breakdown, explore form,
 * sample chip triggers, and subtle scroll reveal micro-interactions.
 */

document.addEventListener("DOMContentLoaded", () => {
  initMobileNav();
  initUlpinStructureWidget();
  initExploreForm();
  initScrollAnimations();
});

/**
 * Mobile Navigation Drawer Toggle
 */
function initMobileNav() {
  const btn = document.getElementById("mobile-menu-btn");
  const menu = document.getElementById("nav-mobile-menu");
  if (!btn || !menu) return;

  btn.addEventListener("click", () => {
    menu.classList.toggle("open");
  });

  document.addEventListener("click", (e) => {
    if (!btn.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.remove("open");
    }
  });
}

/**
 * Interactive ULPIN Structure Diagram
 */
function initUlpinStructureWidget() {
  const segments = document.querySelectorAll(".segment-box");
  const detailPill = document.getElementById("structure-detail-pill");
  if (!segments.length || !detailPill) return;

  const segmentDescriptions = {
    pincode: "<strong>PPPPPP (6 Digits):</strong> Geographic Partitioning Key (Postal Pincode e.g. 560103 - Bengaluru Outer Ring Road).",
    spacetype: "<strong>T (1 Char):</strong> 3D Legal Space Type ('A': Apartment/Flat, 'B': Building Envelope, 'P': Parking, 'M': Common Amenity, 'R': Air-Rights, 'U': Subsurface Utility).",
    token: "<strong>RRRRRRRR (8 Chars):</strong> Cryptographic format-preserving Feistel token (pseudorandom, non-sequential, tamper-resistant parcel serial).",
    check: "<strong>C (1 Digit):</strong> Dihedral D5 Verhoeff Checksum (mathematically detects 100% of single typos and adjacent transposition errors)."
  };

  segments.forEach((seg) => {
    seg.addEventListener("click", () => {
      segments.forEach(s => s.classList.remove("active"));
      seg.classList.add("active");
      const key = seg.getAttribute("data-segment");
      if (segmentDescriptions[key]) {
        detailPill.innerHTML = segmentDescriptions[key];
      }
    });
  });
}

/**
 * Explore a ULPIN Form & Sample Chips
 */
function initExploreForm() {
  const form = document.getElementById("explore-form");
  const input = document.getElementById("explore-ulpin-input");
  const chips = document.querySelectorAll(".sample-chip");
  const validationBadge = document.getElementById("explore-live-val");

  if (!input) return;

  // Sample chips click
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const ulpin = chip.getAttribute("data-ulpin");
      input.value = ulpin;
      validateInput(ulpin);
      input.focus();
    });
  });

  // Real-time input validation
  input.addEventListener("input", () => {
    validateInput(input.value);
  });

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = input.value.trim().toUpperCase();
      if (!val) {
        input.focus();
        return;
      }
      // Navigate to dedicated Land Passport route
      window.location.href = `/ulpin/${encodeURIComponent(val)}`;
    });
  }

  function validateInput(str) {
    if (!validationBadge) return;
    const clean = str.trim().toUpperCase();
    if (!clean) {
      validationBadge.textContent = "";
      validationBadge.style.display = "none";
      return;
    }

    const parts = clean.split("-");
    if (parts.length === 4 && parts[0].length === 6 && parts[1].length === 1 && parts[2].length === 8 && parts[3].length === 1) {
      validationBadge.style.display = "inline-block";
      validationBadge.textContent = `✓ Syntax Matched: Type [${parts[1]}] • Pincode [${parts[0]}]`;
      validationBadge.style.color = "var(--color-teal)";
    } else {
      validationBadge.style.display = "inline-block";
      validationBadge.textContent = "Format: PPPPPP-T-RRRRRRRR-C";
      validationBadge.style.color = "var(--color-slate-gray)";
    }
  }
}

/**
 * Intersection Observer for subtle reveals
 */
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("revealed");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll(".observe-reveal").forEach((el) => {
    observer.observe(el);
  });
}
