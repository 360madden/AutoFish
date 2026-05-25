# AutoFish Incremental Development Goals

This milestone ladder is the guardrail for moving AutoFish from the current live diagnostic stage to a final usable product. Do not skip a gate: if a gate fails, fix that gate only.

## Current stage

AutoFish starts at **G0/G1 live diagnostic readiness**. A Rift client may be running and the character may be positioned at water, but live addon signals are not trusted until captured and logged.

Core rule: **no fishing automation loop until target identity, addon load, pole detection, cast/readiness signals, and fail-closed behavior are proven live.**

## Gates

| Gate | Goal | Exit criteria | Hard stop |
|---|---|---|---|
| G0 - Live Target Preflight | Identify exact `rift_x64` target before input. | One intended PID/HWND selected, foreground confirmed before input, baseline capture proves in-world character at water. | PID/HWND drift, ambiguous clients, non-responding window, foreground mismatch before input. |
| G1 - Addon Load Proof | Prove AutoFish slash diagnostics work in live Rift. | `/autofish help` and `/autofish status` respond, no Lua errors, player/in-game state visible. | Addon missing, command missing, Lua error, command delivery not proven. |
| G2 - Live Signal Inventory | Build the first real signal matrix. | Each signal is classified as `confirmed-native`, `visible-needs-mapping`, `missing`, or `errored`. | Slot `8` causes unexpected disruption, command errors, focus changes. |
| G3 - Observation Mapping | Map confirmed live fields into `rift-observation.schema.json` concepts. | A live observation can feed `AutoFishAddon:onObservation`; missing/ambiguous fields lower confidence and pause safely. | Required live fields cannot be represented and schema/versioning is not updated. |
| G4 - Manual One-Cast Trace | Trace one manually initiated cast without automation. | Pre-cast, cast, wait, bite/ready, loot/complete, and timeout observations are explicit where visible. | Bite/loot or castbar state cannot be observed reliably. |
| G5 - Advisory Mode | Recommend actions without performing them. | Recommendations match several manual casts and never recommend unsafe action. | Unsafe recommendation under combat, missing pole, full inventory, or ambiguous state. |
| G6 - Operator-Gated Single Action | Allow one approved action at a time. | One action is sent to exact bound HWND and before/after proof confirms intended effect. | Repeat behavior, missing emergency stop, or unproven target/focus. |
| G7 - Addon/Helper Live Bridge | Connect helper to real session state. | Helper displays live state, requests snapshots, syncs profile, and bridge loss pauses safely. | Helper starts replacing addon-owned safety. |
| G8 - Profile-Driven Short Session | Run a bounded supervised fishing session. | Hard-capped short session obeys profile pacing/guardrails and updates counters. | Unattended run pressure, target drift, low confidence, combat, full inventory, missing bait/pole. |
| G9 - Release Hardening | Package and document a maintainable product. | Clean validation, repeatable install, documented limits, final handoff/release checklist. | Stale live claims or undocumented failure modes. |

## Agent allocation

Use targeted agents only:

- **Live Target Agent**: PID/HWND discovery, focus/capture, target drift checks.
- **AutoFish Signal Agent**: slash command checklist, output classification, signal matrix.
- **Historical Reference Agent**: local archived Rift fishing sources as clues only.
- **Implementation Agent**: code changes only after live evidence selects the next slice.
- **Validation Agent**: build/profile/Lua checks and staged-output safety review.

Each agent must return evidence and a recommendation for one milestone-bounded task. No agent may advance to the next milestone without exit criteria.

## Interface policy

- No schema changes during G0-G2.
- G3 is the first allowed contract/schema change, and only if live evidence proves the current schema cannot represent confirmed signals.
- Bridge changes must follow `docs/bridge-contract-versioning.md`.
- Helper UI changes wait until signal names and confidence states are stable.

## Historical reference policy

Archived AutoIt/AHK/log/pixel sources under `docs/research` are reference-only. They may suggest signals to observe, such as cursor changes, autoloot, lure state, loot windows, and timeout thresholds, but must not be ported as primary runtime logic. Native addon APIs are preferred; helper-side cursor/pixel/log/audio methods are fallback modules only after native signals fail or cannot expose the needed state.

Because these historical methods are now a priority risk area, validate them through `docs/development/historical-signal-proof-lane.md`: each candidate must be proven current with a local evidence packet, then classified as `promote`, `fallback-only`, or `retire`.
