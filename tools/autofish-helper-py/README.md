# AutoFish Python Helper

This folder is the Python-first home for external AutoFish helper/runtime automation.

The Lua addon remains the in-game Rift addon layer. This helper is for same-PC desktop automation against the local Rift window:

- exact PID/HWND validation,
- screenshot/crop capture,
- cursor hover/move/click,
- keypress orchestration,
- bounded cast-start tests,
- future bite/pull/loot timing and visual detection.

## Window size and readability

Larger Rift windows are supported and preferred. The helper captures the actual client size reported by the exact HWND; it does not require `640x360`. Proof manifests include `clientWidth`, `clientHeight`, and a readability warning when the client is below `960x540`, because small screenshots can make addon/chat output illegible.

Use client-relative coordinates. If the Rift window is resized, rerun preflight/capture and recalibrate fishable X/Y before sending any reticle, click, or cast-start input.

Focus behavior must preserve window size. The Python helper and AutoFish preflight only call Windows `SW_RESTORE` when the Rift window is minimized; they should not de-maximize or shrink a normal/maximized Rift window before proof capture.

## Current priority: historical signal proof

Historical Rift fishing tools repeatedly used cursor changes, `/log`, pixels, audio, and fixed hotbar/bag assumptions. AutoFish treats those as stale until locally proven.

The first implemented proof harness is reticle/cursor evidence capture:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --x <FISHABLE_CLIENT_X> `
  --y <FISHABLE_CLIENT_Y> `
  --key 8 `
  --dry-run
```

After the dry run succeeds and the exact target/coordinate are confirmed, run one bounded live proof:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --x <FISHABLE_CLIENT_X> `
  --y <FISHABLE_CLIENT_Y> `
  --key 8 `
  --watch-seconds 18 `
  --watch-interval-ms 500 `
  --confirm-input
```

`--confirm-input` allows exactly one cursor move, one keypress, and one left-click. Optional `--watch-seconds` keeps capturing cursor/crop evidence after the click without sending more input. It writes a `manifest.json` plus BMP crops under `.autofish-live\signal-proof-reticle-*`.

For reticle color/state calibration where a cast should not be clicked yet, add `--skip-click` with `--confirm-input`. That still requires exact PID/HWND, moves the cursor, presses the fishing key once, captures `after-key`, and records any optional watch captures after the keypress, but sends no left click. Add `--cancel-after-key` to press Escape after the post-key captures and record `after-cancel`.

The manifest records:

- target PID/HWND/client size,
- foreground status,
- OS cursor handle/position per capture,
- cursor-centered BMP crops,
- rough red/yellow/blue-cyan/green color counts,
- the exact bounded actions sent.

No live command should send input without an explicit target PID/HWND and either `--dry-run` or `--confirm-input`. The helper refuses to send `-` by default because this local setup binds it to `reloadui`.

## Log proof harness

The `/log` family of historical signals is read-only and must prove current usefulness before runtime use:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof log `
  --log-path <RIFT_LOG_PATH> `
  --duration-seconds 30 `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND>
```

This starts at the current end of the file, records newly appended text into `appended-log.txt`, scans for fishing-related terms, and writes `manifest.json`. If no stable fishing text appears during manual casts, log parsing should stay retired or debug-only.

## Layout / fixed-coordinate proof harness

Fixed hotbar and bag assumptions are also read-only until proven stable. Capture the current client or specific regions before relying on slot coordinates:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof layout `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --full-client `
  --region hotbar:0,620,900,120 `
  --region bags:900,300,380,420
```

The command sends no input. By default it requires Rift to be foreground so the screenshot is not silently occluded. Use `--allow-not-foreground` only for diagnostics where occlusion is acceptable.

Use these captures to decide whether fixed actionbar/bag coordinates are repeatable enough for a profile field, fallback-only, or retired.

## Audio proof harness

Audio/splash detection is read-only but device-dependent. It records from the current Windows recording input, which may be a microphone rather than Rift/system audio unless Windows is configured with Stereo Mix or another loopback source.

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof audio `
  --seconds 20 `
  --label manual-cast `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND>
```

The command sends no input. It writes a WAV file and `manifest.json` with peak/RMS windows so a manual cast can be checked for a repeatable bite/splash cue. If the loudest windows do not align with the bite across multiple casts, audio stays fallback-only or retired.

## Inventory proof is Lua-native

Inventory deltas are better proven from the addon API than from fixed bag pixels. Use the in-game slash command:

```text
/autofish invproof before
<perform one manual cast/catch/loot attempt>
/autofish invproof after
/autofish invproof diff
```

This stores before/after snapshots in AutoFish saved state and prints item quantity deltas plus raw slot-level add/remove/change diagnostics. Use this before trusting any fixed bag coordinate fallback.

## Lua API discovery probes

Use these read-only commands in game before adding new addon-side signal assumptions:

```text
/autofish api
/autofish apicompact
/autofish apis
/autofish events
```

They list availability/table keys for inventory, chat, cursor/interaction, and candidate skill/currency/experience/profession/crafting namespaces. Use `/autofish apicompact` when the proof needs to fit in one screenshot. A discovered namespace is only a lead; promote it only after a live proof packet shows useful fishing evidence.

To capture those slash-command results as local evidence, use the bounded slash proof harness. Dry-run first:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof slash `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --command "/autofish apicompact" `
  --dry-run
```

Then, only after confirming exact PID/HWND and foreground target, run:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof slash `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --command "/autofish apicompact" `
  --confirm-input
```

This captures full-client BMP screenshots and writes a `manifest.json` under `.autofish-live\signal-proof-slash-*`. It sends no movement and no loop. By default it refuses non-`/autofish` commands and refuses command text containing `-` because that key triggers reloadui on this setup. Use `--default-api-probes` only when you intentionally want the verbose `/autofish api`, `/autofish apis`, and `/autofish events` sequence.

## Proof summary / review buckets

After collecting reticle, log, layout, audio, and inventory proof evidence, summarize generated manifests:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof summarize `
  --proof-root .autofish-live
```

This writes `summary.json` and `summary.md` with per-signal review buckets. The buckets are not final decisions; promotion still requires repeated live evidence and operator review.
