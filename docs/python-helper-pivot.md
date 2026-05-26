# AutoFish Python Helper Pivot

## Decision

AutoFish keeps Lua as the in-game Rift addon ecosystem layer and pivots external helper/runtime automation to Python-first.

This means:

- `lua/AutoFish` remains the in-game addon surface for slash commands, status, diagnostics, guardrails, and future addon-facing state.
- Python becomes the active helper layer for same-PC Rift-window automation, screenshots, cursor/key input, image evidence, and prototype orchestration.
- The existing .NET helper remains legacy/reference until it is explicitly migrated or retired.

## Why

The live blocker is now desktop automation and visual feedback, not a desktop GUI framework.

Python is the smallest practical fit for:

- exact PID/HWND validation,
- foreground/focus checks,
- screenshots and crops,
- cursor hover without clicking,
- keypress and left-click sequences,
- image-detection experiments,
- fast local iteration on the same PC running Rift.

## Current confirmed live mechanic

Operator screenshots on 2026-05-25 proved the cast-start sequence:

1. Hover the cursor over a valid fishable water point.
2. Press/release actionbar 1 key `8`.
3. Rift shows a fishing placement reticle at the cursor.
4. Left-click the placement point.
5. The fishing pole animation starts and a visible line extends toward the placement point.

Evidence screenshots were captured locally from Rift on 2026-05-25:

- `2026-05-25_134047.jpg` - yellow placement circle after pressing `8`.
- `2026-05-25_134759.jpg` - fishing pole animation and visible line after left-click.
- `2026-05-25_141050.jpg` through `2026-05-25_141140.jpg` - red, yellow, and blue/cyan reticle sweep.
- `2026-05-25_141606.jpg` and `2026-05-25_141607.jpg` - blue/cyan reticle over water.
- `2026-05-25_141610.jpg` and `2026-05-25_141611.jpg` - fishing line/cast animation after the blue/cyan reticle sequence.

Current reticle model:

| Reticle color | Helper behavior |
| --- | --- |
| Red | abort; do not click; recalibrate point |
| Yellow | valid/click-confirmable |
| Blue/cyan | valid/click-confirmable |

The first Python helper can start with manually calibrated yellow or blue/cyan coordinates. A later helper pass should add screenshot-based reticle color detection near the cursor after pressing `8`.

## Migration rule

Do not rewrite the whole repo at once.

Use this rule:

> Any new live helper behavior is Python-first. Existing PowerShell and .NET paths remain only until Python has parity for that behavior.

## Current bounded one-cast command

The current helper implements the first bounded cast/click/wait/pull proof as:

```text
signal-proof one-cast:
  validate exact PID/HWND
  focus target window
  move cursor to calibrated client coordinate without clicking
  press key 8
  capture and confirm reticle is not red
  wait briefly
  left-click same coordinate
  capture evidence
```

Dry-run command shape:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast `
  --pid <CURRENT_PID> `
  --hwnd <CURRENT_HWND> `
  --x <FISHABLE_CLIENT_X> `
  --y <FISHABLE_CLIENT_Y> `
  --key 8 `
  --dry-run
```

Then rerun with `--confirm-input` and without `--dry-run` only after exact-window,
coordinate, session-plan, and operator preflight gates pass.

## Safety constraints

- Require exact PID/HWND before input.
- Support dry-run for every live action command.
- Send no movement for fishing casts.
- Never use `-` as a helper hotkey or scripted input on this setup; the operator confirmed that pressing `-` in-game initiates `reloadui`.
- Keep one-cast tests capped until bite/pull/loot timing is proven.
- Stop if the target window changes, loses foreground, `reloadui` occurs, or the character falls into water.

## Historical fallback signal priority

The Python helper should prioritize a signal-proof harness before a longer fishing loop. Historical cursor, `/log`, pixel, audio, and fixed hotbar/bag methods are stale until proven on the current local Rift client.

First prove or retire them in this order:

1. cursor/reticle screenshots and OS-cursor correlation,
2. reticle color crops for red/yellow/blue/green,
3. inventory/bag deltas through addon API evidence,
4. current log/chat/notification output,
5. audio bite/splash cue separation,
6. explicit profile fields for hotbar and bag assumptions.

See `docs/development/historical-signal-proof-lane.md` for the evidence format and promotion criteria.

## Near-term implementation checklist

1. Add `tools/autofish-helper-py/`. Done: initial `signal-proof reticle`, read-only `signal-proof log`, read-only `signal-proof layout`, and read-only `signal-proof audio` harnesses exist. Lua now also has `/autofish invproof` for native inventory-delta proof.
2. Add Python cache/venv ignores.
3. Implement exact PID/HWND validation.
4. Implement screenshot capture.
5. Implement hover without click.
6. Implement key `8`.
7. Capture after keypress and record reticle color.
8. Implement `signal-proof one-cast --dry-run`.
9. Implement left-click confirmation for yellow or blue/cyan reticles.
10. Add bite/pull timing only after scripted cast-start is reproduced.
