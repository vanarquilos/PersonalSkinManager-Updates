/**
 * Personal Skin Manager Client Automation owns ready-check acceptance.
 *
 * The inherited Rose/Jade AutoAccept addon previously watched League client
 * DOM state and issued its own POST to the ready-check accept endpoint. Keeping
 * that path active alongside PSM's event-driven Python controller could create
 * duplicate or competing accepts, so the legacy addon is intentionally a no-op
 * in Client Automation vNext.
 *
 * Historical DataStore values are left untouched for compatibility. They have
 * no runtime effect here and can be ignored by the new control surface.
 */
(() => {
  try {
    console.info("[PSM-ClientAutomation] Legacy Rose/Jade AutoAccept is disabled; PSM Client Automation is authoritative.");
  } catch (_) {}
})();
