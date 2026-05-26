# Historical Signal Proof Lane

Date: 2026-05-25

## Decision

Historical Rift fishing automation signals are now a priority work lane, but only as **proof-first fallback candidates**.

The historical methods are useful because they repeatedly point to the same possible observations:

- cursor/pointer changes,
- `/log` or chat-log messages,
- pixel/color/image checks,
- audio amplitude or splash cues,
- fixed hotbar/bag assumptions.

They are also stale and brittle until proven against the current local Rift client. AutoFish should not build a runtime dependency on any of them until a local proof packet exists.

## Priority rule

Work these signals as a validation matrix, not as copied bot behavior.

A signal can move into implementation only after it has:

1. a current local Rift proof,
2. exact PID/HWND and window-mode context,
3. screenshots/log excerpts or addon output showing before/during/after state,
4. a clear false-positive risk note,
5. a decision: `promote`, `fallback-only`, or `retire`.

No public AutoIt/AHK/bot binary or script should be executed. Archived scripts remain reference-only.

Live proof runbook: `docs/live-validation/2026-05-25-historical-signal-live-proof-runbook.md`. Use it to execute the priority lane in order and classify each stale signal.

## Window size rule

Use larger Rift windows for proof capture whenever practical. The helper does not require `640x360`; it captures the current HWND client size and records it in manifests. `640x360` is tolerated for continuity but should be treated as low-readability evidence, especially for chat/API screenshots. Prefer at least `960x540` before running slash-output, reticle-color, or layout proof. After any resize, recalibrate fishable client X/Y and fixed regions before input because all helper coordinates are client-relative.

Focus operations must preserve the current window size. Do not use a focus path that blindly calls Windows `SW_RESTORE`, because it can shrink a maximized Rift window back to its saved restored size. AutoFish helper/preflight focus should restore only minimized windows.


## Current execution stance

This lane is now the active priority for the next live session.

Do **not** add more historical-signal scaffolding unless a live proof run exposes a specific missing capability. The next useful work is to execute the live proof runbook, collect evidence, run the summarizer, and record reviewed decisions.

Water detection should be reframed as fishability probing. The plan is documented in `docs/development/fishability-probe-plan.md`: generate candidate points, then let game feedback classify whether each point is fishable. Visual water/reticle evidence remains fallback-only. Coordinate-backed micro-step facing is blocked until a reliable player coordinate source is proven.

ChromaLink is now documented as a read-only coordinate-provider candidate in `docs/development/chromalink-readonly-coordinate-provider.md`. AutoFish can query ChromaLink's published local HTTP bridge, but must not modify ChromaLink from this repo and must require fresh `player.position` proof before treating coordinates as live truth.

Operational facing is now a proof lane, not an assumption. `docs/development/facing-delta-calibration.md` and `signal-proof facing-delta` estimate facing from fresh ChromaLink coordinates before/after one tiny confirmed forward movement pulse. Treat the result as a fan-planning hint, not native actor-facing/yaw.

Immediate live order:

1. `/autofish invproof before|after|diff` for native inventory deltas.
2. `signal-proof reticle --dry-run`, then one `--confirm-input --watch-seconds 18` proof.
3. `signal-proof summarize`.
4. `signal-proof decide` for the first reviewed signal.

## Signal validation matrix

| Priority | Signal | Why it matters | Proof test | Promote only if | Default if unproven |
|---:|---|---|---|---|---|
| 1 | Cursor / pointer / reticle state | Historical tools repeatedly used cursor changes, and current screenshots prove colored reticles. | During manual one-cast: capture before key `8`, after key `8`, after valid left-click, bite-ready, and post-reel states. Compare OS cursor, addon cursor/tooltip output, and screenshot crop near cursor. | State changes are repeatable across at least 3 casts and distinguish cast-valid, waiting, bite-ready, and invalid states. | Keep as helper-side diagnostic/fallback only. |
| 2 | Pixel / color / image checks | Current reticle colors are visible and directly actionable. | Capture cursor-centered crops for red/yellow/blue/green reticles and line/bobber/catch states. Record RGB/HSV ranges and crop coordinates. | Yellow/blue/green vs red classification is stable under the current graphics/window setup. | Use only manual calibration; do not auto-click based on pixels. |
| 3 | Inventory / bag deltas | A successful catch should eventually change inventory or loot state. | Snapshot bags before cast, after bite/reel, and after loot using addon item APIs and screenshots if needed. | Item deltas reliably identify catch/loot success without fixed bag coordinates. | Do not infer success from bag pixels; use timeout/manual evidence. |
| 4 | `/log` / chat / notification text | Old tools used logs, but those messages may be gone or language/path dependent. | Enable current supported logging if available, perform manual cast, inspect only new lines around the cast timestamps, and compare with `Event.Chat.Notify` if available. | Current client writes stable fishing-relevant text with timestamps and no language ambiguity. | Retire as primary; keep as optional debug evidence only. |
| 5 | Audio amplitude / splash cue | There is historical Python/audio precedent and bite cues may be audible. | Record manual cast windows with timestamps aligned to screenshots/addon events; measure whether bite/reel cue separates from ambient water/combat/UI sounds. | A simple calibrated threshold or feature separates bite from ambient noise across several casts. | Optional helper experiment only; never first-line truth. |
| 6 | Fixed hotbar assumptions | Actionbar key `8` is locally confirmed, but fixed slots are brittle. | Confirm keybind/profile fields and actionbar location for the current character. | Profile records keybinds explicitly and script validates target window before input. | No hard-coded slot assumptions beyond operator-provided profile/config. |
| 7 | Fixed bag assumptions | Historical scripts clicked fixed bag/lure slots; this is fragile. | Compare fixed bag screenshots against addon item API inventory details. | Only use if addon API cannot see the needed item and operator pins UI layout. | Prefer addon inventory observer; fixed bag coordinates stay last-resort. |

## Evidence packet format

Each proof attempt should record:

```text
Date:
Rift PID/HWND:
Window mode/resolution:
Character/location:
Fishable client coordinate:
Fishing key/action binding:
Signal under test:
Exact steps:
Screenshots/crops:
Addon slash outputs:
Log/audio file if any:
Result:
False positives observed:
Decision: promote | fallback-only | retire
Next action:
```

Store short live evidence in `docs/live-validation/`. Store reusable research conclusions in `docs/research/`.

## Implementation implications

The next helper work should be a **signal-proof harness**, not a full fishing loop.

Implemented first slice: `tools/autofish-helper-py/autofish_helper.py signal-proof reticle` captures cursor-centered BMP crops, OS cursor handle/position, rough reticle color counts, optional timed watch captures, and a JSON manifest. Live input still requires explicit `--confirm-input`; `--dry-run` sends no input. Use `--skip-click` with `--confirm-input` for post-key reticle calibration without sending the left click/cast-start action, and use `--cancel-after-key` to press Escape and record the cleared state after the post-key captures.

Implemented second slice: `tools/autofish-helper-py/autofish_helper.py signal-proof log` watches newly appended log text, scans fishing terms, and writes `appended-log.txt` plus a JSON manifest without sending any input.

Implemented third slice: `tools/autofish-helper-py/autofish_helper.py signal-proof layout` captures the full client and/or named hotbar/bag regions without input so fixed coordinate assumptions can be classified before use.

Implemented fourth slice: `tools/autofish-helper-py/autofish_helper.py signal-proof audio` records a bounded WAV sample from the current Windows recording input and writes peak/RMS timing windows for bite/splash cue experiments.

Implemented fifth slice: `/autofish invproof before|after|diff|status|clear` stores before/after native inventory snapshots in the Lua addon and prints quantity deltas plus raw slot-level add/remove/change diagnostics so catch success can be proven without fixed bag pixels.

Implemented trace extension: `/autofish trace start|status|stop|clear` now records focused addon-side API values (`Inspect.Cursor`, `Inspect.Tooltip`, and `Inspect.Interaction`) in trace samples. Use this to prove whether a visible reticle/tooltip is actually available to the addon before treating native hover APIs as a signal.

Current color-proof caveat: large-window sampling has proven visually yellow valid-water reticles and red invalid/too-far reticles, but has **not** proven a true blue/cyan reticle. The helper now reports conservative color suggestions plus `legacySuggestedReticleColor`, `suggestionReason`, and `manualReviewRequired` because `blueCyan` counts can be dominated by water/highlight background pixels. Treat blue/cyan as manual-review-only until a screenshot proves a real blue/cyan targeting reticle. The summarizer reports manual-review-required only for reticle-phase captures (`after-key`, `after-click`, and watch frames), not baseline or after-cancel background frames.

Implemented fishability planning slice: `tools/autofish-helper-py/autofish_helper.py signal-proof fishability-fan` creates a dry-run screen-space fan of candidate probe points, validates the exact PID/HWND, and optionally captures no-input crops. It does not send movement, fishing key, or clicks. Candidate points are planning evidence only until game feedback classifies them.

Implemented ChromaLink proof slice: `tools/autofish-helper-py/autofish_helper.py signal-proof chromalink` queries `/health`, `/ready`, and `/api/v1/riftreader/world-state` read-only, records `chromalinkWorldState` evidence, and classifies whether fresh `player.position` is available. It sends no game input and does not modify ChromaLink.

Implemented facing proof slice: `tools/autofish-helper-py/autofish_helper.py signal-proof facing-delta` validates exact PID/HWND, requires fresh ChromaLink before-position, and can send one tiny confirmed movement pulse to compute an operational X/Y facing vector from coordinate delta. The dry-run sends no movement and is the required first gate.

Implemented sixth slice: `tools/autofish-helper-py/autofish_helper.py signal-proof summarize` scans proof manifests and writes `summary.json` plus `summary.md` review buckets so stale methods are classified consistently before promotion.

Implemented seventh slice: `/autofish api`, `/autofish apicompact`, `/autofish apis`, and `/autofish events` include read-only table/availability discovery for inventory, chat, cursor/interaction, and candidate skill/currency/experience/profession/crafting namespaces. These probes only report whether namespaces and keys exist; do not treat a listed namespace as a supported fishing signal until a live proof packet shows useful values or events. Use `/autofish apicompact` when the output needs to fit in one screenshot.

Implemented eighth slice: `tools/autofish-helper-py/autofish_helper.py signal-proof slash` sends only explicitly confirmed, bounded slash commands and captures full-client screenshots after each one. By default it refuses non-`/autofish` commands and refuses command text containing `-` because that key triggers reloadui on this setup.

Implemented ninth slice: `/autofish proof` prints a compact screenshot-friendly state pack with coordinates, combat/secure/castbar status, inventory free-slot summary, fishing candidates, fail-closed observation flags, and focused cursor/tooltip/interaction API values. It is addon-side diagnostic output only; it does not promote native water or actor-facing truth. The helper slash proof can request this pack with `--default-proof-pack`.

Target Python commands:

```text
autofish_helper.py signal-proof reticle
  --pid <pid> --hwnd <hwnd> --x <client-x> --y <client-y> --key 8 --dry-run

autofish_helper.py signal-proof reticle
  --pid <pid> --hwnd <hwnd> --x <client-x> --y <client-y> --key 8 --watch-seconds 18 --confirm-input

autofish_helper.py signal-proof reticle
  --pid <pid> --hwnd <hwnd> --x <client-x> --y <client-y> --key 8 --watch-seconds 3 --confirm-input --skip-click --cancel-after-key

Addon API/chat-output proof:
  autofish_helper.py signal-proof slash
    --pid <pid> --hwnd <hwnd> --default-proof-pack --dry-run

  autofish_helper.py signal-proof slash
    --pid <pid> --hwnd <hwnd> --default-proof-pack --confirm-input

Lua addon inventory proof:
  /autofish invproof before
  <perform one manual cast/catch/loot attempt>
  /autofish invproof after
  /autofish invproof diff

autofish_helper.py signal-proof log
  --log-path <path> --duration-seconds 30

autofish_helper.py signal-proof layout
  --pid <pid> --hwnd <hwnd> --full-client --region hotbar:<left>,<top>,<width>,<height> --region bags:<left>,<top>,<width>,<height>

autofish_helper.py signal-proof audio
  --seconds <n> --label manual-cast
```

Each command should capture evidence and classify confidence. None should run an unattended loop.

## Guardrails

- Exact PID/HWND is mandatory before any helper input.
- Dry-run is mandatory for new coordinates or new signal probes.
- No movement commands in signal probes.
- Never use local `-` as a helper hotkey; it triggers `reloadui` on this setup.
- Public scripts/binaries are untrusted and must not be run.
- Any signal that only works under one resolution, UI layout, graphics preset, or language is fallback-only by default.
- Native addon signals still outrank historical helper fallbacks when both are available.

Decision recording command:

```text
autofish_helper.py signal-proof decide
  --signal <reticle|log|layout|audio|inventory> --decision <promote|fallback-only|retire|needs-more-evidence> --reason <reviewed-reason>
```

By default decisions are written to `.autofish-live/signal-proof-decisions.json`; use a docs path only for intentionally versioned decisions.
