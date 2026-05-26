# AutoFish handoff - Python proof lane toward supervised fishing

Date: 2026-05-26 07:57 -04:00
Updated: 2026-05-26 after scoped decision/gate, stop-file readiness, foreground/readability readiness, target-freshness, and fresh screen-coordinate hardening
Repo: `C:\RIFT MODDING\AutoFish`
Branch: `main`
Remote: `https://github.com/360madden/AutoFish`

## Current direction

AutoFish is still Python-helper-first for the external helper/runtime layer and Lua-addon-first for in-game Rift API visibility. The .NET helper remains legacy/reference. ChromaLink remains read-only from this repo.

The current implementation is not an unattended fishing loop yet. It is now a stronger supervised proof pipeline:

1. plan a fishability fan,
2. review one candidate reticle/game-feedback proof,
3. create a session plan directly from that fan candidate,
4. record a scoped `fishabilityCandidate` decision using the plan review token,
5. dry-run one-cast,
6. run one supervised one-cast proof,
7. record a scoped `oneCast` decision using the same plan review token,
8. dry-run bounded session,
9. run a small supervised bounded session with stop-file interruption.

## Latest pushed commits in this lane

- `1b2673b` - Add session plan stop-file commands
- `e6b5252` - Add session plan readiness bundle
- `219a2d7` - Refresh screen coordinates before input
- `4e2e532` - Make cursor handle type portable
- `ecde359` - Avoid setup-dotnet download in CI
- `80c7286` - Gate session plans on target size
- `b9fac9a` - Allow fail-fast session gate checks
- `29e5223` - Attach decisions to session plans
- `bc846e6` - Refresh Python proof lane handoff
- `03b6e19` - Add session plan gate status
- `466f92b` - Scope reviewed proof decisions to session plans
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

Creating that file aborts before the next bounded helper action or during wait periods. Prefer the helper-managed commands so the path comes from the selected session plan:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan stop-file status --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan stop-file create --path .autofish-live\session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py session-plan stop-file clear --path .autofish-live\session-plan-latest.json
```

### Fishability fan to one-cast bridge

`signal-proof fishability-fan` now emits per-candidate suggested reticle commands. `signal-proof fishability-fan-runbook` prints them in sequential order.

For each candidate:

1. run candidate reticle dry-run,
2. run supervised `--skip-click --cancel-after-key` reticle proof,
3. review the manifest/screenshots,
4. create a session plan from the fan candidate,
5. print `session-plan runbook`,
6. record scoped `fishabilityCandidate` with the plan review token.

Example:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan-runbook `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json

python tools\autofish-helper-py\autofish_helper.py session-plan from-fan `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json `
  --candidate-index <index> `
  --profile starter-pond `
  --output .autofish-live\session-plan-latest.json

python tools\autofish-helper-py\autofish_helper.py session-plan runbook `
  --path .autofish-live\session-plan-latest.json

python tools\autofish-helper-py\autofish_helper.py session-plan gates `
  --path .autofish-live\session-plan-latest.json
```

### Scoped review gates

Each new session plan now has a deterministic review scope token (`review.scopeToken`) derived from the target PID/HWND, client coordinate, profile/defaults, and fan source when present. Reviewed `fishabilityCandidate` and `oneCast` decisions should be recorded with `--session-plan <plan>` from the session-plan runbook, which attaches the plan scope automatically. This prevents stale decisions for older coordinates or windows from unlocking new live input.

Use this no-input gate check at any time:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan gates `
  --path .autofish-live\session-plan-latest.json
```

Use `session-plan explain --path .autofish-live\session-plan-latest.json` for the no-input plain-language blocked-gate summary and next action. Use `session-plan preflight --path .autofish-live\session-plan-latest.json --require ready-one-cast` when a script or operator copy/paste step should print the same summary and fail closed.

Use `--require plan-fresh` when a script should fail closed unless the session plan is inside the configured age window. The same age gate is enforced by plan-backed `one-cast` and `bounded-session`. The default is 240 minutes; use `--max-plan-age-minutes <minutes>` to tighten it, or `<=0` only for intentional offline diagnostics.

Use `--require target-current` when a script should fail closed unless the current Rift client size still matches the session plan's recorded `targetValidation.clientWidth/clientHeight`.

Use `--require target-foreground` and `--require client-readable` when scripts should fail closed unless the exact Rift HWND is foreground and the client is restored/readable. Use `--require ready-one-cast` before confirmed one-cast input and `--require ready-bounded-session` before confirmed bounded-session input. These are no-input compound readiness checks over stop-file-clear, plan-age, target-current, foreground/readability, and the relevant reviewed-decision gate.

### Target-freshness gate

Session plans created with `--validate-target`, or from a fishability-fan manifest that recorded live target geometry, now carry a target client-size snapshot. `session-plan gates`, plan-backed `signal-proof one-cast`, and plan-backed `signal-proof bounded-session` compare that stored size with the current target before allowing live input. If the Rift window was resized, restored to a different size, minimized to `0x0`, or otherwise reports a different client rect, recreate the plan and recalibrate X/Y.

The helper also records the current client origin as `clientScreenX/clientScreenY` in target snapshots and recomputes client-to-screen coordinates immediately before each cursor move/click. This prevents reusing stale screen coordinates if the same-size Rift window moves between bounded actions.

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
