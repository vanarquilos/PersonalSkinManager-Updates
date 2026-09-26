/**
 * @name PSM-UI-Polish
 * @description Visual hierarchy polish for Personal Skin Manager settings.
 *
 * v1.0.2 intentionally carries only the visual treatment from the
 * client-automation development branch. No Client Automation behavior,
 * settings, bridge messages, or controls are included here.
 */
(function initPsmUiPolish() {
  const STYLE_ID = "psm-ui-polish-style";
  const SETTINGS_FLYOUT = "#rose-settings-flyout";

  const ICONS = {
    runtime: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-6 4 12 2-6h6"/></svg>`,
    startup: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v8"/><path d="M7.5 6.5a8 8 0 1 0 9 0"/></svg>`,
    game: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v11H4z"/><path d="M8 11v4M6 13h4M15 12h.01M18 15h.01"/></svg>`,
    content: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l8 4-8 4-8-4 8-4z"/><path d="M4 12l8 4 8-4M4 17l8 4 8-4"/></svg>`,
    tools: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 6a4 4 0 0 0-5 5L4 16l4 4 5-5a4 4 0 0 0 5-5l-3 3-4-4 3-3z"/></svg>`,
    about: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M6 20c.6-4 2.6-6 6-6s5.4 2 6 6"/></svg>`,
  };

  // Keep the v1.0.2 information architecture unchanged. This is visual-only.
  const SECTION_MAP = [
    { tokens: ["01 / RUNTIME"], icon: "runtime", display: "01 / RUNTIME" },
    { tokens: ["02 / STARTUP"], icon: "startup", display: "02 / STARTUP" },
    { tokens: ["03 / GAME"], icon: "game", display: "03 / GAME" },
    { tokens: ["04 / CONTENT"], icon: "content", display: "04 / CONTENT" },
    { tokens: ["05 / TOOLS"], icon: "tools", display: "05 / TOOLS" },
    { tokens: ["06 / ABOUT"], icon: "about", display: "06 / ABOUT" },
  ];

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* Clean section hierarchy carried over from the vNext UI exploration. */
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
        box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
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

      /* Slightly tighten the visual rhythm without changing any controls. */
      ${SETTINGS_FLYOUT} .settings-section {
        transition:border-color .14s ease, background .14s ease, transform .14s ease !important;
      }

      ${SETTINGS_FLYOUT} .settings-section:hover {
        transform:translateY(-1px);
      }

      ${SETTINGS_FLYOUT} #logs-folder-button,
      ${SETTINGS_FLYOUT} #troubleshoot-button,
      ${SETTINGS_FLYOUT} #pengu-ui-button,
      ${SETTINGS_FLYOUT} #add-custom-mods-dropdown,
      ${SETTINGS_FLYOUT} #save-button {
        transition:border-color .14s ease, background .14s ease, color .14s ease, transform .14s ease !important;
      }

      ${SETTINGS_FLYOUT} #logs-folder-button:hover,
      ${SETTINGS_FLYOUT} #troubleshoot-button:hover,
      ${SETTINGS_FLYOUT} #pengu-ui-button:hover,
      ${SETTINGS_FLYOUT} #add-custom-mods-dropdown:hover,
      ${SETTINGS_FLYOUT} #save-button:hover {
        transform:translateY(-1px);
      }

      @media (max-width:560px) {
        ${SETTINGS_FLYOUT} .psm-section-heading.psm-core-decorated {
          grid-template-columns:32px minmax(0,1fr) !important;
          column-gap:10px !important;
        }

        ${SETTINGS_FLYOUT} .psm-core-section-icon {
          width:30px;
          height:30px;
          border-radius:6px;
        }

        ${SETTINGS_FLYOUT} .psm-core-section-icon svg {
          width:15px;
          height:15px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function headingEyebrow(heading) {
    return String(heading?.querySelector(".psm-section-eyebrow")?.textContent || "")
      .trim()
      .toUpperCase();
  }

  function decorateCoreSections() {
    const flyout = document.querySelector(SETTINGS_FLYOUT);
    if (!flyout) return;

    flyout.querySelectorAll(".psm-section-heading").forEach((heading) => {
      const eyebrow = headingEyebrow(heading);
      const config = SECTION_MAP.find((entry) =>
        entry.tokens.some((token) => eyebrow.includes(token))
      );
      if (!config) return;

      if (!heading.classList.contains("psm-core-decorated")) {
        const iconBox = document.createElement("div");
        iconBox.className = "psm-core-section-icon";
        iconBox.innerHTML = ICONS[config.icon] || ICONS.runtime;

        const copy = document.createElement("div");
        copy.className = "psm-core-section-copy";
        while (heading.firstChild) copy.appendChild(heading.firstChild);

        heading.appendChild(iconBox);
        heading.appendChild(copy);
        heading.classList.add("psm-core-decorated");
      }

      const label = heading.querySelector(".psm-section-eyebrow");
      if (label && label.textContent.trim() !== config.display) {
        label.textContent = config.display;
      }
    });
  }

  let queued = false;
  function scheduleDecorate() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      injectStyles();
      decorateCoreSections();
    });
  }

  injectStyles();
  scheduleDecorate();

  const observer = new MutationObserver(scheduleDecorate);
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
