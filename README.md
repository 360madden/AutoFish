# AutoFish

AutoFish is now **explicitly scoped** to four things only:

1. a **Lua addon** that runs inside Rift,
2. a **Python helper/runtime automation layer** for local Rift-window control and prototype orchestration,
3. **shared contracts** between the addon and helper,
4. **versioned fishing profiles** for leveling-focused behavior.

The older .NET helper code remains in the repository as legacy/reference code until it is retired or migrated. New live helper work should be Python-first. The Lua addon remains the in-game Rift addon ecosystem layer.

## Product goal

The current target is a modular, reliable foundation for:

- efficient fishing leveling,
- automated fishing flow,
- profile-driven behavior,
- an in-game addon GUI,
- and a local Python helper that can safely drive bounded desktop automation against the same PC running Rift.

## Historical signal proof priority

Historical Rift fishing tools repeatedly used cursor-change detection, `/log`, pixel checks, audio cues, and fixed hotbar/bag assumptions. AutoFish treats those as **stale until proven current**.

Use `docs/live-validation/2026-05-25-historical-signal-live-proof-runbook.md` before promoting any historical signal into runtime behavior. The current proof tools are:

- `/autofish invproof before|after|diff` for native inventory/catch deltas, including raw slot-level add/remove/change diagnostics.
- `/autofish coords` for a direct addon-side player `coordX/coordY/coordZ` readout from `Inspect.Unit.Detail`, useful as a ChromaLink/facing cross-check.
- `python tools/autofish-helper-py/autofish_helper.py target-snapshot` for no-input PID/HWND/client-size/foreground/readability validation before creating or reusing plans.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof reticle` for cursor/reticle/pixel crops.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast` for one bounded Python-native cast/click/wait/pull proof at a calibrated fishable point.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session` for a supervised bounded multi-cast proof after one-cast evidence is reviewed.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan` for dry-run screen-space candidate probe planning without input.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof chromalink` for read-only ChromaLink world-state/player-coordinate freshness proof.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof coordinate-crosscheck` for read-only comparison of manual `/autofish coords` output against fresh ChromaLink `player.position`.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof facing-delta` for guarded operational facing estimation from fresh coordinates plus one tiny confirmed movement pulse.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof facing-from-coords` for no-input operational facing math from two manually captured `/autofish coords` lines when ChromaLink is not fresh.
- `python tools/autofish-helper-py/autofish_helper.py session-plan gates|explain|preflight|checklist|runbook` for no-input readiness checks, blocked-gate explanations, fail-closed readable preflights, ordered operator checklists, and scoped next commands from a current session plan.
- `python tools/autofish-helper-py/autofish_helper.py doctor` for one read-only operator health bundle combining proof-root health and session-plan health when a plan exists.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof slash` for bounded `/autofish` command output screenshots.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof log` for read-only current log checks.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof layout` for fixed hotbar/bag region proof.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof audio` for bounded audio cue experiments.
- `python tools/autofish-helper-py/autofish_helper.py signal-proof summarize` and `decide` to review and record `promote`, `fallback-only`, `retire`, or `needs-more-evidence` decisions.

Do not copy, execute, or port public bot scripts/binaries. Use old methods only as clues, then classify them from current local evidence.

Larger Rift windows are supported and preferred for proof capture. The helper and preflight capture record the live client width/height and warn when the client is below `960x540`, because tiny `640x360` screenshots are often too hard to read. Coordinates remain client-relative; after resizing the game window, recalibrate the fishable client X/Y before sending input.

Focus must preserve the current Rift window size. AutoFish's live-input Python helper commands refuse to restore minimized windows; restore/maximize Rift manually first. The preflight script only restores minimized windows and should not de-maximize or shrink a normal/maximized Rift window before proof capture.

Current reviewed proof result: `docs/live-validation/2026-05-25-historical-signal-proof-results.md`.

Fishability probing plan: `docs/development/fishability-probe-plan.md`. This is the preferred direction over visual water detection: probe candidate points and classify them from game feedback. Coordinate-backed micro-step facing requires a reliable player coordinate source. Use `/autofish coords` as the direct addon-side cross-check and ChromaLink as the read-only helper-side telemetry bridge when fresh.

ChromaLink coordinate provider plan: `docs/development/chromalink-readonly-coordinate-provider.md`. AutoFish may consume ChromaLink as a read-only provider through its published local HTTP bridge, but must not modify ChromaLink from this repo. ChromaLink coordinates require fresh `/health` and fresh `player.position` world-state proof before use.

Facing calibration plan: `docs/development/facing-delta-calibration.md`. This estimates an operational player-facing vector from fresh before/after coordinates and one tiny explicitly confirmed forward movement pulse. It is not native actor facing/yaw.

## Live-development workflow

Use `docs/prototype-first-workflow.md` for live work. It is the active rule set for getting to a working prototype: calibrated fishable coordinate, exact PID/HWND, bounded casts, simple timing, then hardening. Do not block the prototype on perfect native `near_water` proof or broad bridge architecture.

## Repository layout

- `lua/AutoFish` - Lua addon core, GUI model, and bridge queue abstraction.
- `tools/autofish-helper-py` - planned Python helper/runtime automation layer for exact-window control, screenshots, cursor/key input, and prototype orchestration.
- `src/AutoFish.App` - legacy .NET 10 WinForms helper app kept for reference until replaced or retired.
- `src/AutoFish.Contracts` - shared contract models and JSON serialization helpers.
- `contracts` - JSON schemas for commands, envelopes, status, observations, and fishing profiles.
- `profiles` - sample fishing profiles used by the helper.
- `docs/framework-plan.md` - scoped delivery plan for the addon + helper product.
- `docs/addon-probe-plan.md` - offline plan for the prepared in-game addon diagnostics shell.
- `docs/profile-authoring.md` - profile field guidance and validation rules.
- `docs/helper-operator-guide.md` - helper usage notes.
- `docs/addon-architecture.md` - addon module map.
- `docs/prototype-first-workflow.md` - live prototype-first workflow that prevents process drift.
- `docs/python-helper-pivot.md` - Python-first helper direction and migration rules.
- `scripts/run-local-checks.ps1` - one-command offline verification.

## Runtime responsibilities

### Lua addon

Owns:

- local fishing state and decisions,
- local safety/guardrails,
- in-game GUI state,
- outbound session snapshots,
- inbound operator commands when a bridge exists.

The addon should remain fail-safe even if the helper is unavailable.

### Python helper/runtime automation layer

Owns:

- exact Rift PID/HWND validation,
- screenshot capture and crop/diff work,
- cursor hover/move/click and keypress orchestration,
- bounded prototype commands such as hover, press `8`, left-click, and capture,
- one-cast proof commands that click a calibrated point, press the fishing key, wait, and perform a bounded pull/loot click,
- supervised bounded session proofs that repeat the proven one-cast sequence with an explicit cast cap and stop file,
- profile-driven timing defaults from versioned fishing profiles for Python one-cast/session proofs,
- local session plans under `.autofish-live` to carry current PID/HWND/fishable-point/profile defaults between dry-run and confirmed proof commands,
- future bite/pull/loot timing and visual detection.

The helper runs on the same local PC as the Rift game window. It supervises and automates bounded desktop interactions; it should not replace the addon's local safety logic.

### Legacy .NET 10 helper

`src/AutoFish.App` is legacy/reference until explicitly migrated or retired. Do not add new live-window automation there unless the Python helper cannot cover the requirement.

### Shared contracts and profiles

The bridge is still contract-first and transport-agnostic for now. The repository currently defines:

- `bridge-command.schema.json`
- `bridge-envelope.schema.json`
- `session-status.schema.json`
- `rift-observation.schema.json`
- `fishing-profile.schema.json`

## Offline validation you can run now

### Build the legacy helper and contracts

```powershell
dotnet build AutoFish.sln --configuration Release
```

### Validate fishing profiles

```powershell
.\scripts\validate-profiles.ps1
```

### Run all local checks

```powershell
.\scripts\run-local-checks.ps1
```

This now includes the Python helper smoke checks. If local `lua`/`luac` are not installed and the current change is intentionally non-Lua, use:

```powershell
.\scripts\run-local-checks.ps1 -SkipLuaChecks
```

### Run Python helper checks only

```powershell
.\scripts\run-python-helper-checks.ps1
```

### Launch the legacy helper GUI

```powershell
dotnet run --project src/AutoFish.App/AutoFish.App.csproj
```

### Syntax-check and smoke-test the Lua addon scaffold

```powershell
$env:LUA_PATH = '.\\lua\\?.lua;.\\lua\\?\\init.lua;.\\lua\\?\\?.lua;' + $env:LUA_PATH
luac -p lua/AutoFish/AutoFishAddon.lua
lua -e "package.path='lua/?.lua;lua/?/init.lua;lua/?/?.lua;' .. package.path; local Addon = require('AutoFish.AutoFishAddon'); local addon = Addon.new({}, {}); local decision = addon:onObservation({characterName='Tester', inGame=true, nearWater=true, inCombat=false, inventoryFull=false, baitAvailable=true, biteDetected=false, lootReady=false, lineCast=false, canCast=true}); print(decision)"
```

### Syntax-check the prepared live-addon entrypoint offline

```powershell
luac -p lua/AutoFish/Main.lua
```

## Current live status

Live addon diagnostics have started against a Rift client, but AutoFish is still fail-closed and must not run an unattended loop yet.

Confirmed live:

- `/autofish help`, `/autofish status`, `/autofish bags`, `/autofish inventory`, `/autofish invproof`, `/autofish pole`, `/autofish abilities`, `/autofish api`, `/autofish apicompact`, `/autofish apis`, `/autofish events`, `/autofish proof`, `/autofish observe`, and `/autofish trace`
- exact PID/HWND target preflight and capture via the Python helper/RiftReader helpers
- player, combat/secure, inventory/free-slot, pole, Track Fish, ability scan, and castbar signals
- read-only API/event table discovery for inventory, chat, cursor/interaction, and candidate progression namespaces
- low-confidence observation mapping when fishable-water/bait/cast state is unproven

Implemented offline, pending live reload/proof:

- `/autofish coords` direct coordinate probe prints player `coordX/coordY/coordZ` from `Inspect.Unit.Detail` for screenshot-friendly cross-checks against ChromaLink and facing-delta runs.
- `/autofish proof` compact screenshot-friendly state pack prints coordinates, combat/secure/castbar state, inventory slots, fishing candidates, observation flags, and focused cursor/tooltip/interaction API values for helper review.

Current blocker:

- key `8` is confirmed to arm/show the yellow fishing placement circle when the cursor is already over valid fishable water
- a left-click after the yellow circle appears starts the fishing pole animation and casts a visible line
- the bounded helper reticle proof captured cursor-handle transitions, but pixel/reticle color classification still needs cleaner non-chat-overlapped crops before promotion
- the first inventory proof attempt did not show item quantity or raw slot changes, so catch/loot success remains `needs-more-evidence`
- current-client `/log` proof is blocked until a known enabled Rift log path/config is found
- no native `Inspect.Cursor` or `Inspect.Interaction` API was found for fishable-hover detection, so cursor/fishable-point calibration remains helper/operator driven

Useful live scripts:

```powershell
.\scripts\run-live-preflight.ps1 -ExpectedProcessId <pid> -ExpectedWindowHandle <hwnd> -Focus -Capture

.\scripts\invoke-live-fishable-point-probe.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y> -DryRun

.\scripts\invoke-live-fishable-point-probe.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y>

.\scripts\start-live-fishing-prototype.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y> -MaxCasts 1 -DryRun
```

Next live gate: use the expanded API probes plus one visibly successful manual catch/loot cycle to decide whether native inventory/chat/progression signals can prove success. Until then, unattended loops remain out of scope.
