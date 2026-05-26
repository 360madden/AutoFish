# AutoFish compact handoff - live proof-pack Step 8 blocked

Date: 2026-05-26 19:41 -04:00
Repo: `C:\RIFT MODDING\AutoFish`
Branch: `main`
Remote: `https://github.com/360madden/AutoFish`

## TL;DR

The next optimal lane is still the **live `/autofish proof` proof-pack capture gate**. The run reached strict sequential **Step 7/20** and blocked at **Step 8/20** because the current Rift client was foreground and exact-target valid, but below the readable proof threshold.

No repo source code changed during the live attempt. Only ignored `.autofish-live` evidence files were written.

## Current blocker

Step 8 - read-only target snapshot failed `--require-readable`.

Observed target:

- PID: `218384`
- HWND: `0x7390DE6`
- title: `RIFT`
- foreground: `true`
- owner PID matched expected PID: `true`
- client size: `761x522`
- preferred readable minimum: `960x540`

Reason:

```text
Target client is minimized, unreadable, below preferred proof-capture size, or has no client origin.
```

In this case the specific failing condition was the below-threshold client size. The target was not minimized and was foreground.

## Evidence written

Ignored local evidence files:

- `C:\RIFT MODDING\AutoFish\.autofish-live\target-discovery-latest\g0-target-discovery.json`
- `C:\RIFT MODDING\AutoFish\.autofish-live\target-snapshot-latest.json`

These are intentionally not committed.

## Commands already run

```powershell
git status --short
git log --oneline -8
```

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\run-live-preflight.ps1 `
  -OutputRoot .autofish-live\target-discovery-latest
```

```powershell
python tools\autofish-helper-py\autofish_helper.py target-snapshot `
  --pid 218384 `
  --hwnd 0x7390DE6 `
  --require-readable `
  --output .autofish-live\target-snapshot-latest.json
```

Note: the first preflight attempt with Windows PowerShell 5.1 failed because `ConvertFrom-Json -Depth` is unavailable there. Use `pwsh` / PowerShell 7 for this repo's live helper scripts.

## Sequential progress snapshot

```text
Progress: [███████-------------] 7/20 complete, 35%

[x] 1. Review repo status and latest commits.
[x] 2. Review required docs.
[x] 3. Confirm working tree/evidence state.
[x] 4. Confirm no pre-live code changes are needed.
[x] 5. Confirm /autofish help includes /autofish proof.
[x] 6. Confirm /autofish proof still prints readable output.
[x] 7. Resolve current Rift PID and HWND.
[!] 8. Run read-only target snapshot. BLOCKED: client 761x522 is below readable threshold 960x540.
[ ] 9. Run slash proof-pack dry-run.
[ ] 10. Review dry-run manifest/captures.
[ ] 11. Confirm exact foreground before confirmed slash input.
[ ] 12. Run confirmed slash proof-pack capture.
[ ] 13. Review live BMP/readability and manifest.
[ ] 14. Run signal-proof summarize.
[ ] 15. Run doctor.
[ ] 16. Handle stale/invalid evidence blockers without deleting evidence.
[ ] 17. Record reviewed slash-signal decision if evidence is readable.
[ ] 18. Document live evidence paths and interpretation.
[ ] 19. Run validation.
[ ] 20. Commit, push, and verify remote/CI state.
```

## Next unblocked action

Manually enlarge or maximize the Rift game client so the **client area** is at least `960x540`, then resume from Step 7/8 with fresh target validation.

Recommended resume commands:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\run-live-preflight.ps1 `
  -OutputRoot .autofish-live\target-discovery-latest
```

Use the new PID/HWND from discovery, then run:

```powershell
python tools\autofish-helper-py\autofish_helper.py target-snapshot `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --require-readable `
  --output .autofish-live\target-snapshot-latest.json
```

If readable passes, continue:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof slash `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --default-proof-pack `
  --dry-run `
  --output-root .autofish-live\slash-proofpack-dryrun-latest
```

Only after exact PID/HWND and foreground still match:

```powershell
python tools\autofish-helper-py\autofish_helper.py signal-proof slash `
  --pid <CURRENT_RIFT_PID> `
  --hwnd <CURRENT_RIFT_HWND> `
  --default-proof-pack `
  --confirm-input `
  --output-root .autofish-live\slash-proofpack-live-latest
```

## Current classifications

No new signal was promoted because the proof-pack capture did not run.

- slash proof-pack: `needs-more-evidence`
- native water detection: `needs-more-evidence`
- facing detection: `needs-more-evidence`
- reticle/cursor/pixel proof: `needs-more-evidence`
- inventory proof: `needs-more-evidence`
- `/log` proof: `needs-more-evidence`, blocked pending known enabled Rift log path
- fixed layout proof: `fallback-only`, not tested in this run

## Safety reminders

- Do not reuse old PID/HWND after resizing, restarting, or refocusing Rift.
- Do not force the game window back to a small size.
- Do not use `-`; this setup binds it to reloadui.
- Slash proof confirmed input may only send `/autofish proof` and Enter.
- No movement, fishing key, mouse click, or unattended loop is allowed in this proof-pack gate.
- Keep `.autofish-live` evidence local/ignored unless a future task explicitly asks to sanitize and publish selected artifacts.
