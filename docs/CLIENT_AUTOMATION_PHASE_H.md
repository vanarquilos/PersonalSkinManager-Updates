# Client Automation vNext — Phase H Integration Hardening

Status: automated hardening complete; live catalog/function remediation implemented; repeat live League-client QA pending
Branch: `codex/client-automation-vnext`
Stable release protected: `v1.0.1`

## Objective

Phase H hardens the Phase B-G Client Automation implementation before any release-candidate decision or live-user rollout.

Client Automation remains limited to League client workflow automation:

- Auto Queue
- Auto Accept
- Auto Requeue
- Auto Pick
- Auto Ban

It does not automate gameplay, interact with Vanguard, weaken anti-cheat behavior, automate AFK behavior, or perform in-game combat/movement actions.

## Main settings placement

Client Automation is the second visible PSM control-center section:

1. Runtime
2. Client Automation
3. Startup
4. Game
5. Content
6. Tools
7. About

## Authoritative Auto Accept path

The event-driven Python controller is the only authoritative Auto Accept implementation in vNext.

The inherited Rose/Jade `AA.js` addon is an inert compatibility shim. It no longer polls ready-check DOM state or posts to `/lol-matchmaking/v1/ready-check/accept`.

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

## Settings hot reload

Client Automation settings are stored only in `[ClientAutomation]`.

After persistence succeeds, the Pengu bridge invokes the shared Client Automation settings callback and reconciles the active League state. Normal users should not need to restart PSM when changing automation settings.

## Queue catalog — finalized function contract

Client Automation must not dump Riot's entire queue-definition collection into the user-facing selector.

Primary source:

`/lol-game-queues/v1/matchmaking-queues`

Compatibility fallback only:

`/lol-game-queues/v1/queues`

The normalizer:

- rejects hidden queues
- rejects disabled/platform-disabled queues
- rejects custom queue definitions
- derives player-facing names from Riot's live queue type/name/description metadata
- labels `Ranked Solo/Duo` and `Ranked Flex` explicitly
- keeps ordinary `ARAM` distinct from named variants such as `ARAM: Mayhem`
- preserves genuinely distinct live variants
- removes semantically identical duplicate definitions deterministically
- retains the numeric queue ID as an advanced fallback

This avoids the live-QA failure where historical/event/custom entries such as several different ARAM IDs or custom Classic definitions all appeared as if they were equivalent selectable queues.

## Champion catalog — finalized roster contract

Primary source:

`/lol-game-data/assets/v1/champion-summary.json`

Compatibility fallback:

`/lol-game-data/assets/v1/champions.json`

Patch 26.15+ may expose both the current modern League roster and League Classic roster in the same local summary. League Classic entries use a separate +60000 champion-ID namespace for confirmed same-name pairs.

PSM now classifies confirmed pairs and exposes the roster directly in the existing champion search metadata:

- `Modern League · <champion title>`
- `League Classic · <champion title>`

Modern entries sort before their Classic counterpart. Exact-name resolution therefore remains predictable while users can deliberately choose the League Classic entry when required.

Examples from live QA:

- modern Twitch `#29`
- League Classic Twitch `#60029`
- modern Leona `#89`
- League Classic Leona `#60089`

The cache normalizer preserves this classification without repeatedly prefixing display metadata.

## Catalog lifecycle

- live and cached availability are tracked independently
- last-known-good queue/champion metadata is cached locally
- cache is display/editing assistance only
- live League state remains authoritative for queue/pick/ban mutations
- reconnect triggers catalog refresh
- bounded retries cover endpoints not ready immediately after League connects
- manual Refresh Data remains available

## Search/control surface

Champion Pick/Ban priorities use custom searchable comboboxes with:

- case-insensitive prefix/word-prefix/substring search
- keyboard Up/Down/Enter/Escape navigation
- mouse selection
- portrait/name/roster-title/internal-ID metadata
- numeric champion ID fallback
- duplicate and max-10 validation

Queue selection uses the live filtered matchmaking catalog with keyboard/mouse search and numeric fallback.

## Phase H automated gates

CI must pass:

- Python compileall
- Client Automation plugin JavaScript syntax
- PSM UI-polish JavaScript syntax
- retired Rose/Jade AutoAccept shim syntax
- repository unit tests
- Client Automation hardening invariants
- current matchmaking queue-source invariants
- queue filtering/naming/deduplication tests
- modern/League Classic champion-pair tests
- public-source boundary validation

Automated verification does not replace live League-client endpoint/UI QA.

## Repeat live League-client QA required

### Catalog / UI

- Client Automation appears as section 02
- queue list contains only current usable automatic-matchmaking choices
- Ranked Solo/Duo and Ranked Flex are explicit
- ARAM and ARAM variants are distinguishable
- custom/historical duplicate queues are absent
- champion search visibly differentiates Modern League and League Classic when both exist
- exact-name search prefers the modern entry while both remain selectable
- selected priority rows preserve roster metadata
- reconnect refreshes catalogs without restarting PSM
- manual Refresh Data works without resetting saved settings

### Functional automation

- Auto Accept configured delay
- manual Accept wins
- manual Decline wins
- ready-check expiration cancels
- exactly one accept mutation
- Auto Queue in an eligible solo lobby
- configured live queue selection
- primary/secondary role preferences accepted/rejected fail-closed
- premade non-leader authority
- penalty/restriction handling
- manual queue cancellation suppression
- Auto Requeue only after a completed game
- Auto Pick ordered fallback and manual override
- Auto Ban ordered fallback and manual override
- ally-intent protection including an intent appearing during delay
- disconnect/reconnect with pending work leaves no stale action

## Release gate

Do not modify yet:

- application version
- `v1.0.1` tag
- existing installer asset
- `stable/manifest.json`
- updater signing state
- production website release target

Phase H closes only after repeat live League QA passes. A later explicit Phase I release-candidate gate decides semantic version, packaging, signing, final regression, merge, tag/release, and stable-channel publication.
