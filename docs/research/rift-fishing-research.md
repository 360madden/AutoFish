# Rift Fishing Research Library

Last updated: 2026-05-25

## Scope

This is a **Rift-only** research pass for `C:\RIFT MODDING\AutoFish`.

- WoW references were intentionally excluded.
- Findings are split by **confidence** and by **where the signal exists**:
  - native Rift addon/API
  - player-visible game/UI behavior
  - historical external scripts/tools

## Research library layout

This folder now has three separate roles:

- `C:\RIFT MODDING\AutoFish\docs\research\rift-fishing-research.md`
  - human-readable narrative
  - explains what seems true, false, promising, or brittle
- `C:\RIFT MODDING\AutoFish\docs\research\rift-fishing-library.json`
  - source catalog
  - strings, APIs, historical implementations, and architecture notes
- `C:\RIFT MODDING\AutoFish\docs\research\rift-fishing-cross-reference.json`
  - signal-by-signal verdict matrix
  - cross-references signals ↔ APIs ↔ methods ↔ evidence backlog
- `C:\RIFT MODDING\AutoFish\docs\research\archive`
  - preserved third-party Rift artifacts that were actually retrievable
  - includes a manifest of archived vs unresolved script sources
- `C:\RIFT MODDING\AutoFish\docs\research\2026-05-25-online-fishing-research-refresh.md`
  - agentic online refresh covering addon API surfaces, historical fishing scripts/tools, and installed-addon source-pattern lessons

Use them in this order:

1. read this `.md` file for context
2. check `rift-fishing-cross-reference.json` for what should be built first
3. use `rift-fishing-library.json` to trace every verdict back to sources and strings

## Cross-reference workflow

When new information is gathered, update the library like this:

1. add the source or observation to `rift-fishing-library.json`
2. update the affected signal in `rift-fishing-cross-reference.json`
3. change the verdict only if the evidence quality improved materially
4. move the related item in the evidence backlog if a live uncertainty was resolved

This keeps the research library usable as an engineering tool instead of just a note dump.

## Archived script artifacts

Full artifacts currently archived:

- `C:\RIFT MODDING\AutoFish\docs\research\archive\forum-extracts\epvp-simple-autoit-rift-fishing-bot-lure.au3`
- `C:\RIFT MODDING\AutoFish\docs\research\archive\forum-extracts\epvp-simple-autoit-rift-fishing-bot-original.au3`
- `C:\RIFT MODDING\AutoFish\docs\research\archive\external-src\rift-mouselooktoggle`

Reference-only, not archived as full scripts:

- `Rift Fishing Assistant` thread: public thread text available, but download links are hidden behind registration-only wrappers
- `MoeFish` / Tault page: public description available, but no direct retrievable script attachment was exposed
- `OwnedCore [REQ] Working Fishbot`: discussion and hints only, not a full posted script

## Executive summary

### Main conclusions

1. **Track Fish and fish-school data are the strongest verified Rift-native fishing signals.**
2. **Visible cursor changes clearly existed in live gameplay and historical scripts used them successfully, but Rift's addon cursor API appears to describe drag/drop cursor contents, not the world-hover fishing cursor.**
3. **Historical bots that depended on `/log`, fixed UI layouts, water ripple pixels, or exact resolutions did work at times, but they broke often.**
4. **The best AutoFish path is a modular detector chain:**
   1. buff/state/inventory/castbar/secure-mode observations inside the addon
   2. route/pool awareness from Track Fish and location tooling
   3. optional helper-side calibrated cursor/loot fallbacks
   4. raw splash/water pixel logic only as a last resort

### Important negative findings

- `Inspect.Cursor()` is documented as returning cursor **contents** such as `"ability"` or `"item"`, not a fishing-hover icon. So **addon-only fish-cursor detection is unverified**.
- `Inspect.Interaction()` only documents `"auction"`, `"bank"`, `"guildbank"`, and `"mail"`. It is **not** a generic world-object interaction detector.
- `Command.Message.Send/Broadcast/Receive` are useful for **addon-to-addon** messaging, but they do **not by themselves** create a bridge to the external desktop helper.
- Historical `/log`-driven fishing scripts should be treated as **unstable legacy patterns**, especially because the current official slash-command documentation exposes `/combatlog`, not historical `/log`.

## API-first takeaway

The current evidence strongly supports your instinct that **a lot can be obtained from the API**.

### Highest-value API groups

1. **Buff APIs**
   - `Inspect.Buff.List`
   - `Inspect.Buff.Detail`
   - best current path for `Track Fish`
   - likely best path for lure-state discovery if lures surface as buffs

2. **Item APIs**
   - `Inspect.Item.List`
   - `Inspect.Item.Detail`
   - `Inspect.Item.Find`
   - best current path for lure inventory, slot mapping, and bag-independent logic

3. **Castbar APIs**
   - `Event.Unit.Castbar`
   - `Inspect.Unit.Castbar`
   - strongest candidate for real cast timing if fishing uses castbar state

4. **Secure-state APIs**
   - `Inspect.System.Secure`
   - `Event.System.Secure.Enter`
   - `Event.System.Secure.Leave`
   - already good enough for production guardrails

5. **Settings and map APIs**
   - `Inspect.Setting.List`
   - `Inspect.Setting.Detail`
   - `Inspect.Map.Detail`
   - useful for autoloot assumptions and route/profile context

### Lower-confidence or lower-value API groups

- `Inspect.Cursor` / `Event.Cursor`
  - interesting, but still not proven for fishing hover state
- `Inspect.Interaction` / `Event.Interaction`
  - not documented as a fishing-world interaction channel
- `Command.Message.*`
  - useful for addon-to-addon messaging, not for the desktop helper bridge

## Source confidence guide

- **High**: official gamigo support docs, API docs, current community guides with concrete gameplay details.
- **Medium**: addon pages and historical tool pages with specific technical notes.
- **Low**: bot/cheat forum posts that are useful as clues but should not be treated as authoritative on their own.

## Source matrix

| Source | Type | Confidence | Key findings | Why it matters |
|---|---|---:|---|---|
| [RIFT - Creating Macros](https://support.gamigo.com/en/support/solutions/articles/201000105449-rift-creating-macros) | Official support | High | Rift has a macro editor; macros can be saved and dragged to an action bar; `cast <ability>` style commands are supported. | Confirms macro-based execution remains a real in-game mechanism. |
| [RIFT - Slash Commands](https://support.gamigo.com/en/support/solutions/articles/201000105480-rift-slash-commands) | Official support | High | Documents `/macro`, `/combatlog`, `/loc`, `/exportkeybindings`, `/exportui`, `/importui`. | Useful for calibration, route authoring, and config portability; also shows modern docs use `/combatlog`, not `/log`. |
| [How do I import UI settings from another character in RIFT?](https://support.gamigo.com/en/support/solutions/articles/201000105458-rift-how-do-i-import-ui-settings-from-another-character-in-rift-) | Official support | High | `/exportui` writes `UI.dat`; `/importui` reloads it. | Useful for stabilizing calibration-dependent layouts across characters. |
| [Fishing – CADRIFT](https://www.cadrift.net/gameplay/crafting/fishing/) | Community guide | High | Fishing cursor changes are visible to players; water symbols encode fishability; `Track Fish` reveals blue-diamond schools; school types are named. | Best live-game fishing behavior reference found. |
| [UI Customization - Telarapedia](https://telarapedia.fandom.com/wiki/UI_Customization) | Community wiki | High | Rift addons are Lua-based and event/callback driven. | Confirms addon architecture assumptions. |
| [Rift API Docs (PTS mirror)](https://www.seebs.net/rift/pts/) | Community mirror of API docs | High | Documents `Inspect.*`, `Event.*`, secure-mode events, macro event wiring, item/buff/settings/map inspection, queue/message functions. | Primary technical source for addon-surface candidates. |
| [ResourceTracker - RiftUI](https://www.riftui.com/downloads/info335-ResourceTracker.html) | Addon page/search snippet | Medium | Added fishing nodes, warns when the relevant `Track XXX` buff is missing, had combat-hide and some performance issues in versions/comments. | Strong clue that fish tracking is buff-driven and observable in addons. |
| [Simple Autoit Rift Fishing Bot](https://www.elitepvpers.com/forum/rift-hacks-bots-cheats-exploits/3863609-simple-autoit-rift-fishing-bot.html) | Historical script thread | Medium | Used cursor-change detection for fishing, pixel checks for loot, required windowed mode and water ripple, optional lure clicks, autoloot off. | Best documented external fishing implementation pattern found. |
| [MoeFish BOT: advanced-simple fishing bot](https://www.elitepvpers.com/forum/rift-hacks-bots-cheats-exploits/2285108-moefish-bot-advanced-simple-fishing-bot.html) | Historical script thread | Medium | Required `/log`, English client, windowed/windowed fullscreen, autoloot on, rod in slot 1; later rewrote detection and moved loot logic to logs/calibration. | Shows how one popular bot evolved and what broke. |
| [[REQ] Working Fishbot](https://www.ownedcore.com/forums/mmo/rift/387544-req-working-fishbot.html) | Historical forum thread | Low/Medium | Shared AHK-style code using splash pixels, `log.txt`, lure-decay strings, and the advice “check cursor change.” | Useful only as evidence of mixed pixel/log approaches and their brittleness. |
| [Simple Fish Bot](https://www.ownedcore.com/forums/mmo/rift/419314-simple-fish-bot.html) | Historical forum thread | Low | Mixed claims of long unattended runs and at least one 24-hour ban report. | Cautionary signal for unattended external-input automation risk. |
| [Mouse Look Toggle Script and Addon for Rift MMO](https://fabd.github.io/rift-mouselook-addon/) | Addon + AHK helper page | Medium | Confirms real Rift addon+AHK hybrid patterns, keybinding/export usage, windowed/fullscreen limitations, shader sensitivity, and historical AHK reliability concerns. | Useful for environment constraints and helper-side design cautions. |

## Verified Rift-native signals, APIs, and limits

### High-confidence addon/API surfaces

| API surface | Verified behavior | Confidence | AutoFish relevance |
|---|---|---:|---|
| [`Inspect.Buff.List`](https://www.seebs.net/rift/pts/inspect_buff_list.html) | Lists buffs on a unit. | High | Detect `Track Fish` and any lure/fishing-related buff once identified live. |
| [`Inspect.Buff.Detail`](https://www.seebs.net/rift/pts/inspect_buff_detail.html) | Returns buff name, duration, remaining time, icon, stacks, description, etc. | High | Lets the addon turn a raw buff ID into a named fishing signal. |
| [`Inspect.System.Secure`](https://www.seebs.net/rift/pts/inspect_system_secure.html) | Returns current secure mode. | High | Direct input to combat/secure guardrails. |
| [`Event.System.Secure.Enter`](https://www.seebs.net/rift/pts/event_system_secure_enter.html) / [`Leave`](https://www.seebs.net/rift/pts/event_system_secure_leave.html) | Secure mode enter/leave events. | High | Hard pause/resume guardrail boundary. |
| [`Inspect.Setting.List`](https://www.seebs.net/rift/pts/inspect_setting_list.html) / [`Inspect.Setting.Detail`](https://www.seebs.net/rift/pts/inspect_setting_detail.html) | Lists current settings and returns `{ id, value }` for a setting. | High | Candidate calibration layer for settings like autoloot and UI-related dependencies once IDs are mapped. |
| [`Layout:EventMacroSet`](https://www.seebs.net/rift/pts/layout_eventmacroset.html) | Attaches a macro to a frame event; requires secure frame and insecure environment. | High | Strong indicator that macro-triggerable UI modules should stay isolated and optional. |
| [`Command.Console.Display`](https://www.seebs.net/rift/pts/command_console_display.html) | Prints text to general/combat/custom console. | High | Good built-in addon diagnostics sink. |
| [`Event.Unit.Castbar`](https://www.seebs.net/rift/pts/event_unit_castbar.html) / [`Inspect.Unit.Castbar`](https://www.seebs.net/rift/pts/inspect_unit_castbar.html) | Exposes castbar visibility and details including `abilityName`, `begin`, `duration`, `remaining`. | High | Strong candidate for cast-line timing if fishing shows up as a castbar event in the live client. |
| [`Inspect.Item.List`](https://www.seebs.net/rift/pts/inspect_item_list.html), [`Inspect.Item.Detail`](https://www.seebs.net/rift/pts/inspect_item_detail.html), [`Inspect.Item.Find`](https://www.seebs.net/rift/pts/inspect_item_find.html) | Enumerates inventory items and item details; includes names, cooldowns, stacks, descriptions. | High | Best native candidate for lure inventory discovery and cooldown-aware lure maintenance. |
| [`Inspect.Map.Detail`](https://www.seebs.net/rift/pts/inspect_map_detail.html) | Returns map location details including coordinates and title. | High | Useful for route/profiling support if live map locations can be tied to fishing nodes or travel markers. |

### Important API caveats

| API surface | What the docs actually say | Confidence | Practical conclusion |
|---|---|---:|---|
| [`Inspect.Cursor`](https://www.seebs.net/rift/pts/inspect_cursor.html) / [`Event.Cursor`](https://www.seebs.net/rift/pts/event_cursor.html) | Returns cursor **contents**, with types such as `"ability"`, `"item"`, `"itemtype"`, or `nil`. | High | This does **not** prove the addon can read the fishing-hover cursor icon. Treat addon-side cursor detection as unverified until tested live. |
| [`Inspect.Interaction`](https://www.seebs.net/rift/pts/inspect_interaction.html) / [`Event.Interaction`](https://www.seebs.net/rift/pts/event_interaction.html) | Only documents `"auction"`, `"bank"`, `"guildbank"`, and `"mail"`. | High | Not a fishing-world interaction detector. Do not build the fishing adapter around it. |
| [`Command.Message.Send`](https://www.seebs.net/rift/pts/command_message_send.html), [`Command.Message.Broadcast`](https://www.seebs.net/rift/pts/command_message_broadcast.html), [`Command.Message.Accept`](https://www.seebs.net/rift/pts/command_message_accept.html), [`Event.Message.Receive`](https://www.seebs.net/rift/pts/event_message_receive.html) | Reliable/unreliable **addon messages** with accept filters and throttling. | High | Useful for in-game addon messaging patterns, but **not** for desktop-helper transport by themselves. |
| [`Inspect.Queue.Status`](https://www.seebs.net/rift/pts/inspect_queue_status.html) | Reports queue throttling / available size. | High | Good for diagnostics if addon messaging is ever used, but not a fishing signal. |

## Historical implementation matrix

| Implementation | Detection method | Action method | Required setup | What worked | What broke / stayed brittle |
|---|---|---|---|---|---|
| **Simple Autoit Rift Fishing Bot** | OS-level cursor change for fishing, local pixel/static-region check for loot | Press bound rod key, click chosen fishing point, optional lure clicks from bag positions | Windowed mode, fish in lower half of screen, rod on slot `1`, autoloot **off**, visible water ripple, bags open for lures | Well documented; cursor-change approach reduced raw splash dependence | Resolution assumptions, graphics quality, non-rippling water, loot heuristic sensitivity |
| **MoeFish** | Initially calibration/pixel based, later log-based loot detection, later detection rewrite | Keybind slots, optional lure slots, calibrated cast points | English client, `/log`, windowed or windowed fullscreen, autoloot **on**, rod in slot `1`, lures in fixed slots | Popular enough to accumulate version history; “any resolution works now” was a real iteration goal | Language dependence, lag tuning, detection rewrites, log dependence, layout sensitivity |
| **Simple Fish Bot / AHK snippet** | Mixed `PixelSearch` splash detection + `log.txt` string checks | Send rod key, mouse click fishing point, bait key and bag click | Manual screenshot color sampling, Windows profile path, rod/bait bindings, log file path | Shows hybrid fallback pattern: use multiple weak signals together | Heavy manual calibration, log-path brittleness, color tolerance issues |
| **ResourceTracker addon** | Native track-buff and node-state tracking | None; informational addon | Correct `Track Fish` buff active | Confirms fish nodes can be surfaced in addon UI and missing-buff warnings are useful | Some versions/comments mention lag or stutter, especially around ghost mode |
| **MouseLookToggle addon + AHK** | UI recognition/pixel signaling + addon state | External input helper bound to keys/mouse | Active Rift window, windowed/windowed fullscreen, stable chat window, no color-altering shaders | Demonstrates a modular addon + helper split is viable in Rift | Fullscreen issues, moved UI, resolution changes, shader/filter breakage, historical AHK reliability concerns |

## What historically worked best

### 1) Track Fish / fish-school awareness

Highest-confidence outcome:

- `Track Fish` is real and buff-driven.
- Schools appear as **blue diamonds** on the minimap.
- Known school types found consistently in current/historical references:
  - `School of Fish`
  - `School of Rare Fish`
  - `School of Clever Fish`
  - `Sunken Boat`

Why this matters:

- This is the cleanest route/pool optimization input found.
- It is also the strongest evidence that the addon should understand **pool type**, not just “fishable or not.”

### 2) Player-visible cursor changes

Current guide evidence:

- CADRIFT describes:
  - pole active -> **use hand** cursor
  - hover water -> colored round symbol
  - fish-ready -> **fish** cursor, then left click to reel in

Historical script evidence:

- The 2015 AutoIt script explicitly says it “doesn't use the screen at all for the fishing part” and instead waits for cursor changes.
- OwnedCore advice explicitly summarized the easy mode as: **“check cursor change.”**

Why this matters:

- Cursor changes clearly worked for **external** fishing automation.
- But the addon docs do **not** prove those world-hover cursor states are visible to addon Lua.

Practical conclusion:

- Treat cursor-change detection as the best **helper-side fallback**, not yet as a proven addon-native signal.

### 3) Castbar- and buff-driven state

This is an inference from official API docs plus current architecture:

- `Inspect.Unit.Castbar` can expose `abilityName`, duration, and remaining time.
- `Inspect.Buff.Detail` can expose names and timers for buffs.

Practical conclusion:

- If live fishing uses a castbar and/or lure buff, these are safer native inputs than pixel heuristics.
- They should be tested before building any screen-driven detector.

## What repeatedly broke or stayed fragile

### 1) `/log`-driven behavior

Evidence:

- Historical scripts explicitly required `/log` and `log.txt`.
- Current official slash-command docs list `/combatlog`, not `/log`.
- Historical snippets show people complaining about missing or changed `log.txt`.

Conclusion:

- Log scraping is historical evidence, not a stable architecture.
- It can stay in the research library as a fallback experiment, but should not drive core design.

### 2) Resolution-, UI-scale-, and layout-dependent detection

Evidence:

- AutoIt and MoeFish both needed specific visual/setup expectations.
- MouseLookToggle documents failures when the chat window moves or resolution changes.
- UI import/export is explicitly useful because layout stability matters.

Conclusion:

- Any screen-dependent logic must live behind calibration modules, never in the core state machine.

### 3) Water ripple / splash pixel logic

Evidence:

- AutoIt loot detection depended on water visibly rippling.
- AHK snippets used splash colors and tolerance windows.
- Reflection/water variation was a recurring problem in historical discussions.

Conclusion:

- Raw water scanning is too fragile to be the first fishing detector.

### 4) Language-dependent parsing

Evidence:

- MoeFish explicitly required the client language to be **ENGLISH**.
- Historical log-token approaches relied on exact strings such as lure decay and catch messages.

Conclusion:

- Any string-parsing strategy must be localized or avoided.

## Useful strings, settings, and tokens

### Game-facing strings

- `Track Fish`
- `School of Fish`
- `School of Rare Fish`
- `School of Clever Fish`
- `Sunken Boat`
- `use hand` cursor
- `fish` cursor

### Settings and UI terms

- `Auto-Loot By Default`
- `Target Nearest in Front of Player`
- `Smart Target`
- `Windowed`
- `Windowed Fullscreen`

### Slash commands and config portability

- `/macro`
- `/combatlog`
- `/loc`
- `/exportkeybindings`
- `/importkeybindings`
- `/exportui`
- `/importui`
- `UI.dat`

### Historical script tokens and conventions

These are **legacy research tokens**, not trusted modern contract fields:

- `log.txt`
- `lure has decayed`
- `away`
- `stop fishing`
- `received`
- rod in hotbar slot `1`
- lure slots `2` / `3` / `4`

## Design implications for `C:\RIFT MODDING\AutoFish`

### Recommended detector priority

1. **Track Fish / buff state**
2. **Castbar state**
3. **Inventory + lure item state**
4. **Secure/combat state**
5. **Route/location context**
6. **Helper-side calibrated cursor/loot detection**
7. **Raw splash/water pixel scanning**

### Recommended module breakdown

- `Observation/TrackFishDetector`
- `Observation/BuffDetector`
- `Observation/CastbarDetector`
- `Observation/LureInventoryDetector`
- `Observation/SettingsProbe`
- `Observation/RouteContext`
- `Execution/SecureMacroTrigger`
- `Execution/ExternalInputHelper`
- `Calibration/VisualProfile`
- `Calibration/LayoutProfile`
- `Diagnostics/SignalTrace`

### Recommended feature toggles

- `useTrackFish`
- `useCastbarDetection`
- `useLureInventoryDetection`
- `useHelperCursorProbe`
- `useHelperLootProbe`
- `useLegacyLogExperiment`
- `useRawWaterPixelFallback`

### Practical implementation order

1. Prove whether live fishing emits a usable castbar and/or buff footprint.
2. Identify the exact live buff name/icon/id for `Track Fish`.
3. Map lure inventory and cooldown candidates using `Inspect.Item.List/Detail`.
4. Add a helper-side cursor/loot calibration module only if addon-native signals are insufficient.
5. Keep every screen-dependent detector removable via feature flags.

## Open questions that still require live testing

- Does fishing create a player castbar event reliably enough to drive `lineCast` / `canCast`?
- Is `Track Fish` best detected by buff name, icon, or both?
- Do lures show up more reliably as item inventory state, buff state, or both?
- Can any native API expose fish-ready state directly, or will that always require helper-side visual detection?
- Which setting IDs correspond to autoloot and other fishing-relevant options in the live client?

## Bottom line

The research pass points to a clear direction:

- **Use Rift-native buff/castbar/item/secure-state data first.**
- **Use fish-school tracking as a first-class system.**
- **Keep cursor/loot visual logic helper-side and calibrated.**
- **Treat `/log`, raw splash pixels, and one-resolution assumptions as legacy fallbacks only.**
