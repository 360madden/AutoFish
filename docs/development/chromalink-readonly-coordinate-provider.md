# ChromaLink read-only coordinate provider

Date: 2026-05-26

## Decision

AutoFish may use ChromaLink as a **read-only coordinate and telemetry provider**.

AutoFish must not modify ChromaLink from this repo. ChromaLink remains provider-owned; AutoFish only consumes published local surfaces and records evidence.

## Confirmed coordinate source

The local ChromaLink addon gets player coordinates from Rift's in-game Lua API:

```lua
local player = Inspect.Unit.Detail("player")
local x = player and player.coordX
local y = player and player.coordY
local z = player and player.coordZ
```

Local source evidence:

- `C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\ChromaLink\Core\Gather.lua`
- `SafeUnitDetail()` wraps `Inspect.Unit.Detail` with `pcall`.
- `BuildPlayerPositionSnapshot()` reads `coordX`, `coordY`, and `coordZ`.

This confirms coordinates only. It does not prove that Rift exposes actor facing/yaw.

## Published read-only consumer surface

Use ChromaLink's local HTTP bridge when it is running:

```text
http://127.0.0.1:7337/health
http://127.0.0.1:7337/ready
http://127.0.0.1:7337/api/v1/riftreader/world-state
```

The coordinate gate is intentionally stricter than endpoint reachability:

1. `/health` must be reachable and fresh.
2. `/api/v1/riftreader/world-state` must be reachable.
3. world-state must report `ok=true`, `ready=true`, `fresh=true`, and `stale!=true`.
4. `navigation.playerPositionAvailable` must be `true`.
5. `player.position.x/y/z` must be present.
6. `player.position.fresh` must be `true`.

If any gate fails, classify AutoFish as provider/setup blocked for coordinates, not as a fishing, movement, or fishability failure.

## AutoFish proof command

AutoFish now has a read-only proof command:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink `
  --wait-seconds 2 `
  --output-root .autofish-live\chromalink-world-state-latest
```

It sends no game input and does not modify ChromaLink. It only performs HTTP GET requests against the published local bridge and writes a `chromalinkWorldState` manifest.

Use `--require-fresh` only when a script should fail closed unless fresh coordinates are available:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink --require-fresh
```

## Current live result

The first AutoFish-side proof run timed out against the local ChromaLink bridge:

- evidence: `.autofish-live/chromalink-world-state-latest/manifest.json`
- classification: `bridge-down-or-unreachable`
- decision: `chromalinkWorldState = needs-more-evidence`

No coordinates were promoted. The next live step is to restore or start the ChromaLink provider outside AutoFish, then rerun the read-only proof command.

## Facing/yaw boundary

The current ChromaLink world-state contract can provide player coordinates when fresh, but it does not provide heading, facing, yaw, route planning, or movement control.

Future micro-step facing inference remains blocked until all of the following are true:

1. ChromaLink provides fresh before/after player coordinates.
2. A movement calibration command exists with explicit operator confirmation.
3. The movement pulse is tiny and bounded.
4. AutoFish records before/after coordinates and rejects stale data.
5. The result is labeled computed/operational facing, not native Rift actor facing.
