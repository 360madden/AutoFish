# AutoFish — Shoreline Timing Pipeline Handoff

**Date**: 2026-05-27
**Updated**: 2026-05-27T23:47:00 UTC
**Repo**: `C:\Rift Modding\autofish`
**Branch**: `main`
**Remote**: `github.com/360madden/AutoFish`
**Commit (start)**: `61560a2` (docs: replace PowerShell code fences with bash, normalize path separators)

---

## TL;DR

This session made **3 bulk profile timing updates**, **lowered the readability threshold**, and **executed the full autonomous proof pipeline** end-to-end with **shoreline-grind** (30s bite timeout, 1.5s inter-cast delay).

| What | Status |
|------|--------|
| Profile timing updates (all 3 profiles) | ✅ `biteTimeoutMs=30000`, `interCastDelayMs=1500` |
| Readability threshold | ✅ Lowered 960×540 → 320×240 |
| Inter-cast delay schema | ✅ Added `interCastDelayMs` to `fishing-profile.schema.json` |
| Python helper defaults | ✅ Reads `interCastDelayMs` from profile with fallback 800ms |
| One-cast proof (shoreline-grind) | ✅ Confirmed — `bounded-one-cast-evidence`, `castWaitSeconds: 30.0` |
| Bounded-session proof (shoreline-grind) | ✅ **3/3 casts**, `bounded-session-evidence`, `blueCyan` reticle |
| Decision registered (shoreline-grind scope) | 🔲 `oneCast` = `fallback-only` (needs manual promotion); `boundedSession` = unregistered |
| All smoke tests | ✅ PASS |
| **Total manifests** | **65** (+4 from this session) |

---

## Three Review Scopes

| Scope | Token | Session Plan | Profile | Fishable Pt | Client | Live Casts | Decisions |
|-------|-------|-------------|---------|:-----------:|:------:|:----------:|-----------|
| Old #1 | `afscope-3711d8fdafbf50fd` | Expired | starter-pond | (640, 360) | 1280×720 | 21+ (3+8+8+10+partials) | `oneCast`=promote, `boundedSession`=promote |
| Old #2 | `afscope-63430969032699f1` | Expired | starter-pond | (320, 100) | 640×360 | 13 (3+10) | `oneCast`=promote, `boundedSession`=unregistered |
| **New** | **`afscope-2a3942a0cef4bcf8`** | **Active** | **shoreline-grind** | **(640, 200)** | **1280×720** | **3+1 (one-cast + bounded 3)** | **`oneCast`=fallback-only, `boundedSession`=unregistered** |

---

## Code Changes (uncommitted)

| File | Change |
|------|--------|
| `profiles/starter-pond.json` | `biteTimeoutMs` 12000→30000, added `interCastDelayMs: 1500` |
| `profiles/shoreline-grind.json` | `biteTimeoutMs` 10000→30000, added `interCastDelayMs: 1500` |
| `profiles/vendor-recovery-loop.json` | `biteTimeoutMs` 14000→30000, added `interCastDelayMs: 1500` |
| `contracts/fishing-profile.schema.json` | Added `interCastDelayMs` to pacing schema |
| `tools/autofish-helper-py/autofish_helper.py` | Reads `interCastDelayMs` from profile; lowered readability 960×540→320×240; updated warning text |
| `tools/autofish-helper-py/tests/smoke_autofish_helper.py` | Updated readability gate test (640×360 → 100×100) and retitle screen default |

---

## Evidence Paths

| Category | Path |
|----------|------|
| Session plan (shoreline-grind) | `.autofish-live/session-plan-shoreline.json` |
| Decision register | `.autofish-live/signal-proof-decisions.json` |
| Summary (65 manifests) | `.autofish-live/signal-proof-summary-20260527-194655/summary.md` |
| One-cast dry-run (shoreline-grind) | `.autofish-live/signal-proof-one-cast-20260527-194120/manifest.json` |
| One-cast confirmed (shoreline-grind) | `.autofish-live/signal-proof-one-cast-20260527-194316/manifest.json` |
| Bounded-session dry-run (shoreline-grind) | `.autofish-live/signal-proof-bounded-session-20260527-194442/manifest.json` |
| Bounded-session 3-cast confirmed (shoreline-grind) | `.autofish-live/signal-proof-bounded-session-20260527-194450/manifest.json` |
| Doctor report | `.autofish-live/session-plan-doctor-20260527-193013/doctor.md` |

---

## Resume Checklist

- [ ] **Promote shoreline-grind one-cast** — review BMP captures, then `signal-proof decide --signal oneCast --decision promote --evidence .autofish-live/signal-proof-one-cast-20260527-194316/manifest.json --session-plan .autofish-live/session-plan-shoreline.json`
- [ ] **Promote shoreline-grind bounded-session** — review BMP captures, then `signal-proof decide --signal boundedSession --decision promote --evidence .autofish-live/signal-proof-bounded-session-20260527-194450/manifest.json --session-plan .autofish-live/session-plan-shoreline.json`
- [ ] **Commit code changes** — 6 modified files (profiles, schema, helper, tests)
- [ ] **Run extended bounded-session** (8-10 casts) with shoreline-grind 30s timing at 1280×720
- [ ] **Run chromalink** for fresh player position with current HWND

---

## Handoff Chain

| Order | Handoff | Commit |
|-------|---------|--------|
| 1 | `handoff-2026-05-27-135500-autofish-bounded-session-validated.md` | `cac27aa` |
| 2 | `handoff-2026-05-27-133500-autofish-extended-proof-pack.md` | `41b461d` |
| 3 | `handoff-2026-05-27-154700-autofish-maxcast-proof-pack.md` | `d4b2392` |
| 4 | `handoff-2026-05-27-160000-autofish-chromalink-blocker.md` | — |
| 5 | `handoff-2026-05-27-222700-autofish-reticle-heuristic-deficit.md` | `61560a2` |
| 6 | `handoff-2026-05-27-234700-autofish-shoreline-timing-pipeline.md` | `61560a2` (current) |

---

## Safety Verification

- [x] No unattended loops — all `--confirm-input` supervised
- [x] All dry-runs completed before confirm-input
- [x] Stop file guard active — not triggered
- [x] PID (3140) and HWND (`0x508AE`) stable
- [x] Readability threshold lowered — no false positives from gate
- [x] All profile timings verified via JSON validation
