# AutoFish

AutoFish is now **explicitly scoped** to four things only:

1. a **Lua addon** that runs inside Rift,
2. a **.NET 10 helper app** for operator control and session supervision,
3. **shared contracts** between the addon and helper,
4. **versioned fishing profiles** for leveling-focused behavior.

Everything else has been treated as out of scope for now.

## Product goal

The current target is a modular, reliable foundation for:

- efficient fishing leveling,
- automated fishing flow,
- profile-driven behavior,
- an in-game addon GUI,
- and a desktop helper GUI.

## Repository layout

- `lua/AutoFish` - Lua addon core, GUI model, and bridge queue abstraction.
- `src/AutoFish.App` - .NET 10 WinForms helper app.
- `src/AutoFish.Contracts` - shared contract models and JSON serialization helpers.
- `contracts` - JSON schemas for commands, envelopes, status, observations, and fishing profiles.
- `profiles` - sample fishing profiles used by the helper.
- `docs/framework-plan.md` - scoped delivery plan for the addon + helper product.
- `docs/profile-authoring.md` - profile field guidance and validation rules.
- `docs/helper-operator-guide.md` - helper usage notes.
- `docs/addon-architecture.md` - addon module map.
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

### .NET 10 helper

Owns:

- profile loading and operator profile selection,
- session dashboard and logs,
- supervisory commands,
- future profile editing and tooling.

The helper supervises the addon; it should not replace the addon's local safety logic.

### Shared contracts and profiles

The bridge is still contract-first and transport-agnostic for now. The repository currently defines:

- `bridge-command.schema.json`
- `bridge-envelope.schema.json`
- `session-status.schema.json`
- `rift-observation.schema.json`
- `fishing-profile.schema.json`

## Offline validation you can run now

### Build the helper and contracts

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

### Launch the helper GUI

```powershell
dotnet run --project src/AutoFish.App/AutoFish.App.csproj
```

### Syntax-check and smoke-test the Lua addon scaffold

```powershell
$env:LUA_PATH = '.\\lua\\?.lua;.\\lua\\?\\init.lua;.\\lua\\?\\?.lua;' + $env:LUA_PATH
luac -p lua/AutoFish/AutoFishAddon.lua
lua -e "package.path='lua/?.lua;lua/?/init.lua;lua/?/?.lua;' .. package.path; local Addon = require('AutoFish.AutoFishAddon'); local addon = Addon.new({}, {}); local decision = addon:onObservation({characterName='Tester', inGame=true, nearWater=true, inCombat=false, inventoryFull=false, baitAvailable=true, biteDetected=false, lootReady=false, lineCast=false, canCast=true}); print(decision)"
```

## Current limitation

The live Rift-specific addon binding and the real addon-to-helper transport are still the final integration phase. The codebase is intentionally scoped so those live pieces can be added later without reshaping the project.
