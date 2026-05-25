# AutoFish Compact Handoff - Cast-Start Revelation - 2026-05-25 13:51 EDT

## TL;DR

The live fishing blocker narrowed substantially. Operator screenshots prove that actionbar 1 key `8` **does work**: when the cursor is already over a fishable water point, pressing/releasing `8` immediately shows a placement reticle at the cursor. Yellow and blue/cyan reticles are now supported by cast-start evidence; red appears invalid. A subsequent left-click on a valid reticle starts the fishing pole animation and casts a line toward that point.

The next script change should model the real mechanic:

```text
hover calibrated fishable point -> press 8 -> left-click same point -> wait/observe
```

Do not spend more time on alternate hotbar/action-slot clicks unless the keybind changes.

## Current repo state

- Repo: `C:\RIFT MODDING\AutoFish`
- Branch: `main`
- HEAD during this handoff: `86b660d Add live AutoFish prototype workflow`
- Worktree before this handoff: clean
- New documentation added by this handoff:
  - `docs/live-validation/2026-05-25-action-fishable-mapping.md`
  - `docs/handoffs/handoff-2026-05-25-135111-autofish-cast-start-revelation.md`

## Evidence

Operator-provided in-game screenshots:

- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_134047.jpg`
  - Shows the yellow fishing placement circle after initially pressing/releasing number `8`.
  - Operator clarified the circle appears immediately at the cursor only when the cursor is in a certain valid spot on the water.
- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_134759.jpg`
  - Shows the fishing pole use animation after pressing the left mouse button.
  - A visible fishing line runs from the pole toward the general spot where the yellow circle had been.
- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_141050.jpg` through `2026-05-25_141140.jpg`
  - Show red, yellow, and blue/cyan reticle states at different water/shore spots and distances from the player.
- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_141606.jpg` and `2026-05-25_141607.jpg`
  - Show a blue/cyan reticle over water.
- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_141610.jpg` and `2026-05-25_141611.jpg`
  - Show fishing line/cast animation immediately after the blue/cyan reticle sequence.

## Superseded assumption

Earlier live notes said the visible rod/key assumptions did not arm a cast. That is now too broad and should be treated as stale.

Corrected truth:

- key `8` arms/shows the fishing placement indicator when the cursor is already over candidate water;
- the cast is confirmed by left-clicking after a valid reticle appears;
- red reticle means do not click / recalibrate;
- yellow and blue/cyan reticles are valid/click-confirmable based on current evidence;
- failed prior runs likely missed the required cursor-preposition/valid-point timing, used a bad point, or clicked in a sequence that did not match the real mechanic.

## Current mechanic

Known live sequence:

1. Character is on shore facing water.
2. Cursor is placed over a valid fishable water point.
3. Press/release actionbar 1 key `8`.
4. Placement reticle appears immediately at cursor.
5. Left-click.
6. Fishing pole animation starts; line extends from the pole toward the placement point.

## Reticle color model

| Reticle color | Meaning | Helper action |
| --- | --- | --- |
| Red | invalid or unsafe placement | abort / do not click / recalibrate |
| Yellow | valid fishing placement | left-click confirm allowed |
| Blue/cyan | valid fishing placement | left-click confirm allowed |

The Python helper should eventually capture after pressing `8`, classify the reticle near the cursor, and only click-confirm yellow or blue/cyan states.

## Script implication

Current `scripts/start-live-fishing-prototype.ps1` supports:

- default: click point -> press key -> click point
- `-SkipInitialClick`: press key -> click point
- `-ActionClientX/-ActionClientY`: click an action slot instead of pressing the key

The next required mode is:

```text
move cursor to ClientX/ClientY without clicking -> press FishingKey -> delay -> click ClientX/ClientY
```

Suggested flag/name:

```powershell
-HoverBeforeKey
```

Recommended first live run after adding it:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\start-live-fishing-prototype.ps1 `
  -TargetProcessId <CURRENT_PID> `
  -TargetWindowHandle <CURRENT_HWND> `
  -ClientX <CALIBRATED_FISHABLE_X> `
  -ClientY <CALIBRATED_FISHABLE_Y> `
  -FishingKey 8 `
  -MaxCasts 1 `
  -HoverBeforeKey `
  -PostKeyClickDelayMilliseconds 500 `
  -PullClicks 0 `
  -CaptureEachCast `
  -DryRun
```

Then rerun without `-DryRun` only after exact PID/HWND and coordinate checks pass.

## Safety constraints that still hold

- Reconfirm current Rift PID/HWND before any input.
- No movement in fishing scripts.
- No unattended loop yet.
- Keep `MaxCasts=1` until scripted cast-start is reproduced.
- Keep `PullClicks=0` until the script proves it can start the cast and capture the line/cast state.
- Stop if the character falls into water or the target window changes.

## Resume checklist

1. Reconfirm exact Rift process/window.
2. Calibrate the exact client coordinate that produces a yellow or blue/cyan reticle.
3. Add `-HoverBeforeKey` or equivalent cursor-preposition behavior.
4. Dry-run the new flow.
5. Run one real cast-start test with no pull clicks.
6. Capture after keypress and after confirm click.
7. If the line appears, update the live-validation doc with the scripted artifact paths.
8. Only then measure bite/pull timing.

## Optional top 10 next best actions

1. Add `-HoverBeforeKey` to `scripts/start-live-fishing-prototype.ps1`.
2. Record calibrated client coordinates from yellow and blue/cyan reticle screenshots.
3. Reconfirm current PID/HWND before input.
4. Dry-run the hover/key/click flow.
5. Run one real `MaxCasts=1` cast-start test with `PullClicks=0`.
6. Capture immediately after keypress to prove a yellow or blue/cyan reticle appears.
7. Capture immediately after left-click to prove the line/cast starts.
8. Update `docs/live-validation/2026-05-25-action-fishable-mapping.md` with artifact paths from the scripted run.
9. Add configurable bite/pull timing only after scripted cast-start is reproduced.
10. Attempt a single full catch, then a capped three-cast run only after one catch works.
