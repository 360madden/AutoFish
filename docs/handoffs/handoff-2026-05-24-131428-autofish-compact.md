# AutoFish Compact Handoff - 2026-05-24 13:14 EDT

## Repo purpose

`C:\RIFT MODDING\AutoFish` is the scoped Rift AutoFish foundation: a Rift Lua addon, a .NET 10 WinForms helper, shared addon/helper contracts, and versioned fishing profiles for safe fishing-leveling automation.

## Current branch and state

- Branch: `main`
- Latest known commits:
  - `c79b882` - `Archive Rift script references and expand research library`
  - `2b52413` - `Freeze scope to Lua addon + .NET helper foundation`
- Working tree already had prepared-addon/probe changes before this handoff was created.
- This handoff is intended to be committed by itself; the prepared-addon changes should remain unstaged unless intentionally reviewed as their own coherent slice.

## Prepared but uncommitted addon/probe work

Known existing unstaged/untracked files at handoff time:

- Modified docs/meta:
  - `CHANGELOG.md`
  - `README.md`
  - `docs/framework-plan.md`
  - `docs/helper-operator-guide.md`
  - `lua/AutoFish/README.md`
- Untracked prepared addon/probe files:
  - `docs/addon-probe-plan.md`
  - `lua/AutoFish/Main.lua`
  - `lua/AutoFish/RiftAddon.toc`
  - `scripts/deploy-addon.ps1`

Treat these as prepared/offline work, not live-verified functionality.

## Validation snapshot

Last local check attempted with:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-local-checks.ps1
```

Observed result:

- .NET solution build: passed.
- Helper profile loading: passed for 3 profiles.
- Profile validation: passed for 3 profiles.
- Lua syntax/smoke section: blocked because `luac` was not available on PATH.

## Current blocker

The repo is still not live-complete. The prepared Rift addon manifest/entrypoint/deploy script need a narrow in-game validation pass before any claim that Rift API signals, pole/bag/buff detection, cast/bite/loot observations, or addon-helper transport work in the live client.

## Resume recommendation

Next best coherent slice: install or locate `luac`, rerun local checks, then review and either commit or revise the prepared addon diagnostics shell as one separate change set. Do not enable real fishing execution until live diagnostics confirm the required signals and fail-closed behavior.
