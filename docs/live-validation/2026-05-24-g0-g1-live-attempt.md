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
