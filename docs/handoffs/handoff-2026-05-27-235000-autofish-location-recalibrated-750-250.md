# AutoFish — Location Recalibrated to (750, 250)

**Date**: 2026-05-27
**Updated**: 2026-05-28T00:10:00 UTC
**Commit**: `61f6d6f` (feat: unify profile timing to 30s bite timeout with 1.5s inter-cast delay)
**Rift**: PID 3140, HWND `0x508AE`, 1280×720

---

## TL;DR

Player moved to a new shoreline location. Ran the full autonomous pipeline to recalibrate.

| Step | Result | Evidence |
|------|--------|----------|
| Fishability-fan probe | 9 candidates, all in-bounds | `signal-proof-fishability-fan-20260527-195307` |
| Reticle probes (15+ points) | **(750, 250)** best — zero red, 134-244 blueCyan center | 8 reticle manifests |
| One-cast proof | **Fishable** ✅ — 0 red, cast bar appeared, 30s wait → pull | `signal-proof-one-cast-20260527-200553` |
| Decision recorded | **`promote`** | `signal-proof-decisions.json` |
| Bounded session (3 casts) | **3/3 clean** — 205-222 blueCyan after key, 0 red each cast | `signal-proof-bounded-session-20260527-200722` |

### New Review Scope

| Field | Value |
|-------|-------|
| Scope Token | `afscope-8e7df4f3de737c15` |
| Fishable Point | **(750, 250)** client |
| Profile | **shoreline-grind** (30s bite timeout, 1.5s inter-cast delay) |
| Screen | (791, 350) screen coords |
| Key | 8 |
| Pull clicks | 1 |

### Cast Consistency

```
          after-key blueCyan    center blueCyan    red    complete
Cast 1:   222                   134                 0     ✅ 30s → pull
Cast 2:   207                   136                 0     ✅ 30s → pull
Cast 3:   205                   134                 0     ✅ 30s → pull
```

All 7 captures show consistent blueCyan water signal at upper-right area.

---

## What Changed

- **New session plan**: `session-plan-750-250.json` (scope `afscope-8e7df4f3de737c15`)
- **No code changes** — all existing code from commit `61f6d6f` was sufficient
- **ChromaLink stale** (52+ min old from before move) — couldn't determine new facing direction
- **Old scopes**: `afscope-3711d8fdafbf50fd` (640, 360) and `afscope-2a3942a0cef4bcf8` (640, 200) are **stale**

---

## Active Evidence Paths

| Artifact | Path |
|----------|------|
| Session plan (new) | `.autofish-live/session-plan-750-250.json` |
| Decision register | `.autofish-live/signal-proof-decisions.json` |
| One-cast confirmed | `.autofish-live/signal-proof-one-cast-20260527-200553/manifest.json` |
| Bounded session 3-cast | `.autofish-live/signal-proof-bounded-session-20260527-200722/manifest.json` |
| Fan probe | `.autofish-live/signal-proof-fishability-fan-20260527-195307/manifest.json` |
| Reticle (best candidate) | `.autofish-live/signal-proof-reticle-20260527-195512/manifest.json` |

---

## Handoff Chain

| Order | Handoff | Commit |
|-------|---------|--------|
| 1–5 | (previous handoffs) | — |
| 6 | `handoff-2026-05-27-234700-autofish-shoreline-timing-pipeline.md` | `61f6d6f` |
| **7** | **`handoff-2026-05-27-235000-autofish-location-recalibrated-750-250.md`** | **`61f6d6f`** |

---

## Resume Checklist

- [ ] **Run extended bounded session** (8-10 casts) at (750, 250) with shoreline-grind 30s timing
- [ ] **Run ChromaLink** for fresh player position at new location
- [ ] **Run facing-delta** proof to determine actual facing from new position
- [ ] **Promote boundedSession** decision for new scope once extended run completes
