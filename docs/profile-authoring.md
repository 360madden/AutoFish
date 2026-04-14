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
.\scripts\validate-profiles.ps1
```
