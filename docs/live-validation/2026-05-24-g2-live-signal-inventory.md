# AutoFish Live Validation - 2026-05-24 G2 Signal Inventory

## Summary

G2 signal inventory was run against the same live target after G1 passed. Exact-HWND command posting delivered read-only slash commands, but the RiftReader post helper still reports verifier-file failures for AutoFish slash commands because it watches `ReaderBridgeExport.lua`. Visual captures confirm AutoFish command output appeared in chat.

Read-only G2 exposed a real AutoFish estimator bug: `/autofish bags` showed four free bag slots, while `/autofish status` reported `estFree=0` because the estimator subtracted all inventory-scan entries from known bag slots. The addon was patched to sum per-bag `freeSlots`, deployed, and reloaded. Status then reported `estFree=4`.

Slot `8` was pressed exactly once after the estimator fix and fresh preflight. No castbar or fishing state transition was visible in follow-up captures. A pre-slot chat line showed `There are no fishes here`, but that line existed before the recorded slot-8 keypress, so it is not attributed to the probe.

## Target

- Process: `rift_x64`
- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Process start: `2026-05-24T13:20:04.8251137-04:00`
- Foreground/focus preflight: passed

## Artifacts

Run root:

- `.autofish-live/g2-autonomous-20260524-141852/`

Captures:

- Preflight: `.autofish-live/g2-autonomous-20260524-141852/preflight/g0-baseline.png`
- After `/autofish bags`: `.autofish-live/g2-autonomous-20260524-141852/after-bags/g0-baseline.png`
- After `/autofish inventory`: `.autofish-live/g2-autonomous-20260524-141852/after-inventory/g0-baseline.png`
- After `/autofish pole`: `.autofish-live/g2-autonomous-20260524-141852/after-pole/g0-baseline.png`
- After `/autofish status`: `.autofish-live/g2-autonomous-20260524-141852/after-status/g0-baseline.png`
- After estimator fix `/autofish status`: `.autofish-live/g2-autonomous-20260524-141852/after-status-estfree-fix/g0-baseline.png`
- Before slot `8`: `.autofish-live/g2-autonomous-20260524-141852/pre-slot8/g0-baseline.png`
- After slot `8` +0.6s: `.autofish-live/g2-autonomous-20260524-141852/after-slot8-0s/g0-baseline.png`
- After slot `8` +3.6s: `.autofish-live/g2-autonomous-20260524-141852/after-slot8-3s/g0-baseline.png`
- After post-slot `/autofish status`: `.autofish-live/g2-autonomous-20260524-141852/after-status-post-slot8/g0-baseline.png`

Command logs:

- `.autofish-live/g2-autonomous-20260524-141852/post-bags.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-inventory.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-pole.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-status.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-reload-after-estfree-fix.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-slot8.log`
- `.autofish-live/g2-autonomous-20260524-141852/post-status-after-slot8.log`

## Signal Matrix

| Signal | Classification | Evidence / notes |
| --- | --- | --- |
| player available | `confirmed-native` | `/autofish status` output shows `player=Atank Lv45 zone=Sanctum`. |
| in game | `confirmed-native` | Player state, visible world, and command responses from live client. |
| secure/combat state | `confirmed-native` | `/autofish status` shows `combat=false secure=false`. |
| bag/free-slot state | `confirmed-native` | `/autofish bags` output lists three bags with `free=0`, `free=0`, and `free=4`; patched `/autofish status` shows `bags=3 knownSlots=68 estFree=4`. |
| inventory full | `confirmed-native-false` | Corrected live signal shows four free bag slots. |
| pole carried | `confirmed-native` | `/autofish status` and `/autofish pole` show `Beginner's Fishing Pole [inventory]`. |
| pole equipped | `missing/needs-mapping` | Status reports pole in inventory, not equipped. Slot `8` has not been probed. |
| bait/lure candidates | `confirmed-native-missing` | `/autofish inventory` reports no bait/lure candidates matched the current inventory scan. |
| Track Fish buff | `confirmed-native` | `/autofish status` shows `track fish buff detected: Track Fish`; visual UI buff is also present. |
| castbar state | `confirmed-native-idle` | `/autofish status` does not show an active castbar; PlayerCoords overlay shows cast idle. |
| slot `8` effect | `visible-needs-mapping` | One foreground-gated `8` keypress was sent to exact HWND. No new castbar/fishing transition was visible in +0.6s or +3.6s captures. |
| Lua/runtime errors | `not observed` | No visible Lua error in captures. |
| command delivery | `confirmed-visual / verifier-unmapped` | Commands visibly reached chat/addon; post helper verifier failed because it watches `ReaderBridgeExport.lua`, not AutoFish chat output. |

## Fix applied during G2

- `AutoFishLive` now estimates free inventory by summing per-bag `freeSlots` from `collectBagSummaries()`.
- Added `knownUsedSlots` to the inventory snapshot for future diagnostics.
- Deployed patched addon to both local and OneDrive Rift addon folders.
- `/reloadui` posted successfully and updated `AutoFish.lua` SavedVariables at `2026-05-24T18:22:49.8835328Z`.

## Decision

G2 completed the read-only signal inventory and the single slot-8 probe. Live native signals are now sufficient for player state, combat/secure state, bag/free-slot state, carried pole, Track Fish, and idle castbar. The remaining blocker is **action mapping / fishable-location proof**: the slot `8` probe did not produce a confirmed cast transition, and a pre-existing system message indicated `There are no fishes here`.

## Next Gate

Do not start a loop. Before G4 one-cast tracing, resolve action/fishable-location mapping:

1. Confirm whether action bar slot `8` is still the intended fishing action after `/reloadui`.
2. Confirm the character is at a fishable water edge, not merely facing water.
3. Rerun one operator-gated slot `8` probe or manually click the fishing action once.
4. Capture `/autofish status` during/after the attempt and look for castbar or other native state changes.

Only after a cast transition is visible should G4 manual one-cast state tracing continue.
