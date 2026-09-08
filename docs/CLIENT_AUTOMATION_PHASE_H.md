# Client Automation vNext — Phase H Integration Hardening

Status: automated hardening complete; live League-client QA pending
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

If the hot-reload callback itself fails, the saved settings remain valid and controllers still re-read configuration on the next League event. Persistence success is not falsely reported as failure.

## Runtime telemetry

The settings bridge can expose:

- current phase
- whether the Client Automation master switch is enabled
- current coarse activity/status
- LCU WebSocket connected/disconnected state
- transport label
- queue catalog availability
- champion catalog availability

When the automation master switch is enabled but the LCU WebSocket is disconnected, the status becomes `League disconnected` instead of presenting stale lobby/gameflow text as current.

## Catalog behavior

Queue and champion catalogs continue to come from the connected local League client.

The bridge reports availability independently for each catalog so live QA can distinguish:

- League not connected
- League connected but queue catalog unavailable
- League connected but champion catalog unavailable
- both catalogs available

Numeric IDs remain a deliberate fallback for champion priorities and queue configuration; PSM does not silently invent catalog entries.

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

### Automated verification result

Phase H code and documentation have passed the full `Public source checks` workflow. The most recent verified run at the time this document was finalized was run `#55`.

Passed steps:

- dependency setup
- Python compileall
- Client Automation JavaScript syntax
- retired legacy AutoAccept shim syntax
- full repository unit-test discovery/execution
- public-source boundary validation

This automated result does not substitute for live League-client endpoint/UI QA.

## Live League-client QA still required

Automated tests cannot prove Riot client endpoint/DOM behavior across every live client build. Before a release candidate, test manually with a normal League client session.

### Connection lifecycle

- launch PSM before League
- launch League after PSM
- close/reopen League while PSM remains running
- force a temporary LCU/WebSocket disconnect if practical
- reconnect while in Lobby
- reconnect while in ReadyCheck
- reconnect while in Champion Select
- verify no stale action executes after disconnect

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
- queue catalog populates when available
- champion catalog populates when available
- disconnected state is visible and non-destructive
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
