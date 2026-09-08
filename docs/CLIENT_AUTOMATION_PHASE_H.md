# Client Automation vNext — Phase H Integration Hardening

Status: automated hardening complete; first live QA findings remediated; repeat live League-client QA pending
Branch: `codex/client-automation-vnext`
Stable release protected: `v1.0.1`

## Objective

Phase H hardens the Phase B-G Client Automation implementation before any release-candidate decision or live-user rollout.

This phase does not change the product scope. Client Automation remains limited to League client workflow automation:

- Auto Queue
- Auto Accept
- Auto Requeue
- Auto Pick
- Auto Ban

It does not automate gameplay, interact with Vanguard, weaken anti-cheat behavior, automate AFK behavior, or perform in-game combat/movement actions.

## Authoritative Auto Accept path

The event-driven Python controller is the only authoritative Auto Accept implementation in vNext.

The inherited Rose/Jade `AA.js` addon previously:

- watched ready-check DOM state
- scheduled its own timer
- issued a direct POST to `/lol-matchmaking/v1/ready-check/accept`
- optionally hid the ready-check modal and muted related sound requests

That creates an unsafe duplicate-controller condition when the new PSM Auto Accept implementation is enabled. Phase H therefore turns the inherited addon into an inert compatibility shim.

Historical Jade DataStore values are intentionally left untouched, but they no longer perform ready-check mutations. New behavior is configured only through PSM Client Automation.

## Reconnect lifecycle

On LCU WebSocket close:

1. pending Auto Accept timers are cancelled
2. pending Auto Queue/Requeue timers are cancelled
3. pending Auto Pick completion is cancelled
4. pending Auto Ban completion is cancelled
5. no automatic action may execute from stale pre-disconnect state

On LCU WebSocket open:

1. the WAMP JSON API subscription must succeed first
2. PSM reads the authoritative current gameflow phase
3. matchmaking/ready-check automation reconciles that phase
4. Champion Select automation reconciles that phase
5. if already in Champion Select, PSM performs one bounded current-session reconciliation

The WebSocket transport callback is isolated so a consumer failure cannot crash the underlying connection loop.

## Settings hot reload

Client Automation settings are written to the dedicated `[ClientAutomation]` config section.

After persistence succeeds, the Pengu bridge invokes a shared-state callback owned by the LCU WebSocket thread. This immediately reconciles the currently active League phase.

Consequences:

- enabling Auto Accept during an active actionable ready check can reconcile without restarting PSM
- enabling Auto Queue while already in an eligible Lobby can reconcile without restarting PSM
- enabling Auto Pick/Auto Ban while already in Champion Select triggers one bounded session reconciliation
- disabling a feature prevents delayed operations from executing because controllers re-read config before mutation

If the hot-reload callback itself fails, the saved settings remain valid and controllers still reload configuration on the next League event. Persistence success is not falsely reported as failure.

## Runtime telemetry

The settings bridge exposes:

- current phase
- whether the Client Automation master switch is enabled
- current coarse activity/status
- LCU WebSocket connected/disconnected state
- transport label
- queue catalog availability
- champion catalog availability

When the automation master switch is enabled but the LCU WebSocket is disconnected, the status becomes `League disconnected` instead of presenting stale lobby/gameflow text as current.

## Catalog behavior

Queue and champion catalogs continue to come from the connected local League client. PSM does not hard-code Riot's permanent queue-name table.

The bridge reports availability independently for each catalog so live QA can distinguish:

- League not connected
- League connected but queue catalog unavailable
- League connected but champion catalog unavailable
- both catalogs available

Numeric IDs remain a deliberate fallback for champion priorities and queue configuration; PSM does not silently invent catalog entries.

## Live-QA remediation implemented

The first live League-client UI pass exposed two integration/UX problems:

1. champion and queue controls were too ID-centric and did not provide a proper search interaction
2. catalog data could remain unavailable in an already-open panel until the client/PSM lifecycle was restarted or the modal reopened

Phase H now includes the following remediation on the same branch.

### Searchable champion priorities

Pick and Ban priority editors now use custom searchable comboboxes instead of relying on a plain datalist.

- case-insensitive name search
- prefix/word-prefix/substring ranking
- keyboard Up/Down/Enter/Escape navigation
- mouse selection
- champion title and ID as secondary metadata when available
- champion portrait path retained from League's local catalog when available, with a non-destructive fallback avatar
- exact numeric champion ID remains supported as an advanced fallback
- duplicate/max-10 rules remain enforced

The backend still stores ordered champion IDs only.

### Searchable queue selection

Queue configuration now uses a searchable selector populated from League's current local queue catalog.

- search by current queue name
- keyboard and mouse selection
- selected queue name plus internal queue ID displayed to the user
- numeric queue ID remains available as a fallback
- live queue validity is still rechecked by the existing backend before automation acts

### Last-known-good catalog cache

The bridge persists a local display cache under PSM state storage after a successful live catalog fetch.

The cache may be used for:

- champion display names/titles/icons while League is temporarily unavailable
- queue display names while League is temporarily unavailable

The cache is not execution authority. Live League state remains authoritative before matchmaking, pick, or ban mutations.

The catalog response distinguishes:

- live data
- cached data
- mixed live/cache data
- unavailable data

and reports live availability separately for queue and champion catalogs.

### Automatic catalog recovery

The Client Automation UI automatically requests fresh catalogs when it observes the LCU transport reconnecting.

If League reports connected but one or both catalog endpoints are not ready yet, the UI performs a bounded retry sequence while the modal is open. This is not a new permanent LCU polling loop.

Opening the modal also requests fresh catalog data, and a user-accessible `Refresh Data` control is available as a diagnostic/manual fallback.

Normal users should not need to restart PSM merely because a catalog was unavailable during an earlier request.

### Runtime/status UX

The runtime card now shows:

- League/transport state
- current gameflow state
- queue live/cached/unavailable status and count
- champion live/cached/unavailable status and count
- last catalog refresh age when available
- manual `Refresh Data`

Save feedback is state-aware rather than always claiming changes wait for the next client state.

### Section/icon treatment

The Client Automation UI now has visible icons for its major hierarchy instead of leaving numbered section headers visually empty:

- Client Automation launcher/header
- runtime/activity card
- `01 / MATCHMAKING`
- `02 / CHAMPION SELECT`
- queue, delay, role, and priority field labels where useful

Icons are inline UI SVGs so no additional external asset or image dependency is introduced.

## Phase H automated gates

CI must pass:

- Python compileall
- PSM Client Automation plugin JavaScript syntax
- retired Rose/Jade AutoAccept shim JavaScript syntax
- repository unit tests
- Client Automation hardening invariants
- public-source boundary validation

Hardening tests specifically guard that:

- the legacy Jade AutoAccept file no longer contains the ready-check accept endpoint or polling controller
- WebSocket `on_open` consumers run only after JSON API subscription succeeds
- disconnect cancellation and reconnect reconciliation hooks remain wired
- settings hot-reload callback/provider wiring remains present
- disconnected runtime status is explicitly surfaced
- catalog connection/availability telemetry remains present
- champion catalog normalization preserves safe display metadata while IDs remain authoritative

The last fully verified pre-remediation baseline passed the complete `Public source checks` workflow. The live-QA remediation commits require a fresh successful workflow before Phase H can be considered synthetically re-verified.

Automated verification never substitutes for live League-client endpoint/UI QA.

## Repeat live League-client QA required

### Connection lifecycle

- launch PSM before League
- launch League after PSM
- close/reopen League while PSM remains running
- force a temporary LCU/WebSocket disconnect if practical
- reconnect while in Lobby
- reconnect while in ReadyCheck
- reconnect while in Champion Select
- verify no stale action executes after disconnect
- verify an already-open Client Automation modal refreshes catalog state after reconnect without restarting PSM

### Catalog/control surface

- queue search returns current League queue names
- numeric queue ID fallback still works
- champion search resolves partial names such as `yas` to expected matches
- keyboard champion search navigation works
- champion IDs persist internally after name selection
- Pick/Ban priority move/remove controls remain correct
- live queue/champion counts are shown when available
- cached catalog labels are clearly marked when live data is unavailable
- manual Refresh Data updates the modal without resetting saved automation settings
- section/header icons render without missing assets

### Settings hot reload

- master OFF -> enable while in Lobby
- enable/disable Auto Accept during ReadyCheck before its delay expires
- enable Auto Pick during an active local pick action
- enable Auto Ban during an active local ban action
- disable Auto Pick/Auto Ban during the 350 ms completion window and confirm no stale completion occurs

### Matchmaking

- eligible solo lobby
- already searching
- premade non-leader
- premade leader
- queue mismatch in premade
- queue change in solo lobby
- role preferences accepted
- role preferences rejected/unsupported
- active penalty/restriction
- manual queue cancellation
- post-game Auto Requeue

### Champion Select

- manual pick before PSM acts
- manual pick change during completion delay
- manual ban before PSM acts
- manual ban change during completion delay
- ally intent appears before Auto Ban selection
- ally intent appears during completion delay
- priority #1 unavailable -> fallback candidate
- no valid candidate -> no mutation

### UI/control surface

- Client Automation launcher survives PSM settings panel reopen
- modal survives normal League navigation
- disconnected state is visible and non-destructive
- save feedback matches the active client state
- no duplicate legacy Rose/Jade AutoAccept settings path remains operational

## Release gate

Phase H completion does not itself authorize a release.

Do not modify:

- application version
- `v1.0.1` tag
- existing installer asset
- `stable/manifest.json`
- updater signing state
- production website release target

A later explicit release-candidate phase must decide semantic version, build/sign/package the installer, execute live QA, verify hashes/signatures, and only then update the signed stable release channel.