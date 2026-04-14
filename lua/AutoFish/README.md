# AutoFish Lua Addon Scaffold

This folder contains the **in-game Lua-side core** for the split AutoFish architecture.

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

## Intentionally deferred

This scaffold does **not** claim to already be bound to the real Rift addon API.

The expected next live step is to map:

- real Rift observations into `onObservation`,
- real in-game UI primitives to `UI/Layout.lua` / `UI/ViewModel.lua`,
- and the validated desktop bridge transport to `MessageBus.lua`.
