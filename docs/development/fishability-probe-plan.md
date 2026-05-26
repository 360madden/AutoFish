# Fishability probe plan

Date: 2026-05-25

## Decision

AutoFish should prefer **fishability proof** over visual water detection.

The useful runtime question is not "is this pixel water?" The useful question is:

```text
Will the current Rift client accept a fishing action at this candidate point, and does the fishing lifecycle progress?
```

Visual reticle and pixel checks remain fallback diagnostics only. They are useful for calibration, but lighting, water shimmer, UI overlap, camera angle, and window resolution make them too noisy to be primary truth.

## Current implementation slice

`tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan` now creates a **dry-run screen-space fan** of candidate probe points.

It intentionally sends no input:

- no movement,
- no fishing key,
- no click,
- no unattended loop.

The command records candidate client coordinates, fan geometry, exact PID/HWND target context, optional no-input crop captures, and per-candidate suggested reticle proof commands so the operator can review the plan before any future bounded probing.

Example:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan `
  --pid <pid> `
  --hwnd <hwnd> `
  --origin-x <player-or-screen-anchor-x> `
  --origin-y <player-or-screen-anchor-y> `
  --forward-x <operator-forward-point-x> `
  --forward-y <operator-forward-point-y> `
  --dry-run
```

The output is planning evidence only. It does not classify water or fishability.

Each in-bounds candidate includes suggested reticle commands:

1. run the candidate `reticleDryRun` command first,
2. only after review, run the candidate `reticleSkipClickCancel` command while supervised.

The skip-click/cancel command sends one cursor move and one fishing-key press, captures the reticle for a short watch window, presses Escape, and sends no left click.

To print the candidate commands as an ordered runbook:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan-runbook `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json
```

After one candidate is reviewed as fishable, create a local session plan from the same manifest instead of retyping PID/HWND/X/Y:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan from-fan `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json `
  --candidate-index <index> `
  --profile starter-pond `
  --output .autofish-live\session-plan-latest.json
```

Then print the session-plan runbook and use its scoped `signal-proof decide --signal fishabilityCandidate --session-plan <plan>` command before confirmed one-cast input:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan runbook `
  --path .autofish-live\session-plan-latest.json
```

Use the no-input gate check before live commands:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan gates `
  --path .autofish-live\session-plan-latest.json
```

Add `--require stop-file-clear`, `--require target-current`, `--require target-foreground`, `--require client-readable`, `--require confirmed-one-cast`, or `--require confirmed-bounded-session` for fail-closed scripts that should stop unless the requested gate is ready. Use `--require ready-one-cast` before confirmed one-cast input and `--require ready-bounded-session` before confirmed bounded-session input when you want the combined no-input pre-live gate bundle.

Use `session-plan stop-file status/create/clear --path .autofish-live\session-plan-latest.json` instead of manually editing the stop file when operating from a session plan.

The plan remains gated: it records the candidate as fan-planning source evidence and confirmed one-cast input requires a reviewed `fishabilityCandidate` decision attached to that same session plan unless intentionally bypassed. If the plan records a live target client size, plan-backed `one-cast` and `bounded-session` also fail closed when the current Rift client size differs, because old client X/Y points are stale after resize. Same-size window moves are handled by recomputing client-to-screen coordinates immediately before each cursor move/click. Still run the session-plan dry-run before confirmed one-cast input.

If the Rift window is minimized, Windows can report a `0x0` client rect. Do not force a restore just to plan geometry. Use the last verified client size and disable crops:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan `
  --pid <pid> `
  --hwnd <hwnd> `
  --origin-x <player-or-screen-anchor-x> `
  --origin-y <player-or-screen-anchor-y> `
  --forward-x <operator-forward-point-x> `
  --forward-y <operator-forward-point-y> `
  --client-width <last-verified-client-width> `
  --client-height <last-verified-client-height> `
  --no-capture-crops `
  --dry-run
```

That mode still validates the exact PID/HWND, but marks the client size as operator-supplied and produces geometry-only evidence. Use it only for planning, not for live classification.

## Classification source of truth

Future confirmed probes should classify candidate points from game feedback, in this priority order:

1. castbar starts or fishing action is accepted,
2. explicit chat/system error such as not fishable, too far, or invalid target,
3. item/inventory/loot deltas,
4. skill/currency/progression events,
5. visual reticle/cursor evidence as fallback support only.

## Coordinate-backed facing dependency

Rift's addon API does not currently expose player actor facing. A micro-step can infer rough facing only if a reliable player position source exists:

```text
position_before = read_player_position()
operator-confirmed tiny forward tap
position_after = read_player_position()
facing ~= normalize(position_after - position_before)
```

Without a coordinate source, a forward step cannot produce a numeric facing vector. It can only provide visual/operator context.

AutoFish has two coordinate evidence paths:

- direct addon cross-check: `/autofish coords`, which prints `Inspect.Unit.Detail(playerUnit).coordX`, `coordY`, and `coordZ` in game,
- helper-side bridge: ChromaLink, which can expose `player.position` through `/api/v1/riftreader/world-state` when the provider is fresh.
- proof comparison: `signal-proof coordinate-crosscheck`, which compares manually supplied `/autofish coords` output against fresh ChromaLink coordinates without sending input.

See `docs/development/chromalink-readonly-coordinate-provider.md`.

Do not treat ChromaLink reachability as coordinate truth. AutoFish must require fresh `/health`, fresh world-state, `navigation.playerPositionAvailable=true`, and `player.position.fresh=true` before using the coordinates for any fishability/facing proof.

The facing-delta calibration path is documented in `docs/development/facing-delta-calibration.md`. It computes an operational X/Y facing vector from fresh before/after coordinates around one tiny confirmed forward movement pulse. Use that vector as a fan-planning hint only; it is not native Rift actor facing/yaw.

Therefore, coordinate-backed fan probing is blocked on all of the following:

1. reliable current player coordinates,
2. proof that direct addon coordinates and helper-side coordinates agree closely enough for the run,
3. proof that the coordinates update after a tiny controlled movement,
4. a safe movement calibration command with explicit operator confirmation,
5. either a world-to-screen mapping or a separately calibrated screen-space mapping.

Until those are proven, AutoFish should use the screen-space fan planner plus game feedback classification.

## Safety boundary

Micro-step facing calibration exists as the guarded `signal-proof facing-delta` command, but it must not be implicit.

It must require:

- exact PID/HWND,
- foreground target,
- explicit `--confirm-movement`,
- very small max duration,
- before/after coordinate evidence,
- stale-coordinate rejection,
- stop on combat/secure state, target drift, foreground drift, or operator interruption.

## Current status

- Screen-space fishability fan planning: implemented as dry-run evidence.
- Direct addon coordinate probe: implemented, pending live reload/proof.
- Coordinate-backed operational facing calibration: implemented as a guarded command, blocked until coordinate sources are fresh and cross-checked.
- Visual water detection: not a primary path.
- Reticle/pixel evidence: fallback-only.
