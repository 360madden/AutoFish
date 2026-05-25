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
3. Rift shows the yellow fishing placement circle at the cursor when the spot is valid.
4. Left-click the placement point.
5. The fishing pole animation starts and a visible line extends toward the placement point.

Evidence screenshots were captured locally from Rift on 2026-05-25:

- `2026-05-25_134047.jpg` - yellow placement circle after pressing `8`.
- `2026-05-25_134759.jpg` - fishing pole animation and visible line after left-click.

## Migration rule

Do not rewrite the whole repo at once.

Use this rule:

> Any new live helper behavior is Python-first. Existing PowerShell and .NET paths remain only until Python has parity for that behavior.

## Target first Python command

The first useful command should be equivalent to:

```text
one-cast-start:
  validate exact PID/HWND
  focus target window
  move cursor to calibrated client coordinate without clicking
  press key 8
  wait briefly
  left-click same coordinate
  capture evidence
```

Suggested command shape:

```powershell
python tools\autofish-helper-py\autofish_helper.py one-cast-start `
  --pid <CURRENT_PID> `
  --hwnd <CURRENT_HWND> `
  --x <FISHABLE_CLIENT_X> `
  --y <FISHABLE_CLIENT_Y> `
  --key 8 `
  --dry-run
```

Then rerun without `--dry-run` only after the exact-window and coordinate checks pass.

## Safety constraints

- Require exact PID/HWND before input.
- Support dry-run for every live action command.
- Send no movement for fishing casts.
- Keep one-cast tests capped until bite/pull/loot timing is proven.
- Stop if the target window changes, loses foreground, or the character falls into water.

## Near-term implementation checklist

1. Add `tools/autofish-helper-py/`.
2. Add Python cache/venv ignores.
3. Implement exact PID/HWND validation.
4. Implement screenshot capture.
5. Implement hover without click.
6. Implement key `8`.
7. Implement left-click confirmation.
8. Implement `one-cast-start --dry-run`.
9. Run one real cast-start test.
10. Add bite/pull timing only after scripted cast-start is reproduced.
