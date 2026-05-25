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

- `/autofish help`, `/autofish status`, `/autofish bags`, `/autofish inventory`, `/autofish pole`, `/autofish abilities`, `/autofish api`, `/autofish observe`, and `/autofish trace`
- exact PID/HWND target preflight and capture via RiftReader helpers
- player, combat/secure, inventory/free-slot, pole, Track Fish, ability scan, and castbar signals
- low-confidence observation mapping when fishable-water/bait/cast state is unproven

Current blocker:

- key `8` is now confirmed to arm/show the yellow fishing placement circle when the cursor is already over valid fishable water
- a left-click after the yellow circle appears starts the fishing pole animation and casts a visible line
- the next live gate is reproducing this `hover valid water -> press 8 -> left-click` sequence from the Python helper, then measuring bite/pull/loot timing
- no native `Inspect.Cursor` or `Inspect.Interaction` API was found for fishable-hover detection, so cursor/fishable-point calibration remains helper/operator driven

Useful live scripts:

```powershell
.\scripts\run-live-preflight.ps1 -ExpectedProcessId <pid> -ExpectedWindowHandle <hwnd> -Focus -Capture

.\scripts\invoke-live-fishable-point-probe.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y> -DryRun

.\scripts\invoke-live-fishable-point-probe.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y>

.\scripts\start-live-fishing-prototype.ps1 -TargetProcessId <pid> -TargetWindowHandle <hwnd> -ClientX <x> -ClientY <y> -MaxCasts 1 -DryRun
```

Next live gate: implement a Python helper dry-run and one-cast-start command for the confirmed mechanic, capture a scripted successful cast-start trace, then advance to bite/pull timing. Until then, unattended loops remain out of scope.
