# Bridge Contract Versioning Rules

AutoFish bridge traffic is contract-first. Before the live transport is implemented, the addon and helper need an explicit compatibility policy so changes can be reviewed safely.

## Baseline

- Current contract baseline: `1.0.0`.
- Versioning applies to bridge command envelopes, session/status envelopes, and any future transport metadata.
- Payloads must remain understandable across the full lifetime of the supported major version.

## Compatibility policy

### Patch changes

Patch-only changes must not alter payload shape or semantics.

Examples:

- documentation updates,
- comments,
- internal refactors,
- validation code that does not change accepted payloads.

### Minor changes

Minor changes are additive and backward compatible.

Examples:

- new optional fields,
- new non-breaking envelope metadata,
- additional command types that older consumers can safely ignore.

Consumer rule:

- ignore unknown fields,
- preserve existing required fields,
- and continue operating when optional fields are absent.

### Major changes

Major changes are breaking.

Examples:

- removing or renaming fields,
- changing field types,
- adding new required fields,
- changing enum meaning,
- altering the transport envelope in a way that old peers cannot parse.

## Live transport handshake

When the live bridge is added:

- each side must advertise the highest contract version it supports,
- both sides must share the same major version to connect,
- if major versions match, the highest mutually supported minor version should be used,
- if no compatible version exists, the bridge must stay offline and the addon must remain fail-safe locally.

## Change-review gate

Before enabling live transport, verify that:

- Lua constants and helper-side contract models are still aligned,
- the JSON schemas in `contracts/` match the documented version policy,
- any new payload field is optional unless the change is intentionally breaking,
- and downgrade/unknown-field behavior remains safe.
