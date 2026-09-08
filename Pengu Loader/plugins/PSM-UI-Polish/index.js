/**
 * @name PSM-UI-Polish
 * @description Final visual hierarchy and layout polish for Personal Skin Manager settings.
 */
(function initPsmUiPolish() {
  const STYLE_ID = "psm-ui-polish-style";
  const SETTINGS_FLYOUT = "#rose-settings-flyout";
  const AUTOMATION_MODAL = "#psm-client-automation-modal";

  const ICONS = {
    runtime: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-6 4 12 2-6h6"/></svg>`,
    startup: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v8"/><path d="M7.5 6.5a8 8 0 1 0 9 0"/></svg>`,
    game: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v11H4z"/><path d="M8 11v4M6 13h4M15 12h.01M18 15h.01"/></svg>`,
    content: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l8 4-8 4-8-4 8-4z"/><path d="M4 12l8 4 8-4M4 17l8 4 8-4"/></svg>`,
    tools: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 6a4 4 0 0 0-5 5L4 16l4 4 5-5a4 4 0 0 0 5-5l-3 3-4-4 3-3z"/></svg>`,
    about: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M6 20c.6-4 2.6-6 6-6s5.4 2 6 6"/></svg>`,
  };

  const SECTION_MAP = [
    { token: "01 / RUNTIME", icon: "runtime" },
    { token: "02 / STARTUP", icon: "startup" },
    { token: "03 / GAME", icon: "game" },
    { token: "04 / CONTENT", icon: "content" },
    { token: "05 / TOOLS", icon: "tools" },
    { token: "06 / ABOUT", icon: "about" },
  ];

  function svgIcon(name) {
    return ICONS[name] || ICONS.runtime;
  }

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* -------------------------------------------------------------
         Main Personal Skin Manager settings hierarchy
         ------------------------------------------------------------- */
      ${SETTINGS_FLYOUT} .psm-section-heading.psm-core-decorated {
        width:100% !important;
        display:grid !important;
        grid-template-columns:36px minmax(0,1fr) !important;
        align-items:start !important;
        column-gap:12px !important;
        box-sizing:border-box !important;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-icon {
        width:34px;
        height:34px;
        display:grid;
        place-items:center;
        margin-top:1px;
        border:1px solid rgba(49,214,232,.30);
        border-radius:7px;
        color:#67e8f9;
        background:rgba(49,214,232,.055);
        box-sizing:border-box;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-icon svg {
        width:17px;
        height:17px;
        fill:none;
        stroke:currentColor;
        stroke-width:1.8;
        stroke-linecap:round;
        stroke-linejoin:round;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-copy {
        min-width:0;
        display:block;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-copy .psm-section-eyebrow {
        margin-top:0 !important;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-copy .psm-section-title {
        margin-top:3px !important;
      }
      ${SETTINGS_FLYOUT} .psm-core-section-copy .psm-section-description {
        margin-top:3px !important;
      }

      /* -------------------------------------------------------------
         Client Automation final control layout
         ------------------------------------------------------------- */
      ${AUTOMATION_MODAL} .psm-ca-panel {
        width:min(900px,calc(100vw - 48px)) !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-body {
        padding:20px 24px 0 !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-section {
        margin-top:24px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-matchmaking {
        display:grid !important;
        grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important;
        gap:10px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-matchmaking > .psm-ca-span-2 {
        grid-column:1 / -1 !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-matchmaking > .psm-ca-toggle,
      ${AUTOMATION_MODAL} .psm-ca-final-matchmaking > .psm-ca-field,
      ${AUTOMATION_MODAL} .psm-ca-final-champion-toggles > .psm-ca-toggle,
      ${AUTOMATION_MODAL} .psm-ca-priority-editor {
        min-height:74px;
        padding:14px 16px !important;
        border-color:#263746 !important;
        border-radius:6px !important;
        background:#0d141b !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-matchmaking > .psm-ca-toggle,
      ${AUTOMATION_MODAL} .psm-ca-final-champion-toggles > .psm-ca-toggle {
        align-items:center !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-champion-toggles {
        display:grid !important;
        grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important;
        gap:10px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-final-priority-grid {
        display:grid !important;
        grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important;
        gap:10px !important;
        margin-top:10px !important;
        align-items:start !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-inline-protect {
        min-height:0 !important;
        margin:10px 0 2px !important;
        padding:10px 11px !important;
        border:1px solid #263746 !important;
        border-radius:5px !important;
        background:#0a1118 !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-inline-protect .psm-ca-help {
        max-width:280px;
      }

      /* Consistent form controls */
      ${AUTOMATION_MODAL} input[type="text"],
      ${AUTOMATION_MODAL} input[type="number"],
      ${AUTOMATION_MODAL} select {
        height:40px !important;
        margin-top:8px !important;
        padding:0 11px !important;
        border:1px solid #304354 !important;
        border-radius:5px !important;
        background:#090f15 !important;
        color:#edf3f8 !important;
        box-sizing:border-box !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-search-shell {
        min-height:40px !important;
        border-radius:5px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-search-shell input {
        height:38px !important;
        margin-top:0 !important;
        border:0 !important;
        background:transparent !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-add-row {
        grid-template-columns:minmax(0,1fr) 88px !important;
        gap:8px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-add {
        min-width:88px !important;
        height:40px !important;
        border-radius:5px !important;
      }

      /* Replace browser checkboxes with one consistent compact switch. */
      ${AUTOMATION_MODAL} input[type="checkbox"] {
        -webkit-appearance:none !important;
        appearance:none !important;
        width:38px !important;
        min-width:38px !important;
        height:20px !important;
        min-height:20px !important;
        margin:0 !important;
        border:1px solid #3a4b59 !important;
        border-radius:999px !important;
        outline:none !important;
        cursor:pointer !important;
        background-color:#0a1118 !important;
        background-image:radial-gradient(circle at 9px 9px,#8191a2 0 5px,transparent 5.7px) !important;
        transition:background-color .14s ease,border-color .14s ease,box-shadow .14s ease !important;
      }
      ${AUTOMATION_MODAL} input[type="checkbox"]:checked {
        border-color:#31d6e8 !important;
        background-color:#31d6e8 !important;
        background-image:radial-gradient(circle at 27px 9px,#061014 0 5px,transparent 5.7px) !important;
        box-shadow:0 0 0 2px rgba(49,214,232,.07) !important;
      }
      ${AUTOMATION_MODAL} input[type="checkbox"]:focus-visible {
        box-shadow:0 0 0 2px rgba(49,214,232,.20) !important;
      }

      /* Priority rows and action buttons */
      ${AUTOMATION_MODAL} .psm-ca-priority-list {
        gap:6px !important;
        margin-top:10px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-priority-item {
        min-height:38px !important;
        padding:6px 7px !important;
        border-radius:5px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-icon-btn {
        width:30px !important;
        height:28px !important;
        border-radius:4px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-actions {
        position:sticky !important;
        bottom:0 !important;
        z-index:12 !important;
        display:grid !important;
        grid-template-columns:minmax(0,1fr) 112px 152px !important;
        align-items:center !important;
        gap:10px !important;
        margin:24px -24px 0 !important;
        padding:14px 24px 18px !important;
        border-top:1px solid #263746 !important;
        background:linear-gradient(180deg,rgba(8,13,18,.94),#080d12 32%) !important;
        box-shadow:0 -10px 24px rgba(0,0,0,.18) !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-secondary,
      ${AUTOMATION_MODAL} .psm-ca-primary {
        width:100% !important;
        min-width:0 !important;
        height:40px !important;
        min-height:40px !important;
        border-radius:5px !important;
      }
      ${AUTOMATION_MODAL} .psm-ca-save-status {
        min-width:0 !important;
        line-height:1.4 !important;
      }

      @media (max-width:760px) {
        ${AUTOMATION_MODAL} .psm-ca-final-matchmaking,
        ${AUTOMATION_MODAL} .psm-ca-final-champion-toggles,
        ${AUTOMATION_MODAL} .psm-ca-final-priority-grid {
          grid-template-columns:1fr !important;
        }
        ${AUTOMATION_MODAL} .psm-ca-final-matchmaking > .psm-ca-span-2 {
          grid-column:auto !important;
        }
        ${AUTOMATION_MODAL} .psm-ca-actions {
          grid-template-columns:1fr 1fr !important;
        }
        ${AUTOMATION_MODAL} .psm-ca-save-status {
          grid-column:1 / -1 !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function decorateCoreSections() {
    const flyout = document.querySelector(SETTINGS_FLYOUT);
    if (!flyout) return;

    flyout.querySelectorAll(".psm-section-heading").forEach((heading) => {
      if (heading.classList.contains("psm-core-decorated")) return;
      const eyebrow = String(heading.querySelector(".psm-section-eyebrow")?.textContent || "")
        .trim()
        .toUpperCase();
      const config = SECTION_MAP.find((entry) => eyebrow.includes(entry.token));
      if (!config) return;

      const iconBox = document.createElement("div");
      iconBox.className = "psm-core-section-icon";
      iconBox.innerHTML = svgIcon(config.icon);

      const copy = document.createElement("div");
      copy.className = "psm-core-section-copy";
      while (heading.firstChild) copy.appendChild(heading.firstChild);

      heading.appendChild(iconBox);
      heading.appendChild(copy);
      heading.classList.add("psm-core-decorated");
    });

    // Client Automation is visually the next section after 06 / ABOUT.
    const automationEyebrow = flyout.querySelector("#psm-client-automation-launcher .psm-ca-eyebrow span:last-child");
    if (automationEyebrow && automationEyebrow.textContent.trim() !== "07 / CLIENT AUTOMATION") {
      automationEyebrow.textContent = "07 / CLIENT AUTOMATION";
    }
  }

  function directParent(selector, parentClass) {
    const node = document.querySelector(selector);
    return node?.closest(parentClass) || null;
  }

  function finalizeAutomationLayout() {
    const modal = document.querySelector(AUTOMATION_MODAL);
    if (!modal) return;

    const sections = modal.querySelectorAll(".psm-ca-section");
    const matchmaking = sections[0];
    const champion = sections[1];
    if (!matchmaking || !champion) return;

    const matchmakingGrid = matchmaking.querySelector(".psm-ca-grid");
    if (matchmakingGrid && !matchmakingGrid.classList.contains("psm-ca-final-matchmaking")) {
      const queue = modal.querySelector("#psm-ca-queue-search")?.closest(".psm-ca-field");
      const autoQueue = modal.querySelector("#psm-ca-auto-queue")?.closest(".psm-ca-toggle");
      const autoRequeue = modal.querySelector("#psm-ca-auto-requeue")?.closest(".psm-ca-toggle");
      const primary = modal.querySelector("#psm-ca-primary-position")?.closest(".psm-ca-field");
      const secondary = modal.querySelector("#psm-ca-secondary-position")?.closest(".psm-ca-field");
      const autoAccept = modal.querySelector("#psm-ca-auto-accept")?.closest(".psm-ca-toggle");
      const delay = modal.querySelector("#psm-ca-accept-delay")?.closest(".psm-ca-field");

      if (queue) queue.classList.add("psm-ca-span-2");
      [queue, autoQueue, autoRequeue, primary, secondary, autoAccept, delay]
        .filter(Boolean)
        .forEach((node) => matchmakingGrid.appendChild(node));
      matchmakingGrid.classList.add("psm-ca-final-matchmaking");
    }

    const championGrids = champion.querySelectorAll(":scope > .psm-ca-grid");
    const toggleGrid = championGrids[0];
    const priorityGrid = championGrids[1];
    if (toggleGrid) {
      toggleGrid.classList.add("psm-ca-final-champion-toggles");
      const autoPick = modal.querySelector("#psm-ca-auto-pick")?.closest(".psm-ca-toggle");
      const autoBan = modal.querySelector("#psm-ca-auto-ban")?.closest(".psm-ca-toggle");
      [autoPick, autoBan].filter(Boolean).forEach((node) => toggleGrid.appendChild(node));
    }
    if (priorityGrid) priorityGrid.classList.add("psm-ca-final-priority-grid");

    // Protect Ally Intents belongs to the Ban configuration, so keep it with
    // the Ban priority editor instead of leaving a visually orphaned third card.
    const protect = modal.querySelector("#psm-ca-protect-ally")?.closest(".psm-ca-toggle");
    const banEditor = modal.querySelector("#psm-ca-ban-input")?.closest(".psm-ca-priority-editor");
    const banAddRow = banEditor?.querySelector(".psm-ca-add-row");
    if (protect && banEditor && banAddRow && !protect.classList.contains("psm-ca-inline-protect")) {
      protect.classList.add("psm-ca-inline-protect");
      banEditor.insertBefore(protect, banAddRow);
    }
  }

  let queued = false;
  function scheduleDecorate() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      injectStyles();
      decorateCoreSections();
      finalizeAutomationLayout();
    });
  }

  injectStyles();
  scheduleDecorate();

  const observer = new MutationObserver(scheduleDecorate);
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
