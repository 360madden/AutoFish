# AutoFish Framework Plan

## Live workflow override

For live-client work, `docs/prototype-first-workflow.md` is the active workflow. It intentionally favors a simple bounded working prototype over broad framework completion. Do not use this framework plan to block calibrated-coordinate casting, one-cast timing, or short capped prototype runs.

## Scope freeze

AutoFish is currently scoped to:

1. a **Lua addon** for fishing automation and in-game status/control,
2. a **Python helper/runtime automation layer** for local Rift-window control and prototype orchestration,
3. **shared contracts** for command and session data,
4. **fishing profiles** for leveling-focused behavior.

The older .NET helper is legacy/reference until it is explicitly migrated or retired. New live helper behavior should be Python-first. No additional helper runtimes should be added unless they replace a Python gap with a documented reason.

## Objective

Build a modular, reliable fishing-focused system where:

- the **Lua addon** owns local decisions and safety,
- the **Python helper** owns same-PC Rift-window automation, screenshots, and prototype orchestration,
- and both sides evolve through stable contracts.

## Design constraints

- The addon must remain fail-safe if the helper is absent.
- The Python helper must require exact PID/HWND validation before live input.
- The Python helper must support dry-run flows before any real click/key sequence.
- Contracts must be stable and explicit before any real bridge transport is chosen.
- Bridge contract versioning rules are documented in `docs/bridge-contract-versioning.md` and must be followed before live transport work starts.
- Profiles must be data-driven so leveling behavior can scale without rewriting the core.
- The repository must stay Git/GitHub-ready and easy to maintain.

## Product modules

### Lua addon (`lua/AutoFish`)

Owns:

- fishing state machine,
- guardrails,
- GUI view model,
- command intake,
- session snapshot production.

### Python helper (`tools/autofish-helper-py`)

Owns:

- exact process/window validation,
- foreground/focus checks,
- screenshots, crops, and visual-diff artifacts,
- cursor hover/move/click and keypress orchestration,
- bounded prototype commands,
- future bite/pull/loot timing and visual detection.

### Legacy .NET helper (`src/AutoFish.App`)

Owns for now:

- legacy profile catalog loading,
- legacy session dashboard and logs,
- reference supervisory command patterns.

Do not add new live-window automation here unless Python cannot cover the requirement and the exception is documented.

### Shared contracts (`src/AutoFish.Contracts`, `contracts`)

Owns:

- command payload definitions,
- bridge envelope definitions,
- session status payload definitions,
- profile definitions,
- serialization rules for the helper side.

### Profiles (`profiles`)

Own:

- route/pacing/threshold presets,
- bait and maintenance preferences,
- guardrail settings for leveling-oriented fishing sessions.

## Offline-complete work

The following can be completed without the live client:

- final repo structure,
- Python helper scaffold and dry-run checks,
- legacy helper build and GUI scaffold,
- profile catalog and profile samples,
- contract models and serializers,
- Lua addon architecture,
- Lua state/guardrail logic,
- prepared live-addon manifest, slash-command shell, and deployment docs/scripts,
- documentation and GitHub workflow setup.
- local validation scripts and release/support docs.

## Live-only work

The following still require the live client:

- verifying the prepared addon probe commands against real item/bag/buff data,
- real Rift UI binding,
- real observation mapping,
- real transport implementation,
- real timing calibration and recovery tuning.

## Delivery phases

### Phase 1 - Scope-frozen foundation

Current repository target:

- Lua addon structure,
- Python helper structure,
- legacy .NET helper structure,
- shared contracts,
- sample profiles,
- docs and repo hygiene.

### Phase 2 - Addon logic hardening

Next:

- finish modular guardrail/config/profile application inside Lua,
- finish snapshot builders, bridge envelopes, and GUI projection,
- keep the live-addon diagnostics shell documented and ready without treating it as live-verified,
- add stronger Lua-side smoke coverage.

### Phase 3 - Python helper pivot

Next:

- add the Python helper scaffold,
- implement exact PID/HWND validation,
- implement screenshot capture,
- implement cursor hover without clicking,
- implement the confirmed cast-start sequence: hover valid water, press `8`, left-click,
- keep the .NET helper frozen as legacy/reference.

### Phase 4 - Live integration

Next:

- bind real Rift addon APIs,
- enforce the documented bridge contract versioning policy,
- bind the actual helper bridge transport only after the Python prototype proves the live mechanic,
- verify helper/addon sync and reconnect behavior.

### Phase 5 - Release hardening

Next:

- final packaging,
- install/setup docs,
- long-session validation,
- GitHub release workflow.

## Definition of offline completion

Offline completion for this scope means:

- the repo contains only the Lua addon, Python helper, legacy helper, contracts, and profiles,
- the Python helper can dry-run exact-window and cast-start flows,
- the legacy helper still builds until removed,
- the Lua addon passes syntax and smoke checks,
- profiles load correctly,
- and the remaining work is genuinely live-client integration, not architecture cleanup.
