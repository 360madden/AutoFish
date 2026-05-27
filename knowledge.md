# AutoFish — Project Knowledge

## What this project is

AutoFish is a split-stack Rift fishing automation tool with four layers:

1. **Lua addon** (`lua/AutoFish/`) — in-game Rift addon for state, guardrails, GUI, and slash commands.
2. **Python helper** (`tools/autofish-helper-py/`) — same-PC desktop automation: exact PID/HWND validation, screenshot capture, cursor/key input, bounded cast proofs. **This is the active live-work layer.**
3. **Shared contracts** (`src/AutoFish.Contracts/`, `contracts/`) — JSON schemas and C# models for bridge messages, profiles, and proof manifests.
4. **Legacy .NET app** (`src/AutoFish.App/`) — WinForms GUI; kept for reference. Do not add new live-window automation here.

The Python helper is the **primary active development surface**. The Lua addon is the in-game layer. The .NET app is frozen legacy.

## Key files and what they do

| Path | Role |
|---|---|
| `tools/autofish-helper-py/autofish_helper.py` | **Monolithic Python helper** — all proof commands, session plans, gates, doctor, reticle, casts, fan planning, etc. (~9000+ lines) |
| `lua/AutoFish/Main.lua` | Lua addon entrypoint; slash command routing |
| `lua/AutoFish/AutoFishAddon.lua` | Core addon logic, observation, decision rules |
| `lua/AutoFish/Bridge/` | Lua-side bridge queue, command normalizer, contracts |
| `lua/AutoFish/Core/` | State machine, guardrails, observation, session state, profile runtime |
| `lua/AutoFish/UI/` | Addon GUI (Controller, Layout, ViewModel) |
| `src/AutoFish.Contracts/Models/` | C# contract models (BridgeCommand, SessionStatus, etc.) |
| `contracts/` | JSON Schemas for bridge messages and profiles |
| `profiles/` | Versioned fishing profiles (shoreline-grind.json, starter-pond.json, etc.) |
| `scripts/run-local-checks.ps1` | One-command offline validation (build + profiles + Python + Lua) |
| `scripts/run-python-helper-checks.ps1` | Python-only checks (compile, smoke, doc validation, help surfaces) |
| `scripts/run-live-preflight.ps1` | Live target discovery + focus + capture via RiftReader |
| `scripts/deploy-addon.ps1` | Copy Lua addon to Rift addons directory |
| `docs/handoffs/` | Sequential handoff artifacts for live proof-pack runs |
| `.autofish-live/` | **Git-ignored** live evidence directory (target discovery, snapshots, proof manifests, session plans) |

## Commands

### Offline validation (run before PRs)
```powershell
.\scripts\run-local-checks.ps1                     # Full: .NET build + profiles + Python + Lua
.\scripts\run-local-checks.ps1 -SkipLuaChecks      # Skip Lua if luac/lua not installed
.\scripts\run-python-helper-checks.ps1              # Python only: compile, smoke, doc validation, help surfaces
```

### .NET build (legacy)
```powershell
dotnet build AutoFish.sln --configuration Release
dotnet run --project src/AutoFish.App/AutoFish.App.csproj
```

### Profile validation
```powershell
.\scripts\validate-profiles.ps1
```

### Lua syntax/smoke (requires `luac` and `lua` on PATH)
```powershell
luac -p lua/AutoFish/AutoFishAddon.lua
lua scripts/lua-smoke-tests.lua
```

### Live proof commands (Python helper — all require exact PID/HWND)

**Target validation (no input sent):**
```powershell
python tools\autofish-helper-py\autofish_helper.py target-snapshot --pid <PID> --hwnd <HWND> --require-readable
```

**Session plan management:**
```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan create --pid <PID> --hwnd <HWND> --x <X> --y <Y> --profile starter-pond --validate-target --output .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan gates --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan explain --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan preflight --path .autofish-live\session-plan-latest.json --require ready-one-cast
python tools\autofish-helper-py\autofish_helper.py session-plan checklist --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan runbook --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan doctor --path .autofish-live\session-plan-latest.json --proof-root .autofish-live --decision-register .autofish-live\signal-proof-decisions.json
python tools\autofish-helper-py\autofish_helper.py session-plan stop-file create --path .autofish-live\session-plan-latest.json   # Emergency stop
python tools\autofish-helper-py\autofish_helper.py session-plan stop-file clear --path .autofish-live\session-plan-latest.json    # Resume
```

**Proof commands (dry-run first, then --confirm-input):**
```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle --session-plan ... --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast --session-plan ... --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof bounded-session --session-plan ... --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof slash --pid <PID> --hwnd <HWND> --default-proof-pack --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan --pid <PID> --hwnd <HWND> --origin-x <X> --origin-y <Y> --forward-x <FX> --forward-y <FY> --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink --require-fresh
python tools\autofish-helper-py\autofish_helper.py signal-proof coordinate-crosscheck --addon-line "coords x=<x> y=<y> z=<z>"
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta --pid <PID> --hwnd <HWND> --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-from-coords --before-line "..." --after-line "..."
```

**Review and decide:**
```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof summarize --proof-root .autofish-live
python tools\autofish-helper-py\autofish_helper.py signal-proof decide --signal oneCast --decision fallback-only --reason "..." --evidence <manifest> --session-plan <plan>
python tools\autofish-helper-py\autofish_helper.py doctor --proof-root .autofish-live --decision-register .autofish-live\signal-proof-decisions.json
```

## Critical conventions and gotchas

### Safety first
- **Always dry-run before confirm-input.** Every proof command requires `--dry-run` first, then `--confirm-input` only while supervised.
- **Exact PID/HWND always.** No command sends game input without explicit, validated PID and HWND.
- **Stop file:** Default is `.autofish-live/STOP.txt`. If it exists, bounded-session and one-cast abort before the next action.
- **No unattended loops.** The helper supports supervised bounded sessions only.
- **No `-` key:** The `-` dash key is bound to `reloadui` on this setup and is blocked by default in slash commands.
- **Minimized windows refused.** Live-input commands refuse to restore minimized Rift windows (Windows would snap to a tiny restored size). Restore/maximize Rift manually first.
- **No ChromaLink modification.** ChromaLink is consumed read-only via `http://127.0.0.1:7337`. Do not modify ChromaLink from this repo.

### Window size and coordinates
- **Preferred minimum:** `960×540` client area for readable proof screenshots. Below that, manifests warn.
- **Client-relative coordinates.** Recalibrate fishable X/Y after any window resize.
- **Focus preserves size.** The preflight script only calls `SW_RESTORE` on minimized windows; it must not de-maximize or shrink a normal/maximized window.
- **Python helper is Windows-only** (`os.name == "nt"` guard at module level).

### Code organization
- **Monolithic Python helper:** `autofish_helper.py` is a single ~9000+ line file. All commands live in one module. Use internal helper functions, don't add new top-level modules without discussion.
- **Lua addon is modular:** `lua/AutoFish/` is split into `Bridge/`, `Core/`, `UI/` subdirectories with clear responsibilities.
- **Session plans are JSON artifacts** (schema `autofish.sessionPlan.v1`) stored in `.autofish-live/`. They carry PID/HWND, fishable point, profile defaults, target validation, review scope, and source provenance (fan candidate, facing evidence). Do not reuse after Rift restart/resize.
- **Decision register:** `.autofish-live/signal-proof-decisions.json` — scoped signal decisions (`promote`, `fallback-only`, `retire`, `needs-more-evidence`) keyed by review scope token.

### Proof manifests
- All proof commands write a `manifest.json` with schema identifier (e.g. `autofish.signalProof.reticle.v1`).
- Manifests include target info, gates passed/blocked, safety flags, and captured evidence paths.
- Summaries and doctor commands aggregate manifests from a proof root directory.

### Shell requirements
- **PowerShell 7+ (`pwsh`)** required for live scripts. Windows PowerShell 5.1 lacks `ConvertFrom-Json -Depth`.
- Python 3.x required. No external pip packages needed (stdlib only: `ctypes`, `argparse`, `json`, `struct`, `hashlib`, `wave`, `urllib`, etc.).
- `luac` and `lua` required for Lua checks; skip with `-SkipLuaChecks` if working on Python-only changes.

### Historical signals are stale until proven
The project treats all historical Rift fishing methods (cursor-change, `/log`, pixel checks, audio, fixed hotbar/bag) as **stale** until locally proven with current evidence. See `docs/live-validation/2026-05-25-historical-signal-live-proof-runbook.md`.

### Live workflow
Follow `docs/prototype-first-workflow.md`: calibrate fishable coordinate → exact PID/HWND → bounded casts → simple timing → then harden. Don't block on perfect native water detection or broad bridge architecture.

### Profile-driven defaults
Fishing profiles (in `profiles/`) provide `pacing.biteTimeoutMs` → `--cast-wait-seconds` and `pacing.lootTimeoutMs` → `--post-pull-delay-ms`. Use `--profile <id>` to load defaults; CLI overrides take precedence.
