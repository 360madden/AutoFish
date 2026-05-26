# Facing delta calibration

Date: 2026-05-26

## Goal

Establish an **operational facing estimate** for the player without claiming native Rift actor facing/yaw.

Rift's addon/world-state surfaces currently provide player coordinates, not actor-facing. A practical facing estimate can still be computed from:

```text
fresh position before movement
tiny confirmed forward movement pulse
fresh position after movement
normalized X/Y coordinate delta
```

The result is useful for choosing a forward screen-space fishability fan direction, but it is not exact native facing.

## Direct addon coordinate probe

Before relying on the helper-side ChromaLink bridge, the AutoFish addon can print its own current coordinates:

```text
/autofish coords
```

The command reads the same Rift unit detail fields used by the normal snapshot path:

```lua
Inspect.Unit.Lookup("player")
Inspect.Unit.Detail(playerUnit).coordX
Inspect.Unit.Detail(playerUnit).coordY
Inspect.Unit.Detail(playerUnit).coordZ
```

Use this for a visible chat/screenshot cross-check against ChromaLink `player.position`. If the addon printout and ChromaLink disagree, stop and classify the coordinate provider as blocked/stale before sending any movement pulse.

## AutoFish proof command

Dry-run first:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --dry-run
```

The dry-run:

- validates exact PID/HWND,
- queries ChromaLink read-only,
- requires fresh `player.position`,
- sends no movement,
- records whether the run is ready for a confirmed movement pulse.

Confirmed movement mode is intentionally gated:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --confirm-movement `
  --movement-key w `
  --hold-ms 120
```

The confirmed mode sends exactly one tiny movement-key pulse only after:

1. exact PID/HWND validation passes,
2. the target is foreground,
3. the target is not minimized,
4. ChromaLink returns fresh before-position,
5. `--hold-ms` is within the configured safety cap,
6. the movement key is not `-`.

## Output

When successful, the manifest records:

- before/after ChromaLink coordinate evidence,
- movement key and hold duration,
- X/Y/Z delta,
- X/Y distance,
- normalized world-space X/Y vector,
- math angle where `0 = +X`, `90 = +Y`,
- `isNativeActorFacing=false`.

The angle convention is deliberately mathematical. Do not call it north/east/west until the local world coordinate system is separately mapped.

## Current live status

Evidence:

- `.autofish-live/facing-delta-dryrun-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-facing-delta-latest/summary.md`
- `.autofish-live/signal-proof-decisions.json`

Result:

- Exact Rift PID/HWND validation passed for PID `89748`, HWND `0x2CD0D30`.
- Target was foreground, non-minimized, and `1920x1009`.
- ChromaLink timed out, so fresh before-position was unavailable.
- No movement was sent.
- Decision: `facingDelta = needs-more-evidence`.

## Next gate

Reload AutoFish and verify `/autofish coords` prints plausible coordinates. Then restore/start ChromaLink outside AutoFish and rerun:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink --require-fresh
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta --pid <pid> --hwnd <hwnd> --dry-run
```

Only after both are fresh should `--confirm-movement` be used.
