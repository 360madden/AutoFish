# Historical signal proof results - 2026-05-25

## Scope

This note records the first live historical-signal proof pass after adding the Python helper and `/autofish invproof` lane. The run used the current local Rift client only and did not port, execute, or depend on old public bot scripts.

## Target and safety

- Rift PID: `89748`
- Rift HWND: `0x2CD0D30`
- Calibrated fishable client point: `(167,175)`
- Fishing key: `8`
- No movement input was sent.
- No unattended loop was run.
- The local `-` key was not used.

## Sequential result

The strict Top 20 lane reached step 20, but two steps remain blocked/not promoted:

- Step 13: inventory deltas were not clear.
- Step 17: `/log` proof was blocked because no current enabled Rift log path is known.

## Inventory proof

Evidence:

- `.autofish-live/step10-one-attempt-20260525-180422/fishing-prototype-summary.json`
- `.autofish-live/invproof-before-20260525-172008/invproof-before-postmessage.png`
- `.autofish-live/invproof-after-20260525-180727/invproof-after-postmessage.png`
- `.autofish-live/invproof-diff-20260525-180858/invproof-diff.png`
- `.autofish-live/signal-proof-decisions.json`

Result:

- `/autofish invproof before` captured a baseline inventory snapshot.
- One bounded cast/catch/loot attempt was run at `(167,175)`.
- `/autofish invproof after` captured a post-attempt snapshot.
- `/autofish invproof diff` reported no item quantity changes.

Reviewed decision:

- `inventory`: `needs-more-evidence`

Interpretation:

The run produced game/chat feedback, but native inventory quantity deltas did not prove loot. Inventory proof must not be promoted until a visibly successful catch/loot produces repeatable item or raw slot deltas.

Follow-up code gap found:

The first diff only reported aggregate quantity changes. `lua/AutoFish/Main.lua` now adds raw slot-level diff reporting so a later run can distinguish no quantity change from slot add/remove/change evidence.

Follow-up smoke evidence:

- `.autofish-live/rawslot-diff-smoke-20260525-184005/rawslot-diff-smoke.png`
- `.autofish-live/rawslot-diff-smoke-20260525-184005/rawslot-diff-smoke-chat-crop-5x.png`

Result: the saved before/after proof replayed with the new raw-slot branch and reported `no item quantity or raw slot changes detected`.

## API discovery follow-up

The next addon-side evidence lane is read-only API discovery, not assumptions about historical bots. `/autofish api`, `/autofish apis`, and `/autofish events` now expose inventory, chat, cursor/interaction, and candidate progression namespaces (`Skill`, `Currency`, `Experience`, `Profession`, `Crafting`) when the local Rift API makes them visible.

This only proves namespace/key availability. A namespace must still produce useful live values or events during a manual fishing attempt before it can be promoted as a catch, loot, skill-up, or currency signal.

## Reticle and cursor proof

Evidence:

- `.autofish-live/signal-proof-reticle-20260525-181558/manifest.json`
- `.autofish-live/signal-proof-reticle-20260525-181656/manifest.json`
- `.autofish-live/signal-proof-reticle-20260525-181656/reticle-proof-contact-sheet.jpg`
- `.autofish-live/post-reticle-proof-full-20260525-182110/post-reticle-proof-full.png`

Result:

- Dry-run reticle proof passed with exact PID/HWND and no input.
- One bounded reticle proof ran with `--confirm-input --watch-seconds 18`.
- Cursor handles changed across the run:
  - baseline: `0x10003`
  - after hover: `0x630ED0`
  - after key/click/watch: `0x39D40FA9`
- Heuristic crop colors included `blueCyan`, `green`, and `unknown`.

Reviewed status:

- Cursor-handle changes are useful evidence.
- Pixel/reticle color classification remains `needs-more-evidence` because the crop was contaminated by UI/chat overlap.
- Reticle/cursor should remain a fallback candidate until repeated clean crops distinguish valid reticle, cast-start, bite-ready, and invalid states.

## `/log` proof

Result:

- Blocked. No current enabled Rift log path was found under the checked Rift document/install paths.

Classification:

- `/log`: blocked pending known enabled log path/config.

## Layout proof

Evidence:

- `.autofish-live/signal-proof-layout-20260525-182758/manifest.json`

Result:

- Captured full client, hotbar, right bags, and chat regions.

Classification:

- Fixed layout remains fallback-only/profile-candidate evidence. Do not promote fixed bag/hotbar assumptions while native inventory proof is still unresolved.

## Next useful live step

Reload the latest deployed addon if it has not already been reloaded after the API-discovery patch, then run the read-only API probes:

```text
/autofish api
/autofish apis
/autofish events
```

After that, run a new manual catch cycle with visible catch/loot confirmation:

1. `/autofish invproof before`
2. one visibly successful manual catch/loot
3. `/autofish invproof after`
4. `/autofish invproof diff`

The new expected diagnostic is either:

- `no item quantity or raw slot changes detected`, or
- `raw slot changes detected` with per-slot add/remove/change lines.
