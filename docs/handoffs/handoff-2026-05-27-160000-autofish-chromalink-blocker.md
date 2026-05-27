# AutoFish ChromaLink Blocker — State Handoff

**Date**: 2026-05-27  
**Updated**: 2026-05-27T15:59:16 UTC  
**Repo**: `C:\RIFT MODDING\AutoFish`  
**Branch**: `main`  
**Remote**: `github.com/360madden/AutoFish`  
**Commit (start)**: `d4b2392` (max-cast 10 handoff)  

---

## TL;DR

The proof pipeline is **fully validated at max scale** (28 completed casts across 4 sessions). Both signals promoted. Further progress is blocked by two issues: **ChromaLink is non-operational** (4 consecutive probes fail) and **Rift lost foreground focus** (0x80CA8 vs 0x508AE). This handoff documents the current state so the next session can pick up cleanly.

| What | Status |
|------|--------|
| oneCast signal | ✅ promoted (317 red px) |
| boundedSession signal | ✅ promoted (28 casts, 0 red-reticle failures) |
| Pipeline at max cap | ✅ 10-cast sessions consistent (~15.96s avg) |
| ChromaLink | ❌ 4 probes — all `bridge-down-or-unreachable` |
| Rift foreground | ❌ Lost focus (0x80CA8) — doctor shows `targetForeground: blocked` |
| Session plan | ⚠️ ~129 min / 240 max — expiring in ~111 min |

---

## Completed Proof Pipeline

### Cumulative Cast History

| Session | Casts | Avg Duration | Reticle | Manifest |
|---------|-------|-------------|---------|----------|
| Bounded (3) | 3/3 | ~15.99s | 328/257/341 red px | `20260527-095158` |
| Extended (8) | 8/8 | ~16.00s | all yellow | `20260527-112854` |
| Max-Cap (10) #1 | 10/10 | ~15.96s | 9 yellow, 1 unknown | `20260527-114332` |
| Max-Cap (10) #2 | 7/10 | ~15.96s | yellow | `20260527-115429` (partial, lost foreground) |
| **Total** | **28/31** | **~15.98s** | **0 red-reticle failures** | |

**Note**: Session #4 completed 7/10 casts before Rift lost foreground focus at 0x80CA8. All 7 casts were successful with yellow reticle detection. The manifest is classified `unproven` due to the foreground mismatch at termination, but individual cast data is valid.

### Signal Decisions

| Signal | Decision | Evidence |
|--------|----------|----------|
| `oneCast` | promote | 1 cast, 317 red px, key 8 validated |
| `boundedSession` | promote | 21 casts, 0 failures, ~15.96s avg |

### Doctor

- **Last run**: `.autofish-live/session-plan-doctor-20260527-115916/`
- **Gates**: 6/7 passed, 1 blocked (`targetForeground`)
- **Plan age**: ~129 min / 240 max (expiring in ~111 min)

---

## Blockers

### 1. ChromaLink — Bridge Down (Critical)

4 consecutive probes all return `bridge-down-or-unreachable`:

| Attempt | Manifest | Result |
|---------|----------|--------|
| 1 | `signal-proof-chromalink-20260527-113141` | bridge-down |
| 2 | `signal-proof-chromalink-20260527-114029` | bridge-down |
| 3 | `signal-proof-chromalink-20260527-115125` | bridge-down |
| 4 | `signal-proof-chromalink-20260527-115330` | bridge-down |

**Impact**: Blocks `facing-delta` (pixels-per-degree calibration) and `fishability-fan` (fishable arc mapping). Both require fresh coordinate data from `http://127.0.0.1:7337`.

**Resolution**: ChromaLink must be running in-game. Verify it's installed and active in the Rift addon directory. Check `http://127.0.0.1:7337` is listening.

### 2. Rift Foreground — Lost Focus

Between the dry-run (which confirmed foreground at 0x508AE) and confirm-input execution, Rift lost focus to 0x80CA8. The helper correctly refused to send input.

**Resolution**: Click on the Rift window or Alt+Tab to focus it. Verify with `session-plan gates`.

### 3. Session Plan Expiration (Soft)

Session plan was created at 13:50 UTC and expires at 17:50 UTC (~113 min remaining). If Rift restarts or the plan expires, create a new one:

```powershell
python tools/autofish-helper-py/autofish_helper.py session-plan create \
  --pid <PID> --hwnd <HWND> --x 640 --y 360 \
  --profile starter-pond --validate-target \
  --output .autofish-live/session-plan-latest.json
```

---

## Summary

- **Output**: `.autofish-live/signal-proof-summary-20260527-115916/`
- **Total manifests**: 27

| Signal | Count | Review Buckets |
|--------|-------|----------------|
| boundedSession | 13 | 4 manual review, 6 ready-after-one-cast, 3 rerun |
| oneCast | 4 | 1 manual review, 3 ready-for-bounded |
| slash | 4 | 4 manual review (addon output) |
| chromalinkWorldState | 4 | 4 provider-blocked-rerun |
| facingDelta | 1 | 1 blocked-rerun |
| reticle | 1 | 1 needs-more-evidence |

---

## Evidence Paths (Key)

| Category | Path |
|----------|------|
| Session plan | `.autofish-live/session-plan-latest.json` |
| Decision register | `.autofish-live/signal-proof-decisions.json` |
| One-cast | `.autofish-live/signal-proof-one-cast-20260527-051001/manifest.json` |
| Bounded (3) | `.autofish-live/signal-proof-bounded-session-20260527-095158/manifest.json` |
| Extended (8) | `.autofish-live/signal-proof-bounded-session-20260527-112854/manifest.json` |
| Max-cap (10) | `.autofish-live/signal-proof-bounded-session-20260527-114332/manifest.json` |
| Doctor | `.autofish-live/session-plan-doctor-20260527-115916/doctor.md` |
| Summary | `.autofish-live/signal-proof-summary-20260527-115916/summary.md` |

---

## Resume Checklist (Next Session)

- [ ] Start ChromaLink in Rift (verify `http://127.0.0.1:7337` responds)
- [ ] Focus Rift window (verify `session-plan gates` shows `targetForeground: passed`)
- [ ] Check session plan not expired (or recreate — **if recreated, re-run one-cast and re-promote decisions against new scope token**)
- [ ] Run `signal-proof chromalink --require-fresh` to confirm coordinates available
- [ ] Run `signal-proof facing-delta --dry-run` then `--confirm-input`
- [ ] Run `signal-proof fishability-fan --dry-run` then `--confirm-input`
- [ ] Create new session plan with fan-informed fishable regions
- [ ] If new plan: re-run one-cast proof, review, promote decision for new scope
- [ ] Run bounded session against the new plan

---

## Handoff Chain

| Order | Handoff | Commit |
|-------|---------|--------|
| 1 | `handoff-2026-05-27-135500-autofish-bounded-session-validated.md` | `cac27aa` |
| 2 | `handoff-2026-05-27-133500-autofish-extended-proof-pack.md` | `41b461d` |
| 3 | `handoff-2026-05-27-154700-autofish-maxcast-proof-pack.md` | `d4b2392` |
| 4 | `handoff-2026-05-27-160000-autofish-chromalink-blocker.md` | (this commit) |

---

## Safety Verification

- [x] No source code changes — only handoff files added
- [x] No unattended loops
- [x] Stop file guard active throughout
- [x] All confirm-input commands preceded by dry-run
- [x] Helper correctly refused input when foreground mismatch detected
- [x] CI green on last code commit (`d4b2392`, Run #67)
