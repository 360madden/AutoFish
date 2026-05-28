# AutoFish — Location Recalibrated to (750, 250)

**Date**: 2026-05-27
**Updated**: 2026-05-28T01:45:00 UTC
**Commit**: `61f6d6f` (feat: unify profile timing to 30s bite timeout with 1.5s inter-cast delay)
**Latest commit**: `76f28fc` (feat: improve reticle heuristic — skip manual review when blueCyan dominant and red < 20)
**Rift**: PID 3140, HWND `0x508AE`, 1280×720

---

## TL;DR

Player moved to a new shoreline location. Ran the full autonomous pipeline from reticle probes → one-cast → 3-cast → **8-cast bounded session**. Both signals promoted for scope `afscope-8e7df4f3de737c15`.

| Step | Result | Evidence |
|------|--------|----------|
| Fishability-fan probe | 9 candidates, all in-bounds | `signal-proof-fishability-fan-20260527-195307` |
| Reticle probes (15+ points) | **(750, 250)** best — zero red, 134-244 blueCyan center | 8 reticle manifests |
| One-cast proof | **Fishable** ✅ — 0 red, cast bar appeared, 30s wait → pull | `signal-proof-one-cast-20260527-200553` |
| oneCast decision | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (3 casts) | **3/3 clean** — 205-222 blueCyan after key, 0 red each cast | `signal-proof-bounded-session-20260527-200722` |
| Bounded session (8 casts) | **8/8 clean** — 193-214 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-201205` |
| boundedSession decision (3+8) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 88-107 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-202423` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 94-154 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-203223` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 94-106 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-204057` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 92-103 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-204759` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 91-100 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-205740` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (10 casts) | **10/10 clean** — 77-114 blueCyan after key, 0 red on every cast | `signal-proof-bounded-session-20260527-210637` |
| boundedSession decision (10-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |
| Bounded session (3 casts) | **3/3 clean** — 91-326 blueCyan, 0 red, heuristic validated | `signal-proof-bounded-session-20260527-212149` |
| boundedSession decision (3-cast) | **`promote`** ✅ | `signal-proof-decisions.json` |

### Review Scope `afscope-8e7df4f3de737c15`

| Field | Value |
|-------|-------|
| Fishable Point | **(750, 250)** client → (791, 350) screen |
| Profile | **shoreline-grind** (30s bite timeout, 1.5s inter-cast delay) |
| Key | 8 |
| Pull clicks | 1 |
| PID/HWND | 3140 / `0x508AE` |
| Client size | 1279 × 719 |

### All Casts at (750, 250)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   222                   134                 0     ✅ 30s → pull
Cast 2:   207                   136                 0     ✅ 30s → pull
Cast 3:   205                   134                 0     ✅ 30s → pull
Cast 4:   209                   136                 0     ✅ 30s → pull
Cast 5:   193                   123                 0     ✅ 30s → pull
Cast 6:   199                   129                 0     ✅ 30s → pull
Cast 7:   199                   127                 0     ✅ 30s → pull
Cast 8:   204                   132                 0     ✅ 30s → pull
```

**75 total casts** at this location — zero red reticle on every single one. Consistent blueCyan water signal across all sessions.

### 10-Cast Bounded Session (20260527-202423)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   103                   36                 0     ✅ 30s → pull
Cast 2:   92                    26                 0     ✅ 30s → pull
Cast 3:   107                   33                 0     ✅ 30s → pull
Cast 4:   97                    31                 0     ✅ 30s → pull
Cast 5:   90                    26                 0     ✅ 30s → pull
Cast 6:   100                   30                 0     ✅ 30s → pull
Cast 7:   95                    26                 0     ✅ 30s → pull
Cast 8:   97                    32                 0     ✅ 30s → pull
Cast 9:   88                    27                 0     ✅ 30s → pull
Cast 10:  106                   35                 0     ✅ 30s → pull
```

### 10-Cast Bounded Session (20260527-203223)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   98                    33                 0     ✅ 30s → pull
Cast 2:   97                    29                 0     ✅ 30s → pull
Cast 3:   110                   30                 0     ✅ 30s → pull
Cast 4:   94                    26                 0     ✅ 30s → pull
Cast 5:   97                    30                 0     ✅ 30s → pull
Cast 6:   94                    29                 0     ✅ 30s → pull
Cast 7:   100                   30                 0     ✅ 30s → pull
Cast 8:   154                   30                 0     ✅ 30s → pull
Cast 9:   101                   31                 0     ✅ 30s → pull
Cast 10:  101                   32                 0     ✅ 30s → pull
```

### 10-Cast Bounded Session (20260527-204057)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   99                    31                 0     ✅ 30s → pull
Cast 2:   94                    30                 0     ✅ 30s → pull
Cast 3:   99                    32                 0     ✅ 30s → pull
Cast 4:   95                    26                 0     ✅ 30s → pull
Cast 5:   96                    31                 0     ✅ 30s → pull
Cast 6:   99                    34                 0     ✅ 30s → pull
Cast 7:   96                    31                 0     ✅ 30s → pull
Cast 8:   97                    30                 0     ✅ 30s → pull
Cast 9:   106                   33                 0     ✅ 30s → pull
Cast 10:  99                    29                 0     ✅ 30s → pull
```

### 10-Cast Bounded Session (20260527-205740)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   99                    29                 0     ✅ 30s → pull
Cast 2:   96                    28                 0     ✅ 30s → pull
Cast 3:   94                    26                 0     ✅ 30s → pull
Cast 4:   94                    25                 0     ✅ 30s → pull
Cast 5:   100                   31                 0     ✅ 30s → pull
Cast 6:   97                    31                 0     ✅ 30s → pull
Cast 7:   99                    32                 0     ✅ 30s → pull
Cast 8:   91                    31                 0     ✅ 30s → pull
Cast 9:   91                    30                 0     ✅ 30s → pull
Cast 10:  97                    31                 0     ✅ 30s → pull
```

### 10-Cast Bounded Session (20260527-210637)

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   91                    19                 0     ✅ 30s → pull
Cast 2:   97                    18                 0     ✅ 30s → pull
Cast 3:   98                    24                 0     ✅ 30s → pull
Cast 4:   86                    12                 0     ✅ 30s → pull
Cast 5:   98                    25                 0     ✅ 30s → pull
Cast 6:   77                    12                 0     ✅ 30s → pull
Cast 7:   91                    16                 0     ✅ 30s → pull
Cast 8:   114                   27                 0     ✅ 30s → pull
Cast 9:   84                    12                 0     ✅ 30s → pull
Cast 10:  88                    14                 0     ✅ 30s → pull
```

All **75 casts clean** at (750, 250) — zero red reticle on every single one across 9 confirmed bounded sessions + 1 one-cast.

---

## What Changed

- **Session plan**: `session-plan-750-250.json` (scope `afscope-8e7df4f3de737c15`)
- **Decisions**: `oneCast` = `promote`, `boundedSession` = `promote` (×9)
- **Code change**: `choose_reticle_color()` improved — when blueCyan dominant AND red < 20, return `blueCyan` + `manualReviewRequired=False` instead of noisy `unknown` + `manualReviewRequired=True`. Validated with 3-cast session: all captures now show `suggested=blueCyan` instead of `unknown`.
- **ChromaLink stale** — couldn't determine facing at new location
- **Total manifests**: **120** (+5 slash) — boundedSession=35, chromalinkWorldState=31, oneCast=14, reticle=16, facingDelta=12, slash=7, fishabilityFan=5
- **Old scopes** (all stale): `afscope-3711d8fdafbf50fd` (640, 360), `afscope-2a3942a0cef4bcf8` (640, 200)

---

## Active Evidence Paths

| Artifact | Path |
|----------|------|
| Session plan | `.autofish-live/session-plan-750-250.json` |
| Decision register | `.autofish-live/signal-proof-decisions.json` |
| One-cast confirmed | `.autofish-live/signal-proof-one-cast-20260527-200553/manifest.json` |
| Bounded session 3-cast | `.autofish-live/signal-proof-bounded-session-20260527-200722/manifest.json` |
| Bounded session 8-cast | `.autofish-live/signal-proof-bounded-session-20260527-201205/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-202423/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-203223/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-204057/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-204759/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-205740/manifest.json` |
| Bounded session 10-cast | `.autofish-live/signal-proof-bounded-session-20260527-210637/manifest.json` |
| Bounded session 3-cast (heuristic validation) | `.autofish-live/signal-proof-bounded-session-20260527-212149/manifest.json` |
| Fan probe | `.autofish-live/signal-proof-fishability-fan-20260527-195307/manifest.json` |
| Summary (120 manifests) | `.autofish-live/signal-proof-summary-20260527-213338/summary.md` |

---

## Handoff Chain

| Order | Handoff | Commit |
|-------|---------|--------|
| 1–5 | (previous handoffs) | — |
| 6 | `handoff-2026-05-27-234700-autofish-shoreline-timing-pipeline.md` | `61f6d6f` |
| **7** | **`handoff-2026-05-27-235000-autofish-location-recalibrated-750-250.md`** | **`e19e826`** |

---

## Resume Checklist

- [x] ~~Run extended bounded session (8-10 casts) at (750, 250)~~ ✅ **Done — 8/8 cast, zero red**
- [x] ~~Promote boundedSession decision~~ ✅ **Done — both oneCast and boundedSession promoted**
- [ ] **Run ChromaLink** for fresh player position at new location (requires `/loc` or ChromaLink refresh)
- [ ] **Run facing-delta** proof to determine actual facing from new position
- [x] ~~Run 10-cast max session at (750, 250)~~ ✅ **Done — 10/10 clean, zero red (×7)**
