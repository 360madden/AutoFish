# AutoFish — Agent Instructions

> **For both DeepSeek V4 Pro and ChatGPT Codex / ChatGPT 5.5.**
> This is the canonical agent instruction file. Read it first.
> `knowledge.md` has the full project reference (commands, file map, deeper gotchas).

---

## ⛔ Critical Safety Rules (violate none of these)

1. **Never call `--confirm-input` without explicit user approval.** The Python helper sends real keyboard/mouse input to a live Rift game client.
2. **Always dry-run before confirm-input** for any command that sends input.
3. **Exact PID and HWND always.** Every live command requires validated PID and HWND.
4. **No `-` (dash) key as input.** It's bound to `reloadui` and will disrupt the session.
5. **No unattended loops.** Only supervised bounded sessions.
6. **Stop file is sacred.** If `.autofish-live/STOP.txt` exists, bounded-session and one-cast abort.

---

## What This Project Is

AutoFish is a **Rift fishing automation tool** with a split stack:

| Layer | Path | Status |
|---|---|---|
| Python helper | `tools/autofish-helper-py/autofish_helper.py` | **Active development surface** — monolithic ~9k line file |
| Lua addon | `lua/AutoFish/` | In-game layer — modular (Bridge/, Core/, UI/) |
| Contracts | `src/AutoFish.Contracts/`, `contracts/` | Shared JSON schemas and C# models |
| .NET app | `src/AutoFish.App/` | **Frozen legacy** — do not add live automation here |

---

## Architecture Rules

- **Python helper is monolithic.** `autofish_helper.py` stays as one file. Do not split into modules without discussion.
- **Python stdlib only.** No pip packages. Windows-only (`os.name == "nt"` guard).
- **PowerShell 7+ (`pwsh`)** required for live scripts. Windows PowerShell 5.1 lacks `ConvertFrom-Json -Depth`.
- **Lua addon is modular.** Respect the existing `Bridge/`, `Core/`, `UI/` split.
- **.NET app is frozen.** Do not add new live-window automation there.
- **Contracts are shared.** Changes to schemas in `contracts/` must stay in sync with C# models in `src/AutoFish.Contracts/Models/`.
- **Session plans expire.** Max age 240 minutes. Do not reuse after Rift restart/resize.
- **No ChromaLink modification.** Read-only via `http://127.0.0.1:7337`.

---

## Commands Quick Reference

### Validate changes before committing
```powershell
.\scripts\run-local-checks.ps1                     # Full: .NET + profiles + Python + Lua
.\scripts\run-local-checks.ps1 -SkipLuaChecks      # Skip Lua if luac/lua not installed
.\scripts\run-python-helper-checks.ps1              # Python only: compile, smoke, docs, help
```

### Profile validation
```powershell
.\scripts\validate-profiles.ps1
```

### Lua checks
```powershell
luac -p lua/AutoFish/AutoFishAddon.lua
lua scripts/lua-smoke-tests.lua
```

---

## Code Conventions

- **Type hints preferred** in Python (not required everywhere in the 9k-line monolith, but add them to new code).
- **Match existing style.** Follow the patterns in surrounding code exactly.
- **Lua:** Follow the module pattern in `AutoFishAddon.lua` and the bridge/state-machine architecture.
- **Profiles:** `profiles/*.json` — schema-driven; validate with `validate-profiles.ps1`.
- **Handoffs:** Sequential artifacts live in `docs/handoffs/` and record live-run state.
- **Live evidence:** All proof output goes to `.autofish-live/` (git-ignored). Never commit it.

---

## Window & Coordinate Constraints

- **Minimum readable size:** `960×540` client area.
- **Client-relative coordinates only.** Recalibrate fishable X/Y after any resize.
- **Minimized windows refused.** Restore/maximize Rift manually first.
- **Focus preserves size.** Preflight must not de-maximize or shrink a normal/maximized window.

---

## Model-Specific Guidance

### For DeepSeek V4 Pro
- **Be specific and concise.** Prefer bullet points over long paragraphs. Reference exact file paths, function names, and schema identifiers.
- **Keep instructions tight.** DeepSeek degrades with bloated prompts — this AGENTS.md is intentionally lean.
- **One atomic edit at a time.** When orchestrating, issue single-purpose changes rather than bundling unrelated edits. Don't ask DeepSeek to "consider X while doing Y" — split into discrete, ordered tasks.
- **Technical documentation over abstraction.** Cite `knowledge.md` sections, schema IDs (e.g. `autofish.sessionPlan.v1`), and existing function signatures when reasoning about changes.

### For ChatGPT Codex / ChatGPT 5.5
- **Before editing, summarize your understanding and plan.** Write a one-line hypothesis about what the change will accomplish, then verify it after.
- **After gathering context, write a brief findings summary** before proceeding to implementation — this triggers deeper reasoning in ChatGPT 5.5.
- **Structured output works well.** JSON manifests, checklists, and gate evaluations are strengths. Use structured formats when presenting complex analysis.
- **Constraints must be explicit.** List "do not" rules clearly (already done in the safety section above).
- **Modular context.** ChatGPT 5.5 handles larger context windows well but benefits from clean scoping via `.cursor/rules/*.mdc` globs — only relevant rules are loaded per file type.

---

## Key Docs (read when relevant)

| Doc | When to read |
|---|---|
| `knowledge.md` | Full project reference — commands, file map, deeper gotchas |
| `docs/prototype-first-workflow.md` | Live run procedure: calibrate → PID/HWND → bounded casts → harden |
| `docs/helper-operator-guide.md` | Operator instructions for live proof-pack runs |
| `docs/addon-architecture.md` | Lua addon internals |
| `docs/handoffs/` | Where the live run left off (latest = most recent) |
| `contracts/` | JSON schemas for bridge messages and profiles |
