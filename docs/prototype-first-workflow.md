# AutoFish Prototype-First Workflow

This document overrides process-heavy milestone behavior during live development.

The goal is a working Rift autofishing prototype first, then hardening. Do not repeat long validation ladders that never produce a useful mechanic.

## Prime directive

Build the simplest bounded thing that can actually catch fish.

If a task does not directly help one of these outcomes, do not do it yet:

1. cast at a calibrated fishable point,
2. detect or time the bite/pull window,
3. loot or complete the catch,
4. repeat safely for a small capped number of casts,
5. stop safely on obvious danger or operator request.

## Current practical model

Treat fishing as a simple live-client mechanic:

1. operator places the character at water,
2. operator or helper calibrates one fishable client coordinate,
3. helper focuses exact Rift PID/HWND,
4. helper clicks the calibrated point,
5. helper presses the fishing key, currently `8`,
6. helper clicks the calibrated point again,
7. helper waits for a measured bite/pull window,
8. helper clicks/pulls/loots,
9. helper repeats only up to a small explicit cap.

Do not block the prototype waiting for native addon proof of `near_water`. In this workflow, `near_water` means: **the operator calibrated this point and a live probe proved it can fish**.

## What to avoid

Do not spend more live time on:

- proving every signal natively before a cast works,
- broad schema redesign,
- bridge architecture work,
- helper UI polish,
- release packaging,
- exhaustive docs,
- unbounded old-source archaeology,
- multi-agent research unless the current blocker is truly unknown.

Targeted historical-signal validation is now allowed when it directly proves or retires a bite, reticle, loot, log, audio, cursor, hotbar, or bag signal for the current local client.

Do not add an unattended loop until the bounded prototype catches fish repeatedly.

## Minimal live safety rules

Keep these because they prevent wasted time and bad input:

- exact PID/HWND required before any input,
- foreground check before every click/key,
- no movement in fishing scripts,
- no broad automation loop,
- explicit `-MaxCasts`,
- `-DryRun` for new coordinates,
- known local keybind: pressing `-` in-game initiates `reloadui`; do not use `-` as a helper hotkey or scripted input unless intentionally reloading the UI,
- stop if target drifts, window loses foreground, combat appears, or the operator interrupts.

Everything else is optional until the prototype catches fish.

## Working prototype target

The next concrete target is a helper-side script:

```powershell
scripts\start-live-fishing-prototype.ps1 `
  -TargetProcessId <pid> `
  -TargetWindowHandle <hwnd> `
  -ClientX <fishable-x> `
  -ClientY <fishable-y> `
  -FishingKey 8 `
  -MaxCasts 1 `
  -DryRun
```

Then:

1. run `-DryRun`,
2. run `-MaxCasts 1`,
3. if one catch works, run `-MaxCasts 3`,
4. only then add better signal detection.

## Definition of progress

Progress is not more documentation or a cleaner architecture. Progress is:

- one cast starts,
- one bite/pull is handled,
- one fish is looted,
- three capped casts work,
- a stop condition works.

Every work session should end with one of:

- a working cast/catch improvement,
- a smaller blocker with evidence,
- a script that makes the next live attempt faster.

## Documentation budget

Keep live docs short:

- target PID/HWND,
- calibrated coordinate,
- exact command/script run,
- result,
- next action.

Do not write long narrative docs during live iteration unless handing off or committing.

## Decision rules

- If native addon APIs are missing, use helper-side practical methods.
- If a coordinate is not fishable, pick/calibrate another coordinate.
- If the timing is unknown, measure it with a one-cast run and simple waits.
- If visual/bite detection is hard, start with conservative timed clicks.
- If a safety feature delays a working prototype and is not essential for a capped run, defer it.

## Historical signal priority lane

The current priority is to prove or retire the historical fallback signals before trusting them:

1. cursor/pointer/reticle changes,
2. pixel/color/image checks,
3. inventory and bag deltas,
4. `/log` or chat/notification text,
5. audio amplitude or splash cues,
6. fixed hotbar/bag assumptions.

Treat every historical method as **stale until proven current**. Use `docs/development/historical-signal-proof-lane.md` as the proof checklist. Promote a signal only after a current local evidence packet shows it is repeatable and bounded.

## Near-term implementation order

1. Keep `scripts\invoke-live-fishable-point-probe.ps1` for coordinate proof.
2. Add `scripts\start-live-fishing-prototype.ps1`.
3. Support `-DryRun`, `-MaxCasts`, `-CastWaitSeconds`, and post-key/pull delay settings.
4. Run one calibrated point through one cast.
5. Tune timing.
6. Run three capped casts.
7. Only then integrate addon status and advisory mode.

Current script status:

- `scripts\invoke-live-fishable-point-probe.ps1` exists for proving/calibrating a point.
- `scripts\start-live-fishing-prototype.ps1` exists for bounded click/key/click/wait/pull runs.
- Always run the prototype script with `-DryRun` before a real cast at a new coordinate.
- Use `-SkipInitialClick` for the simpler key-then-click sequence if click/key/click does not cast.
- Use `-ActionClientX/-ActionClientY` to click the visible rod action slot directly if the keybind path is uncertain.

## Non-negotiable stop line

If the character falls into water, recover manually or with one bounded backpedal/jump recovery, then stop live fishing probes until the character is stable on shore again.

If `reloadui` is triggered, whether intentionally or by pressing the local `-` keybind, treat the live test state as reset. Wait for the addon to reload, reacquire exact PID/HWND, and rerun `/autofish status` or `/autofish api` before continuing.
