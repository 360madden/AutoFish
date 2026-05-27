# Profile Authoring Guide

## Purpose

Fishing profiles let the helper and addon share leveling-oriented behavior without rewriting code.

## Fields

- `id` - stable lowercase/hyphen identifier.
- `displayName` - user-facing name in the helper.
- `zoneName` - intended fishing area or route.
- `targetSkill` - currently expected to be `fishing`.
- `enabledSkills` - one or more relevant skills such as `fishing`, `survival`, or `cooking`.
- `baitName` - optional bait label.
- `notes` - operator guidance.
- `pacing` - reaction floor/ceiling plus bite/loot timeouts.
- `thresholds` - rebait, maintenance, and recovery cutoffs.
- `guardrails` - local safety switches.

## Rules

- Profile ids must be unique.
- `reactionFloorMs` must be less than or equal to `reactionCeilingMs`.
- Threshold values must be non-negative.
- Keep notes short and operational.

## Validation

Run:

```powershell
python scripts/run_local_checks.py --skip-lua
```

## Python helper usage

The Python helper can use a profile id or JSON path for runtime pacing defaults:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast `
  --pid <pid> `
  --hwnd <hwnd> `
  --x <fishable-client-x> `
  --y <fishable-client-y> `
  --profile starter-pond `
  --dry-run
```

For one-cast and bounded-session proofs:

- `pacing.biteTimeoutMs` becomes the default `--cast-wait-seconds`.
- `pacing.lootTimeoutMs` becomes the default `--post-pull-delay-ms`.
- Explicit CLI values always override profile pacing.
- The selected profile and applied defaults are written into the proof manifest.
