# Historical Signal Live Proof Runbook

Date: 2026-05-25

## Purpose

Use this runbook when working the priority lane for historical Rift fishing signals:

- cursor-change detection,
- `/log` text,
- pixel/reticle checks,
- audio cues,
- fixed hotbar assumptions,
- fixed bag assumptions.

These methods are useful clues, but remain stale until proven current. This runbook turns each live attempt into evidence that can be classified as `promote`, `fallback-only`, or `retire`.

## Preflight requirements

Before any proof run:

1. Confirm exact Rift PID/HWND.
2. Confirm the target window is the intended local game client.
3. Confirm the character is stable at a fishable water edge.
4. Confirm key `8` is still the fishing action binding for this character/profile.
5. Do not use `-`; this local setup binds it to `reloadui`.
6. Keep the run supervised; no unattended loop.

Suggested target discovery:

```powershell
.\scripts\run-live-preflight.ps1 `
  -ExpectedProcessId <pid> `
  -ExpectedWindowHandle <hwnd> `
  -Focus `
  -Capture
```

## Proof order

Run proofs in this order so native/low-brittleness evidence is captured before fragile fallbacks.

### 1. Addon inventory delta proof

Purpose: prove catch/loot success without fixed bag pixels.

In game:

```text
/autofish invproof before
```

Then manually perform one cast/catch/loot attempt.

In game:

```text
/autofish invproof after
/autofish invproof diff
```

Decision:

- `promote` if item deltas repeatedly show caught fish or consumed bait/lure across at least 3 catches.
- `fallback-only` if deltas are useful but delayed, ambiguous, or require manual loot timing.
- `retire` only if current client item APIs cannot show meaningful inventory changes.

### 2. Reticle/cursor/pixel proof

Dry run first:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle `
  --pid <pid> `
  --hwnd <hwnd> `
  --x <fishable-client-x> `
  --y <fishable-client-y> `
  --key 8 `
  --dry-run
```

One bounded live proof:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle `
  --pid <pid> `
  --hwnd <hwnd> `
  --x <fishable-client-x> `
  --y <fishable-client-y> `
  --key 8 `
  --watch-seconds 18 `
  --watch-interval-ms 500 `
  --confirm-input
```

Decision:

- `promote` only if cursor handle/color/crop states distinguish useful fishing phases across at least 3 casts.
- `fallback-only` if it works only under this UI/graphics/window setup.
- `retire` if crops/cursor handles do not separate invalid, valid, waiting, and bite-ready states.

### 3. Current log proof

Only test logs as read-only evidence:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof log `
  --log-path <rift-log-path> `
  --duration-seconds 30 `
  --pid <pid> `
  --hwnd <hwnd>
```

During the 30 seconds, perform one manual fishing attempt.

Decision:

- `promote` only if current logs contain stable fishing-relevant text with useful timing.
- `fallback-only` if text exists but is language/path/settings dependent.
- `retire` if no useful current fishing text appears after repeated manual attempts.

### 4. Fixed layout proof

Capture full client and named hotbar/bag regions:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof layout `
  --pid <pid> `
  --hwnd <hwnd> `
  --full-client `
  --region hotbar:<left>,<top>,<width>,<height> `
  --region bags:<left>,<top>,<width>,<height>
```

Repeat after:

- `/reloadui`,
- closing/reopening bags,
- changing UI scale or resolution if relevant.

Decision:

- `promote` only as explicit profile fields if stable across sessions.
- `fallback-only` if stable only for one UI layout.
- `retire` fixed bag coordinates if addon inventory proof works.

### 5. Audio proof

Only run if the Windows recording device is intentionally set to the desired input.

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof audio `
  --seconds 20 `
  --label manual-cast `
  --pid <pid> `
  --hwnd <hwnd>
```

Decision:

- `promote` only if bite/splash timing creates a repeatable loudness feature across multiple casts.
- `fallback-only` if device/noise dependent.
- `retire` if ambient water/UI/combat sounds overlap too much.

## Summarize collected evidence

After collecting proof manifests:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof summarize `
  --proof-root .autofish-live
```

Review:

- `.autofish-live\signal-proof-summary-*\summary.md`
- `.autofish-live\signal-proof-summary-*\summary.json`

The summarizer suggests review buckets only. It does not make final decisions.

## Classification table

| Signal | Promote when | Fallback-only when | Retire when |
|---|---|---|---|
| Inventory deltas | Catch/bait deltas repeat across 3+ catches | Deltas work but timing is delayed or ambiguous | Item APIs do not expose useful changes |
| Cursor/reticle/pixels | Distinct states repeat across 3+ casts | Works only with current UI/graphics/window setup | Does not distinguish fishing phases |
| `/log` text | Stable current fishing text appears with useful timing | Text is useful but path/language/settings dependent | No useful text appears |
| Fixed hotbar/bag layout | Stable as explicit profile fields | Stable only for one pinned UI setup | Addon/API evidence makes it unnecessary |
| Audio | Bite/splash has repeatable timing feature | Device/noise dependent | Ambient sound overlaps too much |

## Stop conditions

Stop the proof run if:

- PID/HWND changes,
- Rift loses foreground during an input proof,
- `reloadui` triggers unexpectedly,
- character falls into water,
- combat/secure state starts,
- any script reports target mismatch,
- the operator interrupts.

## Recording reviewed decisions

After live proofs are summarized and manually reviewed, record the decision instead of leaving it implicit:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof decide `
  --signal inventory `
  --decision promote `
  --reason "Three manual catches produced stable item deltas" `
  --evidence .autofish-live\signal-proof-summary-<stamp>\summary.md
```

Allowed decisions are:

- `promote`
- `fallback-only`
- `retire`
- `needs-more-evidence`

By default this writes `.autofish-live\signal-proof-decisions.json`. Use `--register docs\live-validation\historical-signal-decisions.json` only when you intentionally want a versioned decision register.
