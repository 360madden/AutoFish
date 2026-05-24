# AutoFish Addon Probe Plan

## Status

This document describes the **prepared but not yet executed** in-game addon diagnostics work for `C:\RIFT MODDING\AutoFish`.

Current intent:

- continue building and documenting the live-addon surface **offline**,
- avoid additional live Rift testing until explicitly resumed,
- keep the next in-game session focused on narrow signal validation rather than real fishing automation.

## Prepared addon files

The repository now contains:

- `C:\RIFT MODDING\AutoFish\lua\AutoFish\RiftAddon.toc`
- `C:\RIFT MODDING\AutoFish\lua\AutoFish\Main.lua`
- `C:\RIFT MODDING\AutoFish\scripts\deploy-addon.ps1`

These files provide a live-loadable shell for diagnostics only. They are not yet treated as a completed fishing implementation.

## Prepared diagnostics scope

When live testing resumes, the addon is prepared to probe:

- addon startup/loading,
- player availability,
- player zone and location text,
- secure/combat state,
- castbar visibility,
- `Track Fish` buff presence,
- equipped or carried fishing-pole candidates,
- bag container discovery,
- rough inventory/free-slot estimates,
- bait/lure item candidates.

## Slash commands already documented in code

The prepared addon shell exposes:

- `/autofish status`
- `/autofish bags`
- `/autofish inventory`
- `/autofish pole`
- `/autofish snapshot`
- `/autofish help`

These commands are intended for signal discovery and validation only.

## What is still intentionally deferred

The following are **not** considered complete yet:

- real water/fishable-state detection,
- real cast-to-bite-to-loot observation mapping,
- confirmed fishing-pole slot identification against live item data,
- confirmed bag/free-slot math against a real character inventory,
- real fishing execution,
- real bridge transport to the .NET helper,
- reconnect/sync behavior with a live helper session.

## Offline validation completed so far

The prepared addon shell has been validated only at the offline level:

- Lua syntax validation for `Main.lua`,
- repository-side deployment script creation,
- repository-side documentation updates,
- deployment copy into detected Rift addon folders.

This is **not** equivalent to in-game verification.

## Recommended next live session scope

When live work resumes, keep the first pass narrow:

1. confirm addon startup,
2. confirm slash command registration,
3. capture pole candidate output,
4. capture bag summary output,
5. capture inventory candidate output,
6. confirm whether `Track Fish` appears as a detectable buff,
7. only then start mapping cast/water/fishing observations.

## Guardrail for future work

Do not treat the addon shell as “live-complete” until:

- command output is verified against a real character,
- pole and bag detection are confirmed against real inventory data,
- observation fields can be fed into `AutoFishAddon:onObservation`,
- and the resulting behavior remains fail-safe when signals are missing or ambiguous.
