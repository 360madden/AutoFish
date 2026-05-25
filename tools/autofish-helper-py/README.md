# AutoFish Python Helper

This folder is the Python-first home for external AutoFish helper/runtime automation.

The Lua addon remains the in-game Rift addon layer. This helper is for same-PC desktop automation against the local Rift window:

- exact PID/HWND validation,
- screenshot capture,
- cursor hover/move/click,
- keypress orchestration,
- bounded cast-start tests,
- future bite/pull/loot timing and visual detection.

First target command:

```text
one-cast-start:
  validate exact PID/HWND
  move cursor to calibrated fishable water point without clicking
  press 8
  left-click the same point
  capture evidence
```

No live command should send input without an explicit target PID/HWND and a dry-run path.
