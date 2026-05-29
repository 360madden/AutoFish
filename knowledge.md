# AutoFish — Project Knowledge

> **Agent note:** This is the detailed project reference. For agent instructions (safety rules, architecture, conventions), read `AGENTS.md` first. This file provides the full command reference, file map, and deeper gotchas.
>
> **Critical:** The Python helper sends real keyboard/mouse input to a live game — never call `--confirm-input` without explicit user approval.

## What this project is

AutoFish is a split-stack Rift fishing automation tool with five layers:

1. **Lua addon** (`lua/AutoFish/`) — in-game Rift addon for state, guardrails, GUI, and slash commands.
2. **Lua chat-copy addon** (`Main.lua` + `RiftAddon.toc` at repo root) — separate simpler addon ("AutoFishChatCopy") that captures future Rift chat events into a bounded buffer and presents copy-ready text in a selectable UI window. Uses `/afcopy` and `/chatcopy` slash commands. Current version 0.1.1 with auto-open-on-load.
3. **Python helper** (`tools/autofish-helper-py/`) — same-PC desktop automation: exact PID/HWND validation, screenshot capture, cursor/key input, bounded cast proofs. **This is the active live-work layer.**
4. **Shared contracts** (`src/AutoFish.Contracts/`, `contracts/`) — JSON schemas and C# models for bridge messages, profiles, and proof manifests.
5. **Legacy .NET app** (`src/AutoFish.App/`) — WinForms GUI; kept for reference. Do not add new live-window automation here.

The Python helper is the **primary active development surface**. The Lua addon is the in-game layer. The .NET app is frozen legacy.

> **Note:** `Main.lua` and `RiftAddon.toc` at the repo root belong to AutoFishChatCopy — a separate addon from `lua/AutoFish/`. Don't confuse the two. The `lua/AutoFish/` addon uses `/autofish`; the root addon uses `/afcopy`.

## Key files and what they do

| Path | Role |
|---|---|
| `tools/autofish-helper-py/autofish_helper.py` | **Monolithic Python helper** — all proof commands, session plans, gates, doctor, reticle, casts, fan planning, etc. (~9000+ lines) |
| `tools/autofish-helper-py/tests/smoke_autofish_helper.py` | Python smoke tests — imports and exercises the helper module programmatically |
| `tools/autofish-helper-py/tests/validate_doc_commands.py` | Validates that CLI commands documented in markdown match actual argparse surface |
| `tools/autofish-helper-py/tests/validate_lua_slash_commands.py` | Validates Lua slash command doc strings |
| `Main.lua` (root) | **AutoFishChatCopy** addon entrypoint — chat capture buffer with `/afcopy` slash commands |
| `RiftAddon.toc` (root) | AutoFishChatCopy addon manifest (Identifier `AutoFishChatCopy`, v0.1.1) |
| `lua/AutoFish/Main.lua` | Lua addon entrypoint; slash command routing |
| `lua/AutoFish/AutoFishAddon.lua` | Core addon logic, observation, decision rules |
| `lua/AutoFish/Bridge/` | Lua-side bridge queue, command normalizer, contracts |
| `lua/AutoFish/Core/` | State machine, guardrails, observation, session state, profile runtime |
| `lua/AutoFish/UI/` | Addon GUI (Controller, Layout, ViewModel) |
| `src/AutoFish.Contracts/Models/` | C# contract models (BridgeCommand, SessionStatus, etc.) |
| `contracts/` | JSON Schemas for bridge messages and profiles |
| `profiles/` | Versioned fishing profiles (shoreline-grind.json, starter-pond.json, etc.) |
| `scripts/run_local_checks.py` | One-command offline validation (build + profiles + Python + Lua) |
| `scripts/run_python_checks.py` | Python-only checks (compile, smoke, doc validation, help surfaces) |
| `scripts/deploy_addon.py` | Copy Lua addon to Rift addons directory |
| `scripts/lua-smoke-tests.lua` | Lua smoke tests for the addon |
| `tools/apply_*.py` / `tools/fix_*.py` | One-off fix scripts (clipboard, doctor, dry-run, inbound bridge) — historical, not for new development |
| `docs/handoffs/` | Sequential handoff artifacts for live proof-pack runs (latest = most recent timestamp) |
| `.autofish-live/` | **Git-ignored** live evidence directory (target discovery, snapshots, proof manifests, session plans) |
| `.cursor/rules/` | 12 `.mdc` rule files loaded per file type (contracts, docs, dotnet, general, github, handoffs, lua, profiles, python, safety, scripts, testing) |
| `.editorconfig` | Code style: UTF-8, CRLF, 4-space indent, trim trailing WS (except .md) |
| `global.json` | .NET SDK 10.0.300 with `latestFeature` rollForward |

## Commands

### Offline validation (run before PRs)
```bash
python scripts/run_local_checks.py                  # Full: .NET build + profiles + Python + Lua
python scripts/run_local_checks.py --skip-lua       # Skip Lua if luac/lua not installed
python scripts/run_python_checks.py                 # Python only: compile, smoke, doc validation, help surfaces
```

### .NET build (legacy)
```bash
dotnet build AutoFish.sln --configuration Release
dotnet run --project src/AutoFish.App/AutoFish.App.csproj
```

### Profile validation
```bash
python scripts/run_local_checks.py --skip-lua
```

### Lua syntax/smoke (requires `luac` and `lua` on PATH)
```bash
luac -p lua/AutoFish/AutoFishAddon.lua
lua scripts/lua-smoke-tests.lua
```

### Live proof commands (Python helper — all require exact PID/HWND)

**Target validation (no input sent):**
```bash
python tools/autofish-helper-py/autofish_helper.py target-snapshot --pid <PID> --hwnd <HWND> --require-readable
```

**Session plan management:**
```bash
python tools/autofish-helper-py/autofish_helper.py session-plan create --pid <PID> --hwnd <HWND> --x <X> --y <Y> --profile starter-pond --validate-target --output .autofish-live/session-plan-latest.json
python tools/autofish-helper-py/autofish_helper.py session-plan gates --path .autofish-live/session-plan-latest.json
python tools/autofish-helper-py/autofish_helper.py session-plan explain --path .autofish-live/session-plan-latest.json
python tools/autofish-helper-py/autofish_helper.py session-plan preflight --path .autofish-live/session-plan-latest.json --require ready-one-cast
python tools/autofish-helper-py/autofish_helper.py session-plan checklist --path .autofish-live/session-plan-latest.json
python tools/autofish-helper-py/autofish_helper.py session-plan runbook --path .autofish-live/session-plan-latest.json
python tools/autofish-helper-py/autofish_helper.py session-plan doctor --path .autofish-live/session-plan-latest.json --proof-root .autofish-live --decision-register .autofish-live/signal-proof-decisions.json
python tools/autofish-helper-py/autofish_helper.py session-plan stop-file create --path .autofish-live/session-plan-latest.json   # Emergency stop
python tools/autofish-helper-py/autofish_helper.py session-plan stop-file clear --path .autofish-live/session-plan-latest.json    # Resume
```

**Proof commands (dry-run first, then --confirm-input):**
```bash
python tools/autofish-helper-py/autofish_helper.py signal-proof reticle --session-plan ... --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof one-cast --session-plan ... --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof bounded-session --session-plan ... --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof slash --pid <PID> --hwnd <HWND> --default-proof-pack --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan --pid <PID> --hwnd <HWND> --origin-x <X> --origin-y <Y> --forward-x <FX> --forward-y <FY> --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof chromalink --require-fresh
python tools/autofish-helper-py/autofish_helper.py signal-proof coordinate-crosscheck --addon-line "coords x=<x> y=<y> z=<z>"
python tools/autofish-helper-py/autofish_helper.py signal-proof facing-delta --pid <PID> --hwnd <HWND> --dry-run
python tools/autofish-helper-py/autofish_helper.py signal-proof facing-from-coords --before-line "..." --after-line "..."
```

**Review and decide:**
```bash
python tools/autofish-helper-py/autofish_helper.py signal-proof summarize --proof-root .autofish-live
python tools/autofish-helper-py/autofish_helper.py signal-proof decide --signal oneCast --decision fallback-only --reason "..." --evidence <manifest> --session-plan <plan>
python tools/autofish-helper-py/autofish_helper.py doctor --proof-root .autofish-live --decision-register .autofish-live/signal-proof-decisions.json
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
- Python 3.x required. No external pip packages needed (stdlib only: `ctypes`, `argparse`, `json`, `struct`, `hashlib`, `wave`, `urllib`, etc.).
- `luac` and `lua` required for Lua checks; skip with `--skip-lua` if working on Python-only changes.

### Historical signals are stale until proven
The project treats all historical Rift fishing methods (cursor-change, `/log`, pixel checks, audio, fixed hotbar/bag) as **stale** until locally proven with current evidence. See `docs/live-validation/2026-05-25-historical-signal-live-proof-runbook.md`.

### Two separate Lua addons share the same repo
- **`lua/AutoFish/`** — the main fishing addon. Uses `/autofish` slash commands. Has `Bridge/`, `Core/`, `UI/` submodules.
- **`Main.lua` + `RiftAddon.toc` (root)** — AutoFishChatCopy, a simpler chat capture addon. Uses `/afcopy` and `/chatcopy`. Saves state in `AutoFishChatCopy_State` SavedVariable. Auto-opens its copy window on load (v0.1.1+).

These are independent addons deployed to the same Rift `Interface/Addons/` directory. The `.toc` files have different `Identifier` values.

### Live workflow
Follow `docs/prototype-first-workflow.md`: calibrate fishable coordinate → exact PID/HWND → bounded casts → simple timing → then harden. Don't block on perfect native water detection or broad bridge architecture.

### Profile-driven defaults
Fishing profiles (in `profiles/`) provide `pacing.biteTimeoutMs` → `--cast-wait-seconds`, `pacing.lootTimeoutMs` → `--post-pull-delay-ms`, and `pacing.interCastDelayMs` → between-cast delay (default 800ms). All profiles currently use 30s bite timeout, 1.5s inter-cast delay. Use `--profile <id>` to load defaults; CLI overrides take precedence.

### Testing
- **Python smoke tests:** `python tools/autofish-helper-py/tests/smoke_autofish_helper.py` — spawns the helper module in-process, exercises profile defaults, session plans, runbook rendering, doctor reports, red-reticle guards, facing deltas, fan planning, and stale-plan refusal. No game interaction.
- **Doc command validation:** `python tools/autofish-helper-py/tests/validate_doc_commands.py` — verifies all CLI commands in markdown docs match the actual argparse surface.
- **Lua smoke tests:** `lua scripts/lua-smoke-tests.lua` — smoke-tests the Lua addon.
- **Full offline validation:** `python scripts/run_local_checks.py` — runs .NET build, profile validation, Python smoke tests, doc validation, and Lua checks.

### Code style (.editorconfig)
- **All files:** UTF-8, CRLF line endings, `insert_final_newline = true`, `trim_trailing_whitespace = true`
- **.cs / .lua / .py:** 4-space indent
- **.md:** trailing whitespace NOT trimmed (preserves markdown line breaks)

### Cursor rules
- `.cursor/rules/` contains 12 `.mdc` files loaded by glob pattern for each file type (contracts, docs, dotnet, general, github, handoffs, lua, profiles, python, safety, scripts, testing). These contain file-type-specific conventions.

### One-off fix scripts
- `tools/apply_clipboard_fix.py`, `tools/apply_doctor_fix2.py`, `tools/apply_final_fixes.py`, `tools/fix_dry_run.py`, `tools/fix_inbound_bridge.py` — historical patches. Do not use as templates for new code. All active logic lives in `autofish_helper.py`.
