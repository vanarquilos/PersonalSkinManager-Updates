# Personal Skin Manager — Client Automation vNext

Status: planning baseline
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

## Current-source findings

PSM already has the main infrastructure required for this feature:

- authenticated LCU connection handling
- generic GET/PUT/PATCH request support
- LCU feature-module structure
- a WebSocket connection subscribed to `OnJsonApiEvent`
- event routing for gameflow and champion-select state

The current repository also contains a legacy Rose/Pengu AutoAccept addon at:

`Pengu Loader/plugins/ROSE-Jade/config/js/addons/AA.js`

That addon detects the ready-check modal from League client DOM state and POSTs `/lol-matchmaking/v1/ready-check/accept` after a delay. It is reference material only for vNext. The new PSM implementation should live in the Python/LCU architecture rather than depending on DOM mutation observers, League-client UI scraping, or a separate Pengu settings path.

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

Expose a concise runtime status, for example:

- Waiting for lobby
- Queueing
- Match found
- Accepting in 1.0s
- Champion Select
- Picking Viego
- Viego unavailable; trying Kayn
- Banning Bel'Veth
- Automation paused by manual action

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

The list is ordered. PSM selects the first currently valid champion.

A candidate is skipped if it is unavailable because of current champion-select state, including being banned, unavailable, already selected where disallowed, or otherwise rejected by the current session.

Before completing the local pick action, PSM must revalidate:

- the same local action is still active
- the action is still a pick
- the user has not manually changed the selection/action state
- the configured champion is still valid

If a manual action changes the state during a pending automation delay, automation cancels for that action.

### Auto Ban

- `auto_ban_enabled: bool = false`
- `ban_priority: list[int]`
- `protect_ally_intents: bool = true`

The list is ordered. PSM selects the first currently valid ban candidate.

When `protect_ally_intents` is enabled, PSM must skip champions currently indicated/hovered by allies when that information is available in the champion-select session.

Before completing a ban, PSM revalidates the active action and current session exactly as for Auto Pick.

## State machine

Client Automation should be coordinated by one controller/state machine instead of five unrelated loops.

Conceptual progression:

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

The controller must also tolerate non-linear transitions, cancellation, dodges, declined ready checks, reconnects, lobby changes, penalties, and League restarts.

## Internal architecture baseline

Recommended modules:

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
  models.py
  state_machine.py
```

Responsibilities:

### `LCUAPI`

Add generic POST support consistent with existing connection recovery, timeout handling, cache invalidation, and logging behavior.

### `lcu_matchmaking.py`

Own only matchmaking/lobby primitives needed by Auto Queue and Auto Requeue.

### `lcu_ready_check.py`

Own ready-check read/accept primitives and ready-check normalization.

### `lcu_champ_select_automation.py`

Own champion-select action inspection, candidate validity checks, selection updates, and action completion primitives.

### `automation/config.py`

Typed/persisted Client Automation settings and validation.

### `automation/state_machine.py`

Normalize League client states relevant to automation.

### `automation/controller.py`

Coordinate feature decisions and prevent duplicate/stale actions. This is the only layer that decides whether an automatic action should happen.

## Event model

Primary trigger source: existing authenticated `OnJsonApiEvent` WebSocket subscription.

Relevant event families are expected to include:

- gameflow phase changes
- ready-check state changes
- lobby/matchmaking state changes
- champion-select session/action changes

Polling may be used only for bounded reconciliation/recovery where an event could have been missed, such as PSM starting in the middle of a ready check or reconnecting after a WebSocket interruption.

Do not introduce permanent high-frequency polling if the same state is already available from events.

## Concurrency and idempotency

The controller must protect against:

- duplicate WebSocket events
- HTTP retry duplicates
- multiple threads scheduling the same action
- stale delayed actions
- League state changing between selection and completion

Each automated action needs an idempotency key or equivalent local guard derived from the current League session/action identity.

Examples:

- one accept attempt per ready-check instance
- one pick completion attempt per champion-select action id
- one ban completion attempt per champion-select action id
- one queue-start attempt per eligible lobby transition unless state materially changes

## Manual override rule

Manual input has priority.

If PSM schedules an action and the League state changes in a way consistent with user input before execution, PSM cancels the pending automatic action.

PSM must never repeatedly overwrite a user's manual champion selection.

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
[AUTOMATION] Controller enabled
[AUTOMATION] Queue eligible: <queue>
[AUTOMATION] Queue started
[READY CHECK] Detected
[READY CHECK] Auto-accept scheduled: 1.0s
[READY CHECK] Accepted
[CHAMP SELECT] Pick action detected: <action id>
[CHAMP SELECT] Picking <champion>
[CHAMP SELECT] Candidate unavailable; trying next
[CHAMP SELECT] Manual state change detected; automation cancelled
[CHAMP SELECT] Ban complete: <champion>
[AUTOMATION] Requeue skipped: <reason>
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
- manual ban change -> automation cancels

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

### Phase A — Architecture and specification

- lock product behavior and boundaries
- identify current LCU/event integration points
- define state machine and configuration model
- identify legacy RoseAA behavior that must not be copied blindly

### Phase B — LCU primitives

- generic POST support
- matchmaking module
- ready-check module
- champion-select automation module
- unit/synthetic tests for request behavior

### Phase C — Auto Accept

- event routing
- delayed revalidation
- idempotency
- settings plumbing

### Phase D — Auto Queue and Auto Requeue

- queue eligibility
- lobby authority checks
- retry suppression
- post-game transition handling

### Phase E — Auto Pick

- active local action detection
- ordered fallback selection
- manual override detection

### Phase F — Auto Ban

- ordered fallback selection
- ally-intent protection
- manual override detection

### Phase G — UI and persistence

- one Client Automation feature area
- master toggle
- child settings
- champion priority editors
- activity/status display

### Phase H — Integration hardening

- concurrency guards
- reconnect recovery
- diagnostics/logging
- failure-state handling

### Phase I — QA and release candidate

- synthetic test suite
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

## Phase A exit criteria

Phase A is complete when:

1. this specification is reviewed and accepted
2. exact current settings persistence/UI integration points are identified
3. exact current WebSocket routing changes are identified
4. legacy RoseAA is classified as reference-only or explicitly removed/deactivated in a later implementation phase
5. no stable release files have changed
6. implementation can begin with Phase B without reopening product behavior
