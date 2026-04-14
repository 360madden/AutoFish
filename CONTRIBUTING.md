# Contributing to AutoFish

## Current project shape

AutoFish is a split-stack project:

- `lua/AutoFish` for the in-game Lua core and GUI model.
- `src/AutoFish.App` for the external .NET 10 desktop GUI.
- `src/AutoFish.Contracts` for shared desktop-side contract models.
- `contracts` for transport-neutral JSON schemas.
- `profiles` for fishing behavior presets.

## Before opening a PR

Run the offline checks that are currently expected to pass:

```powershell
.\scripts\run-local-checks.ps1
```

## Contribution guidelines

- Keep Lua, .NET, and schema changes aligned when bridge payloads change.
- Keep profiles and helper-side profile loading aligned when profile fields change.
- Prefer shared contracts over ad-hoc field names.
- Keep the Lua side fail-safe if the desktop app is unavailable.
- Keep the desktop app supervisory, not authoritative over local safety.
- Document any new bridge or UI assumptions before implementing them.
