# CLAUDE.md — AutoFish Agent Instructions

## Project Identity

AutoFish is a **Rift fishing automation tool** with four layers:
1. **Lua addon** (`lua/AutoFish/`) — in-game Rift addon: state machine, guardrails, GUI, slash commands
2. **Python helper** (`tools/autofish-helper-py/`) — same-PC desktop automation: PID/HWND validation, screenshots, cursor/key input, bounded cast proofs. **Active development surface.**
3. **Shared contracts** (`src/AutoFish.Contracts/`, `contracts/`) — JSON schemas and C# models
4. **Legacy .NET app** (`src/AutoFish.App/`) — frozen WinForms GUI, reference only

**Python helper is primary.** The Lua addon is the in-game layer. The .NET app is frozen legacy.

## CRITICAL: This project sends real keyboard/mouse input to a running game

Every command that can send input requires `--dry-run` first, then `--confirm-input` only while supervised. You must never skip this pattern. Read `docs/prototype-first-workflow.md` before working on any live-input code.

## Commands

### Offline validation (run before PRs, after any code change)
```powershell
.\scripts\run-local-checks.ps1                     # Full: .NET build + profiles + Python + Lua
.\scripts\run-local-checks.ps1 -SkipLuaChecks      # Skip Lua if luac/lua not installed
.\scripts\run-python-helper-checks.ps1              # Python only: compile, smoke, doc validation, help surfaces
```

### Python helper (all proof commands)
```powershell
# Target validation (no input)
python tools\autofish-helper-py\autofish_helper.py target-snapshot --pid <PID> --hwnd <HWND> --require-readable

# Session plans
python tools\autofish-helper-py\autofish_helper.py session-plan create --pid <PID> --hwnd <HWND> --x <X> --y <Y> --profile starter-pond --validate-target --output .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan gates --path <plan> --require ready-one-cast
python tools\autofish-helper-py\autofish_helper.py session-plan explain --path <plan>
python tools\autofish-helper-py\autofish_helper.py session-plan preflight --path <plan> --require ready-one-cast
python tools\autofish-helper-py\autofish_helper.py session-plan checklist --path <plan>

# Proof commands (always dry-run first)
python tools\autofish-helper-py\autofish_helper.py signal-proof <reticle|one-cast|bounded-session|slash|fishability-fan|chromalink|facing-delta|facing-from-coords> --dry-run ... 
# Then: --confirm-input ...

# Review
python tools\autofish-helper-py\autofish_helper.py signal-proof summarize --proof-root .autofish-live
python tools\autofish-helper-py\autofish_helper.py signal-proof decide --signal <sig> --decision <d> --reason "..." --evidence <manifest> --session-plan <plan>
python tools\autofish-helper-py\autofish_helper.py doctor --proof-root .autofish-live --decision-register .autofish-live\signal-proof-decisions.json
```

## Hard Constraints — Never Violate These

1. **No unattended loops.** The helper supports supervised bounded sessions only. Max casts are always capped.
2. **No `-` key as input.** The dash key is bound to `reloadui` on this setup. Never use it in slash commands or scripted input.
3. **Exact PID/HWND always.** No input without validated, exact PID and HWND.
4. **Dry-run before confirm-input.** Every command that sends input (reticle, one-cast, bounded-session, slash, facing-delta with --confirm-movement) requires dry-run first. Read-only commands (target-snapshot, session-plan gates, doctor, summarize, chromalink, etc.) don't need dry-run.
5. **Minimized windows refused.** Live-input refuses to restore minimized Rift (Windows snaps to tiny restored size). Operator must restore/maximize manually.
6. **No ChromaLink modification.** Consumed read-only via `http://127.0.0.1:7337`. Do not modify ChromaLink from this repo.
7. **PowerShell 7 (`pwsh`) required** for live scripts. Windows PowerShell 5.1 lacks `ConvertFrom-Json -Depth`.
8. **Client-relative coordinates only.** Recalibrate X/Y after any window resize. Preferred minimum: 960×540.
9. **Stop file respected.** Default: `.autofish-live/STOP.txt`. If it exists, bounded-session and one-cast abort before the next action.
10. **No movement in fishing casts.** Helper sends cursor + key + click only.
11. **Session plans expire.** Default max age is 240 minutes. Stale plans fail the `planFresh` gate. Recreate after Rift restart, resize, or coordinate change.

## Architecture Rules

- **Python helper is monolithic.** `autofish_helper.py` is a single ~9000+ line file. Do not split it or add new top-level modules without explicit discussion.
- **Lua addon is modular.** `lua/AutoFish/` splits into `Bridge/`, `Core/`, `UI/` with clear responsibilities.
- **Session plans are JSON artifacts** (schema `autofish.sessionPlan.v1`) stored in `.autofish-live/`. Do not reuse after Rift restart, resize, or coordinate change. Max plan age: 240 minutes.
- **Proof manifests** all write `manifest.json` with schema identifiers. Manifests record target info, gate status, safety flags, and evidence paths.
- **Decision register:** `.autofish-live/signal-proof-decisions.json` — scoped decisions keyed by review scope token.
- **Profiles drive timing.** `pacing.biteTimeoutMs` → `--cast-wait-seconds`, `pacing.lootTimeoutMs` → `--post-pull-delay-ms`. CLI overrides take precedence.

## Code Conventions

- **Python:** stdlib only (no pip packages). Type hints preferred. Windows-only (`os.name == "nt"` guard). Use `argparse` for all CLI.
- **Lua:** Follow existing module patterns. Each file under `lua/AutoFish/` has a clear single responsibility. Keep the addon fail-safe if the helper is unavailable.
- **C#:** Frozen legacy. No new live-window automation here. Keep existing patterns if touching it.
- **Shell:** PowerShell 7 scripts only in `scripts/`. Use `$ErrorActionPreference = 'Stop'`. Bash is available but scripts target PowerShell.
- **Evidence:** All live evidence goes under `.autofish-live/` (git-ignored). Never commit live evidence files. Handoffs go in `docs/handoffs/`.
- **Documentation:** Keep it short. Handoffs are the primary communication format — they record exactly what ran, what blocked, and what's next.

## What NOT To Do

- Don't add new top-level modules to the Python helper
- Don't add new live-window automation to the .NET helper
- Don't run destructive git commands (push, force push) unless asked
- Don't install packages globally
- Don't use `as any` / unchecked type casts
- Don't commit `.autofish-live/` files
- Don't skip the dry-run phase for live-input commands
- Don't assume historical Rift fishing methods work — they're stale until locally proven
- Don't modify ChromaLink from this repo
- Don't split the monolithic Python helper without discussion

## Key Docs

| Doc | When to read |
|---|---|
| `docs/prototype-first-workflow.md` | Before any live-input code changes |
| `docs/python-helper-pivot.md` | Understanding the Python-first direction |
| `docs/framework-plan.md` | Overall architecture and delivery phases |
| `docs/handoffs/` | Most recent handoff for current live state |
| `docs/live-validation/` | Historical signal proof results |
| `README.md` | Full command reference and live status |
| `knowledge.md` | Condensed project knowledge for agents |

> **Sync note:** CLAUDE.md is the canonical agent instruction file. Keep in sync with `.cursor/rules` and `knowledge.md` when updating safety rules or constraints.
