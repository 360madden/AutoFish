# AutoFish Live Validation - 2026-05-24 G3/G4 Observation and Trace Prep

## Summary

Implemented and live-tested the first fail-closed observation mapper for G3 and a bounded manual trace recorder for G4. No fishing loop was started. No movement input was sent during this pass, so the character did not fall into the water.

## Target

- Process: `rift_x64`
- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Process start: `2026-05-24T13:20:04.8251137-04:00`
- Foreground/focus preflight: passed

## Artifacts

Run root:

- `.autofish-live/g3g4-autonomous-20260524-144631/`

Captures:

- Preflight: `.autofish-live/g3g4-autonomous-20260524-144631/preflight/g0-baseline.png`
- Observation mapping: `.autofish-live/g3g4-autonomous-20260524-144631/after-observe/g0-baseline.png`
- Trace status: `.autofish-live/g3g4-autonomous-20260524-144631/after-trace-status/g0-baseline.png`
- Pre traced slot `8`: `.autofish-live/g3g4-autonomous-20260524-144631/pre-traced-slot8/g0-baseline.png`
- Post traced slot `8` status: `.autofish-live/g3g4-autonomous-20260524-144631/after-traced-slot8-status/g0-baseline.png`
- Trace stop: `.autofish-live/g3g4-autonomous-20260524-144631/after-trace-stop/g0-baseline.png`

## G3 - Observation Mapping

Added `/autofish observe` and `AutoFish_State.currentObservation` using the existing `rift-observation.schema.json` fields without a schema change.

Live output classified confirmed native signals into the observation contract while preserving fail-closed behavior:

- `in_game=true`
- `near_water=false`
- `inventory_full=false`
- `bait_available=false`
- `line_cast=false`
- `bobber_visible=false`
- `bite_detected=false`
- `loot_window_open=false`
- `can_cast=false`
- `confidence=0.45`

Important notes emitted live:

- no native bait/lure candidate matched the inventory scan
- near_water is not confirmed by native addon APIs yet

Decision:

- G3 mapper is implemented and live-visible.
- Missing/ambiguous fields produce low confidence and `can_cast=false`, so the state remains safe-paused for automation.

## G4 - Manual Trace Prep

Added `/autofish trace start|status|stop|clear`.

Trace samples are bounded and capture the key one-cast state fields visible from native APIs:

- player availability
- zone
- combat/secure state
- castbar active/ability
- mapped `line_cast`
- mapped `can_cast`
- confidence
- inventory free slots
- pole candidate
- Track Fish buff state

Live trace command output was visible after reload. The command-post helper still reports verifier-file failures for AutoFish commands because it watches `ReaderBridgeExport.lua`; visual chat output remains the proof path until AutoFish has a helper-visible verifier.

One traced slot `8` probe was run after exact target preflight. Result:

- `post-rift-key.ps1 -Key 8` reported `SUCCESS` through foreground-gated `SendInput`.
- `/autofish trace status` after the keypress reported trace active with samples recorded.
- Last trace status remained fail-closed: `castbar=false`, `line_cast=false`, `can_cast=false`, `confidence=0.45`, `free=4`.
- No visible fall into water occurred; no movement input was sent.

## Current blocker

G4 cannot proceed to a successful one-cast state trace until fishable-location/action mapping is resolved. Traced slot-8 probing did not produce a confirmed castbar transition, and the native observation mapper correctly reports `near_water=false` and `can_cast=false` because near-water/fishable status is not available from native APIs yet.

## Stop decision

Stopped before movement or any repeated action. The bounded trace was stopped after the probe. No fall-into-water event occurred during this pass.
