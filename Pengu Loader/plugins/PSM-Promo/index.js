/**
 * @name PSM-Promo
 * @description Phase 4C RC Hotfix: persistent creator card for Personal Skin Manager.
 */
(function psmPromoHotfix() {
  const VERSION = "1.0.0";
  const KEY = `psm.promo.seen.${VERSION}`;
  const ID = "psm-creator-card";

  const PORTFOLIO = "https://vanarquilos.dev";
  const TIKTOK = "https://www.tiktok.com/@vanarquilos";
  const FACEBOOK = "https://www.facebook.com/vanmichael.lelis/";

  function seen() {
    try { return localStorage.getItem(KEY) === "1"; }
    catch { return false; }
  }

  function markSeen() {
    try { localStorage.setItem(KEY, "1"); }
    catch {}
  }

  function champSelectVisible() {
    try {
      return Boolean(document.querySelector(
        ".champion-select,.champ-select-main,.champion-select-container,[data-screen='champ-select']"
      ));
    } catch {
      return false;
    }
  }

  function openExternal(url) {
    try {
      const opened = window.open(url, "_blank", "noopener,noreferrer");
      if (opened) opened.opener = null;
    } catch (error) {
      console.warn("[PSM-Promo] Could not open external link", error);
    }
  }

  function injectStyle() {
    if (document.getElementById("psm-promo-style")) return;

    const style = document.createElement("style");
    style.id = "psm-promo-style";
    style.textContent = `
      #${ID} {
        position:fixed;right:28px;bottom:76px;z-index:9999;width:338px;
        box-sizing:border-box;padding:18px;color:#edf3f8;
        background:radial-gradient(circle at 100% 0,rgba(139,92,246,.12),transparent 210px),
        radial-gradient(circle at 0 0,rgba(49,214,232,.08),transparent 220px),#080d12;
        border:1px solid #304354;border-top:2px solid #31d6e8;border-radius:7px;
        box-shadow:0 24px 64px rgba(0,0,0,.68);font-family:"Spiegel",Arial,sans-serif;
        opacity:0;transform:translateY(12px);transition:opacity .22s ease,transform .22s ease;
      }
      #${ID}.visible { opacity:1;transform:translateY(0); }
      #${ID}.psm-temporarily-hidden { opacity:0!important;pointer-events:none!important;transform:translateY(8px)!important; }
      #${ID} .close { position:absolute;right:10px;top:10px;width:26px;height:26px;background:#0b1219;
        border:1px solid #263746;border-radius:3px;color:#8191a2;cursor:pointer; }
      #${ID} .close:hover { color:#edf3f8;border-color:#31d6e8; }
      #${ID} .eyebrow { color:#31d6e8;font-size:9px;font-weight:700;letter-spacing:.18em; }
      #${ID} .title { margin-top:7px;font-family:"Beaufort for LOL",serif;font-size:19px;font-weight:700; }
      #${ID} .copy { margin-top:6px;padding-right:18px;color:#8191a2;font-size:11px;line-height:1.5; }
      #${ID} .primary { width:100%;min-height:36px;margin-top:14px;background:#31d6e8;border:1px solid #31d6e8;
        border-radius:4px;color:#061014;font-size:10px;font-weight:700;cursor:pointer; }
      #${ID} .primary:hover { background:#74e9f5;border-color:#74e9f5; }
      #${ID} .social { display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px; }
      #${ID} .social button { min-height:33px;background:#0b1219;border:1px solid #304354;border-radius:4px;
        color:#cbd6df;font-size:10px;font-weight:700;cursor:pointer; }
      #${ID} .social button:hover { border-color:#8b5cf6;color:#edf3f8; }
      #${ID} .meta { margin-top:11px;color:#5e6d7b;font-size:9px; }
    `;
    document.head.appendChild(style);
  }

  function permanentlyDismiss() {
    markSeen();
    document.getElementById(ID)?.remove();
  }

  function updateVisibility() {
    const card = document.getElementById(ID);
    if (!card) return;
    card.classList.toggle("psm-temporarily-hidden", champSelectVisible());
  }

  function show() {
    if (seen() || document.getElementById(ID)) return false;

    injectStyle();

    const card = document.createElement("aside");
    card.id = ID;
    card.innerHTML = `
      <button class="close" type="button" aria-label="Dismiss">×</button>
      <div class="eyebrow">PERSONAL SKIN MANAGER</div>
      <div class="title">Built by Van Arquilos</div>
      <div class="copy">I build software, developer tools, and experiments like this. See more projects and build updates.</div>
      <button class="primary" type="button">View Portfolio</button>
      <div class="social">
        <button type="button" data-link="tiktok">TikTok</button>
        <button type="button" data-link="facebook">Facebook</button>
      </div>
      <div class="meta">Personal build · v${VERSION}</div>
    `;

    card.querySelector(".close").addEventListener("click", permanentlyDismiss);

    // External links intentionally do NOT dismiss or mark the card seen.
    card.querySelector(".primary").addEventListener("click", () => openExternal(PORTFOLIO));
    card.querySelector('[data-link="tiktok"]').addEventListener("click", () => openExternal(TIKTOK));
    card.querySelector('[data-link="facebook"]').addEventListener("click", () => openExternal(FACEBOOK));

    document.body.appendChild(card);
    requestAnimationFrame(() => card.classList.add("visible"));
    updateVisibility();

    // Low-cost visibility check only while the small card exists.
    const visibilityTimer = setInterval(() => {
      if (!document.getElementById(ID)) {
        clearInterval(visibilityTimer);
        return;
      }
      updateVisibility();
    }, 1500);

    return true;
  }

  function schedule() {
    if (seen()) return;

    let attempts = 0;
    const timer = setInterval(() => {
      attempts += 1;
      if (show() || attempts >= 12) clearInterval(timer);
    }, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(schedule, 3500), { once: true });
  } else {
    setTimeout(schedule, 3500);
  }
})();
