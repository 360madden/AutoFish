# Lua Addon Architecture

## Core modules

- `Core/Defaults.lua` - normalized addon settings.
- `Core/ProfileRuntime.lua` - applies profile-shaped settings into runtime config.
- `Core/Guardrails.lua` - high-priority safety decisions.
- `Core/SessionState.lua` - session object creation and maintenance resets.
- `Core/StateMachine.lua` - fishing flow decisions and counter updates.
- `Core/SnapshotBuilder.lua` - helper-facing snapshot projection.

## Bridge modules

- `Bridge/Contracts.lua` - command/message constants and contract version.
- `Bridge/CommandNormalizer.lua` - inbound command sanitation.
- `Bridge/EnvelopeBuilder.lua` - outbound envelope construction.
- `Bridge/MessageBus.lua` - in-memory inbound/outbound queues.

## UI modules

- `UI/Layout.lua` - declarative UI sections.
- `UI/ViewModel.lua` - state-to-view projection.
- `UI/Controller.lua` - UI intent to command conversion.

## Principle

The addon should own local state and safety. The helper should configure and supervise it, not replace it.
