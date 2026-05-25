# AutoFish Compact Handoff - 2026-05-25

## TL;DR

`C:\RIFT MODDING\AutoFish` is a Rift MMO AutoFish prototype/foundation repo: Rift Lua addon + .NET 10 helper + shared contracts + profiles. The current active lane is **prototype-first live fishing**, not release hardening. Exact-window targeting and addon diagnostics work; the practical blocker is identifying the correct live fishing-start action/slot/item-use path and one fishable coordinate that starts a cast.

## Current repo state

- Branch: `main`
- Latest commit at handoff creation: `6347bfb Add AutoFish live milestone gates`
- Worktree has intentional unstaged prototype/live-validation changes.
- Do **not** assume these changes are committed.

Known changed/untracked files:

- Modified:
  - `README.md`
  - `docs/framework-plan.md`
  - `docs/live-validation/2026-05-24-g0-g1-live-attempt.md`
  - `lua/AutoFish/Main.lua`
- Untracked:
  - `docs/live-validation/2026-05-24-g2-live-signal-inventory.md`
  - `docs/live-validation/2026-05-24-g3-g4-observation-trace.md`
  - `docs/live-validation/2026-05-25-action-fishable-mapping.md`
  - `docs/prototype-first-workflow.md`
  - `scripts/invoke-live-fishable-point-probe.ps1`
  - `scripts/start-live-fishing-prototype.ps1`
  - this handoff file

## Live target snapshot

Latest known live Rift target from this session:

- Process: `rift_x64`
- PID: `89748`
- HWND: `0x2CD0D30`
- Title: `RIFT`
- Start time: `2026-05-24T13:20:04.8251137-04:00`
- Window/client: client roughly `640x360`, title visible as `RIFT`
- Character: `Atank`, level `45`, zone `Sanctum`, on shore by water
- Pole: `Beginner's Fishing Pole [inventory] slot=si02.009`
- Track Fish: detected
- Inventory: `estFree=4`

Reconfirm PID/HWND before any future input. Treat this snapshot as stale if the game/client restarted.

## Proven live milestones

- G0/G1 passed: exact target preflight, focus/capture, `/autofish help`, `/autofish status` work.
- G2/G3 partially passed: addon can report player, combat/secure, inventory/free slots, pole, Track Fish, ability scan, and castbar idle state.
- Fail-closed observation is working: no native `near_water`, no proven cast, low confidence, `can_cast=false`.
- Native APIs missing for fishable hover/interaction: `Inspect.Cursor` and `Inspect.Interaction` unavailable.
- `/autofish apis` added; live output showed `Command.Ability` exists but `Command.Item` is unavailable/empty in this addon context.

## Current practical blocker

Input infrastructure is no longer the main blocker. Bounded scripts can focus exact HWND, click client coordinates, press keys, and capture before/after. Multiple one-cast attempts did **not** visibly start fishing:

- key `8` + water points: no visible cast
- direct visible rod/action slot clicks around `(400,335)`, `(310,335)`, `(315,307)` + water/school points: no visible cast
- action-arm check did not reveal a targeting/armed state
- one earlier point produced `This area is not fishable`

Current narrow blocker: identify the real live action surface that starts fishing: correct hotbar page/slot, inventory item-use path, macro/command path, or correct fishable point sequence.

## Useful scripts added

Use PowerShell 7 (`pwsh`) when possible.

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\run-live-preflight.ps1 `
  -ExpectedProcessId 89748 `
  -ExpectedWindowHandle 0x2CD0D30 `
  -Focus `
  -Capture
```

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\invoke-live-fishable-point-probe.ps1 `
  -TargetProcessId 89748 `
  -TargetWindowHandle 0x2CD0D30 `
  -ClientX 250 `
  -ClientY 115 `
  -DryRun
```

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\start-live-fishing-prototype.ps1 `
  -TargetProcessId 89748 `
  -TargetWindowHandle 0x2CD0D30 `
  -ClientX 250 `
  -ClientY 115 `
  -MaxCasts 1 `
  -DryRun
```

Prototype script supports `-ActionClientX/-ActionClientY` for direct hotbar slot clicks, `-SkipInitialClick` for key-then-click, and `-EmergencyStopPath`.

## RiftReader reuse audit summary

Useful local repo: `C:\RIFT MODDING\RiftReader`.

Immediately useful pieces:

1. `scripts\get-rift-window-targets.ps1` - robust Rift PID/HWND discovery and window metadata.
2. `scripts\post-rift-key.ps1` - proven key delivery helper; already useful for slot/key probes.
3. `scripts\post-rift-command.ps1` - slash command delivery; adapt verification for AutoFish so it does not falsely fail on ReaderBridge-specific files.
4. `tools\rift-game-mcp\helpers\window-tools.ps1` - client capture, click, send-key, wait-for-change, compare-images, diff-region.
5. `tools\RiftReader.WindowTools` - C# exact-HWND inspect/click/resize tool; good replacement for duplicated PowerShell native click code.
6. `tools\RiftReader.SendInput` - C# key sender with scancode/virtual-key modes; good long-term input backend.
7. `tools\rift-window-capture` - capture/crop/diff pipeline for bobber/bite/loot visual fallback.
8. `reader\RiftReader.Reader\Lua\LuaAssignmentParser.cs` - reusable Lua SavedVariables parser.
9. `reader\RiftReader.Reader\AddonSnapshots\SavedVariablesFileLocator.cs` - reusable SavedVariables locator pattern.
10. `addon\ReaderBridgeExport\main.lua` and `addon\ReaderBridge\ReaderBridge_Logic.lua` - useful addon snapshot/dirty-state/castbar/buff patterns.

Not worth pulling now: navigation, actor memory, x64dbg/CE lanes, route/facing logic. Those are overkill for fishing prototype.

## Validation snapshot

Recently passed before this handoff:

- `dotnet build AutoFish.sln --configuration Release`
- `dotnet run --project src\AutoFish.App\AutoFish.App.csproj --configuration Release --no-build -- --validate-profiles`
- `scripts\validate-profiles.ps1`
- PowerShell parse checks for the two prototype scripts
- `git diff --check` passed except harmless LF->CRLF warnings

Not verified here:

- Lua syntax, because `lua`, `luac`, and `luajit` were not available on PATH.
- A successful live cast/catch; still blocked by action/fishable mapping.

## Resume instructions

Start practical, not process-heavy:

1. Reconfirm exact Rift PID/HWND.
2. Confirm the character is still on shore, not swimming.
3. Use numpad `*` if a native in-game screenshot is needed while Rift is focused.
4. Identify the true fishing action source before more architecture work.
5. Prefer a direct operator-assisted check: user points out/clicks the exact hotbar/inventory item, then codify it in the prototype script.
6. Once one cast visibly starts, capture the before/after and update `docs/live-validation/2026-05-25-action-fishable-mapping.md`.
7. Only after one fish/catch works, attempt `-MaxCasts 3`.

## Optional top 10 next best actions

1. Re-run exact preflight for the current Rift PID/HWND.
2. Take an in-game screenshot with numpad `*` for a clean ground-truth frame.
3. Ask the operator to manually start one cast and note the exact input sequence.
4. If manual start works, reproduce that exact sequence in `start-live-fishing-prototype.ps1`.
5. Adapt RiftReader `post-rift-command.ps1` into an AutoFish-specific slash-command sender/verifier.
6. Add a tiny hotbar coordinate calibration note/table to the live mapping doc.
7. Use RiftReader `window-tools.ps1` image diff around water/castbar after a manual cast.
8. Port/reuse `RiftReader.WindowTools` or `RiftReader.SendInput` instead of further PowerShell Add-Type duplication.
9. Add an AutoFish SavedVariables snapshot loader using RiftReader parser/locator patterns.
10. Commit the coherent doc/script/addon slice once the handoff and validation status are reviewed.
