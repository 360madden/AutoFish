# AutoFish Lua Addon Scaffold

This folder contains the **in-game Lua-side core** for the split AutoFish architecture, plus a first live-loadable addon shell for probing player, buff, equipment, bag, and inventory state inside Rift.

## Included now

- `Core/Defaults.lua` - normalized addon-side defaults and thresholds.
- `Core/ProfileRuntime.lua` - profile-shaped runtime configuration mapping.
- `Core/Guardrails.lua` - high-priority safety decision rules.
- `Core/SessionState.lua` - session object creation and maintenance resets.
- `Core/StateMachine.lua` - local fishing/session state machine.
- `Core/SnapshotBuilder.lua` - snapshot projection for helper-facing status payloads.
- `Bridge/Contracts.lua` - shared string constants that align with desktop-side bridge contracts.
- `Bridge/CommandNormalizer.lua` - inbound command sanitation.
- `Bridge/EnvelopeBuilder.lua` - outbound bridge message envelopes.
- `Bridge/MessageBus.lua` - transport-agnostic inbound/outbound queue.
- `UI/Layout.lua` - declarative GUI layout description.
- `UI/ViewModel.lua` - GUI view-model projection from session snapshot data.
- `UI/Controller.lua` - UI intent-to-command translation.
- `AutoFishAddon.lua` - composition root that wires state, bridge, and GUI model together.
- `Main.lua` - live Rift addon entry point with `/autofish` diagnostics commands.
- `RiftAddon.toc` - addon manifest for live loading and saved-variable persistence.

## Prepared live diagnostics

The repository now contains a prepared Rift addon shell that is intended to verify the following when live testing resumes:

- addon startup/loading,
- player availability and zone,
- secure/combat state,
- castbar visibility,
- `Track Fish` buff presence,
- equipped and carried fishing-pole candidates,
- bag container discovery,
- inventory item counts and bait/lure candidates.

Slash commands:

- `/autofish status`
- `/autofish coords`
- `/autofish bags`
- `/autofish inventory`
- `/autofish invproof before|after|diff|status|clear`
- `/autofish pole`
- `/autofish abilities`
- `/autofish api`
- `/autofish apicompact`
- `/autofish apis`
- `/autofish signals`
- `/autofish events`
- `/autofish proof`
- `/autofish observe`
- `/autofish trace start|status|stop`
- `/autofish snapshot`
- `/autofish help`

`/autofish proof` is the compact screenshot-friendly state pack. It prints coordinates, combat/secure/castbar state, inventory free-slot summary, fishing candidates, observation flags, and focused cursor/tooltip/interaction API values in a few chat lines for helper review. It is diagnostic only and does not claim native water/facing truth.

For the current offline-only phase, treat these commands as documented/prepared rather than already live-verified.

## Intentionally deferred

This scaffold does **not** yet claim to perform real fishing actions in the live client.

The expected next live step is to map:

- real water/fishable-state observations into `onObservation`,
- real cast/bite/loot transitions into the state machine,
- real in-game UI primitives to `UI/Layout.lua` / `UI/ViewModel.lua`,
- and the validated desktop bridge transport to `MessageBus.lua`.
