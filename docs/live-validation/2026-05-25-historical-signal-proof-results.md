# Historical signal proof results - 2026-05-25

## Scope

This note records the first live historical-signal proof pass after adding the Python helper and `/autofish invproof` lane. The run used the current local Rift client only and did not port, execute, or depend on old public bot scripts.

## Target and safety

- Rift PID: `89748`
- Rift HWND: `0x2CD0D30`
- Calibrated fishable client point: `(167,175)`
- Fishing key: `8`
- No movement input was sent.
- No unattended loop was run.
- The local `-` key was not used.

Window-size note:

- The live captures in this proof pass used the then-current small client size of roughly `640x360`.
- That size is not a helper limit. Larger Rift windows are supported and should be preferred for future proof screenshots.
- After resizing, rerun exact PID/HWND preflight and recalibrate fishable client X/Y before sending input.
- The helper now records a readability warning when the client is below `960x540`.
- A later focus-preflight bug was found: the old focus path used `SW_RESTORE` and could shrink/maximize-state-reset Rift back to its small restored size. AutoFish focus paths now only call `SW_RESTORE` when the target window is minimized.

## Sequential result

The strict Top 20 lane reached step 20, but two steps remain blocked/not promoted:

- Step 13: inventory deltas were not clear.
- Step 17: `/log` proof was blocked because no current enabled Rift log path is known.

## Inventory proof

Evidence:

- `.autofish-live/step10-one-attempt-20260525-180422/fishing-prototype-summary.json`
- `.autofish-live/invproof-before-20260525-172008/invproof-before-postmessage.png`
- `.autofish-live/invproof-after-20260525-180727/invproof-after-postmessage.png`
- `.autofish-live/invproof-diff-20260525-180858/invproof-diff.png`
- `.autofish-live/signal-proof-decisions.json`

Result:

- `/autofish invproof before` captured a baseline inventory snapshot.
- One bounded cast/catch/loot attempt was run at `(167,175)`.
- `/autofish invproof after` captured a post-attempt snapshot.
- `/autofish invproof diff` reported no item quantity changes.

Reviewed decision:

- `inventory`: `needs-more-evidence`

Interpretation:

The run produced game/chat feedback, but native inventory quantity deltas did not prove loot. Inventory proof must not be promoted until a visibly successful catch/loot produces repeatable item or raw slot deltas.

Follow-up code gap found:

The first diff only reported aggregate quantity changes. `lua/AutoFish/Main.lua` now adds raw slot-level diff reporting so a later run can distinguish no quantity change from slot add/remove/change evidence.

Follow-up smoke evidence:

- `.autofish-live/rawslot-diff-smoke-20260525-184005/rawslot-diff-smoke.png`
- `.autofish-live/rawslot-diff-smoke-20260525-184005/rawslot-diff-smoke-chat-crop-5x.png`

Result: the saved before/after proof replayed with the new raw-slot branch and reported `no item quantity or raw slot changes detected`.

## API discovery follow-up

The next addon-side evidence lane is read-only API discovery, not assumptions about historical bots. `/autofish api`, `/autofish apis`, and `/autofish events` now expose inventory, chat, cursor/interaction, and candidate progression namespaces (`Skill`, `Currency`, `Experience`, `Profession`, `Crafting`) when the local Rift API makes them visible.

This only proves namespace/key availability. A namespace must still produce useful live values or events during a manual fishing attempt before it can be promoted as a catch, loot, skill-up, or currency signal.

Follow-up helper gap found and patched:

- The normal `/autofish api`, `/autofish apis`, and `/autofish events` output is too tall for one visible chat screenshot.
- `signal-proof slash` now captures bounded slash-command output as full-client screenshots.
- `/autofish apicompact` now prints the key API proof facts in a compact screenshot-oriented form.

Live evidence:

- `.autofish-live/slash-help-live-validation-latest/manifest.json`
- `.autofish-live/slash-help-live-validation-latest/command-001-autofish-help-full-client.bmp`
- `.autofish-live/slash-api-live-validation-latest/manifest.json`
- `.autofish-live/slash-api-live-validation-latest/command-001-autofish-api-full-client.bmp`
- `.autofish-live/slash-api-live-validation-latest/command-002-autofish-apis-full-client.bmp`
- `.autofish-live/slash-api-live-validation-latest/command-003-autofish-events-full-client.bmp`
- `.autofish-live/slash-reloadui-live-validation-latest/manifest.json`
- `.autofish-live/slash-reloadui-live-validation-latest/command-001-reloadui-full-client.bmp`
- `.autofish-live/slash-apicompact-live-validation-latest/manifest.json`
- `.autofish-live/slash-apicompact-live-validation-latest/command-001-autofish-apicompact-full-client.bmp`
- `.autofish-live/slash-apicompact-live-validation-latest/command-001-autofish-apicompact-chat-crop-4x.png`
- `.autofish-live/preflight-focus-preserve-large-validation-latest/g0-preflight-summary.json`
- `.autofish-live/preflight-focus-preserve-large-validation-latest/g0-baseline.png`
- `.autofish-live/slash-apicompact-large-validation-latest/manifest.json`
- `.autofish-live/slash-apicompact-large-validation-latest/command-001-autofish-apicompact-full-client.bmp`
- `.autofish-live/slash-apicompact-large-validation-latest/command-001-autofish-apicompact-large-chat-crop.png`

Observed from the readable large-window `/autofish apicompact` capture:

- inventory APIs/signals are present: item list/detail, inventory slot utility, item slot/update events.
- chat/cursor/interact probes are present: `Event.Chat.Notify`, `Inspect.Cursor`, `Inspect.Tooltip`, and `Inspect.Interaction`.
- inspect progression: `Inspect.Currency` is available; `Inspect.Skill`, `Inspect.Experience`, `Inspect.Profession`, and `Inspect.Crafting` were not visible as available inspect namespaces.
- event progression: `Event.Currency` and `Event.Experience` are available; `Event.Skill`, `Event.Profession`, and `Event.Crafting` were not visible as available event namespaces.
- key details visible in the large capture: `Inspect.Currency` exposes `Category`, `Detail`, and `List`; `Event.Experience` exposes `Accumulated` and `Rested`; `Event.Chat` exposes `Notify` and `Npc`; `Event.Item` exposes `Slot` and `Update`.

Classification:

- slash-command output capture: `promote` as an evidence collection helper only.
- compact API namespace proof: `needs-more-evidence` until candidate event namespaces produce useful values during a manual catch/loot/skill-up attempt.

## Reticle and cursor proof

Evidence:

- `.autofish-live/signal-proof-reticle-20260525-181558/manifest.json`
- `.autofish-live/signal-proof-reticle-20260525-181656/manifest.json`
- `.autofish-live/signal-proof-reticle-20260525-181656/reticle-proof-contact-sheet.jpg`
- `.autofish-live/post-reticle-proof-full-20260525-182110/post-reticle-proof-full.png`
- `.autofish-live/preflight-large-reticle-candidate-latest/g0-preflight-summary.json`
- `.autofish-live/preflight-large-reticle-candidate-latest/g0-baseline.png`
- `.autofish-live/reticle-large-dryrun-1000-450-latest/manifest.json`
- `.autofish-live/reticle-large-dryrun-1244-382-latest/manifest.json`
- `.autofish-live/reticle-large-live-1244-382-latest/manifest.json`
- `.autofish-live/reticle-large-live-1244-382-latest/after-key.bmp`
- `.autofish-live/reticle-large-live-1244-382-latest/watch-015.bmp`
- `.autofish-live/signal-proof-summary-after-large-reticle-latest/summary.md`
- `.autofish-live/reticle-skip-click-dryrun-validation-latest/manifest.json`
- `.autofish-live/reticle-skip-click-live-validation-latest/manifest.json`
- `.autofish-live/reticle-skip-click-live-validation-latest/after-key.bmp`
- `.autofish-live/signal-proof-summary-after-skip-click-latest/summary.md`
- `.autofish-live/post-skip-click-state-latest/g0-baseline.png`
- `.autofish-live/slash-signals-during-reticle-latest/manifest.json`
- `.autofish-live/slash-signals-during-reticle-latest/command-001-autofish-signals-full-client.bmp`
- `.autofish-live/signal-proof-summary-after-reticle-signals-latest/summary.md`
- `.autofish-live/reticle-escape-cancel-latest/manifest.json`
- `.autofish-live/reticle-skip-click-cancel-live-validation-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-cancel-option-latest/summary.md`
- `.autofish-live/reloadui-after-signaltrace-counts-latest/manifest.json`
- `.autofish-live/preflight-after-signaltrace-counts-reload-latest/g0-preflight-summary.json`
- `.autofish-live/signaltrace-counts-start-live-latest/manifest.json`
- `.autofish-live/signaltrace-counts-reticle-live-latest/manifest.json`
- `.autofish-live/signaltrace-counts-reticle-live-latest/after-key.bmp`
- `.autofish-live/signaltrace-counts-stop-status-live-latest/manifest.json`
- `.autofish-live/signaltrace-counts-stop-status-live-latest/command-002-autofish-trace-status-full-client.bmp`
- `.autofish-live/signal-proof-summary-after-signaltrace-latest/summary.md`
- `.autofish-live/preflight-reticle-color-sweep-latest/g0-preflight-summary.json`
- `.autofish-live/reticle-color-sweep-water-left-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-water-known-yellow-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-bright-water-right-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-far-water-center-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-far-water-left-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-land-shore-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-near-player-shore-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-near-water-edge-left-latest/manifest.json`
- `.autofish-live/reticle-color-sweep-contact-sheet-latest/reticle-color-sweep-contact-sheet-8.jpg`
- `.autofish-live/signal-proof-summary-after-color-sweep-latest/summary.md`
- `.autofish-live/reticle-analyzer-validation-yellow-latest/manifest.json`
- `.autofish-live/reticle-analyzer-validation-far-center-review-latest/manifest.json`
- `.autofish-live/reticle-analyzer-validation-far-left-red-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-color-analyzer2-latest/summary.md`

Result:

- Dry-run reticle proof passed with exact PID/HWND and no input.
- One bounded reticle proof ran with `--confirm-input --watch-seconds 18`.
- Cursor handles changed across the run:
  - baseline: `0x10003`
  - after hover: `0x630ED0`
  - after key/click/watch: `0x39D40FA9`
- Heuristic crop colors included `blueCyan`, `green`, and `unknown`.

Large-window follow-up:

- Exact target was revalidated at PID `89748`, HWND `0x2CD0D30`, foreground, with a `1920x1009` client.
- Focus preservation did not call `SW_RESTORE` because the window was not minimized, so the large/maximized Rift window remained readable.
- The first large-window dry-run candidate `(1000,450)` was rejected because the crop overlapped the player.
- The second dry-run candidate `(1244,382)` was clean water and was used for one bounded live proof.
- At `(1244,382)`, pressing actionbar key `8` produced the yellow fishing reticle in the `after-key` capture.
- One left click immediately after the yellow reticle produced visible fishing cast evidence in the watch captures: a line leading to the water and a splash/ripple at the target area.
- The bounded run sent only one cursor move, one key `8`, and one left click; it did not send movement input or start an unattended loop.
- The large-window live run observed cursor handles `0x630ED0`, `0x3BF07A0`, and `0xBB065A`. The handle change is useful evidence, but it is not yet enough to define a durable state machine.
- A follow-up skip-click validation added `--skip-click` for reticle calibration. The live validation at `(1244,382)` sent one cursor move and one key `8`, captured the yellow `after-key` reticle plus short after-key watch captures, and sent no left click.
- The post-skip-click full screenshot showed a visible game tooltip at the reticle: `Deep Water`, `Requires Fishing 1`, and `Your skill is 9`.
- `/autofish signals` was run while that yellow reticle/tooltip was still visible. The addon printed `Inspect.Cursor type=nil held=nil`, `Inspect.Tooltip type=nil shown=nil extra=nil`, and `Inspect.Interaction none-active`.
- Escape cancellation was validated with the same exact PID/HWND: the crop changed from yellow reticle/cursor handle `0x3BF07A0` to normal water/cursor handle `0x630ED0`. `--cancel-after-key` was then added and live-validated so future skip-click proofs can automatically clear the targeting reticle unless the operator intentionally wants it left active.
- A follow-up addon-side trace patch records `Inspect.Cursor`, `Inspect.Tooltip`, and `Inspect.Interaction` values in bounded `/autofish trace` samples. A live trace over a skip-click key-`8` reticle proof recorded `samples=13` with `cursor_non_nil=0`, `tooltip_non_nil=0`, and `interaction_active=0`.
- A large-window color sweep then sampled eight client points with `--skip-click --cancel-after-key` and no left click. Clean water points produced visually yellow reticles; shore/land/too-far points produced visually red reticles. Within this run, yellow samples used OS cursor handle `0x3BF07A0`, while red/invalid samples used `0x39D40FA9`.
- No true blue/cyan reticle was proven in this sweep. Some manifests suggested `blueCyan`, but manual review showed the heuristic was dominated by water/highlight background pixels rather than a blue/cyan targeting reticle.
- The helper color analyzer was tightened after that finding. New manifests include `legacySuggestedReticleColor`, `suggestionReason`, and `manualReviewRequired`. Validation samples now classify a known yellow point as `yellow`, a red/orange invalid far-left point as `red` even when legacy counts say `blueCyan`, and a background-contaminated far-center sample as `unknown` with manual review required.
- The proof summarizer now reports legacy colors, color reasons, and manual-review-required captures. Manual-review counts are scoped to reticle-phase captures (`after-key`, `after-click`, and watch frames) so baseline or after-cancel background frames do not wrongly force a proof run into manual review.

Reviewed status:

- Cursor-handle changes are useful evidence.
- The large-window proof confirms the user's observation that key `8` can display a yellow cast reticle over water and that left click can start the fishing-pole cast animation.
- The visible `Deep Water` tooltip is useful visual evidence, but the current native `Inspect.Tooltip` and `Inspect.Interaction` probes did not expose that tooltip/hover state to the addon during this run.
- Native API hover detection is **not promoted**: the current local client exposed no useful cursor, tooltip, or interaction values while the visual yellow reticle was active.
- Pixel/reticle color classification is now `fallback-only` for helper-side calibration/proof because yellow valid-water and red invalid/too-far states are visually repeatable, but promotion still requires repeated casts and clean separation of valid reticle, invalid reticle, cast-start, bite-ready, and post-loot states.
- Treat `blueCyan` color stats as manual-review-only; current evidence shows water/background contamination can produce false blue/cyan suggestions, and the helper now flags those cases instead of silently suggesting blue/cyan.
- Reticle/cursor should remain a fallback candidate until repeated clean crops distinguish valid reticle, cast-start, bite-ready, and invalid states.

## Fishability fan planning follow-up

Evidence:

- `.autofish-live/preflight-fishability-fan-latest/g0-preflight-summary.json`
- `.autofish-live/fishability-fan-dryrun-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-fishability-fan-latest/summary.md`
- `.autofish-live/signal-proof-decisions.json`

Result:

- The current exact Rift target still resolves to PID `89748`, HWND `0x2CD0D30`.
- The target was minimized during this follow-up, so Windows reported the live client rect as `0x0`.
- To avoid forcing the game foreground or shrinking/restoring the game window, the proof used `--client-width 1920 --client-height 1009 --no-capture-crops`.
- The dry-run generated nine in-bounds screen-space candidate points from origin `(965,690)` toward operator-forward point `(1244,382)` using distances `180`, `280`, and `380` with lateral offsets `-120`, `0`, and `120`.
- No movement, fishing key, mouse click, or unattended loop was sent.
- This is planning evidence only. It does not prove water or fishability until a later bounded probe classifies each point from game feedback.

Reviewed decision:

- `fishabilityFan`: `needs-more-evidence`

Interpretation:

The repo now has a safer path for the user's proposed cone/fan approach: plan a forward screen-space fan first, then classify each candidate from castbar, chat/system error, item/inventory, skill/currency/progression, and only then fallback visuals. Coordinate-backed micro-step facing remains blocked because player actor facing is not exposed by the Rift API and a forward tap only becomes numeric evidence after a reliable before/after player coordinate source is proven.

## ChromaLink coordinate-provider follow-up

Evidence:

- `.autofish-live/chromalink-world-state-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-chromalink-latest/summary.md`
- `.autofish-live/signal-proof-decisions.json`

Result:

- AutoFish now has a read-only `signal-proof chromalink` command.
- The command sends no game input and does not modify ChromaLink.
- It queries ChromaLink's published local HTTP bridge endpoints: `/health`, `/ready`, and `/api/v1/riftreader/world-state`.
- The first run timed out against `http://127.0.0.1:7337`, so the current classification is `bridge-down-or-unreachable`.
- No ChromaLink coordinates were promoted or used.

Reviewed decision:

- `chromalinkWorldState`: `needs-more-evidence`

Interpretation:

ChromaLink is the correct read-only provider candidate for player coordinates because its addon reads `Inspect.Unit.Detail("player").coordX`, `coordY`, and `coordZ`. AutoFish must still fail closed until ChromaLink reports fresh `/health`, fresh world-state, `navigation.playerPositionAvailable=true`, and `player.position.fresh=true`. ChromaLink does not currently expose heading/facing/yaw, so any future facing estimate must be computed from fresh coordinate deltas and labeled as operational inference.

Follow-up implemented on 2026-05-26, pending live reload/proof:

- `/autofish coords` now prints the AutoFish addon's direct `Inspect.Unit.Detail` coordinate readout.
- Use the visible in-game output as a cross-check against ChromaLink `player.position` before trusting helper-side coordinate automation.
- This is still coordinate evidence only; it does not prove native actor facing/yaw.

## Facing-delta calibration follow-up

Evidence:

- `.autofish-live/facing-delta-dryrun-latest/manifest.json`
- `.autofish-live/signal-proof-summary-after-facing-delta-latest/summary.md`
- `.autofish-live/signal-proof-decisions.json`

Result:

- AutoFish now has a guarded `signal-proof facing-delta` command.
- The dry-run validated exact Rift PID `89748`, HWND `0x2CD0D30`.
- The target was foreground, non-minimized, and `1920x1009`.
- ChromaLink timed out, so fresh before-position was unavailable.
- No movement was sent.

Reviewed decision:

- `facingDelta`: `needs-more-evidence`

Interpretation:

This is the intended path for deriving a usable player-facing hint without native facing/yaw: fresh coordinates before a tiny forward pulse, one explicitly confirmed movement pulse, fresh coordinates after, then normalized X/Y delta. Because ChromaLink was not fresh, AutoFish stopped before movement. Once ChromaLink is fresh, rerun `facing-delta --dry-run` before using `--confirm-movement`.

## `/log` proof

Result:

- Blocked. No current enabled Rift log path was found under the checked Rift document/install paths.

Classification:

- `/log`: blocked pending known enabled log path/config.

## Layout proof

Evidence:

- `.autofish-live/signal-proof-layout-20260525-182758/manifest.json`

Result:

- Captured full client, hotbar, right bags, and chat regions.

Classification:

- Fixed layout remains fallback-only/profile-candidate evidence. Do not promote fixed bag/hotbar assumptions while native inventory proof is still unresolved.

## Next useful live step

Use current PID/HWND, not stale values, if the Rift process has restarted. Keep the larger window size whenever practical and recalibrate all client X/Y points after any resize.

Run a new manual catch cycle with visible catch/loot confirmation:

1. `/autofish invproof before`
2. one visibly successful manual catch/loot
3. `/autofish invproof after`
4. `/autofish invproof diff`

The new expected diagnostic is either:

- `no item quantity or raw slot changes detected`, or
- `raw slot changes detected` with per-slot add/remove/change lines.

Then repeat the clean reticle proof around the current fishable coordinate enough times to classify reticle/cursor as `fallback-only`, `promote`, or `retire`. Promotion still requires repeatability across multiple casts and a clear distinction between cast-valid, invalid, bite-ready, and post-loot states.

For the fishability fan lane, restore/maximize Rift only when the operator is ready for live evidence, rerun exact PID/HWND preflight, confirm current client size, and use the dry-run candidate manifest as the starting point for later bounded game-feedback classification.
