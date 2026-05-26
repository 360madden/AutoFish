# AutoFish Python Helper

This folder is the Python-first home for external AutoFish helper/runtime automation.

Run helper-only smoke checks from the repo root:

```powershell
.\scripts\run-python-helper-checks.ps1
```

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

Focus behavior must preserve window size. Live-input Python helper commands now refuse to restore a minimized Rift window; restore/maximize Rift manually first so Windows does not snap back to a tiny saved restored size. AutoFish preflight only calls Windows `SW_RESTORE` when the Rift window is minimized; it should not de-maximize or shrink a normal/maximized Rift window before proof capture.

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
- tightened color suggestions plus legacy suggestion/review flags,
- the exact bounded actions sent.

Color suggestions are conservative. Red/orange invalid reticles can include yellow pixels, and water/highlight backgrounds can inflate blue/cyan counts. The manifest keeps `legacySuggestedReticleColor`, `suggestionReason`, and `manualReviewRequired` so suspected blue/cyan/background cases are reviewed visually instead of silently promoted.

No live command should send input without an explicit target PID/HWND and either `--dry-run` or `--confirm-input`. The helper refuses to send `-` by default because this local setup binds it to `reloadui`.

## Bounded one-cast proof

Use `one-cast` after the reticle proof has identified a current fishable client coordinate. This is the Python-native replacement path for the older PowerShell prototype script.

To avoid long repeated command lines, create a local session plan after confirming current PID/HWND and fishable client X/Y:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan create `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --x <FISHABLE_CLIENT_X> `
  --y <FISHABLE_CLIENT_Y> `
  --profile starter-pond `
  --validate-target `
  --output .autofish-live\session-plan-latest.json
```

Session plans are local proof artifacts. Do not reuse one after Rift restarts, the window is resized, or the fishable coordinate changes. When a plan has `targetValidation.clientWidth/clientHeight` from `--validate-target` or a fishability-fan manifest, `session-plan gates`, `one-cast`, and `bounded-session` now compare that size with the current Rift target before allowing plan-backed live input. Live-input commands also recompute client-to-screen coordinates immediately before each cursor move/click, so a same-size window move does not reuse stale screen coordinates.

By default, a session plan includes `.autofish-live\STOP.txt` as the emergency stop file. Create that file to stop before the next bounded action or during a wait period; delete it before a later supervised rerun.

To print the exact next commands from a plan:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan runbook `
  --path .autofish-live\session-plan-latest.json
```

Dry-run first:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast `
  --session-plan .autofish-live\session-plan-latest.json `
  --dry-run
```

Then, only while supervised and with Rift already restored/maximized and foregroundable:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast `
  --session-plan .autofish-live\session-plan-latest.json `
  --cast-wait-seconds 18 `
  --pull-clicks 1 `
  --confirm-input
```

The command performs at most one cast attempt. Confirmed mode can move the cursor, press the fishing key once, left-click the calibrated cast point, wait, and perform the configured bounded pull/loot clicks. It sends no movement and no loop. The default stop file is `.autofish-live\STOP.txt`; if that file or an explicit `--stop-file <path>` exists before or during the wait, the command aborts before the next action. Live-input mode refuses minimized Rift windows so it does not restore the client to a tiny saved size.

When `--profile <id-or-json-path>` is supplied, the helper records the profile in the manifest and uses profile pacing defaults unless the CLI overrides them:

- `pacing.biteTimeoutMs` -> `--cast-wait-seconds`
- `pacing.lootTimeoutMs` -> `--post-pull-delay-ms`

## Supervised bounded session proof

Use `bounded-session` only after the current coordinate has a reviewed one-cast proof. It repeats the same fixed-timing sequence with an explicit cast cap and stop file support. This is still a supervised proof command, not an unattended runtime loop.

Dry-run:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof bounded-session `
  --session-plan .autofish-live\session-plan-latest.json `
  --max-casts 3 `
  --dry-run
```

Confirmed supervised proof:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof bounded-session `
  --session-plan .autofish-live\session-plan-latest.json `
  --max-casts 3 `
  --cast-wait-seconds 18 `
  --pull-clicks 1 `
  --confirm-input
```

Confirmed mode refuses minimized Rift windows, sends no movement, and stops before the next action if `.autofish-live\STOP.txt` or an explicit `--stop-file <path>` exists. Use `--capture-each-cast` when visual proof for each phase is more important than minimizing captures.

Confirmed bounded sessions also require a reviewed `oneCast` decision in `.autofish-live\signal-proof-decisions.json`:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof decide `
  --signal oneCast `
  --decision fallback-only `
  --reason "Reviewed one-cast proof at current coordinate is acceptable for a small supervised bounded session." `
  --evidence .autofish-live\<one-cast-proof>\manifest.json `
  --session-plan .autofish-live\session-plan-latest.json
```

Accepted decisions are `promote` or `fallback-only`. Use `--allow-unreviewed-one-cast` only when intentionally bypassing that gate for a supervised experiment.

## Fishability fan planning

Prefer proving **fishability** over visually detecting water. The helper can plan a screen-space fan of candidate points without sending input:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --origin-x <PLAYER_OR_SCREEN_ANCHOR_X> `
  --origin-y <PLAYER_OR_SCREEN_ANCHOR_Y> `
  --forward-x <OPERATOR_FORWARD_POINT_X> `
  --forward-y <OPERATOR_FORWARD_POINT_Y> `
  --dry-run
```

If Rift is minimized and the live client rect reports `0x0`, keep the helper read-only and avoid forced restore by doing geometry-only planning with the last verified client size:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --origin-x <PLAYER_OR_SCREEN_ANCHOR_X> `
  --origin-y <PLAYER_OR_SCREEN_ANCHOR_Y> `
  --forward-x <OPERATOR_FORWARD_POINT_X> `
  --forward-y <OPERATOR_FORWARD_POINT_Y> `
  --client-width <LAST_VERIFIED_CLIENT_WIDTH> `
  --client-height <LAST_VERIFIED_CLIENT_HEIGHT> `
  --no-capture-crops `
  --dry-run
```

This writes a `fishabilityFan` manifest with candidate client points, optional no-input crops, and per-candidate suggested reticle commands. It does not press the fishing key, click, move, or classify water. Use the suggested dry-run command first, then the suggested `--skip-click --cancel-after-key` command only while supervised to capture a candidate reticle without sending a left click. Future confirmed probing must classify points from game feedback such as castbar start, chat/system errors, item events, inventory deltas, or progression events. Coordinate-backed micro-step facing requires a reliable before/after player coordinate source; use `/autofish coords` as the direct addon-side cross-check and ChromaLink as the helper-side bridge when fresh.

To print those candidate commands as a sequential runbook:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan-runbook `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json
```

After one candidate is reviewed as fishable from reticle/game feedback, turn it into a local one-cast session plan:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan from-fan `
  --manifest .autofish-live\<fishability-fan-proof>\manifest.json `
  --candidate-index <index> `
  --profile starter-pond `
  --output .autofish-live\session-plan-latest.json
```

Then print the session-plan runbook and use its scoped `signal-proof decide --signal fishabilityCandidate --session-plan <plan>` command before confirmed one-cast input:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan runbook `
  --path .autofish-live\session-plan-latest.json
```

At any point, print the current scoped gate status without sending input:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan gates `
  --path .autofish-live\session-plan-latest.json
```

Add `--require stop-file-clear`, `--require target-current`, `--require confirmed-one-cast`, or `--require confirmed-bounded-session` when a script should fail closed unless that gate is ready. For the practical pre-live bundles, use `--require ready-one-cast` before confirmed `one-cast` and `--require ready-bounded-session` before confirmed `bounded-session`; these compound checks include the stop-file and target-current gates plus the needed reviewed-decision gate.

The created plan still marks the fan candidate as planning-only source evidence; confirmed one-cast input from that plan requires a reviewed `fishabilityCandidate` decision attached to that same session plan unless intentionally bypassed with `--allow-unreviewed-fan-candidate`. Run the generated session-plan dry-run before any confirmed one-cast proof.

## ChromaLink coordinate proof

ChromaLink can be used as a **read-only** coordinate provider when its local bridge is fresh. AutoFish must not modify ChromaLink from this repo.

Use the in-game addon probe as the direct source cross-check:

```text
/autofish coords
```

It prints the current player `coordX`, `coordY`, and `coordZ` values read from `Inspect.Unit.Detail`. Compare that visible addon output to the ChromaLink `player.position` values before trusting helper-side coordinate automation.

The helper can record that comparison as a read-only proof after you reload the addon and transcribe the visible `/autofish coords` line:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof coordinate-crosscheck `
  --addon-line "coords x=<x> y=<y> z=<z> playerUnit=<unit>" `
  --wait-seconds 2
```

Or pass the three numeric values directly:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof coordinate-crosscheck `
  --addon-x <x> --addon-y <y> --addon-z <z> `
  --require-match
```

This command sends no input. It queries ChromaLink read-only, compares the two coordinate sources within a configurable `--tolerance`, and writes a `coordinateCrosscheck` manifest.

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink `
  --wait-seconds 2 `
  --output-root .autofish-live\chromalink-world-state-latest
```

The command performs read-only HTTP GETs against:

- `http://127.0.0.1:7337/health`
- `http://127.0.0.1:7337/ready`
- `http://127.0.0.1:7337/api/v1/riftreader/world-state`

It sends no game input, no movement, no fishing key, and no mouse clicks. It classifies coordinates as usable only when ChromaLink reports fresh health/world-state, `navigation.playerPositionAvailable=true`, present `player.position.x/y/z`, and `player.position.fresh=true`.

Use `--require-fresh` for scripts that should fail closed unless fresh coordinates are available:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof chromalink --require-fresh
```

## Facing delta calibration

Use ChromaLink coordinates plus one tiny confirmed forward movement pulse to estimate **operational** player facing. This does not prove native Rift actor-facing/yaw.

Dry-run first:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --dry-run
```

Only after ChromaLink is fresh and the dry-run is ready, allow one bounded movement pulse:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-delta `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --confirm-movement `
  --movement-key w `
  --hold-ms 120
```

Confirmed mode requires exact PID/HWND, foreground target, non-minimized target, fresh ChromaLink before-position, and a movement hold within the safety cap. It sends no fishing key and no mouse clicks. The result is a normalized X/Y coordinate-delta vector plus a math angle; treat it as an operational facing hint only.

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
/autofish coords
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
