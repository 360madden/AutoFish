# Online Rift Fishing Research Refresh

Date: 2026-05-25

## Scope

This refresh used three parallel research lanes so online findings could be separated by evidence type:

1. **Rift addon API surfaces**: find documented Lua APIs/events that can provide fishing-adjacent feedback.
2. **Historical Rift fishing scripts/tools**: identify old observation channels without copying or executing bot code.
3. **Existing Rift addon patterns**: inspect public addon pages/source availability for inventory, buff, ability, castbar, and event-loop patterns.

This is research for AutoFish design only. Public bot scripts/binaries are untrusted and must not become runtime dependencies.

## Bottom-line verdict

The strongest AutoFish path is still **API-first Lua observation plus Python helper fallbacks**:

1. Native addon observations first: castbar, inventory deltas, buffs/lures, ability usability/cooldown, secure/combat state.
2. Helper-side calibrated cursor/color/audio only when native signals fail live validation.
3. Historical `/log`, fixed UI coordinates, water pixels, and old AutoIt/AHK patterns are evidence of prior mechanics, not safe current architecture.

## Current gameplay evidence that matches online references

CADRIFT's fishing guide matches the latest local screenshots: activating the pole changes the cursor, hovering water shows a colored round symbol, clicking the symbol casts, and later the cursor changes to a fish symbol for reeling.

CADRIFT color semantics:

- Red: no fish here.
- Blue: shallow-water fish.
- Yellow: deep-water fish.
- Green: schools or treasure.

Local screenshots have already confirmed red, yellow, and blue/cyan reticles. Yellow and blue/cyan should be treated as valid click-confirmable cast points; red should be treated as invalid.

Source: https://www.cadrift.net/gameplay/crafting/fishing/

## Addon API findings

The public Seebs Rift API mirror exposes the best available online index of Rift addon API names. It is consistent with an in-game `Inspect.Documentation` style source and should still be live-verified in the client.

High-value surfaces for AutoFish:

| Signal | API surface | AutoFish value | Confidence |
|---|---|---|---|
| Cast start/end/progress | `Event.Unit.Castbar`, `Inspect.Unit.Castbar` | Detect fishing cast transitions if fishing uses player castbar state. | High API confidence; live fishing behavior unproven. |
| Inventory/catch/bait deltas | `Event.Item.Slot`, `Event.Item.Update`, `Inspect.Item.List`, `Inspect.Item.Detail`, `Inspect.Item.Find` | Detect caught items, consumed bait/lures, bag-full state. | High API confidence; live timing unproven. |
| Lure/Track Fish/buff state | `Event.Buff.Add`, `Event.Buff.Change`, `Event.Buff.Remove`, `Inspect.Buff.List`, `Inspect.Buff.Detail` | Track `Track Fish` and any lure/fishing effects that appear as buffs. | High API confidence; exact buff names need live capture. |
| Ability availability | `Inspect.Ability.New.List`, `Inspect.Ability.New.Detail`, `Event.Ability.New.*` | Discover fishing/lure ability IDs, usability, cooldown, range/target state. | High API confidence; exact ability mapping needs live capture. |
| Safety state | `Inspect.System.Secure`, `Event.System.Secure.Enter`, `Event.System.Secure.Leave`, `Event.Unit.Detail.Combat` | Pause in combat/secure states and explain blocked actions. | High. |
| Mouse/cursor/tooltip | `Inspect.Mouse`, `Event.Cursor`, `Inspect.Cursor`, `Inspect.Tooltip`, `Event.Tooltip` | Useful diagnostics/correlation. Cursor API appears to report held cursor contents, not guaranteed world-hover fishing reticle/bite icon. | Medium/low for fishing state until live-proven. |
| Chat/notification | `Event.Chat.Notify` | Possible failed-cast or warning text if Rift emits it as notify. | Low until live-proven. |
| Interaction | `Inspect.Interaction`, `Event.Interaction` | Not promising; documented interactions are bank/mail/auction/guildbank style, not fishing. | Low for fishing. |

Key API sources:

- API index: https://www.seebs.net/rift/pts/
- `Inspect.Cursor`: https://www.seebs.net/rift/pts/inspect_cursor.html
- `Event.Cursor`: https://www.seebs.net/rift/pts/event_cursor.html
- `Event.Unit.Castbar`: https://www.seebs.net/rift/pts/event_unit_castbar.html
- `Inspect.Unit.Castbar`: https://www.seebs.net/rift/pts/inspect_unit_castbar.html
- `Inspect.Item.List`: https://www.seebs.net/rift/pts/inspect_item_list.html
- `Inspect.Item.Detail`: https://www.seebs.net/rift/pts/inspect_item_detail.html
- `Event.Item.Slot`: https://www.seebs.net/rift/pts/event_item_slot.html
- `Event.Item.Update`: https://www.seebs.net/rift/pts/event_item_update.html
- `Inspect.Buff.List`: https://www.seebs.net/rift/pts/inspect_buff_list.html
- `Inspect.Buff.Detail`: https://www.seebs.net/rift/pts/inspect_buff_detail.html
- `Event.Buff.Add`: https://www.seebs.net/rift/pts/event_buff_add.html
- `Inspect.Ability.New.Detail`: https://www.seebs.net/rift/pts/inspect_ability_new_detail.html
- `Event.Chat.Notify`: https://www.seebs.net/rift/pts/event_chat_notify.html
- API Browser addon context: https://www.curseforge.com/rift/addons/apibrowser

## Historical script/tool findings

Historical Rift fishing tools repeatedly used these observation channels:

| Channel | Evidence | AutoFish takeaway | Risk |
|---|---|---|---|
| Cursor/pointer change | 2015 AutoIt thread says the fishing part waited on cursor changes; CADRIFT confirms visible cursor changes in gameplay. | Best helper-side fallback candidate if native Lua cannot see bite/reticle state. | OS cursor behavior may be stale; not proven addon-visible. |
| `/log` / chat-log parsing | MoeFish and older AHK discussions used `/log` or `log.txt`. | Keep as research-only unless current client proves useful. | Broken by patch changes, language, path, permissions, and message changes. |
| Pixel/color/image checks | Used for loot windows, water ripple checks, catch images, or generic key senders. | Last-resort fallback only. | Fragile across resolution, graphics quality, UI layout, shaders, and water rendering. |
| Audio amplitude | `faddison/riftreeler` is a Python proof-of-concept described as a Rift fishing bot that uses sound. | Optional helper-side diagnostic/fallback concept. | Machine/device/noise dependent and stale. |
| Hotbar/lure/bag conventions | Historical tools assumed specific rod/lure slots and autoloot settings. | Profiles should model bindings/settings explicitly rather than hard-code them. | Fixed positions are brittle. |

Important historical sources:

- Simple AutoIt Rift Fishing Bot: https://www.elitepvpers.com/forum/rift-hacks-bots-cheats-exploits/3863609-simple-autoit-rift-fishing-bot.html
- MoeFish Bot: https://www.elitepvpers.com/forum/rift-hacks-bots-cheats-exploits/2285108-moefish-bot-advanced-simple-fishing-bot.html
- Rift Fishing Assistant: https://www.elitepvpers.com/forum/rift-hacks-bots-cheats-exploits/2291047-rift-fishing-assistant.html
- TaultUnleashed MoeFish mirror: https://www.taultunleashed.com/rift-submissions/rift-fishing-bot-advanced-t83221.html
- `faddison/riftreeler`: https://github.com/faddison/riftreeler
- MouseLookToggle addon/helper reference: https://fabd.github.io/rift-mouselook-addon/

Do not copy or run public bot code or binaries. Use these only to understand possible observation channels and historical brittleness.

Priority follow-up: validate these stale historical channels through `docs/development/historical-signal-proof-lane.md` before promoting any of them into helper runtime behavior.

## Existing addon source/pattern findings

Installed/local helper addons are useful as API-pattern teachers, but AutoFish should not depend on them at runtime.

| Addon | Public source/license status found | Useful patterns | AutoFish decision |
|---|---|---|---|
| Imhothar's Bags / ImhoBags | CurseForge project; public CurseForge git; MIT license noted by research agent. | Inventory snapshots, `Inspect.Item.List/Detail`, `Event.Item.Slot`, `Event.Item.Update`, delayed rescans after load/reload. | Reimplement a minimal AutoFish inventory observer; no runtime dependency. |
| KaruulAlert | CurseForge project/zip; All Rights Reserved. | Buff/ability/cooldown/cast condition watching; ability scanner; dirty-on-event/tick-process pattern. | Conceptual reference only; do not copy code. |
| Gadgets | CurseForge project; public CurseForge git; BSD license noted by research agent. | Central unit/buff/castbar caches; normalized events; `Event.System.Update.Begin` processing. | Conceptual reference; no runtime dependency. |
| RiftMeter | CurseForge project/public source references; All Rights Reserved on CurseForge per research agent. | Event lifecycle, combat aggregation, recent-event style diagnostics. | Conceptual reference only; do not copy code. |

Public addon pages:

- ImhoBags: https://www.curseforge.com/rift/addons/imhobags
- Gadgets: https://www.curseforge.com/rift/addons/gadgets
- KaruulAlert: https://www.curseforge.com/rift/addons/karuulalert
- Rift Meter: https://www.curseforge.com/rift/addons/rift-meter
- Rift addon catalog context: https://www.curseforge.com/rift/

## Engineering implications for AutoFish

1. Addon should own minimal observers: `InventoryObserver`, `CastObserver`, `ConditionObserver`, and `RecentEvents`.
2. Event handlers should be thin: mark dirty, record compact facts, and defer heavier scans to a throttled update tick.
3. Inventory/catch success should be inferred from before/after item deltas around known cast windows.
4. Bite/reel timing has no proven native API event yet; live probes must determine whether cursor, castbar, tooltip, chat notify, buff, or inventory transitions expose it.
5. Helper-side fallback signals should carry source provenance, for example `source=addon`, `helper_cursor`, `helper_audio`, `helper_pixel`, or `legacy_log`.
6. Reload/UI reset behavior matters: after `reloadui`, reacquire addon state and delay initial inventory/API scans.
7. Python helper remains the best fit for local PC observation channels such as cursor shape/color/audio/screenshot correlation.

## Live validation checklist

Run these manually with the in-game addon probe before building a loop:

1. `/autofish api` before fishing to confirm API surface availability.
2. `/autofish events` after reload to confirm event tables are present.
3. Apply/enable `Track Fish`; record buff add/change/detail output.
4. Press actionbar 1 key `8`; record cursor, tooltip, ability usability, and castbar output.
5. Hover red/yellow/blue/green reticles; record cursor/tooltip/mouse outputs.
6. Left-click valid yellow/blue/green reticle; record castbar transitions and ability name/id.
7. Wait for bite/fish cursor; record any cursor, tooltip, chat notify, castbar, buff, or item events.
8. Reel/click; record loot/inventory item deltas.
9. Fill or nearly fill bags if safe; record bag-full behavior.
10. Press `-` reloadui; verify observers reset, delay scans, and repopulate state.

## Recommended detector priority

1. `secure/combat` guardrails.
2. `ability/cooldown/usable` for fishing/lures.
3. `castbar` for cast lifecycle.
4. `buff` for Track Fish/lures.
5. `inventory delta` for catch/loot/bait confirmation.
6. `chat notify` for error/failure messages if live-proven.
7. `cursor/tooltip/mouse` addon diagnostics if live-proven.
8. Python helper cursor-shape/reticle color fallback.
9. Python helper audio fallback.
10. Python helper pixel/image fallback.
11. Legacy log parsing only if current `/combatlog` or other logs prove useful.
