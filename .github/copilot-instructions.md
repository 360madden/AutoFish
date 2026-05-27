# AutoFish — GitHub Copilot Instructions

This project is a Rift fishing automation tool. Read `AGENTS.md` for the full agent instruction set. For detailed commands, file maps, and deeper gotchas, see `knowledge.md`.

## Critical Safety Rules
1. **Never call `--confirm-input` without explicit user approval.** The Python helper sends real keyboard/mouse input to a live game.
2. **Always dry-run first** for any command that sends input.
3. **Exact PID and HWND** required for every live command.

## Architecture
- **Active dev surface:** `tools/autofish-helper-py/autofish_helper.py` — monolithic Python helper (~9k lines). Stdlib only, Windows-only.
- **In-game layer:** `lua/AutoFish/` — modular Lua addon (Bridge/, Core/, UI/).
- **Frozen legacy:** `src/AutoFish.App/` — do not add live automation here.
- **Contracts:** `contracts/` (JSON schemas) ↔ `src/AutoFish.Contracts/` (C# models). Must stay in sync.

## Key Constraints
- Python: stdlib only, no pip packages, Windows-only.
- PowerShell 7+ required for live scripts.
- No `-` (dash) key as input (bound to `reloadui`).
- Minimum readable window: 960×540 client area.
- Session plans expire after 240 minutes.

## Validation
```powershell
.\scripts\run-local-checks.ps1 -SkipLuaChecks     # Python-only changes
.\scripts\run-python-helper-checks.ps1              # Quick Python checks
.\scripts\validate-profiles.ps1                     # Profile validation
```
