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

For a single read-only operator health bundle before choosing the next command, run:

```powershell
python tools\autofish-helper-py\autofish_helper.py doctor `
  --proof-root .autofish-live `
  --decision-register .autofish-live\signal-proof-decisions.json `
  --session-plan .autofish-live\session-plan-latest.json
```

Top-level `doctor` sends no game input. It writes `doctor.json` and `doctor.md` under `.autofish-live\autofish-doctor-*`, combining proof-root health with session-plan health when the plan exists.

Add `--refresh-summary` when the same command should also refresh the standalone signal-proof review artifacts under `signal-proof-summary\summary.json` and `signal-proof-summary\summary.md` inside the doctor output folder:

```powershell
python tools\autofish-helper-py\autofish_helper.py doctor `
  --refresh-summary `
  --output-root .autofish-live\autofish-doctor-latest
```

For fail-closed scripts, repeat `--fail-on` with the conditions that should return exit code `1` after still writing the doctor artifacts:

```powershell
python tools\autofish-helper-py\autofish_helper.py doctor `
  --fail-on invalid-manifest `
  --fail-on weak-decision-evidence `
  --fail-on not-ready-one-cast
```

Use `--next-action-only` when a script or operator prompt needs just the first recommended action while still writing the full doctor artifacts:

```powershell
python tools\autofish-helper-py\autofish_helper.py doctor --next-action-only
```

## Bounded one-cast proof

Use `one-cast` after the reticle proof has identified a current fishable client coordinate. This is the Python-native replacement path for the older PowerShell prototype script.

Before creating or reusing a session plan, verify the exact target without focusing, restoring, capturing, or sending input:

```powershell
python tools\autofish-helper-py\autofish_helper.py target-snapshot `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --require-readable
```

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

Session plans are local proof artifacts. Do not reuse one after Rift restarts, the window is resized, the fishable coordinate changes, or the plan is stale. `session-plan gates`, plan-backed `one-cast`, and plan-backed `bounded-session` include a `planFresh`/age gate that defaults to a 240-minute maximum age; override with `--max-plan-age-minutes <minutes>` or use `<=0` only for intentional offline diagnostics. When a plan has `targetValidation.clientWidth/clientHeight` from `--validate-target` or a fishability-fan manifest, `session-plan gates`, `one-cast`, and `bounded-session` now compare that size with the current Rift target before allowing plan-backed live input. Live-input commands also recompute client-to-screen coordinates immediately before each cursor move/click, so a same-size window move does not reuse stale screen coordinates.

Plan-backed `one-cast` and `bounded-session` manifests expose a normalized `reviewGates` object so summaries can consistently report `planFresh`, `targetCurrent`, `fishabilityCandidate`, and `oneCast` gate status. Older top-level gate fields remain for compatibility.

By default, a session plan includes `.autofish-live\STOP.txt` as the emergency stop file. Use `session-plan stop-file create --path <plan>` to stop before the next bounded action or during a wait period, `session-plan stop-file clear --path <plan>` before a later supervised rerun, and `session-plan stop-file status --path <plan>` to inspect it without changing it.

To print the exact next commands from a plan:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan runbook `
  --path .autofish-live\session-plan-latest.json
```

To explain blocked readiness gates without sending input:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan explain `
  --path .autofish-live\session-plan-latest.json
```

To combine the readable explanation with a fail-closed exit code for scripts:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan preflight `
  --path .autofish-live\session-plan-latest.json `
  --require ready-one-cast
```

To print an ordered operator checklist from the current plan:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan checklist `
  --path .autofish-live\session-plan-latest.json
```

To write one read-only operator triage bundle with gate status, the checklist, and the next action:

```powershell
python tools\autofish-helper-py\autofish_helper.py session-plan doctor `
  --path .autofish-live\session-plan-latest.json `
  --proof-root .autofish-live `
  --decision-register .autofish-live\signal-proof-decisions.json
```

`session-plan doctor` sends no game input. It writes `doctor.json` and `doctor.md` under `.autofish-live\session-plan-doctor-*` unless `--output-root` is supplied.

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

The command performs at most one cast attempt. Confirmed mode can move the cursor, press the fishing key once, left-click the calibrated cast point, wait, and perform the configured bounded pull/loot clicks. It sends no movement and no loop. The default stop file is `.autofish-live\STOP.txt`; if that file or an explicit `--stop-file <path>` exists before or during the wait, the command aborts before the next action. Live-input mode refuses minimized Rift windows so it does not restore the client to a tiny saved size. After the fishing key, the helper captures the reticle crop before the confirm click and refuses to click if the heuristic reports an obvious red reticle. Use `--allow-red-reticle-click` only for an explicitly supervised diagnostic override.

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

Confirmed mode refuses minimized Rift windows, sends no movement, checks the after-key reticle crop before each confirm click, and stops before the next action if `.autofish-live\STOP.txt` or an explicit `--stop-file <path>` exists. Use `--capture-each-cast` when visual proof for each phase is more important than minimizing captures. Obvious red reticles abort before clicking unless `--allow-red-reticle-click` is supplied intentionally.

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

If you have a usable `facingDelta` manifest from `facing-delta` or `facing-from-coords`, attach it as audit context:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof fishability-fan `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --origin-x <PLAYER_OR_SCREEN_ANCHOR_X> `
  --origin-y <PLAYER_OR_SCREEN_ANCHOR_Y> `
  --forward-x <OPERATOR_FORWARD_POINT_X> `
  --forward-y <OPERATOR_FORWARD_POINT_Y> `
  --facing-manifest .autofish-live\<facing-proof>\manifest.json `
  --require-usable-facing `
  --dry-run
```

This does not convert world-coordinate facing into screen coordinates. The fan's candidate points still come from the operator-supplied screen-space origin and forward point; the facing evidence only records that the fan was planned with a reviewed operational-facing hint available.

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
  --require-usable-facing `
  --output .autofish-live\session-plan-latest.json
```

Use `--require-usable-facing` when the source fan was expected to carry a usable `facingDelta` audit trail. The session plan preserves that facing evidence under `source.facingEvidence` and includes it in the review scope token, but it still requires a reviewed `fishabilityCandidate` decision before confirmed one-cast input.

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

Use `session-plan explain --path .autofish-live\session-plan-latest.json` when the JSON gates are not enough; it prints a no-input operator summary, blocked reasons, and the next unblocked action. Use `session-plan preflight --require ready-one-cast` or `--require ready-bounded-session` when a script should print that same readable summary and fail closed if the requested readiness bundle is blocked.

Add `--require stop-file-clear`, `--require plan-fresh`, `--require target-current`, `--require target-foreground`, `--require client-readable`, `--require confirmed-one-cast`, or `--require confirmed-bounded-session` when a script should fail closed unless that gate is ready. For the practical pre-live bundles, use `--require ready-one-cast` before confirmed `one-cast` and `--require ready-bounded-session` before confirmed `bounded-session`; these compound checks include the stop-file, plan-age, target-current, foreground, readability, and needed reviewed-decision gates.

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

If ChromaLink is not fresh but `/autofish coords` is visible in chat, compute the same operational delta from two manually captured coordinate lines without helper movement or ChromaLink queries:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof facing-from-coords `
  --before-line "coords x=<x1> y=<y1> z=<z1> playerUnit=<unit>" `
  --after-line "coords x=<x2> y=<y2> z=<z2> playerUnit=<unit>"
```

Use this only after the operator deliberately collects the before coordinate, performs the intended tiny manual step, and collects the after coordinate. It still writes a `facingDelta` manifest, but marks the movement as operator-manual and `isNativeActorFacing=false`.

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

For a faster read-only health check of the current proof root and decision register, run:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof doctor `
  --proof-root .autofish-live `
  --decision-register .autofish-live\signal-proof-decisions.json
```

This writes `doctor.json` and `doctor.md` with invalid-manifest counts, failed review gates, red-reticle blocked-click counts, decision-evidence quality, latest proof by signal, and suggested next actions. It sends no game input.
