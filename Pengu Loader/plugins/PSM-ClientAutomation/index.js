/**
 * @name PSM-ClientAutomation
 * @description Personal Skin Manager Client Automation control surface.
 */
(function initPsmClientAutomation() {
  const LOG_PREFIX = "[PSM-ClientAutomation]";
  const LAUNCHER_ID = "psm-client-automation-launcher";
  const MODAL_ID = "psm-client-automation-modal";
  const STYLE_ID = "psm-client-automation-style";
  const CHAMPION_LIST_ID = "psm-ca-champion-list";
  const QUEUE_LIST_ID = "psm-ca-queue-list";

  const POSITION_OPTIONS = [
    ["", "Not set"],
    ["TOP", "Top"],
    ["JUNGLE", "Jungle"],
    ["MIDDLE", "Mid"],
    ["BOTTOM", "Bottom"],
    ["UTILITY", "Support"],
    ["FILL", "Fill"],
  ];

  let bridge = null;
  let observer = null;
  let statusTimer = null;
  let settings = defaultSettings();
  let catalog = { queues: [], champions: [], currentQueueId: null };
  let status = { phase: null, status: "Disabled", enabled: false };

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
      #${LAUNCHER_ID} .psm-ca-eyebrow { color:#31d6e8; font:700 9px "Spiegel",Arial,sans-serif; letter-spacing:.16em; }
      #${LAUNCHER_ID} .psm-ca-card { margin-top:7px; padding:14px 15px; background:#0d141b; border:1px solid #21303d; border-radius:5px; }
      #${LAUNCHER_ID} .psm-ca-row { display:flex; align-items:center; gap:12px; }
      #${LAUNCHER_ID} .psm-ca-copy { flex:1; min-width:0; }
      #${LAUNCHER_ID} .psm-ca-title { color:#edf3f8; font:700 14px "Beaufort for LOL",serif; }
      #${LAUNCHER_ID} .psm-ca-status { margin-top:3px; color:#8191a2; font:10px/1.4 "Spiegel",Arial,sans-serif; }
      #${LAUNCHER_ID} .psm-ca-open { min-width:100px; min-height:34px; border:1px solid #31d6e8; border-radius:4px; background:#0b1219; color:#67e8f9; cursor:pointer; font:700 9px "Spiegel",Arial,sans-serif; }
      #${LAUNCHER_ID} .psm-ca-open:hover { background:#12202a; }

      #${MODAL_ID} { position:fixed; inset:0; z-index:10080; display:flex; align-items:center; justify-content:center; font-family:"Spiegel",Arial,sans-serif; }
      #${MODAL_ID} .psm-ca-backdrop { position:absolute; inset:0; background:rgba(0,0,0,.72); }
      #${MODAL_ID} .psm-ca-panel { position:relative; width:min(760px,calc(100vw - 48px)); max-height:calc(100vh - 72px); overflow:hidden; background:#080d12; border:1px solid #304354; border-top:2px solid #31d6e8; border-radius:7px; box-shadow:0 28px 80px rgba(0,0,0,.78); color:#edf3f8; }
      #${MODAL_ID} .psm-ca-header { display:flex; align-items:flex-start; gap:16px; padding:22px 24px 18px; border-bottom:1px solid #21303d; }
      #${MODAL_ID} .psm-ca-header-copy { flex:1; }
      #${MODAL_ID} .psm-ca-kicker { color:#31d6e8; font-size:9px; font-weight:700; letter-spacing:.18em; }
      #${MODAL_ID} h2 { margin:5px 0 0; font:700 21px "Beaufort for LOL",serif; }
      #${MODAL_ID} .psm-ca-subtitle { margin-top:4px; color:#8191a2; font-size:10px; line-height:1.5; }
      #${MODAL_ID} .psm-ca-close { width:30px; height:30px; border:1px solid #304354; border-radius:4px; background:#0d141b; color:#8191a2; cursor:pointer; font-size:18px; }
      #${MODAL_ID} .psm-ca-close:hover { border-color:#31d6e8; color:#edf3f8; }
      #${MODAL_ID} .psm-ca-body { max-height:calc(100vh - 190px); overflow-y:auto; padding:20px 24px 24px; scrollbar-width:thin; scrollbar-color:#31d6e8 #0b1016; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar { width:7px; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar-track { background:#0b1016; }
      #${MODAL_ID} .psm-ca-body::-webkit-scrollbar-thumb { background:#31d6e8; border-radius:8px; }
      #${MODAL_ID} .psm-ca-runtime { display:flex; align-items:center; gap:12px; padding:12px 14px; margin-bottom:18px; background:#0d141b; border:1px solid #21303d; border-radius:5px; }
      #${MODAL_ID} .psm-ca-dot { width:8px; height:8px; border-radius:50%; background:#607080; box-shadow:0 0 0 3px rgba(96,112,128,.12); }
      #${MODAL_ID} .psm-ca-dot.on { background:#31d6e8; box-shadow:0 0 0 3px rgba(49,214,232,.12); }
      #${MODAL_ID} .psm-ca-runtime-copy { flex:1; }
      #${MODAL_ID} .psm-ca-runtime-title { color:#edf3f8; font-size:11px; font-weight:700; }
      #${MODAL_ID} .psm-ca-runtime-meta { margin-top:2px; color:#8191a2; font-size:9px; }
      #${MODAL_ID} .psm-ca-section { margin-top:20px; }
      #${MODAL_ID} .psm-ca-section-heading { margin-bottom:9px; }
      #${MODAL_ID} .psm-ca-section-eyebrow { color:#8b5cf6; font-size:8px; font-weight:700; letter-spacing:.17em; }
      #${MODAL_ID} .psm-ca-section-title { margin-top:3px; color:#edf3f8; font:700 15px "Beaufort for LOL",serif; }
      #${MODAL_ID} .psm-ca-section-desc { margin-top:3px; color:#8191a2; font-size:9px; line-height:1.45; }
      #${MODAL_ID} .psm-ca-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
      #${MODAL_ID} .psm-ca-field, #${MODAL_ID} .psm-ca-toggle { min-width:0; padding:13px 14px; background:#0d141b; border:1px solid #21303d; border-radius:5px; box-sizing:border-box; }
      #${MODAL_ID} .psm-ca-toggle { display:flex; align-items:center; justify-content:space-between; gap:14px; }
      #${MODAL_ID} .psm-ca-toggle-copy { min-width:0; }
      #${MODAL_ID} .psm-ca-label { color:#cbd6df; font-size:10px; font-weight:700; }
      #${MODAL_ID} .psm-ca-help { margin-top:3px; color:#6f8091; font-size:8px; line-height:1.4; }
      #${MODAL_ID} input[type="checkbox"] { width:18px; height:18px; accent-color:#31d6e8; cursor:pointer; }
      #${MODAL_ID} input[type="text"], #${MODAL_ID} input[type="number"], #${MODAL_ID} select { width:100%; height:34px; margin-top:7px; padding:0 9px; box-sizing:border-box; background:#090f15; border:1px solid #304354; border-radius:4px; color:#edf3f8; font:10px "Spiegel",Arial,sans-serif; outline:none; }
      #${MODAL_ID} input:focus, #${MODAL_ID} select:focus { border-color:#31d6e8; }
      #${MODAL_ID} .psm-ca-priority-editor { padding:13px 14px; background:#0d141b; border:1px solid #21303d; border-radius:5px; }
      #${MODAL_ID} .psm-ca-add-row { display:grid; grid-template-columns:1fr auto; gap:7px; margin-top:8px; }
      #${MODAL_ID} .psm-ca-add-row input { margin-top:0; }
      #${MODAL_ID} .psm-ca-add { min-width:70px; border:1px solid #304354; border-radius:4px; background:#111a23; color:#cbd6df; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-add:hover { border-color:#31d6e8; }
      #${MODAL_ID} .psm-ca-priority-list { display:flex; flex-direction:column; gap:5px; margin-top:9px; }
      #${MODAL_ID} .psm-ca-priority-item { display:grid; grid-template-columns:24px 1fr auto auto auto; gap:5px; align-items:center; min-height:32px; padding:4px 6px; background:#090f15; border:1px solid #21303d; border-radius:4px; }
      #${MODAL_ID} .psm-ca-priority-index { color:#31d6e8; font-size:9px; font-weight:700; text-align:center; }
      #${MODAL_ID} .psm-ca-priority-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#cbd6df; font-size:9px; }
      #${MODAL_ID} .psm-ca-icon-btn { width:26px; height:24px; border:1px solid #253443; border-radius:3px; background:#0d141b; color:#8191a2; cursor:pointer; }
      #${MODAL_ID} .psm-ca-icon-btn:hover { border-color:#8b5cf6; color:#edf3f8; }
      #${MODAL_ID} .psm-ca-empty { padding:8px 0 2px; color:#607080; font-size:8px; }
      #${MODAL_ID} .psm-ca-error { min-height:14px; margin-top:5px; color:#ff8a8a; font-size:8px; }
      #${MODAL_ID} .psm-ca-master { border-color:#304354; background:linear-gradient(135deg,rgba(49,214,232,.06),rgba(139,92,246,.045)),#0d141b; }
      #${MODAL_ID} .psm-ca-actions { display:flex; align-items:center; gap:10px; margin-top:22px; padding-top:16px; border-top:1px solid #21303d; }
      #${MODAL_ID} .psm-ca-save-status { flex:1; color:#8191a2; font-size:9px; }
      #${MODAL_ID} .psm-ca-secondary { min-width:90px; min-height:36px; border:1px solid #304354; border-radius:4px; background:#0d141b; color:#cbd6df; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-primary { min-width:120px; min-height:36px; border:1px solid #31d6e8; border-radius:4px; background:#31d6e8; color:#061014; cursor:pointer; font-size:9px; font-weight:700; }
      #${MODAL_ID} .psm-ca-primary:hover { background:#67e8f9; }
      @media (max-width:720px) { #${MODAL_ID} .psm-ca-grid { grid-template-columns:1fr; } }
    `;
    document.head.appendChild(style);
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
    if (payload.status !== undefined || payload.phase !== undefined) {
      status = { phase: payload.phase || null, status: payload.status || "Waiting for League", enabled: !!payload.enabled };
    }
    refreshLauncher();
    renderFormValues();
  }

  function handleSettingsData(payload) {
    normalizeSettings(payload || {});
  }

  function handleStatusData(payload) {
    status = {
      phase: payload?.phase || null,
      status: payload?.status || "Waiting for League",
      enabled: !!payload?.enabled,
    };
    refreshLauncher();
    renderRuntimeStatus();
  }

  function handleCatalogData(payload) {
    catalog = {
      queues: Array.isArray(payload?.queues) ? payload.queues : [],
      champions: Array.isArray(payload?.champions) ? payload.champions : [],
      currentQueueId: Number(payload?.currentQueueId) > 0 ? Number(payload.currentQueueId) : null,
    };
    renderCatalogs();
    renderPriority("pickPriority");
    renderPriority("banPriority");
  }

  function handleSaved(payload) {
    const message = document.getElementById("psm-ca-save-status");
    if (payload?.success) {
      normalizeSettings(payload);
      if (message) {
        message.textContent = "Saved. Changes apply to the next eligible client state.";
        message.style.color = "#67e8f9";
      }
    } else if (message) {
      message.textContent = payload?.error || "Could not save Client Automation settings.";
      message.style.color = "#ff8a8a";
    }
  }

  function phaseMeta() {
    return status.phase ? `League state: ${status.phase}` : "League state is not available yet";
  }

  function refreshLauncher() {
    const label = document.querySelector(`#${LAUNCHER_ID} .psm-ca-status`);
    if (label) label.textContent = `${status.status || (settings.enabled ? "Enabled" : "Disabled")} · ${phaseMeta()}`;
  }

  function renderRuntimeStatus() {
    const title = document.getElementById("psm-ca-runtime-title");
    const meta = document.getElementById("psm-ca-runtime-meta");
    const dot = document.getElementById("psm-ca-runtime-dot");
    if (title) title.textContent = status.status || (settings.enabled ? "Enabled" : "Disabled");
    if (meta) meta.textContent = phaseMeta();
    if (dot) dot.classList.toggle("on", !!status.enabled);
  }

  function ensureLauncher() {
    const saveButton = document.getElementById("save-button");
    if (!saveButton || !saveButton.closest("#rose-settings-flyout")) return;
    if (document.getElementById(LAUNCHER_ID)) return;

    const wrapper = document.createElement("section");
    wrapper.id = LAUNCHER_ID;
    wrapper.innerHTML = `
      <div class="psm-ca-eyebrow">03 / CLIENT AUTOMATION</div>
      <div class="psm-ca-card">
        <div class="psm-ca-row">
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

  function openModal() {
    closeModal();
    const modal = document.createElement("div");
    modal.id = MODAL_ID;
    modal.innerHTML = `
      <div class="psm-ca-backdrop"></div>
      <section class="psm-ca-panel" role="dialog" aria-modal="true" aria-labelledby="psm-ca-title">
        <header class="psm-ca-header">
          <div class="psm-ca-header-copy">
            <div class="psm-ca-kicker">PERSONAL SKIN MANAGER</div>
            <h2 id="psm-ca-title">Client Automation</h2>
            <div class="psm-ca-subtitle">Configure matchmaking and Champion Select automation. Manual client actions always take priority.</div>
          </div>
          <button class="psm-ca-close" type="button" aria-label="Close">×</button>
        </header>
        <div class="psm-ca-body">
          <div class="psm-ca-runtime">
            <span class="psm-ca-dot" id="psm-ca-runtime-dot"></span>
            <div class="psm-ca-runtime-copy">
              <div class="psm-ca-runtime-title" id="psm-ca-runtime-title">Loading status…</div>
              <div class="psm-ca-runtime-meta" id="psm-ca-runtime-meta">League state is not available yet</div>
            </div>
          </div>

          <div class="psm-ca-toggle psm-ca-master">
            <div class="psm-ca-toggle-copy">
              <div class="psm-ca-label">Client Automation</div>
              <div class="psm-ca-help">Master switch for every automatic client action below. Off by default.</div>
            </div>
            <input id="psm-ca-enabled" type="checkbox" aria-label="Client Automation">
          </div>

          <section class="psm-ca-section">
            <div class="psm-ca-section-heading">
              <div class="psm-ca-section-eyebrow">01 / MATCHMAKING</div>
              <div class="psm-ca-section-title">Queue lifecycle</div>
              <div class="psm-ca-section-desc">Start a configured queue, accept ready checks, and optionally requeue after completed games.</div>
            </div>
            <div class="psm-ca-grid">
              ${toggleHtml("psm-ca-auto-queue", "Auto Queue", "Start matchmaking from an eligible lobby.")}
              ${toggleHtml("psm-ca-auto-requeue", "Auto Requeue", "Queue again after a completed game returns to an eligible lobby.")}
              <div class="psm-ca-field">
                <div class="psm-ca-label">Queue</div>
                <div class="psm-ca-help">Choose from League's current queue catalog or enter a queue ID.</div>
                <input id="psm-ca-queue" type="number" min="1" list="${QUEUE_LIST_ID}" placeholder="Queue ID">
                <datalist id="${QUEUE_LIST_ID}"></datalist>
              </div>
              <div class="psm-ca-field">
                <div class="psm-ca-label">Auto Accept delay</div>
                <div class="psm-ca-help">Ready check is revalidated immediately before acceptance.</div>
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
                <div class="psm-ca-label">Primary role</div>
                <div class="psm-ca-help">Optional. If set, choose both role preferences.</div>
                <select id="psm-ca-primary-position">${positionOptionsHtml()}</select>
              </div>
              <div class="psm-ca-field">
                <div class="psm-ca-label">Secondary role</div>
                <div class="psm-ca-help">Applied immediately before matchmaking starts.</div>
                <select id="psm-ca-secondary-position">${positionOptionsHtml()}</select>
              </div>
            </div>
          </section>

          <section class="psm-ca-section">
            <div class="psm-ca-section-heading">
              <div class="psm-ca-section-eyebrow">02 / CHAMPION SELECT</div>
              <div class="psm-ca-section-title">Pick & ban priorities</div>
              <div class="psm-ca-section-desc">Ordered preferences use champion IDs internally. Add champions by name when the League catalog is available, or by numeric ID.</div>
            </div>
            <div class="psm-ca-grid">
              ${toggleHtml("psm-ca-auto-pick", "Auto Pick", "Select and lock the first available configured champion.")}
              ${toggleHtml("psm-ca-auto-ban", "Auto Ban", "Ban the first valid configured champion.")}
              ${toggleHtml("psm-ca-protect-ally", "Protect ally intents", "Skip ally hovered or intended champions during Auto Ban.")}
            </div>
            <div class="psm-ca-grid" style="margin-top:8px">
              ${priorityEditorHtml("pick", "Pick priority")}
              ${priorityEditorHtml("ban", "Ban priority")}
            </div>
            <datalist id="${CHAMPION_LIST_ID}"></datalist>
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
    modal.querySelector(".psm-ca-backdrop")?.addEventListener("click", closeModal);
    modal.querySelector(".psm-ca-close")?.addEventListener("click", closeModal);
    modal.querySelector("#psm-ca-cancel")?.addEventListener("click", closeModal);
    modal.querySelector("#psm-ca-save")?.addEventListener("click", saveAutomationSettings);
    modal.querySelector("#psm-ca-pick-add")?.addEventListener("click", () => addPriority("pickPriority", "psm-ca-pick-input", "psm-ca-pick-error"));
    modal.querySelector("#psm-ca-ban-add")?.addEventListener("click", () => addPriority("banPriority", "psm-ca-ban-input", "psm-ca-ban-error"));
    modal.querySelector("#psm-ca-pick-input")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") { event.preventDefault(); addPriority("pickPriority", "psm-ca-pick-input", "psm-ca-pick-error"); }
    });
    modal.querySelector("#psm-ca-ban-input")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") { event.preventDefault(); addPriority("banPriority", "psm-ca-ban-input", "psm-ca-ban-error"); }
    });

    renderFormValues();
    renderCatalogs();
    renderPriority("pickPriority");
    renderPriority("banPriority");
    renderRuntimeStatus();

    send({ type: "client-automation-settings-request" });
    send({ type: "client-automation-catalog-request" });
    send({ type: "client-automation-status-request" });

    statusTimer = setInterval(() => {
      if (!document.getElementById(MODAL_ID)) {
        clearStatusTimer();
        return;
      }
      send({ type: "client-automation-status-request" });
    }, 1500);
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

  function positionOptionsHtml() {
    return POSITION_OPTIONS.map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("");
  }

  function priorityEditorHtml(prefix, title) {
    return `
      <div class="psm-ca-priority-editor">
        <div class="psm-ca-label">${escapeHtml(title)}</div>
        <div class="psm-ca-help">Up to 10 champions, evaluated from top to bottom.</div>
        <div class="psm-ca-add-row">
          <input id="psm-ca-${prefix}-input" type="text" list="${CHAMPION_LIST_ID}" placeholder="Champion name or ID">
          <button class="psm-ca-add" id="psm-ca-${prefix}-add" type="button">Add</button>
        </div>
        <div class="psm-ca-error" id="psm-ca-${prefix}-error"></div>
        <div class="psm-ca-priority-list" id="psm-ca-${prefix}-list"></div>
      </div>
    `;
  }

  function closeModal() {
    clearStatusTimer();
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
    setValue("psm-ca-queue", settings.queueId);
    setValue("psm-ca-primary-position", settings.primaryPosition || "");
    setValue("psm-ca-secondary-position", settings.secondaryPosition || "");
    setValue("psm-ca-accept-delay", settings.autoAcceptDelayMs);
    renderPriority("pickPriority");
    renderPriority("banPriority");
    renderRuntimeStatus();
  }

  function renderCatalogs() {
    const queueList = document.getElementById(QUEUE_LIST_ID);
    if (queueList) {
      const rows = [...catalog.queues];
      if (catalog.currentQueueId && !rows.some((item) => Number(item.id) === catalog.currentQueueId)) {
        rows.push({ id: catalog.currentQueueId, name: "Current lobby queue" });
      }
      queueList.innerHTML = rows
        .filter((item) => Number(item?.id) > 0)
        .map((item) => `<option value="${Number(item.id)}">${escapeHtml(item.name || `Queue ${item.id}`)}</option>`)
        .join("");
    }

    const championList = document.getElementById(CHAMPION_LIST_ID);
    if (championList) {
      championList.innerHTML = catalog.champions
        .filter((item) => Number(item?.id) > 0 && item?.name)
        .map((item) => `<option value="${escapeHtml(item.name)}">#${Number(item.id)}</option>`)
        .join("");
    }
  }

  function championName(id) {
    const found = catalog.champions.find((item) => Number(item?.id) === Number(id));
    return found?.name || `Champion ${id}`;
  }

  function resolveChampion(value) {
    const raw = String(value || "").trim();
    if (!raw) return null;
    if (/^\d+$/.test(raw)) {
      const id = Number(raw);
      return id > 0 ? id : null;
    }
    const lower = raw.toLowerCase();
    const found = catalog.champions.find((item) => String(item?.name || "").toLowerCase() === lower);
    return found ? Number(found.id) : null;
  }

  function addPriority(key, inputId, errorId) {
    const input = document.getElementById(inputId);
    const error = document.getElementById(errorId);
    if (!input) return;
    const championId = resolveChampion(input.value);
    if (!championId) {
      if (error) error.textContent = catalog.champions.length ? "Choose a champion from the list or enter a numeric champion ID." : "League champion catalog unavailable. Enter a numeric champion ID.";
      return;
    }
    if (settings[key].includes(championId)) {
      if (error) error.textContent = "That champion is already in this priority list.";
      return;
    }
    if (settings[key].length >= 10) {
      if (error) error.textContent = "Priority lists are limited to 10 champions.";
      return;
    }
    settings[key] = [...settings[key], championId];
    input.value = "";
    if (error) error.textContent = "";
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
    list.innerHTML = items.map((championId, index) => `
      <div class="psm-ca-priority-item" data-index="${index}">
        <div class="psm-ca-priority-index">${index + 1}</div>
        <div class="psm-ca-priority-name">${escapeHtml(championName(championId))} <span style="color:#607080">#${championId}</span></div>
        <button class="psm-ca-icon-btn" type="button" data-action="up" aria-label="Move up">↑</button>
        <button class="psm-ca-icon-btn" type="button" data-action="down" aria-label="Move down">↓</button>
        <button class="psm-ca-icon-btn" type="button" data-action="remove" aria-label="Remove">×</button>
      </div>
    `).join("");
    list.querySelectorAll(".psm-ca-priority-item").forEach((row) => {
      const index = Number(row.getAttribute("data-index"));
      row.querySelector('[data-action="up"]')?.addEventListener("click", () => movePriority(key, index, -1));
      row.querySelector('[data-action="down"]')?.addEventListener("click", () => movePriority(key, index, 1));
      row.querySelector('[data-action="remove"]')?.addEventListener("click", () => removePriority(key, index));
    });
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

  function saveAutomationSettings() {
    const queueRaw = String(value("psm-ca-queue")).trim();
    const queueId = queueRaw ? Number(queueRaw) : null;
    const primary = String(value("psm-ca-primary-position") || "").trim() || null;
    const secondary = String(value("psm-ca-secondary-position") || "").trim() || null;
    const autoQueueEnabled = checked("psm-ca-auto-queue");
    const autoRequeueEnabled = checked("psm-ca-auto-requeue");
    const autoPickEnabled = checked("psm-ca-auto-pick");
    const autoBanEnabled = checked("psm-ca-auto-ban");

    if ((autoQueueEnabled || autoRequeueEnabled) && (!Number.isInteger(queueId) || queueId <= 0)) {
      showSaveError("Choose a valid queue before enabling Auto Queue or Auto Requeue.");
      return;
    }
    if ((primary && !secondary) || (!primary && secondary)) {
      showSaveError("Choose both primary and secondary roles, or leave both unset.");
      return;
    }
    if (primary && primary === secondary) {
      showSaveError("Primary and secondary roles must be different.");
      return;
    }
    if (autoPickEnabled && settings.pickPriority.length === 0) {
      showSaveError("Add at least one champion before enabling Auto Pick.");
      return;
    }
    if (autoBanEnabled && settings.banPriority.length === 0) {
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
      queueId,
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
