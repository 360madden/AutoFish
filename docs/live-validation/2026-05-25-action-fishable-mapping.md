# AutoFish Live Validation - 2026-05-25 Action and Fishable Mapping

## Summary

Continued the live milestone ladder against the same Rift client. The exact target stayed foreground, responding, and unchanged. No unattended loop was started. No fall into water was observed.

This pass added live API/status instrumentation, then ran bounded one-action probes to determine why the prepared slot `8` fishing action still does not produce a cast transition.

Result: slot `8` input reaches the exact Rift HWND, the addon trace remains healthy, and native ability inventory can see fishing-related abilities. However, the selected water points did not produce a fishing cast. One historical click/key/click probe produced the live system error `This area is not fishable`, and all trace snapshots remained fail-closed with `castbar=false`, `line_cast=false`, `can_cast=false`, `confidence=0.45`.

## Target

- Process: `rift_x64`
- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Process start: `2026-05-24T13:20:04.8251137-04:00`
- Foreground/focus preflight: passed
- Client rect: `640x360`

## Artifacts

Run root:

- `.autofish-live/autonomous-20260525-continued-20260525-064411/`

Key captures:

- Preflight: `.autofish-live/autonomous-20260525-continued-20260525-064411/preflight/g0-baseline.png`
- API probe: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-autofish-api/g0-baseline.png`
- API probe chat crop: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-autofish-api/chat-crop-4x.png`
- Status after instrumentation: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-autofish-status/g0-baseline.png`
- Status chat crop: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-autofish-status/chat-crop-4x.png`
- Coordinate grid: `.autofish-live/autonomous-20260525-continued-20260525-064411/pre-historic-sequence/coord-grid.png`
- Historical sequence after 1s: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-historic-sequence-1s/g0-baseline.png`
- Historical sequence trace status: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-historic-sequence-trace-status/g0-baseline.png`
- Historical sequence trace chat crop: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-historic-sequence-trace-status/chat-crop-4x.png`
- Fishable probe `250,115` trace status: `.autofish-live/autonomous-20260525-continued-20260525-064411/after-fishable-probe-250-115-trace-status/g0-baseline.png`
- Final trace stop: `.autofish-live/autonomous-20260525-continued-20260525-064411/final-trace-stop/g0-baseline.png`

Command logs:

- `.autofish-live/autonomous-20260525-continued-20260525-064411/reloadui-after-api-patch.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/autofish-api-command.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/autofish-status-command.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/historic-sequence-click1.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/historic-sequence-key8.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/historic-sequence-click2.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/fishable-probe-250-115-click1.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/fishable-probe-250-115-key8.txt`
- `.autofish-live/autonomous-20260525-continued-20260525-064411/fishable-probe-250-115-click2.txt`

## Addon changes made during this pass

- Added `/autofish api` to print native API availability relevant to fishing probes.
- Added status output for `abilityCandidates`, `usableLureAbilities`, and `abilityScan`.
- Kept existing fail-closed observation behavior; no schema change was made.
- Deployed patched addon to both discovered Rift addon folders and reloaded the UI.

## API probe result

Live `/autofish api` output confirmed:

| API | Classification | Notes |
| --- | --- | --- |
| `Command.Console.Display` | `confirmed-native` | Chat output works. |
| `Command.Event.Attach` | `confirmed-native` | Event wiring path works. |
| `Command.Slash.Register` | `confirmed-native` | Slash command path works. |
| `Inspect.Ability.New.List` / `Detail` | `confirmed-native` | Used for fishing ability discovery. |
| Legacy `Inspect.Ability.List` / `Detail` | `missing` | Not available in this client/addon context. |
| `Inspect.Buff.List` / `Detail` | `confirmed-native` | Track Fish buff detection works. |
| `Inspect.Item.List` / `Detail` | `confirmed-native` | Inventory/pole/bag probes work. |
| `Inspect.Unit.Lookup` / `Detail` / `Castbar` | `confirmed-native` | Player/castbar trace path works. |
| `Inspect.Cursor` | `missing` | No native cursor/fishable-hover signal found. |
| `Inspect.Interaction` | `missing` | No native interaction/fishable target signal found. |
| `Utility.Item.Slot.Inventory` / `Equipment` / `Parse` | `confirmed-native` | Slot and bag mapping work. |

## Ability/status probe result

Live status after instrumentation:

- `player=Atank Lv45 zone=Sanctum`
- `combat=false`
- `secure=false`
- `items=71`
- `bags=3`
- `knownSlots=68`
- `estFree=4`
- `pole=Beginner's Fishing Pole [inventory] slot=si02.009`
- `track fish buff detected: Track Fish`
- `abilityCandidates=2`
- `usableLureAbilities=0`
- `abilityScan=ok`

Earlier ability probe screenshots showed:

- `Flame Lure` present but `unusable=true`
- `Track Fish` present and usable

Decision: native ability discovery works, but it does not currently establish `bait_available=true` because the only lure-like ability is not usable.

## Bounded action probes

### Historical click/key/click sequence

Historical archived AutoIt sources use a click/key/click pattern: select water, press the rod action, then click the selected water point. One bounded probe used that historical pattern with slot `8`.

Probe:

- first click: client `(320,160)`
- key: `8`
- second click: client `(320,160)`
- exact HWND foreground gate: passed
- movement keys: none

Result:

- Live system error visible: `This area is not fishable`.
- `/autofish trace status` remained `castbar=false`, `line_cast=false`, `can_cast=false`, `confidence=0.45`, `free=4`.
- No fall into water was observed.

### Alternate water point probe

One follow-up bounded probe tried a visually deeper water point:

- first click: client `(250,115)`
- key: `8`
- second click: client `(250,115)`
- exact HWND foreground gate: passed
- movement keys: none

Result:

- No castbar appeared in +1s or +4s captures.
- `/autofish trace status` remained `castbar=false`, `line_cast=false`, `can_cast=false`, `confidence=0.45`, `free=4`.
- No fall into water was observed.

## Current signal matrix update

| Signal | Classification | Evidence / notes |
| --- | --- | --- |
| exact target identity | `confirmed-live` | PID `89748`, HWND `0x2CD0D30`, title `RIFT`, foreground and responding. |
| command delivery | `confirmed-visual / verifier-unmapped` | AutoFish chat output appears; RiftReader post helper still fails its unrelated verifier-file check for AutoFish commands. |
| player/in-game state | `confirmed-native` | `/autofish status` reports player/zone/combat/secure. |
| inventory/free slots | `confirmed-native` | `estFree=4`. |
| carried pole | `confirmed-native` | Beginner's Fishing Pole found in inventory. |
| usable lure/bait | `confirmed-native-missing` | No inventory bait/lure candidates; `Flame Lure` is present but unusable. |
| Track Fish | `confirmed-native` | Buff and ability present. |
| castbar state | `confirmed-native-idle` | Trace/status stay idle after probes. |
| fishable water point | `visible-needs-mapping` | Client `(320,160)` produced `This area is not fishable`; `(250,115)` also did not cast. |
| near-water native signal | `missing` | `Inspect.Cursor` and `Inspect.Interaction` are unavailable; mapper correctly keeps `near_water=false`. |
| safe pause behavior | `confirmed` | Observation remains `can_cast=false`, low confidence, no loop. |

## Decision

G3 remains valid and fail-closed. G4 manual one-cast tracing is still blocked, but the blocker is now narrower:

1. slot `8` reaches the client;
2. native castbar tracing works;
3. the current clicked water points are not proven fishable;
4. no native cursor/interaction API is available for fishable-hover detection.

The next milestone should not add an automation loop. The next smallest useful slice is a **fishable-point calibration gate**: let the operator manually hover/click a known fishable point or use a helper-side cursor/pixel fallback only to identify a valid water point, then run one bounded trace.

## Reacquisition and recovery update

Later reacquisition found the exact same target still alive, but the character appeared to be in/swimming at the waterline:

- Reacquire capture: `.autofish-live/reacquire-20260525-105429/g0-baseline.png`
- Target unchanged: PID `89748`, HWND `0x2CD0D30`
- Foreground recovery gate: passed

Recovery input was bounded and directed away from the water:

- `S` held for `1800ms`
- `Space` held for `250ms`
- no loop and no repeated movement sequence

Recovery succeeded visually:

- Recovery capture: `.autofish-live/recovery-$(Get-Date -Format yyyyMMdd-HHmmss)/after-recover-1/g0-baseline.png`
- Character is back on the shore/edge, facing water.

Note: the recovery artifact folder name contains the literal PowerShell expression because the ad hoc command used single quotes. The artifact itself is still valid and ignored by git under `.autofish-live/`.

## Repo support added after recovery

Added `scripts/invoke-live-fishable-point-probe.ps1` to make the next fishable-point tests repeatable without overbuilding a loop.

The script:

- runs exact target preflight/focus/capture,
- validates PID/HWND and client coordinate bounds,
- optionally clicks the candidate client point,
- presses the configured fishing key once,
- optionally clicks the same point again,
- captures +1s and +4s follow-ups,
- writes a JSON summary,
- supports `-DryRun` to validate target and coordinate bounds without clicking or pressing the fishing key,
- never sends movement,
- never loops.

Dry-run a candidate point first:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\invoke-live-fishable-point-probe.ps1 `
  -TargetProcessId 89748 `
  -TargetWindowHandle 0x2CD0D30 `
  -ClientX 250 `
  -ClientY 115 `
  -DryRun
```

Probe a calibrated point:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\invoke-live-fishable-point-probe.ps1 `
  -TargetProcessId 89748 `
  -TargetWindowHandle 0x2CD0D30 `
  -ClientX 250 `
  -ClientY 115
```

Dry-run verification:

- `-DryRun` was executed against PID `89748` / HWND `0x2CD0D30` at client `(250,115)`.
- Summary confirmed `sendsMovement=false`, `sendsLoop=false`, `sendsFishingKeyOnce=false`, and `clickCount=0`.
- The script resolved the point to screen `(308,137)` and captured follow-ups without moving or acting.
- Follow-up capture showed the character still recovered on shore:
  - `.autofish-live/fishable-dryrun-$(Get-Date -Format yyyyMMdd-HHmmss)/after-4s/g0-baseline.png`

Prototype runner added:

- `scripts/start-live-fishing-prototype.ps1`
- Performs the practical bounded sequence: select calibrated point, press fishing key, confirm point, wait, pull/loot click.
- Requires exact PID/HWND and client coordinate.
- Supports `-DryRun`, `-MaxCasts`, `-CastWaitSeconds`, `-PullClicks`, `-CaptureEachCast`, and an emergency stop file.
- Sends no movement.

Prototype runner live attempts:

- Dry-run at `(250,115)` passed with exact PID/HWND and no input:
  - `.autofish-live/prototype-dryrun-20260525-123330/final/g0-baseline.png`
- One key-driven cast attempt at `(250,115)` ran cleanly but did not visibly cast:
  - `.autofish-live/prototype-keyclick-onecast-20260525-123829/final/g0-baseline.png`
- Switched real keypresses to the proven RiftReader `post-rift-key.ps1` helper; one helper-key attempt still did not visibly cast:
  - `.autofish-live/prototype-helperkey-onecast-20260525-124132/final/g0-baseline.png`
- Added direct action-slot support and tried visible rod/action slots:
  - action `(400,335)` + water `(250,115)`: no visible cast
  - action `(400,335)` + water/school `(185,110)`: no visible cast
  - action `(310,335)` + water/school `(185,110)`: no visible cast
  - upper-row action `(315,307)` + water/school `(185,110)`: no visible cast
- A one-action arm check on `(400,335)` with no water click did not reveal an armed targeting state in the capture.

Current practical conclusion:

- The prototype runner is usable and bounded.
- The click/key infrastructure is no longer the main unknown.
- The current blocker is identifying the correct live action surface for starting fishing: the visible rod/key assumptions did not arm a cast.
- `/autofish apis` was added to inspect live API surfaces. It showed `Command.Ability` has entries but `Command.Item` is unavailable/empty in this addon context, so direct item-use via addon is not currently proven.

## Operator-confirmed cast-start mechanic update

Later operator-provided in-game screenshots corrected the action model and supersede the earlier "slot/key assumptions did not arm a cast" conclusion.

Screenshots:

- Yellow placement circle after pressing `8`: `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_134047.jpg`
- Fishing pole animation / line cast after left-click: `C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-05-25_134759.jpg`

Corrected mechanic:

1. Put the cursor over a valid fishable water point.
2. Press/release actionbar 1 key `8`.
3. A yellow placement circle appears immediately at the cursor if the cursor is over an eligible water spot.
4. Left-click that placement point.
5. The character starts the fishing pole animation and a fishing line extends from the pole toward the placement point.

New evidence-based conclusion:

- Key `8` is confirmed working.
- Valid cursor position before pressing `8` is required.
- Left-click after the yellow placement circle is the cast-confirm action.
- The next script shape should be `hover calibrated point -> press 8 -> left-click same point -> wait/observe`, not direct action-slot experiments.
- Hotbar/action-slot alternatives should be paused unless the keybind changes.

Next smallest implementation slice:

- Add a `HoverBeforeKey`-style mode, or equivalent cursor pre-position step, to `scripts/start-live-fishing-prototype.ps1`.
- Run one bounded dry-run and then one real `MaxCasts=1` test at the calibrated water point.
- Keep `PullClicks=0` until the scripted cast start is reproduced and captured.
