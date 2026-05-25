# AutoFish Live Validation - 2026-05-24 G0/G1 Attempt

## Summary

Implemented the milestone process against the live client and stopped at G1 because slash command delivery/addon load proof is not yet reliable.

## G0 - Live Target Preflight

Status: **passed with caveat**

Read-only discovery found exactly one `rift_x64` client:

- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Process start: `2026-05-24T13:20:04.8251137-04:00`
- Responding: `true`
- Window rect: `20,16` to `676,415`
- Client rect: `28,47` to `668,407` (`640x360`)

The first helper focus call restored/captured the window but still reported `isForeground=false`. A stronger focus-only Win32 request then made the exact HWND foreground. No game input was sent before foreground was confirmed.

Baseline artifacts:

- `.autofish-live/20260524-implement-plan/g0-baseline.png`
- `.autofish-live/20260524-implement-plan/g0-focused-baseline.png`

Visual baseline confirmed the character was in-world, by water, and Track Fish appeared visible in the UI.

## G1 - AutoFish Addon Load Proof

Status: **blocked**

Attempted:

- `/autofish help` via RiftReader `post-rift-command.ps1`
- `/autofish status` via RiftReader `post-rift-command.ps1`
- `/reloadui` via the same command path with AutoFish SavedVariables as the verifier
- `/autofish help` via exact-foreground-gated `SendKeys`

Observed:

- `post-rift-command.ps1` reported no verification file update after `/autofish help`, `/autofish status`, and `/reloadui`.
- Captures did not visibly show AutoFish command output.
- The exact-foreground `SendKeys` attempt did not safely enter chat and triggered in-game UI/hotkey behavior instead; live input stopped immediately and one `Escape` was sent to close the accidental UI.
- `AutoFish.lua` SavedVariables files found under OneDrive are stale and did not update during this attempt.

G1 blocker classification:

- `slash-command-delivery-not-proven`
- `addon-load-not-proven-current-session`
- `savedvariables-not-updating`

## Stop decision

Per the milestone ladder, G2 was not attempted. Slot `8` was not pressed. No fishing automation loop was started.

## Next recommended slice

Fix G1 before any G2 work:

1. Establish a reliable chat/slash-command delivery method for the exact HWND, or use a manual operator-entered command path.
2. Confirm AutoFish appears enabled in the Rift addon list after `/reloadui`.
3. Capture visible `/autofish help` output or a fresh `AutoFish_State.current` write from the current character.
4. Only after G1 passes, continue to `/autofish bags`, `/autofish inventory`, `/autofish pole`, and the single slot `8` probe.

## G1 Fix Pass - 2026-05-24 14:05 EDT

Status: **patched and deployed; live proof still blocked on command delivery/reload**

Root cause addressed in code:

- Switched event registration to prefer `Command.Event.Attach(...)`, retaining the older `table.insert(...)` fallback.
- Changed slash, saved-variable, and addon-load handlers to tolerate Rift event callback signatures that include the event handle before command/addon arguments.
- Changed addon startup proof to attach to `Event.Addon.Load.End` when available, with the older startup event retained as a fallback.
- Updated `AutoFishLive.Refresh(...)` to keep `AutoFish_State` current on every refresh, not only at save time.

Deployment:

- `scripts/deploy-addon.ps1` copied the patched addon to:
  - `C:\Users\mrkoo\Documents\RIFT\Interface\Addons\AutoFish`
  - `C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\Addons\AutoFish`

Validation run:

- `dotnet build AutoFish.sln --configuration Release` passed.
- `dotnet run --project src/AutoFish.App/AutoFish.App.csproj --configuration Release --no-build -- --validate-profiles` passed for 3 profiles.
- `scripts/validate-profiles.ps1` passed for 3 profiles.
- `lua`, `luac`, and `luajit` are not installed in this environment, so Lua syntax validation was not run.

Live target reconfirmed after deployment:

- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Foreground: `true`
- Responding: `true`
- Capture: `.autofish-live/g1-fix-preflight/g0-baseline.png`

Safe reload attempt:

- Attempted `/reloadui` once via RiftReader `post-rift-command.ps1` with exact PID/HWND and foreground requirement.
- No `AutoFish.lua` SavedVariables update was observed.
- Follow-up target/capture remained exact-foreground and responding:
  - `.autofish-live/g1-fix-after-reload-attempt/g0-baseline.png`

Stop decision:

- G1 is **not passed** yet because there is still no visible `/autofish help` output and no fresh `AutoFish_State.current` write from the live character.
- No `SendKeys` fallback was retried because the previous exact-foreground SendKeys attempt caused unintended UI/hotkey behavior.
- Slot `8` was not pressed. G2 remains blocked until the operator manually confirms addon reload/load and slash-command response, or a safer command-delivery path is added.

## Operator Evidence - 2026-05-24 live chat screenshot

Status: **G1 partial pass; status proof still required**

The operator provided a live chat screenshot showing visible AutoFish slash-command output:

- `[AutoFish] Commands:`
- `/autofish status`
- `/autofish bags`
- `/autofish inventory`
- `/autofish pole`
- `/autofish snapshot`
- `/autofish help`

Evidence classification:

- Slash command responds: `confirmed-native`
- Addon loaded in the live client: `confirmed-native`
- Lua/runtime error visible in provided screenshot: `not observed`
- Player/in-game status signal: `not yet proven in screenshot`

Stop decision:

- G1 is no longer blocked on addon load or `/autofish help` registration.
- G1 should not be marked fully passed until `/autofish status` output is captured and shows live player/in-game state without Lua errors.
- G2 remains blocked until `/autofish status` is captured.

## Operator Evidence - 2026-05-24 `/autofish status` screenshot

Status: **G1 passed**

The operator provided a live chat screenshot showing `/autofish status` output from the patched addon.

Observed output excerpts:

- `[AutoFish] player=Atank Lv45 zone=Sanctum`
- `[AutoFish] combat=false secure=false items=71 bags=3 knownSlots=68 estFree=0`
- `[AutoFish] pole=Beginner's Fishing Pole [inventory] ...`
- `[AutoFish] track fish buff detected: Track Fish`

Evidence classification:

- Slash command responds: `confirmed-native`
- Addon loaded in the live client: `confirmed-native`
- Player/in-game state: `confirmed-native`
- Combat/secure state: `confirmed-native`
- Inventory summary: `confirmed-native`
- Pole candidate: `confirmed-native`
- Track Fish buff: `confirmed-native`
- Lua/runtime error visible in provided screenshot: `not observed`

Exit decision:

- G1 exit criteria are satisfied.
- Proceed to G2 signal inventory, starting with read-only slash commands only.
- Note: `estFree=0` may indicate full inventory or an inventory free-slot estimator issue; classify during G2 before any cast/loot action.
