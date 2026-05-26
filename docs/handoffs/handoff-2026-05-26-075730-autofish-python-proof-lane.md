# AutoFish handoff - Python proof lane toward supervised fishing

Date: 2026-05-26 07:57 -04:00
Repo: `C:\RIFT MODDING\AutoFish`
Branch: `main`
Remote: `https://github.com/360madden/AutoFish`

## Current direction

AutoFish is still Python-helper-first for the external helper/runtime layer and Lua-addon-first for in-game Rift API visibility. The .NET helper remains legacy/reference. ChromaLink remains read-only from this repo.

The current implementation is not an unattended fishing loop yet. It is now a stronger supervised proof pipeline:

1. plan a fishability fan,
2. review one candidate reticle/game-feedback proof,
3. record a `fishabilityCandidate` decision,
4. create a session plan directly from that fan candidate,
5. dry-run one-cast,
6. run one supervised one-cast proof,
7. record a `oneCast` decision,
8. dry-run bounded session,
9. run a small supervised bounded session with stop-file interruption.

## Latest pushed commits in this lane

- `ba96541` - Run Python helper checks in CI
- `cc57c09` - Gate fan-derived one-cast plans
- `62bf289` - Create session plans from fan candidates
- `dca56fa` - Include Python helper in local checks
- `e0723a1` - Add fishability fan runbook
- `6410c4c` - Add fan candidate reticle commands
- `7fedd44` - Default live proof commands to stop file
- `0e6ae0e` - Default session plans to stop file

## New helper capabilities

### Stop-file defaults

The default stop file is now:

```text
.autofish-live/STOP.txt
```

It is included by default in:

- `session-plan create`
- `session-plan from-fan`
- `signal-proof one-cast`
- `signal-proof bounded-session`

Creating that file aborts before the next bounded helper action or during wait periods. Delete it before a later supervised rerun.

### Fishability fan to one-cast bridge

`signal-proof fishability-fan` now emits per-candidate suggested reticle commands. `signal-proof fishability-fan-runbook` prints them in sequential order.

For each candidate:

1. run candidate reticle dry-run,
2. run supervised `--skip-click --cancel-after-key` reticle proof,
3. review the manifest/screenshots,
4. record `fishabilityCandidate`,
5. create a session plan from the fan candidate.

Example:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan-runbook `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json

python tools\autofish-helper-py\autofish_helper.py signal-proof decide `
  --signal fishabilityCandidate `
  --decision fallback-only `
  --reason "Reviewed fan candidate as fishable enough for one supervised one-cast proof." `
  --evidence .autofish-live\<candidate-reticle-proof>\manifest.json

python tools\autofish-helper-py\autofish_helper.py session-plan from-fan `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json `
  --candidate-index <index> `
  --profile starter-pond `
  --output .autofish-live\session-plan-latest.json
```

### Fan-derived one-cast gate

Confirmed `one-cast` from a `session-plan from-fan` plan now requires a reviewed `fishabilityCandidate` decision of `promote` or `fallback-only`, unless intentionally bypassed with:

```powershell
--allow-unreviewed-fan-candidate
```

This prevents a planning-only fan point from silently becoming confirmed live input.

### CI/local checks

The Python helper smoke checks are now part of:

- local `scripts/run-local-checks.ps1`
- GitHub Actions workflow `.github/workflows/ci.yml`

This environment does not currently have `lua`/`luac` on PATH, so full local checks require either installing Lua or intentionally using:

```powershell
.\scripts\run-local-checks.ps1 -SkipLuaChecks
```

## Validation completed locally

Passed:

```powershell
.\scripts\run-python-helper-checks.ps1
.\scripts\run-local-checks.ps1 -SkipLuaChecks
```

Known local validation blocker:

```text
luac is not on PATH, so full Lua syntax/smoke checks cannot run in this shell.
```

## Still external/live-gated

These are not proven current in this shell/session:

- live Rift PID/HWND,
- live addon reload after latest Lua changes,
- `/autofish coords` current output,
- fresh ChromaLink bridge health/world-state,
- successful one-cast proof from current fishable point,
- repeated inventory/catch/loot proof,
- bounded-session proof.

## Recommended next live sequence

1. Restore/maximize Rift manually; keep a readable large client size.
2. Reload AutoFish in Rift.
3. Run `/autofish help` and confirm `/autofish coords` and `/autofish invproof` appear.
4. Run `/autofish coords` and capture/transcribe the line.
5. Verify current PID/HWND.
6. Run read-only ChromaLink freshness proof if ChromaLink is running.
7. Run coordinate cross-check if both sources are available.
8. Plan a fishability fan at the current large-window geometry.
9. Generate `fishability-fan-runbook` and review one candidate at a time.
10. Promote a reviewed candidate into a session plan, then run session-plan dry-run before confirmed one-cast.

## Safety reminder

Do not reuse old PID/HWND, old client coordinates, or old session plans after Rift restarts, window resize, camera change, or character movement. Do not use `-`; this setup binds it to reloadui. No unattended loop is ready yet.
