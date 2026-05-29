# AutoFish — Reticle Heuristic Deficit Handoff

**Date**: 2026-05-27
**Updated**: 2026-05-27T22:27:00 UTC
**Repo**: `C:\Rift Modding\autofish`
**Branch**: `main`
**Remote**: `github.com/360madden/AutoFish`
**Commit (start)**: `61560a2` (docs: replace PowerShell code fences with bash, normalize path separators)

---

## TL;DR

Completed the **full proof pipeline** across **two review scopes** with **ChromaLlink fully operational**. Processed **48 manifests** encompassing chromalink, facing-delta, fishability-fan, one-cast, bounded-session, and slash proofs. **13 live casts** (3 + 10) across the current scope at **640×360 / fishable (320, 100)**.

**Zero red reticles detected** across every single one of the 13 casts — the reticle heuristic consistently sees `blueCyan` (water background) at 640×360, where earlier sessions at 1280×720 at least saw `yellow` bobber hints. This is the single blocking issue for autonomous bite detection.

| What | Status |
|------|--------|
| ChromaLink (current scope) | ✅ **Operational** — 2 fresh position captures |
| Facing-delta calibration | ✅ 315.0° and 321.6° (NW toward water) |
| Fishability-fan probes | ✅ 2 dry-runs, 3 in-bounds candidates each |
| oneCast signal (current scope) | ✅ Promoted (live evidence) |
| boundedSession signal (current scope) | 🔲 Needs formal promotion for 10-cast evidence |
| **Red reticle detections (all time)** | **❌ 0 across 29+ live casts** |
| Reticle at 640×360 | `blueCyan` only — water background dominates |
| Session plan | ✅ Fresh, created at 20:54 UTC, expires ~00:54 UTC |

---

## Two Review Scopes

This project now spans two independent scopes, each with their own decisions:

| Scope | Token | Session Plan | Fishable Point | Client Size | Live Casts | Decisions |
|-------|-------|-------------|---------------|-------------|------------|-----------|
| Old | `afscope-3711d8fdafbf50fd` | Expired | (640, 360) | 1280×720 | 21 (3+8+8+10, 3 partial) | `oneCast`=promote, `boundedSession`=promote |
| **Current** | **`afscope-63430969032699f1`** | **Active (~2h exp)** | **(320, 100)** | **640×360** | **13 (3+10)** | **`oneCast`=promote, `boundedSession`=needs decision** |

---

## ChromaLink Recovery

After 7 consecutive failures in the prior scope, ChromaLink was successfully restored:

| Attempt | Result | Classification |
|---------|--------|---------------|
| 8 (`145748`) | ✅ Fresh at 0.12s | `fresh-player-position` |
| 9 (`165112`) | ✅ Fresh at 0.16s | `fresh-player-position` |

**Position**: `x=7158.2 y=823.6 z=3222.1` (surface water, near previous position)

**Enabling actions**:
1. Deployed Lua addon to Rift AddOns (12+ files)
2. Resized Rift to native 640×360
3. Performed `/reloadui` in Rift
4. Restarted HttpBridge + CLI watch processes (PID 24512 + PID 9420)
5. Killed stale ChromaLink processes first

---

## Facing-Delta Calibration

| Attempt | Delta | Vector | Angle | Notes |
|---------|-------|--------|-------|-------|
| **#8** (`150349`) | dx=0.23, dy=-0.23 | (0.707, -0.707) | **315.0°** | Very small movement (0.32 units) |
| **#9** (`165308`) | dx=2.35, dy=-1.86 | (0.784, -0.621) | **321.6°** | Cleaner (3.0 units), preferred |

The 321.6° vector points NW — the character faces the water (confirmed by player position relative to known water edge). This was used for fishability-fan probes.

---

## Fishability-Fan Probes

Two dry-run probes, one per facing calibration:

| Probe | Facing | Origin | Forward | Candidates | In-Bounds |
|-------|--------|--------|---------|:----------:|:---------:|
| 1 (`150426`) | 315.0° | (320, 180) | (320, 80) | 9 | **3** |
| 2 (`165352`) | 321.6° | (320, 180) | (320, 80) | 9 | **3** |

Both probes returned 3 in-bounds candidates at 180px distance. The fishable point (320, 100) was selected from these candidates.

---

## Live Casts: Reticle Analysis

### One-Cast Proof

| Evidence | Result |
|----------|--------|
| Dry-run: gates passed | ✅ |
| Live: 6 BMP captures | ✅ |
| Red reticle detected | **0 px** |
| Classification | `bounded-one-cast-evidence` |
| Decision | **promote** |

### Bounded Session (3 casts) — `165826`

| Cast | Reticle | Red Detected | Manual Review |
|------|---------|:------------:|:-------------:|
| 1 | `unknown` | 0 | Required |
| 2 | `unknown` | 0 | Required |
| 3 | `unknown` | 0 | Required |

### Bounded Session (10 casts) — `172918`

| Cast | Reticle | Red Detected | Manual Review |
|:----:|:-------:|:------------:|:-------------:|
| 1 | `blueCyan` | 0 | Required |
| 2 | `blueCyan` | 0 | Required |
| 3 | `blueCyan` | 0 | Required |
| 4 | `blueCyan` | 0 | Required |
| 5 | `blueCyan` | 0 | Required |
| 6 | `blueCyan` | 0 | Required |
| 7 | `blueCyan` | 0 | Required |
| 8 | `blueCyan` | 0 | Required |
| 9 | `blueCyan` | 0 | Required |
| 10 | `blueCyan` | 0 | Required |

**Every cast at 640×360 produced `blueCyan` reticle** — the heuristic consistently classifies the water surface as `blueCyan` with `blue_cyan_requires_manual_review_due_to_water_background_risk`. This is a regression from 1280×720 where some casts saw `yellow` bobber pixels. The smaller client means the 220×220 reticle crop covers proportionally more water surface and less bobber detail.

---

## Cumulative Cast History (All Scopes)

| Session | Casts | Client | Reticle Colors | Red? |
|---------|:-----:|:------:|:--------------:|:----:|
| Bounded (3) — 09:51 | 3/3 | 1280×720 | unknown | 0 |
| Extended (8) — 11:22 | 8/8 | 1280×720 | blueCyan | 0 |
| Extended (8) — 11:25 | 8/8 | 1280×720 | blueCyan | 0 |
| Max-Cap (10) — 11:43 | 10/10 | 1280×720 | **yellow**, unknown | 0 |
| Max-Cap (10) — 11:54 | 7/10 | 1280×720 | **yellow** | 0 (fg lost) |
| **New scope — 3-cast (16:58)** | **3/3** | **640×360** | **blueCyan, unknown** | **0** |
| **New scope — 10-cast (17:29)** | **10/10** | **640×360** | **blueCyan** | **0** |
| **Total** | **29+ casts** | — | — | **0 red** |

The 1280×720 sessions at least saw yellow bobber pixels. The 640×360 sessions see only blueCyan water background. **This strongly suggests the reticle crop resolution is the limiting factor** — the 220×220 pixel crop at 640×360 captures less bobber detail than the same crop at 1280×720.

---

## Evidence Paths

| Category | Path |
|----------|------|
| Session plan (current) | `.autofish-live/session-plan-latest.json` |
| Decision register | `.autofish-live/signal-proof-decisions.json` |
| Summary (48 manifests) | `.autofish-live/signal-proof-summary-20260527-185024/summary.md` |
| Live one-cast (new scope) | `.autofish-live/signal-proof-one-cast-20260527-165643/manifest.json` |
| Bounded 3-cast (new scope) | `.autofish-live/signal-proof-bounded-session-20260527-165826/manifest.json` |
| Bounded 10-cast (new scope) | `.autofish-live/signal-proof-bounded-session-20260527-172918/manifest.json` |
| ChromaLink fresh (2) | `.autofish-live/signal-proof-chromalink-20260527-145748/` and `165112/` |
| Facing-delta 315° | `.autofish-live/signal-proof-facing-delta-20260527-150349/manifest.json` |
| Facing-delta 321.6° | `.autofish-live/signal-proof-facing-delta-20260527-165308/manifest.json` |
| Fishability-fan (315°) | `.autofish-live/signal-proof-fishability-fan-20260527-150426/manifest.json` |
| Fishability-fan (321.6°) | `.autofish-live/signal-proof-fishability-fan-20260527-165352/manifest.json` |

---

## Resume Checklist (Next Session)

- [ ] **Promote boundedSession decision** for new scope — `signal-proof decide --signal boundedSession --decision promote --evidence .autofish-live/signal-proof-bounded-session-20260527-172918/manifest.json --session-plan .autofish-live/session-plan-latest.json`
- [ ] **Address reticle-heuristic deficit** — investigate why 640×360 produces only `blueCyan` vs 1280×720's `yellow`:
  - Check if the 220×220 reticle crop is too large for 640×360 (captures more water) — possibly make the crop size proportional to client resolution
  - Alternatively, enlarge Rift to 960×540 (preferred minimum for readability) and recalibrate fishable point
- [ ] Increase `biteTimeoutMs` from 12s to 20-30s — Rift fish may take longer to bite; the helper might be pulling before a bite occurs
- [ ] Re-run one-cast proof at 960×540 with longer wait to verify red reticle can be detected at all
- [ ] Review BMP captures from all sessions for visual evidence of cast bar, loot messages, and fish

---

## Handoff Chain

| Order | Handoff | Commit |
|-------|---------|--------|
| 1 | `handoff-2026-05-27-135500-autofish-bounded-session-validated.md` | `cac27aa` |
| 2 | `handoff-2026-05-27-133500-autofish-extended-proof-pack.md` | `41b461d` |
| 3 | `handoff-2026-05-27-154700-autofish-maxcast-proof-pack.md` | `d4b2392` |
| 4 | `handoff-2026-05-27-160000-autofish-chromalink-blocker.md` | — |
| 5 | `handoff-2026-05-27-222700-autofish-retical-reticle-heuristic-deficit.md` | `61560a2` (this commit) |

---

## Safety Verification

- [x] No source code changes — only handoff file added
- [x] No unattended loops — all sessions manually supervised
- [x] Stop file (`STOP.txt`) guard active — not triggered
- [x] All `--confirm-input` commands preceded by `--dry-run`
- [x] Rift PID (3140) and HWND (`0x508AE`) unchanged throughout session
- [x] Only handoff file added to repo — no code modifications
- [x] Working tree clean (except `Untitled.png` in root)
