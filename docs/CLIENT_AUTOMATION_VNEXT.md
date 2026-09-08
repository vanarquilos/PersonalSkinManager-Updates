# Personal Skin Manager — Client Automation vNext

Status: implementation complete through Phase H automated hardening; live League-client QA pending
Branch: `codex/client-automation-vnext`
Stable release protected: `v1.0.1`

## Product definition

Client Automation is one user-facing PSM feature area for League client workflow automation. It combines:

- Auto Queue
- Auto Accept
- Auto Requeue
- Auto Pick
- Auto Ban

This feature automates League client interactions only. It does not automate gameplay, interact with Vanguard, modify anti-cheat behavior, automate AFK behavior, or perform in-game actions.

## Product principles

1. Disabled by default.
2. Manual user actions always win over pending automation.
3. Event-driven behavior is preferred over constant polling.
4. Every action must be valid for the current League client state.
5. Every potentially destructive or stale action is revalidated immediately before execution.
6. Duplicate League events must not produce duplicate actions.
7. Automation errors must fail closed and leave the user in control.
8. Stable `v1.0.1`, its release asset, tag, and signed stable manifest remain unchanged until a new release passes QA.

## User-facing information architecture

### Client Automation

Master toggle:

- `Client Automation` — OFF by default

### Matchmaking

- `Auto Queue`
- `Queue`
- `Primary role` where applicable
- `Secondary role` where applicable
- `Auto Accept`
- `Accept delay`
- `Auto Requeue`

### Champion Select

- `Auto Pick`
- ordered Pick Priority list
- `Auto Ban`
- ordered Ban Priority list
- `Protect ally intents` — ON by default when Auto Ban is enabled

### Activity

The control surface exposes current League phase/status, including states such as:

- Disabled
- Waiting for League
- League disconnected
- Lobby ready
- Searching for match
- Match found
- Champion Select
- In game
- Post-game

The bridge also reports LCU WebSocket connection state plus queue/champion catalog availability for integration QA.

## Settings baseline

### Master

`client_automation_enabled: bool = false`

The master toggle gates all automation actions even if child settings remain persisted.

### Auto Queue

- `auto_queue_enabled: bool = false`
- `queue_id: int | null`
- `primary_position: string | null`
- `secondary_position: string | null`

Auto Queue only runs when:

- Client Automation is enabled
- League is connected
- an eligible lobby exists or can be created safely
- the configured queue is valid
- the user is allowed to start matchmaking
- matchmaking is not already active
- no blocking penalty/error condition is present

For premade lobbies, PSM must not attempt to start matchmaking unless the local player has the required lobby authority.

When both role preferences are configured, PSM applies them through the local lobby position-preferences endpoint immediately before starting matchmaking. Incomplete, duplicate, invalid, or League-rejected role preferences fail closed and prevent that queue-start attempt.

### Auto Accept

- `auto_accept_enabled: bool = false`
- `auto_accept_delay_ms: int = 1000`

Initial allowed delay presets:

- 0 ms
- 500 ms
- 1000 ms
- 2000 ms
- 3000 ms

Auto Accept must:

1. detect a valid ready check
2. schedule the configured delay
3. re-read/revalidate the current ready-check state
4. cancel if the user already accepted, declined, or the ready check ended
5. send accept only once

The new event-driven Python controller is the only authoritative Auto Accept path. The inherited Rose/Jade DOM-driven AutoAccept addon is intentionally inert in vNext so it cannot issue a competing ready-check mutation.

### Auto Requeue

- `auto_requeue_enabled: bool = false`

Definition for vNext:

After a completed game/session, when League returns the user to an eligible lobby and the configured queue is still valid, PSM may start matchmaking again.

Auto Requeue must not create an uncontrolled retry loop after errors, penalties, lobby changes, or manual cancellation.

### Auto Pick

- `auto_pick_enabled: bool = false`
- `pick_priority: list[int]`

The list is ordered and bounded to 10 champion IDs. PSM selects the first currently valid configured champion.

A candidate is skipped if it is unavailable because of current champion-select state, including being banned, unavailable, already selected where disallowed, or otherwise rejected by the current session.

Before completing the local pick action, PSM revalidates:

- the same local action is still active
- the action is still a pick
- the user has not manually changed the selection/action state
- the configured champion is still valid
- Auto Pick is still enabled

If a manual action or settings change invalidates the pending operation during the completion delay, automation cancels for that action.

### Auto Ban

- `auto_ban_enabled: bool = false`
- `ban_priority: list[int]`
- `protect_ally_intents: bool = true`

The list is ordered and bounded to 10 champion IDs. PSM selects the first currently valid ban candidate.

When `protect_ally_intents` is enabled, PSM skips champions currently indicated/hovered by allies when that information is available in the champion-select session. The protection is rechecked before completing the ban so a newly appearing ally intent cancels a pending automated ban.

Before completing a ban, PSM revalidates the active action, current session, current protection state, and whether Auto Ban is still enabled.

## State machine

Client Automation is coordinated by one matchmaking/ready-check controller plus an isolated champion-select coordinator rather than unrelated loops.

```text
Disconnected
    |
    v
Lobby
    |
    | Auto Queue
    v
Matchmaking
    |
    v
ReadyCheck
    |
    | Auto Accept
    v
ChampSelect
    |
    | Auto Pick / Auto Ban
    v
InProgress
    |
    v
PostGame / EndOfGame
    |
    v
Lobby
    |
    | Auto Requeue (if enabled and still eligible)
    +------------------------------> Matchmaking
```

The controllers tolerate non-linear transitions, cancellation, dodges, declined ready checks, reconnects, lobby changes, penalties, and League restarts.

On LCU WebSocket disconnect, pending matchmaking, ready-check, pick, and ban timers are cancelled by routing the controllers into a disconnected lifecycle state. On reconnect, PSM waits for the JSON API subscription, reads the authoritative current gameflow phase, and reconciles that phase. Champion Select additionally performs one bounded current-session reconciliation.

## Internal architecture

```text
lcu/
  features/
    lcu_matchmaking.py
    lcu_ready_check.py
    lcu_champ_select_automation.py

automation/
  __init__.py
  config.py
  controller.py
  champ_select.py
  lcu_adapter.py
  settings_contract.py

pengu/
  communication/
    client_automation_message_handler.py

Pengu Loader/plugins/
  PSM-ClientAutomation/
    index.js
  ROSE-Jade/config/js/addons/
    AA.js  # inert compatibility shim in vNext
```

### `LCUAPI`

Generic POST support is implemented consistently with existing connection recovery, timeout handling, cache invalidation, and logging behavior.

### `lcu_matchmaking.py`

Owns lobby/search/play-again primitives plus local role-preference mutation.

### `lcu_ready_check.py`

Owns ready-check read/accept primitives and actionable-state normalization.

### `lcu_champ_select_automation.py`

Owns champion-select action inspection, ally intents, selected/banned champion collection, local action selection, and completion primitives.

### `automation/config.py`

Owns typed persisted Client Automation settings. The feature remains default-off.

### `automation/controller.py`

Coordinates Auto Queue, Auto Requeue, and Auto Accept decisions with duplicate/stale-action protection.

### `automation/champ_select.py`

Coordinates Auto Pick and Auto Ban with ordered fallback, manual override, delayed revalidation, ally-intent protection, action-id idempotency, and settings revalidation before completion.

### `automation/lcu_adapter.py`

Applies optional persisted role preferences immediately before queue start while preserving the existing matchmaking controller contract. Invalid or rejected role preference mutations fail closed.

### `automation/settings_contract.py`

Pure UI/backend validation and serialization contract. It validates queue/role settings, priority lists, delay presets, status labels, and local queue/champion catalog normalization without importing the full Pengu runtime dependency graph.

### `pengu/communication/client_automation_message_handler.py`

Extends the existing bridge with dedicated Client Automation messages. It deliberately does not overload the inherited General `settings-save` path.

After a successful settings save it invokes a shared-state hot-reload callback owned by the LCU WebSocket thread. If that callback fails, persistence remains successful and the controllers still reload configuration on the next League event.

Supported requests:

- `client-automation-settings-request`
- `client-automation-settings-save`
- `client-automation-status-request`
- `client-automation-catalog-request`

Supported responses:

- `client-automation-settings-data`
- `client-automation-settings-saved`
- `client-automation-status-data`
- `client-automation-catalog-data`

### `PSM-ClientAutomation/index.js`

Adds a Client Automation launcher to the existing PSM settings flyout and opens a dedicated control surface for all five automation features. Queue and champion choices are sourced from the local League client when available; numeric IDs remain an explicit fallback rather than hard-coded stale catalogs.

### `ROSE-Jade/config/js/addons/AA.js`

The inherited AutoAccept addon is now an inert compatibility shim. It no longer polls the ready-check DOM, hides ready-check state, patches ready-check sound requests, exposes a second AutoAccept settings path, or posts to the ready-check accept endpoint.

## Event model

Primary automation trigger source: existing authenticated `OnJsonApiEvent` WebSocket subscription.

Relevant event families:

- gameflow phase changes
- ready-check state changes
- lobby/matchmaking state changes
- champion-select session/action changes

Polling is limited to bounded reconciliation where an event could have been missed. Runtime UI status requests run only while the configuration modal is open and read existing shared phase/transport state rather than repeatedly polling LCU.

## Concurrency and idempotency

The implementation protects against:

- duplicate WebSocket events
- HTTP retry duplicates
- multiple scheduled actions for the same state
- stale delayed actions
- League state changing between selection and completion
- a disconnect occurring while an action is pending
- a settings change occurring while an action is pending

Guards include:

- one accept attempt per ready-check generation
- one pick completion attempt per champion-select action id
- one ban completion attempt per champion-select action id
- one queue-start attempt per eligible lobby transition unless state materially changes
- disconnect cancellation before reconnect reconciliation

## Manual override rule

Manual input has priority.

If PSM schedules an action and the League state changes in a way consistent with user input before execution, PSM cancels the pending automatic action. PSM must never repeatedly overwrite a user's manual champion selection or ban selection.

## Failure behavior

On an LCU error or unexpected response:

- log the failure without credentials or sensitive authorization data
- do not retry indefinitely
- refresh the LCU connection only through the existing connection lifecycle
- fail closed for the current action
- allow later valid state transitions to recover naturally

## Logging baseline

Examples:

```text
[AUTOMATION] Queue started
[AUTOMATION] Role preferences applied: JUNGLE / MIDDLE
[READY CHECK] Auto-accept scheduled: 1.0s
[READY CHECK] Accepted
[CHAMP SELECT] Auto Pick selected champion <id>; revalidating before lock
[CHAMP SELECT] Auto Pick complete: champion <id>
[CHAMP SELECT] Auto Ban selected champion <id>; revalidating before lock
[CHAMP SELECT] Auto Ban complete: champion <id>
[AUTOMATION] Pending actions cancelled after LCU disconnect
[AUTOMATION] Reconciled after LCU WebSocket reconnect: <phase>
[AUTOMATION] Settings hot-reloaded for phase: <phase>
```

Never log:

- League lockfile password
- Authorization header/token
- private updater signing material

## vNext QA baseline

### Master control

- master OFF means no automatic action can execute
- child settings persist without bypassing master OFF

### Ready check

- Auto Accept OFF -> never accepts
- valid ready check -> accepts once
- duplicate event -> no duplicate action
- manual accept/decline during delay -> pending PSM accept cancels
- disable Auto Accept during delay -> pending PSM accept does not execute
- disconnect during delay -> pending PSM accept is cancelled
- reconnect into ReadyCheck -> bounded state reconciliation

### Matchmaking

- Auto Queue OFF -> never queues
- already searching -> no duplicate queue start
- invalid/restricted lobby -> fail closed
- solo queue switch -> revalidate before start
- premade non-leader -> no start
- premade queue mismatch -> no silent change
- role preferences rejected -> no queue start
- manual cancellation -> no immediate restart loop
- completed-game Auto Requeue -> at most one eligible restart
- reconnect into Lobby -> reconcile current lobby once through normal guards

### Champion Select

- Auto Pick/Ban OFF -> no mutation
- priority #1 unavailable -> use next configured valid candidate
- no valid candidate -> no destructive fallback
- manual selection before automation -> preserve manual choice
- manual selection during completion delay -> cancel automation
- disable feature during completion delay -> cancel completion
- ally intent protection -> skip/cancel protected ban candidate
- duplicate session events -> no duplicate completion
- disconnect during completion delay -> cancel pending completion
- reconnect into ChampSelect -> bounded session reconciliation

### UI and bridge

- settings persist only to `[ClientAutomation]`
- successful save hot-reloads current phase without requiring PSM restart
- queue/champion catalogs are local-client sourced when available
- catalog payload reports connection and availability independently
- disconnected runtime status does not present stale lobby/gameflow text as current
- legacy Rose/Jade AutoAccept cannot compete with PSM Auto Accept

## Phase H automated verification

The repository CI additionally validates:

- Python compileall
- `PSM-ClientAutomation/index.js` syntax
- retired `ROSE-Jade/.../AA.js` shim syntax
- WebSocket `on_open` consumer behavior after JSON API subscription
- Client Automation integration/hot-reload wiring invariants
- full repository unit-test discovery/execution
- public-source boundary validation

The detailed live-client matrix is recorded in `docs/CLIENT_AUTOMATION_PHASE_H.md`.

## Release gate

Automated Phase H completion does not authorize a release.

Before a new stable release:

1. run the live League-client QA matrix
2. record actual endpoint/control-surface results
3. fix any compatibility defects on the same feature branch
4. rerun full automated verification
5. decide the semantic version explicitly
6. build/sign/package only after explicit release approval
7. verify installer hash/signature/provenance
8. update the signed stable manifest only at the final publication gate

Until then, do not modify:

- `APP_VERSION`
- `v1.0.1` tag
- existing `PersonalSkinManager_Setup.exe`
- `stable/manifest.json`
- published updater signing state
