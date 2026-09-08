# Personal Skin Manager — Client Automation vNext

Status: implementation in progress through Phase G
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

The Phase G control surface exposes current League phase/status, including states such as:

- Disabled
- Waiting for League
- Lobby ready
- Searching for match
- Match found
- Champion Select
- In game
- Post-game

Fine-grained last-action telemetry such as the exact champion currently being picked/banned may be added during integration hardening without changing the settings contract.

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

If a manual action changes the state during a pending automation delay, automation cancels for that action.

### Auto Ban

- `auto_ban_enabled: bool = false`
- `ban_priority: list[int]`
- `protect_ally_intents: bool = true`

The list is ordered and bounded to 10 champion IDs. PSM selects the first currently valid ban candidate.

When `protect_ally_intents` is enabled, PSM skips champions currently indicated/hovered by allies when that information is available in the champion-select session. The protection is rechecked before completing the ban so a newly appearing ally intent cancels a pending automated ban.

Before completing a ban, PSM revalidates the active action and current session exactly as for Auto Pick.

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

Coordinates Auto Pick and Auto Ban with ordered fallback, manual override, delayed revalidation, ally-intent protection, and action-id idempotency.

### `automation/lcu_adapter.py`

Applies optional persisted role preferences immediately before queue start while preserving the existing matchmaking controller contract. Invalid or rejected role preference mutations fail closed.

### `automation/settings_contract.py`

Pure UI/backend validation and serialization contract for Phase G. It validates queue/role settings, priority lists, delay presets, status labels, and local queue/champion catalog normalization without importing the full Pengu runtime dependency graph.

### `pengu/communication/client_automation_message_handler.py`

Extends the existing bridge with dedicated Client Automation messages. It deliberately does not overload the inherited General `settings-save` path.

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

## Event model

Primary automation trigger source: existing authenticated `OnJsonApiEvent` WebSocket subscription.

Relevant event families:

- gameflow phase changes
- ready-check state changes
- lobby/matchmaking state changes
- champion-select session/action changes

Polling is limited to bounded reconciliation where an event could have been missed. Phase G runtime UI status requests run only while the configuration modal is open and read existing shared phase state rather than repeatedly polling LCU.

## Concurrency and idempotency

The implementation protects against:

- duplicate WebSocket events
- HTTP retry duplicates
- multiple scheduled actions for the same state
- stale delayed actions
- League state changing between selection and completion

Guards include:

- one accept attempt per ready-check generation
- one pick completion attempt per champion-select action id
- one ban completion attempt per champion-select action id
- one queue-start attempt per eligible lobby transition unless state materially changes

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
- already accepted -> no action
- already declined -> no action
- manual accept during delay -> cancel
- manual decline during delay -> cancel
- ready check expires during delay -> cancel
- reconnect during ready check -> bounded reconciliation

### Queue/Requeue

- valid solo lobby -> queues once
- already matchmaking -> no duplicate start
- premade non-leader -> no queue attempt
- blocking penalty/error -> no retry loop
- manual stop/cancel -> no immediate unwanted requeue
- post-game eligible lobby -> requeues once when enabled
- configured role pair -> applied before queue start
- incomplete/duplicate role pair -> fail closed
- League-rejected role preference -> no queue start

### Pick

- preferred champion available -> select/complete once
- first preference unavailable -> use next valid fallback
- no valid preference -> no destructive fallback
- manual selection change -> automation cancels
- duplicate session events -> no duplicate completion

### Ban

- preferred ban available -> ban once
- first preference unavailable -> next valid fallback
- ally intent protected -> candidate skipped
- new ally intent during completion delay -> cancel
- manual ban change -> automation cancels

### Settings/control surface

- master and all child feature settings round-trip through the dedicated bridge
- queue required before Auto Queue/Requeue can be enabled
- role pair validation is enforced on both UI and backend contract
- Pick/Ban priorities preserve order, deduplicate, and cap at 10
- Auto Pick/Ban cannot be enabled without at least one configured champion
- queue/champion catalogs fail gracefully when League is unavailable
- status reflects current shared gameflow phase
- Client Automation plugin JavaScript passes syntax validation

### Regression

Must remain unchanged:

- skin selection
- chroma handling
- custom mods
- Swiftplay handling
- gameflow monitoring
- WebSocket reconnect behavior
- updater/signature behavior
- installer/uninstaller behavior

## Development phases

### Phase A — Architecture and specification — COMPLETE

### Phase B — LCU primitives — COMPLETE

### Phase C — Auto Accept — COMPLETE

### Phase D — Auto Queue and Auto Requeue — COMPLETE

### Phase E — Auto Pick — COMPLETE

### Phase F — Auto Ban — COMPLETE

### Phase G — UI and persistence — IMPLEMENTED / SYNTHETIC GATE PASSED

Implemented:

- dedicated Client Automation settings bridge
- isolated settings validation/serialization contract
- one Client Automation launcher inside the existing settings surface
- dedicated configuration modal
- master toggle and all child controls
- queue input/catalog
- optional role preferences
- Auto Accept delay presets
- ordered Pick/Ban priority editors with add/reorder/remove
- local League champion catalog when available
- phase-based runtime status
- role preferences applied before queue start
- JavaScript syntax gate
- synthetic settings/adapter/catalog tests

Live League-client UI/endpoint QA remains part of integration hardening and release-candidate QA; Phase G completion does not imply those live checks have already been performed.

### Phase H — Integration hardening — NEXT

- verify reconnect/reload behavior across all automation controllers
- validate dedicated bridge lifecycle in a live League client
- validate queue/champion catalog endpoint shapes live
- validate role preference endpoint behavior across queue types
- harden settings hot-reload/transition behavior
- ensure the inherited legacy Rose/Jade AutoAccept path cannot compete with the new authoritative Python Auto Accept pipeline
- expand diagnostics/activity telemetry where it materially improves QA

### Phase I — QA and release candidate

- full synthetic test suite
- live League QA
- regression QA
- release notes draft

### Phase J — Release gate

Only after all prior phases pass:

- choose next semantic version
- build/package
- sign required release metadata
- verify installer hash/size
- publish GitHub release
- update signed stable manifest
- update website/README/docs

## Explicitly out of scope for this vNext baseline

- gameplay automation
- anti-AFK behavior
- Vanguard bypass/evasion
- anti-cheat weakening
- memory/driver manipulation
- auto dodge
- auto chat
- auto honor
- automatic runes/spells
- pick-order trade automation
- role-swap automation

These are not silently added during implementation. Any later expansion requires an explicit new scope decision.

## Current release protection

Until Phase J is explicitly authorized and passed, do not change:

- application version `1.0.1`
- published `v1.0.1` tag
- existing v1.0.1 installer/release asset
- `stable/manifest.json`
- signed stable updater state
- production website release target
