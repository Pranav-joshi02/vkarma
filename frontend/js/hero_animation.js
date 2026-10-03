/**
 * VKARMA — Cinematic 150-Frame Scroll-Driven Hero Animation Engine
 * Features:
 * - HTML5 Canvas hardware-accelerated rendering
 * - Progressive batch frame preloading (1 -> 10 -> 30 -> 70 -> 150)
 * - RequestAnimationFrame loop with linear interpolation (lerp) for smooth motion
 * - Device Pixel Ratio (DPR) crisp display on Retina / 4K screens
 * - Synchronized editorial text phases (LAND -> IDENTITY -> INTELLIGENCE -> VKARMA)
 * - Seamless bridge transition into the ULPIN section
 */

(function () {
  'use strict';

  // Configurable frame manifest
  const TOTAL_FRAMES = 150;
  const getFramePath = (index) => {
    const clamped = Math.max(1, Math.min(TOTAL_FRAMES, index));
    return `/assets/hero-sequence/frame_${String(clamped).padStart(3, "0")}.jpg`;
  };

  // State
  const images = new Array(TOTAL_FRAMES);
  let loadedCount = 0;
  let isFirstFrameReady = false;
  let targetProgress = 0;
  let currentProgress = 0;
  let currentDrawnIndex = 1;
  let isRunning = false;

  // DOM Elements
  let trackEl, stickyStageEl, canvas, ctx, loaderEl, loaderBar, loaderText;
  let phaseTagEl, headlineEl, subtextEl, cardEl, overlayEl, telemetryFrameEl;

  // Editorial Copy Phases (Right -> Left -> Right -> Left alternating transitions)
  const PHASES = [
    {
      range: [0.0, 0.28],
      side: "right", // Phase 01: first on right side
      tag: "PHASE 01 • SPATIAL SUBSTRATE",
      headline: 'LAND<span class="accent-cyan">.</span>',
      subtext: "A digital infrastructure for understanding property, land, and 3D spatial boundaries from the ground up."
    },
    {
      range: [0.28, 0.58],
      side: "left", // Phase 02: then left
      tag: "PHASE 02 • VOLUMETRIC CADASTRAL ENVELOPE",
      headline: 'IDENTITY<span class="accent-cyan">.</span>',
      subtext: "Every parcel, floor, and air-rights corridor mapped into an unambiguous volumetric coordinate space."
    },
    {
      range: [0.58, 0.84],
      side: "right", // Phase 03: then again right
      tag: "PHASE 03 • CRYPTOGRAPHIC INTEGRITY",
      headline: 'INTELLIGENCE<span class="accent-cyan">.</span>',
      subtext: "Automated legal subdivision, RERA deed verification, and topological collision scanning in real-time."
    },
    {
      range: [0.84, 1.0],
      side: "left", // Phase 04: like that (left)
      tag: "PHASE 04 • DIGITAL LAND PASSPORT",
      headline: 'VKARMA<span class="accent-cyan">.</span>',
      subtext: "The National 3D Cadastral Digital Twin & Land Passport System. One identity. One property."
    }
  ];

  let currentPhaseIndex = -1;

  function init() {
    trackEl = document.getElementById("hero-scroll-track");
    stickyStageEl = document.getElementById("hero-sticky-stage");
    canvas = document.getElementById("hero-canvas");
    if (!canvas) return;

    ctx = canvas.getContext("2d", { alpha: false });

    loaderEl = document.getElementById("hero-loader");
    loaderBar = document.getElementById("loader-bar");
    loaderText = document.getElementById("loader-status-text");

    phaseTagEl = document.getElementById("hero-phase-tag");
    headlineEl = document.getElementById("hero-headline");
    subtextEl = document.getElementById("hero-subtext");
    cardEl = document.getElementById("hero-editorial-card");
    overlayEl = document.getElementById("hero-editorial-overlay");
    telemetryFrameEl = document.getElementById("telemetry-frame");

    handleResize();
    window.addEventListener("resize", handleResize, { passive: true });
    window.addEventListener("scroll", handleScroll, { passive: true });

    // Reduced motion check
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      loadFirstFrameOnly();
      return;
    }

    // Step 1: Immediate First Frame Paint
    loadFirstFrame(() => {
      // Step 2: Progressive Batch Loading
      startProgressivePreload();
      // Step 3: Start Render Loop
      startRenderLoop();
    });
  }

  function handleResize() {
    if (!canvas || !ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2); // Cap at 2 for performance
    const w = stickyStageEl.clientWidth || window.innerWidth;
    const h = stickyStageEl.clientHeight || window.innerHeight;

    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);

    // Re-draw current frame after resize
    if (images[currentDrawnIndex - 1] && images[currentDrawnIndex - 1].complete) {
      drawFrame(currentDrawnIndex);
    }
  }

  function handleScroll() {
    if (!trackEl) return;
    const rect = trackEl.getBoundingClientRect();
    const trackHeight = trackEl.offsetHeight;
    const viewportHeight = window.innerHeight;

    // Track scroll distance: top of track reaches top of screen to end of track
    const totalScrollable = trackHeight - viewportHeight;
    const scrolled = -rect.top;

    if (totalScrollable <= 0) {
      targetProgress = 0;
      return;
    }

    const progress = Math.max(0, Math.min(1, scrolled / totalScrollable));
    targetProgress = progress;
  }

  function loadFirstFrame(onReady) {
    const img = new Image();
    img.src = getFramePath(1);
    img.onload = () => {
      images[0] = img;
      loadedCount++;
      isFirstFrameReady = true;
      drawFrame(1);
      updateLoaderUI(1);
      if (onReady) onReady();
    };
    img.onerror = () => {
      console.warn("Failed to load initial frame 1");
      if (onReady) onReady();
    };
  }

  function loadFirstFrameOnly() {
    const img = new Image();
    img.src = getFramePath(1);
    img.onload = () => {
      images[0] = img;
      drawFrame(1);
      if (loaderEl) loaderEl.classList.add("loaded");
    };
  }

  /**
   * Progressive batch loading:
   * Frames 1-10 -> Frames 11-30 -> Frames 31-70 -> Frames 71-150
   */
  async function startProgressivePreload() {
    const batches = [
      { start: 2, end: 10 },
      { start: 11, end: 35 },
      { start: 36, end: 75 },
      { start: 76, end: TOTAL_FRAMES }
    ];

    for (let b = 0; b < batches.length; b++) {
      const { start, end } = batches[b];
      await loadBatch(start, end);

      // Once the first 25 frames are loaded, reveal the hero view seamlessly
      if (b === 1 && loaderEl) {
        loaderEl.classList.add("loaded");
      }
    }

    if (loaderEl) loaderEl.classList.add("loaded");
  }

  function loadBatch(startIdx, endIdx) {
    return new Promise((resolve) => {
      let pending = endIdx - startIdx + 1;
      if (pending <= 0) return resolve();

      for (let i = startIdx; i <= endIdx; i++) {
        if (images[i - 1]) {
          pending--;
          if (pending === 0) resolve();
          continue;
        }

        const img = new Image();
        img.src = getFramePath(i);
        img.onload = () => {
          images[i - 1] = img;
          loadedCount++;
          updateLoaderUI(loadedCount);
          pending--;
          if (pending === 0) resolve();
        };
        img.onerror = () => {
          // Fallback to nearest prior frame
          images[i - 1] = images[Math.max(0, i - 2)] || images[0];
          pending--;
          if (pending === 0) resolve();
        };
      }
    });
  }

  function updateLoaderUI(count) {
    if (!loaderBar) return;
    const pct = Math.min(100, Math.round((count / TOTAL_FRAMES) * 100));
    loaderBar.style.width = pct + "%";
    if (loaderText) {
      loaderText.textContent = `Initializing spatial intelligence... ${pct}% (${count}/${TOTAL_FRAMES} frames)`;
    }
  }

  function drawFrame(frameNumber) {
    if (!ctx || !canvas) return;
    const img = images[frameNumber - 1];
    if (!img || !img.complete || img.naturalWidth === 0) {
      // Find nearest loaded prior frame
      for (let f = frameNumber - 1; f >= 1; f--) {
        if (images[f - 1] && images[f - 1].complete) {
          drawScaledImage(images[f - 1]);
          return;
        }
      }
      return;
    }
    drawScaledImage(img);
  }

  function drawScaledImage(img) {
    const cWidth = canvas.width;
    const cHeight = canvas.height;
    const iWidth = img.naturalWidth;
    const iHeight = img.naturalHeight;

    // Use "contain" to ensure the entire building parcel and surroundings remain intact
    // or cover with safe margins. Contain guarantees the 3D cutaway and HUD callouts are never cropped.
    const hRatio = cWidth / iWidth;
    const vRatio = cHeight / iHeight;
    const ratio = Math.min(hRatio, vRatio);

    const destW = iWidth * ratio;
    const destH = iHeight * ratio;
    const destX = (cWidth - destW) / 2;
    const destY = (cHeight - destH) / 2;

    // Clear and draw
    ctx.fillStyle = "#F5F7F8";
    ctx.fillRect(0, 0, cWidth, cHeight);
    ctx.drawImage(img, 0, 0, iWidth, iHeight, destX, destY, destW, destH);
  }

  function updateEditorialText(progress) {
    let matchedPhaseIndex = 0;
    for (let i = 0; i < PHASES.length; i++) {
      if (progress >= PHASES[i].range[0] && progress <= PHASES[i].range[1]) {
        matchedPhaseIndex = i;
        break;
      }
    }

    if (matchedPhaseIndex !== currentPhaseIndex) {
      const isInitial = currentPhaseIndex === -1;
      currentPhaseIndex = matchedPhaseIndex;
      const phase = PHASES[matchedPhaseIndex];

      if (isInitial) {
        if (overlayEl) {
          overlayEl.classList.remove("pos-left", "pos-right");
          overlayEl.classList.add(phase.side === "right" ? "pos-right" : "pos-left");
        }
        if (phaseTagEl) phaseTagEl.textContent = phase.tag;
        if (headlineEl) headlineEl.innerHTML = phase.headline;
        if (subtextEl) subtextEl.textContent = phase.subtext;
        if (cardEl) {
          cardEl.style.opacity = "1";
          cardEl.style.transform = "translateX(0)";
        }
      } else {
        if (cardEl) {
          cardEl.style.opacity = "0";
          cardEl.style.transform = phase.side === "right" ? "translateX(-24px)" : "translateX(24px)";
        }

        setTimeout(() => {
          if (overlayEl) {
            overlayEl.classList.remove("pos-left", "pos-right");
            overlayEl.classList.add(phase.side === "right" ? "pos-right" : "pos-left");
          }

          if (phaseTagEl) phaseTagEl.textContent = phase.tag;
          if (headlineEl) headlineEl.innerHTML = phase.headline;
          if (subtextEl) subtextEl.textContent = phase.subtext;

          if (cardEl) {
            cardEl.style.opacity = "1";
            cardEl.style.transform = "translateX(0)";
          }
        }, 130);
      }
    }

    if (telemetryFrameEl) {
      telemetryFrameEl.textContent = `FRAME: ${String(currentDrawnIndex).padStart(3, "0")} / 150`;
    }
  }

  function startRenderLoop() {
    if (isRunning) return;
    isRunning = true;

    function render() {
      // Smooth lerp: currentProgress moves towards targetProgress
      const lerpFactor = 0.14;
      currentProgress += (targetProgress - currentProgress) * lerpFactor;

      if (Math.abs(targetProgress - currentProgress) < 0.0001) {
        currentProgress = targetProgress;
      }

      // Map progress [0..1] to [1..150]
      const targetFrame = Math.max(1, Math.min(TOTAL_FRAMES, Math.floor(currentProgress * (TOTAL_FRAMES - 1)) + 1));

      if (targetFrame !== currentDrawnIndex) {
        currentDrawnIndex = targetFrame;
        drawFrame(currentDrawnIndex);
        updateEditorialText(currentProgress);
      }

      requestAnimationFrame(render);
    }

    requestAnimationFrame(render);
  }

  // Self-initialize on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Export for external hooks if needed
  window.HeroAnimation = {
    drawFrame,
    getProgress: () => currentProgress,
    getLoadedCount: () => loadedCount
  };
})();
