/**
 * @name PSM-ClientAutomation
 * @description Personal Skin Manager Client Automation control surface.
 */
(function initPsmClientAutomation() {
  const LOG_PREFIX = "[PSM-ClientAutomation]";
  const LAUNCHER_ID = "psm-client-automation-launcher";
  const MODAL_ID = "psm-client-automation-modal";
  const STYLE_ID = "psm-client-automation-style";
  const CATALOG_RETRY_DELAYS = [900, 2200, 5000];

  const POSITION_OPTIONS = [
    ["", "Not set"],
    ["TOP", "Top"],
    ["JUNGLE", "Jungle"],
    ["MIDDLE", "Mid"],
    ["BOTTOM", "Bottom"],
    ["UTILITY", "Support"],
    ["FILL", "Fill"],
  ];

  const ICONS = {
    automation: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/><circle cx="12" cy="12" r="4"/></svg>`,
    activity: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-6 4 12 2-6h6"/></svg>`,
    matchmaking: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h10M12 4l3 3-3 3M19 17H9M12 14l-3 3 3 3"/></svg>`,
    champion: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-2.9 8.2-7 10-4.1-1.8-7-5.5-7-10V6l7-3z"/><path d="M9 12l2 2 4-4"/></svg>`,
    search: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6"/><path d="M16 16l4 4"/></svg>`,
    refresh: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.2 9A7 7 0 006.5 6.5L4 9M5.8 15A7 7 0 0017.5 17.5L20 15"/></svg>`,
    queue: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M5 12h14M5 18h9"/><circle cx="3" cy="6" r="1"/><circle cx="3" cy="12" r="1"/><circle cx="3" cy="18" r="1"/></svg>`,
    clock: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/></svg>`,
    role: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M6 20c.6-4 2.6-6 6-6s5.4 2 6 6"/></svg>`,
  };

  let bridge = null;
  let observer = null;
  let statusTimer = null;
  let catalogRetryTimer = null;
  let catalogRetryIndex = 0;
  let lastCatalogRequestAt = 0;
  let queueSuggestionIndex = -1;
  let championSuggestionIndex = { pick: -1, ban: -1 };
  let settings = defaultSettings();
  let catalog = defaultCatalog();
  let status = defaultStatus();

  function defaultSettings() {
    return {
      enabled: false,
      autoQueueEnabled: false,
      queueId: null,
      primaryPosition: null,
      secondaryPosition: null,
      autoAcceptEnabled: false,
      autoAcceptDelayMs: 1000,
      autoRequeueEnabled: false,
      autoPickEnabled: false,
      pickPriority: [],
      autoBanEnabled: false,
      banPriority: [],
      protectAllyIntents: true,
    };
  }

  function defaultCatalog() {
    return {
      queues: [],
      champions: [],
      currentQueueId: null,
      leagueConnected: false,
      queueCatalogAvailable: false,
      championCatalogAvailable: false,
      queueCatalogCached: false,
      championCatalogCached: false,
      catalogSource: "none",
      catalogUpdatedAt: null,
    };
  }

  function defaultStatus() {
    return {
      phase: null,
      status: "Disabled",
      enabled: false,
      connected: false,
      transport: "Disconnected",
    };
  }

  function icon(name, extraClass = "") {
    const svg = ICONS[name] || ICONS.automation;
    return `<span class="psm-ca-icon ${extraClass}" aria-hidden="true">${svg}</span>`;
  }

  function waitForBridge() {
    return new Promise((resolve, reject) => {
      const timeout = 10000;
      const interval = 50;
      let elapsed = 0;
      const check = () => {
        if (window.__roseBridge) return resolve(window.__roseBridge);
        elapsed += interval;
        if (elapsed >= timeout) return reject(new Error("Bridge not available"));
        setTimeout(check, interval);
      };
      check();
    });
  }

  function send(payload) {
    try {
      bridge?.send(payload);
    } catch (error) {
      console.warn(`${LOG_PREFIX} bridge send failed`, error);
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${LAUNCHER_ID} { width:100%; box-sizing:border-box; margin:16px 0 4px; }
      #${LAUNCHER_ID} .psm-ca-eyebrow { display:flex; align-items:center; gap:6px; color:#31d6e8; font:700 9px "Spiegel",Arial,sans-serif; letter-spacing:.16em; }
      #${LAUNCHER_ID} .psm-ca-card { margin-top:7px; padding:14px 15px; background:#0d141b; border:1px solid #21303d; border-radius:5px; }
      #${LAUNCHER_ID} .psm-ca-row { display:flex; align-items:center; gap:12px; }
      #${LAUNCHER_ID} .psm-ca-launcher-icon { width:34px; height:34px; flex:0 0 34px; display:grid; place-items:center; border:1px solid rgba(49,214,232,.28); border-radius:7px; background:rgba(49,214,232,.07); color:#67e8f9; }
      #${LAUNCHER_ID} .psm-ca-copy { flex:1; min-width:0; }
      #${LAUNCHER_ID} .psm-ca-title { color:#edf3f8; font:700 14px "Beaufort for LOL",serif; }
      #${LAUNCHER_ID} .psm-ca-status { margin-top:3px; color:#8191a2; font:10px/1.4 "Spiegel",Arial,sans-serif; }
      #${LAUNCHER_ID} .psm-ca-open { min-width:100px; min-height:34px; border:1px solid #31d6e8; border-radius:4px; background:#0b1219; color:#67e8f9; cursor:pointer; font:700 9px "Spiegel",Arial,sans-serif; }
      #${LAUNCHER_ID} .psm-ca-open:hover { background:#12202a; }

      .psm-ca-icon { display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; flex:0 0 auto; }
      .psm-ca-icon svg { width:100%; height:100%; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }

      #${MODAL_ID} { position:fixed; inset:0; z-index:10080; display:flex; align-items:center; justify-content:center; font-family:"Spiegel",Arial,sans-serif; }
      #${MODAL_ID} .psm-ca-backdrop { position:absolute; inset:0; background:rgba(0,0,0,.74); backdrop-filter:blur(2px); }
      #${MODAL_ID} .psm-ca-panel { position:relative; width:min(820px,calc(100vw - 48px)); max-height:calc(100vh - 64px); overflow:hidden; background:#080d12; border:1px solid #304354; border-top:2px solid #31d6e8; border-radius:8px; box-shadow:0 28px 80px rgba(0,0,0,.78); color:#edf3f8; }
      #${MODAL_ID} .psm-ca-header { display:flex; align-items:flex-start; gap:16px; padding:22px 24px 18px; border-bottom:1px solid #21303d; background:linear-gradient(180deg,rgba(49,214,232,.035),transparent); }
      #${MODAL_ID} .psm-ca-header-icon { width:38px; height:38px; display:grid; place-items:center; flex:0 0 38px; border:1px solid rgba(49,214,232,.32); border-radius:8px; color:#67e8f9; background:rgba(49,214,232,.07); }
      #${MODAL_ID} .psm-ca-header-icon .psm-ca-icon { width:20px; height:20px; }
      #${MODAL_ID} .psm-ca-header-copy { flex:1; }
      #${MODAL_ID} .psm-ca-kicker { color:#31d6e8; font-size:9px; font-weight:700; letter-spacing:.18em; }
      #${MODAL_ID} h2 { margin:5px 0 0; font:700 21px "Beaufort for LOL",serif; }
      #${MODAL_ID} .psm-ca-subtitle { margin-top:4px; color:#8191a2; font-size:10px; line-height:1.5; }
      #${MODAL_ID} .psm-ca-close { width:30px; height:30px; border:1px solid #304354; border-radius:4px; background:#0d141b; color:#8191a2; cursor:pointer; font-size:18px; }
      #${MODAL_ID} .psm-ca-close:hover { border-color:#31d6e8; color:#edf3f8; }
      #${MODAL_ID} .psm-ca-body { max-height:calc(100vh - 178px); overflow-y:auto; overflow-x:visible; padding:20px 24px 24px; scrollbar-width:thin; scrollbar-color:#31d6e8 #0b1016; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar { width:7px; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar-track { background:#0b1016; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar-thumb { background:#31d6e8; border-radius:8px; }

      #${MODAL_ID} .psm-ca-runtime { display:grid; grid-template-columns:38px minmax(0,1fr) auto; align-items:center; gap:12px; padding:13px 14px; margin-bottom:18px; background:#0d141b; border:1px solid #21303d; border-radius:6px; }
      #${MODAL_ID} .psm-ca-runtime-icon { width:36px; height:36px; display:grid; place-items:center; border:1px solid #263848; border-radius:7px; color:#8191a2; background:#0a1118; }
      #${MODAL_ID} .psm-ca-runtime-icon.on { color:#67e8f9; border-color:rgba(49,214,232,.35); background:rgba(49,214,232,.06); }
      #${MODAL_ID} .psm-ca-runtime-copy { min-width:0; }
      #${MODAL_ID} .psm-ca-runtime-title { color:#edf3f8; font-size:11px; font-weight:700; }
      #${MODAL_ID} .psm-ca-runtime-meta { margin-top:3px; color:#8191a2; font-size:9px; line-height:1.45; }
      #${MODAL_ID} .psm-ca-runtime-chips { display:flex; flex-wrap:wrap; gap:5px; margin-top:7px; }
      #${MODAL_ID} .psm-ca-chip { padding:3px 6px; border:1px solid #263746; border-radius:999px; color:#8294a5; background:#0a1118; font-size:8px; white-space:nowrap; }
      #${MODAL_ID} .psm-ca-chip.live { color:#73e7f2; border-color:rgba(49,214,232,.3); }
      #${MODAL_ID} .psm-ca-chip.cached { color:#d3b46f; border-color:rgba(211,180,111,.28); }
      #${MODAL_ID} .psm-ca-refresh { display:inline-flex; align-items:center; gap:6px; min-height:32px; padding:0 10px; border:1px solid #304354; border-radius:4px; background:#101820; color:#b7c4cf; cursor:pointer; font-size:8px; font-weight:700; white-space:nowrap; }
      #${MODAL_ID} .psm-ca-refresh:hover:not(:disabled) { border-color:#31d6e8; color:#67e8f9; }
      #${MODAL_ID} .psm-ca-refresh:disabled { opacity:.45; cursor:default; }
      #${MODAL_ID} .psm-ca-refresh .psm-ca-icon { width:13px; height:13px; }

      #${MODAL_ID} .psm-ca-section { margin-top:22px; }
      #${MODAL_ID} .psm-ca-section-heading { display:flex; align-items:flex-start; gap:10px; margin-bottom:10px; }
      #${MODAL_ID} .psm-ca-section-icon { width:31px; height:31px; display:grid; place-items:center; flex:0 0 31px; border:1px solid rgba(139,92,246,.32); border-radius:7px; color:#b39af8; background:rgba(139,92,246,.07); }
      #${MODAL_ID} .psm-ca-section-icon.matchmaking { color:#67e8f9; border-color:rgba(49,214,232,.3); background:rgba(49,214,232,.06); }
      #${MODAL_ID} .psm-ca-section-icon .psm-ca-icon { width:17px; height:17px; }
      #${MODAL_ID} .psm-ca-section-copy { min-width:0; }
      #${MODAL_ID} .psm-ca-section-eyebrow { color:#8b5cf6; font-size:8px; font-weight:700; letter-spacing:.17em; }
      #${MODAL_ID} .psm-ca-section-heading.matchmaking .psm-ca-section-eyebrow { color:#31d6e8; }
      #${MODAL_ID} .psm-ca-section-title { margin-top:3px; color:#edf3f8; font:700 15px "Beaufort for LOL",serif; }
      #${MODAL_ID} .psm-ca-section-desc { margin-top:3px; color:#8191a2; font-size:9px; line-height:1.45; }
      #${MODAL_ID} .psm-ca-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
      #${MODAL_ID} .psm-ca-field, #${MODAL_ID} .psm-ca-toggle { min-width:0; padding:13px 14px; background:#0d141b; border:1px solid #21303d; border-radius:5px; box-sizing:border-box; }
      #${MODAL_ID} .psm-ca-toggle { display:flex; align-items:center; justify-content:space-between; gap:14px; }
      #${MODAL_ID} .psm-ca-toggle-copy { min-width:0; }
      #${MODAL_ID} .psm-ca-label-row { display:flex; align-items:center; gap:6px; }
      #${MODAL_ID} .psm-ca-label-row .psm-ca-icon { width:13px; height:13px; color:#71869a; }
      #${MODAL_ID} .psm-ca-label { color:#cbd6df; font-size:10px; font-weight:700; }
      #${MODAL_ID} .psm-ca-help { margin-top:3px; color:#6f8091; font-size:8px; line-height:1.4; }
      #${MODAL_ID} input[type="checkbox"] { width:18px; height:18px; accent-color:#31d6e8; cursor:pointer; }
      #${MODAL_ID} input[type="text"], #${MODAL_ID} input[type="number"], #${MODAL_ID} select { width:100%; height:34px; margin-top:7px; padding:0 9px; box-sizing:border-box; background:#090f15; border:1px solid #304354; border-radius:4px; color:#edf3f8; font:10px "Spiegel",Arial,sans-serif; outline:none; }
      #${MODAL_ID} input:focus, #${MODAL_ID} select:focus { border-color:#31d6e8; }
      #${MODAL_ID} .psm-ca-master { border-color:#304354; background:linear-gradient(135deg,rgba(49,214,232,.06),rgba(139,92,246,.045)),#0d141b; }
      #${MODAL_ID} .psm-ca-master .psm-ca-label-row .psm-ca-icon { color:#67e8f9; }

      #${MODAL_ID} .psm-ca-combobox { position:relative; margin-top:7px; }
      #${MODAL_ID} .psm-ca-search-shell { position:relative; }
      #${MODAL_ID} .psm-ca-search-shell > .psm-ca-icon { position:absolute; left:9px; top:50%; transform:translateY(-50%); width:13px; height:13px; color:#60778b; pointer-events:none; z-index:2; }
      #${MODAL_ID} .psm-ca-search-shell input { margin-top:0; padding-left:30px; }
      #${MODAL_ID} .psm-ca-suggestions { display:none; position:absolute; z-index:10095; left:0; right:0; top:calc(100% + 5px); max-height:238px; overflow-y:auto; padding:4px; background:#080e14; border:1px solid #304354; border-radius:5px; box-shadow:0 14px 32px rgba(0,0,0,.6); }
      #${MODAL_ID} .psm-ca-suggestions.open { display:block; }
      #${MODAL_ID} .psm-ca-suggestion { width:100%; min-height:38px; display:flex; align-items:center; gap:9px; padding:6px 8px; box-sizing:border-box; border:0; border-radius:4px; background:transparent; color:#cbd6df; cursor:pointer; text-align:left; }
      #${MODAL_ID} .psm-ca-suggestion:hover, #${MODAL_ID} .psm-ca-suggestion.active { background:#121f29; color:#edf3f8; }
      #${MODAL_ID} .psm-ca-suggestion-main { min-width:0; flex:1; }
      #${MODAL_ID} .psm-ca-suggestion-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-suggestion-meta { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:2px; color:#6f8091; font-size:8px; }
      #${MODAL_ID} .psm-ca-suggestion-id { flex:0 0 auto; color:#60778b; font-size:8px; }
      #${MODAL_ID} .psm-ca-suggestion-empty { padding:10px 9px; color:#6f8091; font-size:8px; line-height:1.4; }
      #${MODAL_ID} .psm-ca-selected-note { min-height:12px; margin-top:5px; color:#6f8091; font-size:8px; }
      #${MODAL_ID} .psm-ca-selected-note strong { color:#9fb0bd; font-weight:700; }

      #${MODAL_ID} .psm-ca-champion-avatar { position:relative; width:28px; height:28px; flex:0 0 28px; display:grid; place-items:center; overflow:hidden; border:1px solid #344657; border-radius:50%; background:#121b24; color:#8fa1b2; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-champion-avatar img { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
      #${MODAL_ID} .psm-ca-priority-editor { position:relative; padding:13px 14px; background:#0d141b; border:1px solid #21303d; border-radius:5px; }
      #${MODAL_ID} .psm-ca-add-row { display:grid; grid-template-columns:1fr auto; gap:7px; margin-top:8px; }
      #${MODAL_ID} .psm-ca-add-row .psm-ca-combobox { margin-top:0; }
      #${MODAL_ID} .psm-ca-add { min-width:70px; border:1px solid #304354; border-radius:4px; background:#111a23; color:#cbd6df; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-add:hover { border-color:#31d6e8; }
      #${MODAL_ID} .psm-ca-priority-list { display:flex; flex-direction:column; gap:5px; margin-top:9px; }
      #${MODAL_ID} .psm-ca-priority-item { display:grid; grid-template-columns:22px 30px minmax(0,1fr) auto auto auto; gap:5px; align-items:center; min-height:38px; padding:4px 6px; background:#090f15; border:1px solid #21303d; border-radius:4px; }
      #${MODAL_ID} .psm-ca-priority-index { color:#31d6e8; font-size:9px; font-weight:700; text-align:center; }
      #${MODAL_ID} .psm-ca-priority-copy { min-width:0; }
      #${MODAL_ID} .psm-ca-priority-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#cbd6df; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-priority-meta { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:2px; color:#607080; font-size:8px; }
      #${MODAL_ID} .psm-ca-icon-btn { width:26px; height:24px; border:1px solid #253443; border-radius:3px; background:#0d141b; color:#8191a2; cursor:pointer; }
      #${MODAL_ID} .psm-ca-icon-btn:hover { border-color:#8b5cf6; color:#edf3f8; }
      #${MODAL_ID} .psm-ca-empty { padding:8px 0 2px; color:#607080; font-size:8px; }
      #${MODAL_ID} .psm-ca-error { min-height:14px; margin-top:5px; color:#ff8a8a; font-size:8px; }

      #${MODAL_ID} .psm-ca-actions { display:flex; align-items:center; gap:10px; margin-top:22px; padding-top:16px; border-top:1px solid #21303d; }
      #${MODAL_ID} .psm-ca-save-status { flex:1; color:#8191a2; font-size:9px; line-height:1.4; }
      #${MODAL_ID} .psm-ca-secondary { min-width:90px; min-height:36px; border:1px solid #304354; border-radius:4px; background:#0d141b; color:#cbd6df; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-primary { min-width:120px; min-height:36px; border:1px solid #31d6e8; border-radius:4px; background:#31d6e8; color:#061014; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-primary:hover { background:#67e8f9; }
      @media (max-width:720px) {
        #${MODAL_ID} .psm-ca-grid { grid-template-columns:1fr; }
        #${MODAL_ID} .psm-ca-runtime { grid-template-columns:38px minmax(0,1fr); }
        #${MODAL_ID} .psm-ca-refresh { grid-column:1 / -1; justify-self:start; }
      }
    `;
    document.head.appendChild(style);
  }

  function mergeStatus(payload) {
    const previousConnected = status.connected;
    status = {
      phase: payload?.phase || null,
      status: payload?.status || (payload?.enabled ? "Waiting for League" : "Disabled"),
      enabled: !!payload?.enabled,
      connected: payload?.connected === true,
      transport: payload?.transport || (payload?.connected ? "LCU WebSocket" : "Disconnected"),
    };
    refreshLauncher();
    renderRuntimeStatus();

    if (!previousConnected && status.connected) {
      catalogRetryIndex = 0;
      requestCatalog("reconnect", true);
    } else if (previousConnected && !status.connected) {
      clearCatalogRetry();
    }
  }

  function normalizeSettings(payload) {
    settings = {
      enabled: !!payload.enabled,
      autoQueueEnabled: !!payload.autoQueueEnabled,
      queueId: Number.isFinite(Number(payload.queueId)) && Number(payload.queueId) > 0 ? Number(payload.queueId) : null,
      primaryPosition: payload.primaryPosition || null,
      secondaryPosition: payload.secondaryPosition || null,
      autoAcceptEnabled: !!payload.autoAcceptEnabled,
      autoAcceptDelayMs: [0, 500, 1000, 2000, 3000].includes(Number(payload.autoAcceptDelayMs)) ? Number(payload.autoAcceptDelayMs) : 1000,
      autoRequeueEnabled: !!payload.autoRequeueEnabled,
      autoPickEnabled: !!payload.autoPickEnabled,
      pickPriority: Array.isArray(payload.pickPriority) ? payload.pickPriority.map(Number).filter((id) => id > 0).slice(0, 10) : [],
      autoBanEnabled: !!payload.autoBanEnabled,
      banPriority: Array.isArray(payload.banPriority) ? payload.banPriority.map(Number).filter((id) => id > 0).slice(0, 10) : [],
      protectAllyIntents: payload.protectAllyIntents !== false,
    };
    if (payload.status !== undefined || payload.phase !== undefined || payload.connected !== undefined) {
      mergeStatus(payload);
    }
    refreshLauncher();
    renderFormValues();
  }

  function handleSettingsData(payload) {
    normalizeSettings(payload || {});
  }

  function handleStatusData(payload) {
    mergeStatus(payload || {});
  }

  function handleCatalogData(payload) {
    catalog = {
      queues: Array.isArray(payload?.queues) ? payload.queues : [],
      champions: Array.isArray(payload?.champions) ? payload.champions : [],
      currentQueueId: Number(payload?.currentQueueId) > 0 ? Number(payload.currentQueueId) : null,
      leagueConnected: payload?.leagueConnected === true,
      queueCatalogAvailable: payload?.queueCatalogAvailable === true,
      championCatalogAvailable: payload?.championCatalogAvailable === true,
      queueCatalogCached: payload?.queueCatalogCached === true,
      championCatalogCached: payload?.championCatalogCached === true,
      catalogSource: payload?.catalogSource || "none",
      catalogUpdatedAt: Number(payload?.catalogUpdatedAt) > 0 ? Number(payload.catalogUpdatedAt) : null,
    };

    if (catalog.leagueConnected && (!catalog.queueCatalogAvailable || !catalog.championCatalogAvailable)) {
      scheduleCatalogRetry();
    } else {
      clearCatalogRetry();
      catalogRetryIndex = 0;
    }

    renderQueueSelection();
    renderPriority("pickPriority");
    renderPriority("banPriority");
    renderRuntimeStatus();
    renderOpenSuggestions();
  }

  function saveFeedback() {
    if (!status.connected) return settings.enabled ? "Saved · League disconnected" : "Saved · Waiting for League";
    const labels = {
      Lobby: "Saved · Lobby settings applied",
      Matchmaking: "Saved · Matchmaking settings applied",
      ReadyCheck: "Saved · Ready-check settings applied",
      ChampSelect: "Saved · Champion Select settings applied",
      InProgress: "Saved · Will apply at the next eligible client state",
      EndOfGame: "Saved · Post-game settings applied",
    };
    return labels[status.phase] || "Saved";
  }

  function handleSaved(payload) {
    const message = document.getElementById("psm-ca-save-status");
    if (payload?.success) {
      normalizeSettings(payload);
      if (message) {
        message.textContent = saveFeedback();
        message.style.color = "#67e8f9";
      }
    } else if (message) {
      message.textContent = payload?.error || "Could not save Client Automation settings.";
      message.style.color = "#ff8a8a";
    }
  }

  function requestCatalog(reason = "manual", force = false) {
    if (!bridge) return;
    const now = Date.now();
    if (!force && now - lastCatalogRequestAt < 500) return;
    lastCatalogRequestAt = now;
    const button = document.getElementById("psm-ca-refresh-data");
    if (button) {
      button.disabled = true;
      button.dataset.loading = "true";
      button.querySelector("span:last-child")?.replaceChildren(document.createTextNode("Refreshing…"));
    }
    send({ type: "client-automation-catalog-request", reason });
    window.setTimeout(() => {
      const current = document.getElementById("psm-ca-refresh-data");
      if (current) {
        current.disabled = !status.connected;
        current.dataset.loading = "false";
        current.querySelector("span:last-child")?.replaceChildren(document.createTextNode("Refresh Data"));
      }
    }, 900);
  }

  function scheduleCatalogRetry() {
    if (catalogRetryTimer || !document.getElementById(MODAL_ID) || !status.connected) return;
    if (catalogRetryIndex >= CATALOG_RETRY_DELAYS.length) return;
    const delay = CATALOG_RETRY_DELAYS[catalogRetryIndex++];
    catalogRetryTimer = window.setTimeout(() => {
      catalogRetryTimer = null;
      if (!document.getElementById(MODAL_ID) || !status.connected) return;
      requestCatalog("bounded-retry", true);
    }, delay);
  }

  function clearCatalogRetry() {
    if (catalogRetryTimer) {
      clearTimeout(catalogRetryTimer);
      catalogRetryTimer = null;
    }
  }

  function phaseMeta() {
    if (!status.connected) return "League client is not connected";
    return status.phase ? `League state: ${status.phase}` : "League connected · waiting for gameflow state";
  }

  function refreshLauncher() {
    const label = document.querySelector(`#${LAUNCHER_ID} .psm-ca-status`);
    if (label) label.textContent = `${status.status || (settings.enabled ? "Enabled" : "Disabled")} · ${phaseMeta()}`;
  }

  function catalogChip(kind) {
    const isQueue = kind === "queue";
    const rows = isQueue ? catalog.queues : catalog.champions;
    const live = isQueue ? catalog.queueCatalogAvailable : catalog.championCatalogAvailable;
    const cached = isQueue ? catalog.queueCatalogCached : catalog.championCatalogCached;
    const label = isQueue ? "Queues" : "Champions";
    if (live) return { text: `${label} ${rows.length} live`, cls: "live" };
    if (cached && rows.length) return { text: `${label} ${rows.length} cached`, cls: "cached" };
    return { text: `${label} unavailable`, cls: "" };
  }

  function formatCatalogAge() {
    if (!catalog.catalogUpdatedAt) return "";
    const delta = Math.max(0, Date.now() - catalog.catalogUpdatedAt);
    if (delta < 60000) return "Updated just now";
    const minutes = Math.floor(delta / 60000);
    if (minutes < 60) return `Updated ${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `Updated ${hours}h ago`;
    return `Updated ${Math.floor(hours / 24)}d ago`;
  }

  function renderRuntimeStatus() {
    if (!document.getElementById(MODAL_ID)) return;
    const title = document.getElementById("psm-ca-runtime-title");
    const meta = document.getElementById("psm-ca-runtime-meta");
    const runtimeIcon = document.getElementById("psm-ca-runtime-icon");
    const chips = document.getElementById("psm-ca-runtime-chips");
    const refresh = document.getElementById("psm-ca-refresh-data");

    if (title) title.textContent = status.status || (settings.enabled ? "Enabled" : "Disabled");
    if (meta) {
      const age = formatCatalogAge();
      meta.textContent = age ? `${phaseMeta()} · ${age}` : phaseMeta();
    }
    if (runtimeIcon) runtimeIcon.classList.toggle("on", status.connected);
    if (refresh && refresh.dataset.loading !== "true") refresh.disabled = !status.connected;

    if (chips) {
      const queue = catalogChip("queue");
      const champion = catalogChip("champion");
      chips.innerHTML = `
        <span class="psm-ca-chip ${status.connected ? "live" : ""}">${escapeHtml(status.transport || "Disconnected")}</span>
        <span class="psm-ca-chip ${queue.cls}">${escapeHtml(queue.text)}</span>
        <span class="psm-ca-chip ${champion.cls}">${escapeHtml(champion.text)}</span>
      `;
    }
  }

  function ensureLauncher() {
    const saveButton = document.getElementById("save-button");
    if (!saveButton || !saveButton.closest("#rose-settings-flyout")) return;
    if (document.getElementById(LAUNCHER_ID)) return;

    const wrapper = document.createElement("section");
    wrapper.id = LAUNCHER_ID;
    wrapper.innerHTML = `
      <div class="psm-ca-eyebrow">${icon("automation")}<span>03 / CLIENT AUTOMATION</span></div>
      <div class="psm-ca-card">
        <div class="psm-ca-row">
          <div class="psm-ca-launcher-icon">${icon("automation")}</div>
          <div class="psm-ca-copy">
            <div class="psm-ca-title">Matchmaking & Champion Select</div>
            <div class="psm-ca-status">${escapeHtml(status.status)} · ${escapeHtml(phaseMeta())}</div>
          </div>
          <button class="psm-ca-open" type="button">Configure</button>
        </div>
      </div>
    `;
    wrapper.querySelector(".psm-ca-open")?.addEventListener("click", openModal);
    saveButton.parentNode?.insertBefore(wrapper, saveButton);
  }

  function sectionHeading(number, iconName, eyebrow, title, desc, className = "") {
    return `
      <div class="psm-ca-section-heading ${className}">
        <div class="psm-ca-section-icon ${className}">${icon(iconName)}</div>
        <div class="psm-ca-section-copy">
          <div class="psm-ca-section-eyebrow">${escapeHtml(number)} / ${escapeHtml(eyebrow)}</div>
          <div class="psm-ca-section-title">${escapeHtml(title)}</div>
          <div class="psm-ca-section-desc">${escapeHtml(desc)}</div>
        </div>
      </div>
    `;
  }

  function fieldLabel(title, help, iconName = null) {
    return `
      <div class="psm-ca-label-row">${iconName ? icon(iconName) : ""}<div class="psm-ca-label">${escapeHtml(title)}</div></div>
      <div class="psm-ca-help">${escapeHtml(help)}</div>
    `;
  }

  function openModal() {
    closeModal();
    const modal = document.createElement("div");
    modal.id = MODAL_ID;
    modal.innerHTML = `
      <div class="psm-ca-backdrop"></div>
      <section class="psm-ca-panel" role="dialog" aria-modal="true" aria-labelledby="psm-ca-title">
        <header class="psm-ca-header">
          <div class="psm-ca-header-icon">${icon("automation")}</div>
          <div class="psm-ca-header-copy">
            <div class="psm-ca-kicker">PERSONAL SKIN MANAGER</div>
            <h2 id="psm-ca-title">Client Automation</h2>
            <div class="psm-ca-subtitle">Automate repetitive League client actions. Manual client actions always take priority.</div>
          </div>
          <button class="psm-ca-close" type="button" aria-label="Close">×</button>
        </header>
        <div class="psm-ca-body">
          <div class="psm-ca-runtime">
            <div class="psm-ca-runtime-icon" id="psm-ca-runtime-icon">${icon("activity")}</div>
            <div class="psm-ca-runtime-copy">
              <div class="psm-ca-runtime-title" id="psm-ca-runtime-title">Loading status…</div>
              <div class="psm-ca-runtime-meta" id="psm-ca-runtime-meta">League state is not available yet</div>
              <div class="psm-ca-runtime-chips" id="psm-ca-runtime-chips"></div>
            </div>
            <button class="psm-ca-refresh" id="psm-ca-refresh-data" type="button">${icon("refresh")}<span>Refresh Data</span></button>
          </div>

          <div class="psm-ca-toggle psm-ca-master">
            <div class="psm-ca-toggle-copy">
              <div class="psm-ca-label-row">${icon("automation")}<div class="psm-ca-label">Client Automation</div></div>
              <div class="psm-ca-help">Master switch for every automatic client action below. Off by default.</div>
            </div>
            <input id="psm-ca-enabled" type="checkbox" aria-label="Client Automation">
          </div>

          <section class="psm-ca-section">
            ${sectionHeading("01", "matchmaking", "MATCHMAKING", "Queue lifecycle", "Start a configured queue, accept ready checks, and optionally requeue after completed games.", "matchmaking")}
            <div class="psm-ca-grid">
              ${toggleHtml("psm-ca-auto-queue", "Auto Queue", "Start matchmaking from an eligible lobby.")}
              ${toggleHtml("psm-ca-auto-requeue", "Auto Requeue", "Queue again after a completed game returns to an eligible lobby.")}
              ${queueFieldHtml()}
              <div class="psm-ca-field">
                ${fieldLabel("Auto Accept delay", "Ready check is revalidated immediately before acceptance.", "clock")}
                <select id="psm-ca-accept-delay">
                  <option value="0">Immediate</option>
                  <option value="500">0.5 seconds</option>
                  <option value="1000">1.0 second</option>
                  <option value="2000">2.0 seconds</option>
                  <option value="3000">3.0 seconds</option>
                </select>
              </div>
              ${toggleHtml("psm-ca-auto-accept", "Auto Accept", "Accept an actionable matchmaking ready check once.")}
              <div class="psm-ca-field">
                ${fieldLabel("Primary role", "Optional. If set, choose both role preferences.", "role")}
                <select id="psm-ca-primary-position">${positionOptionsHtml()}</select>
              </div>
              <div class="psm-ca-field">
                ${fieldLabel("Secondary role", "Applied immediately before matchmaking starts.", "role")}
                <select id="psm-ca-secondary-position">${positionOptionsHtml()}</select>
              </div>
            </div>
          </section>

          <section class="psm-ca-section">
            ${sectionHeading("02", "champion", "CHAMPION SELECT", "Pick & ban priorities", "Search champions by name and keep an ordered fallback list. IDs remain an advanced fallback.")}
            <div class="psm-ca-grid">
              ${toggleHtml("psm-ca-auto-pick", "Auto Pick", "Select and lock the first available configured champion.")}
              ${toggleHtml("psm-ca-auto-ban", "Auto Ban", "Ban the first valid configured champion.")}
              ${toggleHtml("psm-ca-protect-ally", "Protect ally intents", "Skip ally hovered or intended champions during Auto Ban.")}
            </div>
            <div class="psm-ca-grid" style="margin-top:8px">
              ${priorityEditorHtml("pick", "Pick priority")}
              ${priorityEditorHtml("ban", "Ban priority")}
            </div>
          </section>

          <div class="psm-ca-actions">
            <div class="psm-ca-save-status" id="psm-ca-save-status">Settings are stored locally in PSM.</div>
            <button class="psm-ca-secondary" id="psm-ca-cancel" type="button">Cancel</button>
            <button class="psm-ca-primary" id="psm-ca-save" type="button">Save Automation</button>
          </div>
        </div>
      </section>
    `;

    document.body.appendChild(modal);
    bindModalEvents(modal);
    renderFormValues();
    renderRuntimeStatus();

    send({ type: "client-automation-settings-request" });
    send({ type: "client-automation-status-request" });
    requestCatalog("modal-open", true);

    statusTimer = setInterval(() => {
      if (!document.getElementById(MODAL_ID)) {
        clearStatusTimer();
        return;
      }
      send({ type: "client-automation-status-request" });
    }, 1500);
  }

  function bindModalEvents(modal) {
    modal.querySelector(".psm-ca-backdrop")?.addEventListener("click", closeModal);
    modal.querySelector(".psm-ca-close")?.addEventListener("click", closeModal);
    modal.querySelector("#psm-ca-cancel")?.addEventListener("click", closeModal);
    modal.querySelector("#psm-ca-save")?.addEventListener("click", saveAutomationSettings);
    modal.querySelector("#psm-ca-refresh-data")?.addEventListener("click", () => {
      catalogRetryIndex = 0;
      clearCatalogRetry();
      requestCatalog("manual-refresh", true);
    });

    const queueInput = modal.querySelector("#psm-ca-queue-search");
    queueInput?.addEventListener("focus", () => renderQueueSuggestions(queueInput.value, true));
    queueInput?.addEventListener("input", () => {
      const raw = queueInput.value.trim();
      if (/^\d+$/.test(raw)) settings.queueId = Number(raw) > 0 ? Number(raw) : null;
      else settings.queueId = null;
      queueSuggestionIndex = -1;
      renderQueueSuggestions(raw, true);
      renderQueueSelectedNote();
    });
    queueInput?.addEventListener("keydown", handleQueueKeydown);
    queueInput?.addEventListener("blur", () => window.setTimeout(closeQueueSuggestions, 120));

    ["pick", "ban"].forEach((prefix) => {
      const input = modal.querySelector(`#psm-ca-${prefix}-input`);
      input?.addEventListener("focus", () => renderChampionSuggestions(prefix, input.value, true));
      input?.addEventListener("input", () => {
        championSuggestionIndex[prefix] = -1;
        setPriorityError(prefix, "");
        renderChampionSuggestions(prefix, input.value, true);
      });
      input?.addEventListener("keydown", (event) => handleChampionKeydown(prefix, event));
      input?.addEventListener("blur", () => window.setTimeout(() => closeChampionSuggestions(prefix), 120));
      modal.querySelector(`#psm-ca-${prefix}-add`)?.addEventListener("click", () => addPriorityFromInput(prefix));
    });
  }

  function toggleHtml(id, title, help) {
    return `
      <div class="psm-ca-toggle">
        <div class="psm-ca-toggle-copy">
          <div class="psm-ca-label">${escapeHtml(title)}</div>
          <div class="psm-ca-help">${escapeHtml(help)}</div>
        </div>
        <input id="${id}" type="checkbox" aria-label="${escapeHtml(title)}">
      </div>
    `;
  }

  function queueFieldHtml() {
    return `
      <div class="psm-ca-field">
        ${fieldLabel("Queue", "Search League's current queue catalog. Numeric queue ID remains available as a fallback.", "queue")}
        <div class="psm-ca-combobox">
          <div class="psm-ca-search-shell">
            ${icon("search")}
            <input id="psm-ca-queue-search" type="text" autocomplete="off" placeholder="Search queue or enter ID">
          </div>
          <div class="psm-ca-suggestions" id="psm-ca-queue-suggestions"></div>
        </div>
        <div class="psm-ca-selected-note" id="psm-ca-queue-selected"></div>
      </div>
    `;
  }

  function positionOptionsHtml() {
    return POSITION_OPTIONS.map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("");
  }

  function priorityEditorHtml(prefix, title) {
    return `
      <div class="psm-ca-priority-editor">
        <div class="psm-ca-label-row">${icon("champion")}<div class="psm-ca-label">${escapeHtml(title)}</div></div>
        <div class="psm-ca-help">Search by champion name. Up to 10 priorities are evaluated from top to bottom.</div>
        <div class="psm-ca-add-row">
          <div class="psm-ca-combobox">
            <div class="psm-ca-search-shell">
              ${icon("search")}
              <input id="psm-ca-${prefix}-input" type="text" autocomplete="off" placeholder="Search champion or enter ID">
            </div>
            <div class="psm-ca-suggestions" id="psm-ca-${prefix}-suggestions"></div>
          </div>
          <button class="psm-ca-add" id="psm-ca-${prefix}-add" type="button">Add</button>
        </div>
        <div class="psm-ca-error" id="psm-ca-${prefix}-error"></div>
        <div class="psm-ca-priority-list" id="psm-ca-${prefix}-list"></div>
      </div>
    `;
  }

  function closeModal() {
    clearStatusTimer();
    clearCatalogRetry();
    document.getElementById(MODAL_ID)?.remove();
  }

  function clearStatusTimer() {
    if (statusTimer) {
      clearInterval(statusTimer);
      statusTimer = null;
    }
  }

  function setChecked(id, value) {
    const input = document.getElementById(id);
    if (input) input.checked = !!value;
  }

  function setValue(id, value) {
    const input = document.getElementById(id);
    if (input) input.value = value == null ? "" : String(value);
  }

  function renderFormValues() {
    if (!document.getElementById(MODAL_ID)) return;
    setChecked("psm-ca-enabled", settings.enabled);
    setChecked("psm-ca-auto-queue", settings.autoQueueEnabled);
    setChecked("psm-ca-auto-requeue", settings.autoRequeueEnabled);
    setChecked("psm-ca-auto-accept", settings.autoAcceptEnabled);
    setChecked("psm-ca-auto-pick", settings.autoPickEnabled);
    setChecked("psm-ca-auto-ban", settings.autoBanEnabled);
    setChecked("psm-ca-protect-ally", settings.protectAllyIntents);
    setValue("psm-ca-primary-position", settings.primaryPosition || "");
    setValue("psm-ca-secondary-position", settings.secondaryPosition || "");
    setValue("psm-ca-accept-delay", settings.autoAcceptDelayMs);
    renderQueueSelection();
    renderPriority("pickPriority");
    renderPriority("banPriority");
    renderRuntimeStatus();
  }

  function queueById(id) {
    return catalog.queues.find((item) => Number(item?.id) === Number(id)) || null;
  }

  function renderQueueSelection() {
    const input = document.getElementById("psm-ca-queue-search");
    if (!input) return;
    if (document.activeElement !== input) {
      const selected = queueById(settings.queueId);
      input.value = selected?.name || (settings.queueId ? String(settings.queueId) : "");
    }
    renderQueueSelectedNote();
  }

  function renderQueueSelectedNote() {
    const note = document.getElementById("psm-ca-queue-selected");
    if (!note) return;
    if (!settings.queueId) {
      if (!catalog.queueCatalogAvailable && catalog.queueCatalogCached) {
        note.innerHTML = "Showing cached queue names. Live validation occurs before matchmaking.";
      } else if (!catalog.queueCatalogAvailable) {
        note.innerHTML = "Live queue catalog unavailable. You can still enter a numeric queue ID.";
      } else {
        note.innerHTML = "No queue selected.";
      }
      return;
    }
    const selected = queueById(settings.queueId);
    note.innerHTML = selected
      ? `Selected: <strong>${escapeHtml(selected.name)}</strong> · #${Number(settings.queueId)}`
      : `Selected queue ID: <strong>#${Number(settings.queueId)}</strong>`;
  }

  function scoreText(name, query) {
    const text = String(name || "").toLowerCase();
    const q = String(query || "").trim().toLowerCase();
    if (!q) return 4;
    if (text === q) return 0;
    if (text.startsWith(q)) return 1;
    if (text.split(/\s+/).some((word) => word.startsWith(q))) return 2;
    if (text.includes(q)) return 3;
    return 999;
  }

  function matchingQueues(query) {
    const q = String(query || "").trim();
    const rows = catalog.queues
      .map((item) => ({ item, score: Math.min(scoreText(item.name, q), scoreText(item.id, q)) }))
      .filter((row) => !q || row.score < 999)
      .sort((a, b) => a.score - b.score || String(a.item.name).localeCompare(String(b.item.name)))
      .slice(0, 10)
      .map((row) => row.item);
    return rows;
  }

  function renderQueueSuggestions(query, open = false) {
    const target = document.getElementById("psm-ca-queue-suggestions");
    if (!target) return;
    const rows = matchingQueues(query);
    if (!rows.length) {
      target.innerHTML = `<div class="psm-ca-suggestion-empty">${catalog.queues.length ? "No matching queue. Enter a numeric queue ID as a fallback." : "Queue catalog is not available yet. Use Refresh Data or enter a numeric queue ID."}</div>`;
    } else {
      target.innerHTML = rows.map((item, index) => `
        <button class="psm-ca-suggestion ${index === queueSuggestionIndex ? "active" : ""}" type="button" data-queue-id="${Number(item.id)}">
          <span class="psm-ca-suggestion-main">
            <span class="psm-ca-suggestion-name">${escapeHtml(item.name || `Queue ${item.id}`)}</span>
            <span class="psm-ca-suggestion-meta">League matchmaking queue</span>
          </span>
          <span class="psm-ca-suggestion-id">#${Number(item.id)}</span>
        </button>
      `).join("");
      target.querySelectorAll("[data-queue-id]").forEach((button) => {
        button.addEventListener("mousedown", (event) => event.preventDefault());
        button.addEventListener("click", () => selectQueue(Number(button.getAttribute("data-queue-id"))));
      });
    }
    target.classList.toggle("open", !!open);
  }

  function closeQueueSuggestions() {
    document.getElementById("psm-ca-queue-suggestions")?.classList.remove("open");
  }

  function selectQueue(queueId) {
    if (!Number.isFinite(queueId) || queueId <= 0) return;
    settings.queueId = queueId;
    queueSuggestionIndex = -1;
    renderQueueSelection();
    closeQueueSuggestions();
  }

  function handleQueueKeydown(event) {
    const rows = matchingQueues(event.currentTarget.value);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      queueSuggestionIndex = rows.length ? Math.min(queueSuggestionIndex + 1, rows.length - 1) : -1;
      renderQueueSuggestions(event.currentTarget.value, true);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      queueSuggestionIndex = rows.length ? Math.max(queueSuggestionIndex - 1, 0) : -1;
      renderQueueSuggestions(event.currentTarget.value, true);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (queueSuggestionIndex >= 0 && rows[queueSuggestionIndex]) {
        selectQueue(Number(rows[queueSuggestionIndex].id));
      } else {
        const raw = event.currentTarget.value.trim();
        if (/^\d+$/.test(raw) && Number(raw) > 0) selectQueue(Number(raw));
        else if (rows.length === 1) selectQueue(Number(rows[0].id));
      }
    } else if (event.key === "Escape") {
      closeQueueSuggestions();
    }
  }

  function championById(id) {
    return catalog.champions.find((item) => Number(item?.id) === Number(id)) || null;
  }

  function matchingChampions(query) {
    const q = String(query || "").trim();
    return catalog.champions
      .map((item) => ({
        item,
        score: Math.min(
          scoreText(item.name, q),
          scoreText(item.title, q) + 1,
          scoreText(item.id, q)
        ),
      }))
      .filter((row) => !q || row.score < 999)
      .sort((a, b) => a.score - b.score || String(a.item.name).localeCompare(String(b.item.name)))
      .slice(0, 10)
      .map((row) => row.item);
  }

  function championIconUrl(champion) {
    const path = String(champion?.iconPath || "").trim();
    if (!path) return "";
    if (/^https?:\/\//i.test(path)) return "";
    return path.startsWith("/") ? path : `/${path.replace(/^\/+/, "")}`;
  }

  function championAvatarHtml(champion) {
    const name = champion?.name || `Champion ${champion?.id || ""}`;
    const initial = String(name).trim().slice(0, 1).toUpperCase() || "?";
    const url = championIconUrl(champion);
    return `<span class="psm-ca-champion-avatar"><span>${escapeHtml(initial)}</span>${url ? `<img src="${escapeHtml(url)}" alt="">` : ""}</span>`;
  }

  function bindImageFallbacks(root) {
    root?.querySelectorAll(".psm-ca-champion-avatar img").forEach((img) => {
      img.addEventListener("error", () => img.remove(), { once: true });
    });
  }

  function renderChampionSuggestions(prefix, query, open = false) {
    const target = document.getElementById(`psm-ca-${prefix}-suggestions`);
    if (!target) return;
    const rows = matchingChampions(query);
    const active = championSuggestionIndex[prefix];
    if (!rows.length) {
      const message = catalog.champions.length
        ? "No matching champion. You can enter a numeric champion ID as a fallback."
        : "Champion catalog is unavailable. Use Refresh Data or enter a numeric champion ID.";
      target.innerHTML = `<div class="psm-ca-suggestion-empty">${escapeHtml(message)}</div>`;
    } else {
      target.innerHTML = rows.map((champion, index) => `
        <button class="psm-ca-suggestion ${index === active ? "active" : ""}" type="button" data-champion-id="${Number(champion.id)}">
          ${championAvatarHtml(champion)}
          <span class="psm-ca-suggestion-main">
            <span class="psm-ca-suggestion-name">${escapeHtml(champion.name)}</span>
            <span class="psm-ca-suggestion-meta">${escapeHtml(champion.title || "League champion")}</span>
          </span>
          <span class="psm-ca-suggestion-id">#${Number(champion.id)}</span>
        </button>
      `).join("");
      target.querySelectorAll("[data-champion-id]").forEach((button) => {
        button.addEventListener("mousedown", (event) => event.preventDefault());
        button.addEventListener("click", () => {
          addChampionId(prefix, Number(button.getAttribute("data-champion-id")));
        });
      });
      bindImageFallbacks(target);
    }
    target.classList.toggle("open", !!open);
  }

  function closeChampionSuggestions(prefix) {
    document.getElementById(`psm-ca-${prefix}-suggestions`)?.classList.remove("open");
  }

  function handleChampionKeydown(prefix, event) {
    const rows = matchingChampions(event.currentTarget.value);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      championSuggestionIndex[prefix] = rows.length ? Math.min(championSuggestionIndex[prefix] + 1, rows.length - 1) : -1;
      renderChampionSuggestions(prefix, event.currentTarget.value, true);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      championSuggestionIndex[prefix] = rows.length ? Math.max(championSuggestionIndex[prefix] - 1, 0) : -1;
      renderChampionSuggestions(prefix, event.currentTarget.value, true);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const index = championSuggestionIndex[prefix];
      if (index >= 0 && rows[index]) addChampionId(prefix, Number(rows[index].id));
      else addPriorityFromInput(prefix);
    } else if (event.key === "Escape") {
      closeChampionSuggestions(prefix);
    }
  }

  function resolveChampion(value) {
    const raw = String(value || "").trim();
    if (!raw) return null;
    if (/^\d+$/.test(raw)) {
      const id = Number(raw);
      return id > 0 ? id : null;
    }
    const lower = raw.toLowerCase();
    const exact = catalog.champions.find((item) => String(item?.name || "").toLowerCase() === lower);
    if (exact) return Number(exact.id);
    const matches = matchingChampions(raw);
    return matches.length === 1 ? Number(matches[0].id) : null;
  }

  function priorityKey(prefix) {
    return prefix === "pick" ? "pickPriority" : "banPriority";
  }

  function setPriorityError(prefix, message) {
    const error = document.getElementById(`psm-ca-${prefix}-error`);
    if (error) error.textContent = message || "";
  }

  function addPriorityFromInput(prefix) {
    const input = document.getElementById(`psm-ca-${prefix}-input`);
    if (!input) return;
    const championId = resolveChampion(input.value);
    if (!championId) {
      setPriorityError(prefix, catalog.champions.length
        ? "Choose a champion from the search results or enter a numeric champion ID."
        : "League champion catalog unavailable. Enter a numeric champion ID or refresh data.");
      return;
    }
    addChampionId(prefix, championId);
  }

  function addChampionId(prefix, championId) {
    const key = priorityKey(prefix);
    const input = document.getElementById(`psm-ca-${prefix}-input`);
    if (!Number.isFinite(championId) || championId <= 0) return;
    if (settings[key].includes(championId)) {
      setPriorityError(prefix, "That champion is already in this priority list.");
      return;
    }
    if (settings[key].length >= 10) {
      setPriorityError(prefix, "Priority lists are limited to 10 champions.");
      return;
    }
    settings[key] = [...settings[key], championId];
    if (input) input.value = "";
    championSuggestionIndex[prefix] = -1;
    setPriorityError(prefix, "");
    closeChampionSuggestions(prefix);
    renderPriority(key);
  }

  function renderPriority(key) {
    const prefix = key === "pickPriority" ? "pick" : "ban";
    const list = document.getElementById(`psm-ca-${prefix}-list`);
    if (!list) return;
    const items = settings[key] || [];
    if (!items.length) {
      list.innerHTML = `<div class="psm-ca-empty">No champions configured.</div>`;
      return;
    }
    list.innerHTML = items.map((championId, index) => {
      const champion = championById(championId) || { id: championId, name: `Champion ${championId}` };
      return `
        <div class="psm-ca-priority-item" data-index="${index}">
          <div class="psm-ca-priority-index">${index + 1}</div>
          ${championAvatarHtml(champion)}
          <div class="psm-ca-priority-copy">
            <div class="psm-ca-priority-name">${escapeHtml(champion.name)}</div>
            <div class="psm-ca-priority-meta">${escapeHtml(champion.title || "Configured champion")} · #${Number(championId)}</div>
          </div>
          <button class="psm-ca-icon-btn" type="button" data-action="up" aria-label="Move up">↑</button>
          <button class="psm-ca-icon-btn" type="button" data-action="down" aria-label="Move down">↓</button>
          <button class="psm-ca-icon-btn" type="button" data-action="remove" aria-label="Remove">×</button>
        </div>
      `;
    }).join("");
    list.querySelectorAll(".psm-ca-priority-item").forEach((row) => {
      const index = Number(row.getAttribute("data-index"));
      row.querySelector('[data-action="up"]')?.addEventListener("click", () => movePriority(key, index, -1));
      row.querySelector('[data-action="down"]')?.addEventListener("click", () => movePriority(key, index, 1));
      row.querySelector('[data-action="remove"]')?.addEventListener("click", () => removePriority(key, index));
    });
    bindImageFallbacks(list);
  }

  function movePriority(key, index, delta) {
    const next = index + delta;
    if (index < 0 || next < 0 || next >= settings[key].length) return;
    const values = [...settings[key]];
    [values[index], values[next]] = [values[next], values[index]];
    settings[key] = values;
    renderPriority(key);
  }

  function removePriority(key, index) {
    settings[key] = settings[key].filter((_, current) => current !== index);
    renderPriority(key);
  }

  function renderOpenSuggestions() {
    const queueInput = document.getElementById("psm-ca-queue-search");
    if (queueInput && document.activeElement === queueInput) renderQueueSuggestions(queueInput.value, true);
    ["pick", "ban"].forEach((prefix) => {
      const input = document.getElementById(`psm-ca-${prefix}-input`);
      if (input && document.activeElement === input) renderChampionSuggestions(prefix, input.value, true);
    });
  }

  function checked(id) {
    return !!document.getElementById(id)?.checked;
  }

  function value(id) {
    return document.getElementById(id)?.value ?? "";
  }

  function showSaveError(message) {
    const target = document.getElementById("psm-ca-save-status");
    if (target) {
      target.textContent = message;
      target.style.color = "#ff8a8a";
    }
  }

  function syncQueueFromInput() {
    const input = document.getElementById("psm-ca-queue-search");
    if (!input) return;
    const raw = input.value.trim();
    if (!raw) return;
    if (/^\d+$/.test(raw) && Number(raw) > 0) {
      settings.queueId = Number(raw);
      return;
    }
    const exact = catalog.queues.find((item) => String(item.name || "").toLowerCase() === raw.toLowerCase());
    if (exact) settings.queueId = Number(exact.id);
  }

  function saveAutomationSettings() {
    syncQueueFromInput();
    const autoQueueEnabled = checked("psm-ca-auto-queue");
    const autoRequeueEnabled = checked("psm-ca-auto-requeue");
    const autoPickEnabled = checked("psm-ca-auto-pick");
    const autoBanEnabled = checked("psm-ca-auto-ban");
    const primary = value("psm-ca-primary-position") || null;
    const secondary = value("psm-ca-secondary-position") || null;

    if ((primary && !secondary) || (!primary && secondary)) {
      showSaveError("Choose both primary and secondary roles, or leave both unset.");
      return;
    }
    if (primary && primary === secondary) {
      showSaveError("Primary and secondary roles must be different.");
      return;
    }
    if ((autoQueueEnabled || autoRequeueEnabled) && !settings.queueId) {
      showSaveError("Choose a queue before enabling Auto Queue or Auto Requeue.");
      return;
    }
    if (autoPickEnabled && !settings.pickPriority.length) {
      showSaveError("Add at least one champion before enabling Auto Pick.");
      return;
    }
    if (autoBanEnabled && !settings.banPriority.length) {
      showSaveError("Add at least one champion before enabling Auto Ban.");
      return;
    }

    const target = document.getElementById("psm-ca-save-status");
    if (target) {
      target.textContent = "Saving…";
      target.style.color = "#8191a2";
    }

    send({
      type: "client-automation-settings-save",
      enabled: checked("psm-ca-enabled"),
      autoQueueEnabled,
      queueId: settings.queueId,
      primaryPosition: primary,
      secondaryPosition: secondary,
      autoAcceptEnabled: checked("psm-ca-auto-accept"),
      autoAcceptDelayMs: Number(value("psm-ca-accept-delay") || 1000),
      autoRequeueEnabled,
      autoPickEnabled,
      pickPriority: [...settings.pickPriority],
      autoBanEnabled,
      banPriority: [...settings.banPriority],
      protectAllyIntents: checked("psm-ca-protect-ally"),
    });
  }

  function startObserver() {
    ensureLauncher();
    if (observer) return;
    observer = new MutationObserver(() => ensureLauncher());
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  async function init() {
    injectStyles();
    try {
      bridge = await waitForBridge();
    } catch (error) {
      console.warn(`${LOG_PREFIX} ${error.message}`);
      return;
    }

    bridge.subscribe("client-automation-settings-data", handleSettingsData);
    bridge.subscribe("client-automation-settings-saved", handleSaved);
    bridge.subscribe("client-automation-status-data", handleStatusData);
    bridge.subscribe("client-automation-catalog-data", handleCatalogData);

    send({ type: "client-automation-settings-request" });
    startObserver();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();