# AutoFish Framework Plan

## Scope freeze

AutoFish is currently scoped to:

1. a **Lua addon** for fishing automation and in-game status/control,
2. a **.NET 10 helper** for profiles, supervision, and operator controls,
3. **shared contracts** for command and session data,
4. **fishing profiles** for leveling-focused behavior.

No extra runtimes or prototype stacks are part of the product scope now.

## Objective

Build a modular, reliable fishing-focused system where:

- the **Lua addon** owns local decisions and safety,
- the **.NET helper** owns operator supervision and profile management,
- and both sides evolve through stable contracts.

## Design constraints

- The addon must remain fail-safe if the helper is absent.
- The helper must remain useful offline with mock data and profile loading.
- Contracts must be stable and explicit before any real bridge transport is chosen.
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

### .NET helper (`src/AutoFish.App`)

Owns:

- operator GUI,
- profile catalog loading,
- session dashboard,
- logs and supervisory commands.

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
- helper build and GUI scaffold,
- profile catalog and profile samples,
- contract models and serializers,
- Lua addon architecture,
- Lua state/guardrail logic,
- documentation and GitHub workflow setup.
- local validation scripts and release/support docs.

## Live-only work

The following still require the live client:

- real Rift UI binding,
- real observation mapping,
- real transport implementation,
- real timing calibration and recovery tuning.

## Delivery phases

### Phase 1 - Scope-frozen foundation

Current repository target:

- Lua addon structure,
- .NET helper structure,
- shared contracts,
- sample profiles,
- docs and repo hygiene.

### Phase 2 - Addon logic hardening

Next:

- finish modular guardrail/config/profile application inside Lua,
- finish snapshot builders, bridge envelopes, and GUI projection,
- add stronger Lua-side smoke coverage.

### Phase 3 - Helper hardening

Next:

- improve profile presentation,
- persist helper preferences,
- add helper-side profile validation and richer logs.

### Phase 4 - Live integration

Next:

- bind real Rift addon APIs,
- bind the actual helper bridge transport,
- verify helper/addon sync and reconnect behavior.

### Phase 5 - Release hardening

Next:

- final packaging,
- install/setup docs,
- long-session validation,
- GitHub release workflow.

## Definition of offline completion

Offline completion for this scope means:

- the repo contains only the Lua addon, helper, contracts, and profiles,
- the helper builds and runs,
- the Lua addon passes syntax and smoke checks,
- profiles load correctly,
- and the remaining work is genuinely live-client integration, not architecture cleanup.
