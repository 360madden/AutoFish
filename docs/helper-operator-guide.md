# Helper Operator Guide

## Purpose

The .NET 10 helper is the supervisory surface for:

- selecting a profile,
- issuing start/pause/resume/stop/snapshot commands,
- reviewing alerts and counters,
- monitoring bridge/session state.

## Current offline behavior

- profiles load from the repository `profiles` directory,
- the helper runs against a mock session service,
- selected profile and refresh interval are persisted locally,
- the profile tab shows the full preset currently selected in the UI.
- the status strip shows selected profile, active profile, refresh interval, and last update time.

## Notes

- The helper is intentionally supervisory.
- The addon should still remain safe if the helper disconnects.
- The active profile shown in session status may differ from the currently selected helper profile until the operator syncs it.
- Live addon diagnostics are being documented separately in `C:\RIFT MODDING\AutoFish\docs\addon-probe-plan.md`; they are not yet part of the helper's verified runtime flow.
