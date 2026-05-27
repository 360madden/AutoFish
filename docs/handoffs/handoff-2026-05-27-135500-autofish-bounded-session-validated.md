# AutoFish — Bounded Session Pipeline Validated

Date: 2026-05-27 13:55 +00:00
Updated: All 7 gates passed, bounded session complete (3/3 casts)
Repo: `C:\RIFT MODDING\AutoFish`
Branch: `main`
Remote: `https://github.com/360madden/AutoFish`

## TL;DR

The **one-cast → bounded-session pipeline** was validated end-to-end with live game input. Key `8` triggers the fishing reticle consistently (257-341 red px post-keypress), the reticle clears after confirm click, and all 3 supervised casts completed without guardrail triggers. The session plan doctor reports **7/7 gates passed**, ready for bounded sessions.

No repo source code was changed. Only `.autofish-live` evidence and this handoff were written.

## What happened

### Phase 1 — Addon verification
- Sent `/autofish pole` and `/autofish abilities` via slash proof (PID 3140, HWND `0x508AE`)
- Confirmed fishing pole and ability are mapped to key `8`
- Scope token: `afscope-3711d8fdafbf50fd`

### Phase 2 — One-cast proof
- Dry-run: all gates passed, ~15.4s planned pipeline
- Confirm-input: executed successfully at center (640, 360) client
- **Reticle timeline**: 0 → 0 → **317 red px** (after-key) → 0 (after-click) → 0 (before-pull) → 0 (after-pull)
- Classification: `bounded-one-cast-evidence`
- Decision: **promote** — "Key 8 triggered fishing reticle, reticle cleared after confirm click, all review gates passed"
- Evidence: `.autofish-live/signal-proof-one-cast-20260527-051001/manifest.json`

### Phase 3 — Bounded session proof
- Session plan recreated (original expired after 240 min)
- Dry-run: all gates passed, 3 casts × 12s each, 800ms inter-cast
- Confirm-input: 3/3 casts completed, ~49s total duration
- **Cast-level reticle detection:**

| Cast | Post-key red px | Post-complete red px | Guard |
|------|----------------|---------------------|-------|
| 1 | 328 | 0 | ✅ pass |
| 2 | 257 | 0 | ✅ pass |
| 3 | 341 | 0 | ✅ pass |

- Classification: `bounded-session-evidence`
- Evidence: `.autofish-live/signal-proof-bounded-session-20260527-095158/manifest.json`

### Phase 4 — Doctor report
- **7/7 gates passed**: stopFileClear, planFresh, targetCurrent, targetForeground, clientReadable, fishabilityCandidate (N/A), oneCast (promoted)
- Ready for one-cast: ✅
- Ready for bounded session: ✅
- Doctor: `.autofish-live/session-plan-doctor-20260527-095412/doctor.md`

## Evidence written (git-ignored)

| Path | Description |
|------|-------------|
| `.autofish-live/session-plan-latest.json` | Current session plan (PID 3140, HWND `0x508AE`, 1280×720, center 640×360, starter-pond) |
| `.autofish-live/signal-proof-decisions.json` | Decision register — oneCast = promoted |
| `.autofish-live/signal-proof-slash-pole/manifest.json` | `/autofish pole` confirmation |
| `.autofish-live/signal-proof-slash-abilities/manifest.json` | `/autofish abilities` confirmation |
| `.autofish-live/signal-proof-one-cast-20260527-051001/manifest.json` | One-cast proof (promoted) |
| `.autofish-live/signal-proof-bounded-session-20260527-095158/manifest.json` | Bounded session proof (3/3 casts) |
| `.autofish-live/session-plan-doctor-20260527-095412/` | Doctor report (7/7 gates passed) |
| `.autofish-live/signal-proof-reticle-20260527-050752/manifest.json` | Reticle calibration (clean water at cast point) |

These are intentionally not committed.

## Profile timing analysis

The `starter-pond` profile (12s bite timeout, 2.2s loot timeout) produced consistent cast durations:

| Cast | Duration |
|------|----------|
| 1 | 16.00s |
| 2 | 16.00s |
| 3 | 15.98s |

Configured overhead per cast: 150ms hover + 80ms key hold + 350ms post-key + 800ms post-click + 12000ms bite wait + 2200ms post-pull = 15.58s. Actual durations (~16.0s) include screenshot capture overhead (~0.4s), consistent across all 3 casts.

**Verdict**: No profile tuning needed. The 12s `biteTimeoutMs` is appropriate for starter-pond. Cast durations are consistent within 20ms. No missed-bite evidence was observed.

## Commands already run

```powershell
# Phase 1 — Addon verification
python tools\autofish-helper-py\autofish_helper.py signal-proof slash --pid 3140 --hwnd 0x508AE --command "/autofish pole" --confirm-input
python tools\autofish-helper-py\autofish_helper.py signal-proof slash --pid 3140 --hwnd 0x508AE --command "/autofish abilities" --confirm-input

# Phase 2 — One-cast proof
python tools\autofish-helper-py\autofish_helper.py session-plan create --pid 3140 --hwnd 0x508AE --x 640 --y 360 --profile starter-pond --validate-target --output .autofish-live/session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py signal-proof reticle --pid 3140 --hwnd 0x508AE --x 640 --y 360 --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast --session-plan .autofish-live/session-plan-latest.json --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof one-cast --session-plan .autofish-live/session-plan-latest.json --confirm-input
python tools\autofish-helper-py\autofish_helper.py signal-proof decide --signal oneCast --decision promote --reason "..." --evidence .autofish-live/signal-proof-one-cast-20260527-051001/manifest.json --session-plan .autofish-live/session-plan-latest.json

# Phase 3 — Bounded session proof (plan recreated after expiry)
python tools\autofish-helper-py\autofish_helper.py session-plan create --pid 3140 --hwnd 0x508AE --x 640 --y 360 --profile starter-pond --validate-target --output .autofish-live/session-plan-latest.json
python tools\autofish-helper-py\autofish_helper.py signal-proof bounded-session --session-plan .autofish-live/session-plan-latest.json --dry-run
python tools\autofish-helper-py\autofish_helper.py signal-proof bounded-session --session-plan .autofish-live/session-plan-latest.json --confirm-input

# Phase 4 — Doctor and summary
python tools\autofish-helper-py\autofish_helper.py session-plan doctor --path .autofish-live/session-plan-latest.json --proof-root .autofish-live --decision-register .autofish-live/signal-proof-decisions.json
```

## Safety verification

- Stop file: clear ✅
- Red reticle guard: passed all 4 cast checks (one-cast + 3 bounded) ✅
- Max casts: capped at 3 (profile default) ✅
- No movement sent ✅
- No unattended loops ✅
- Exact PID/HWND validated at each stage ✅
- Foreground verified before confirm-input ✅

## Next steps

1. **Decide on bounded-session signal** — promote via `signal-proof decide --signal boundedSession --decision promote`
2. **Run extended bounded session** — increase `maxCasts` for longer supervised runs (e.g., 5-10 casts)
3. **Calibrate facing delta** — `signal-proof facing-delta` for future auto-repositioning
4. **Create zone-specific profile** — tune bite/loot timings for the actual fishing zone (starter-pond is generic)
5. **Run fishability fan probe** — map valid cast arcs from this position
