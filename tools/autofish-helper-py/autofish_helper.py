"""AutoFish Python helper.

Current focus: proof-first diagnostics for stale historical Rift fishing signals.

This module intentionally avoids unattended loops. Live input commands require an
exact PID/HWND and an explicit --confirm-input flag.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timezone
from typing import Any


if os.name != "nt":
    raise SystemExit("autofish_helper.py currently supports Windows only.")


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
winmm = ctypes.WinDLL("winmm", use_last_error=True)

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0
WAVE_FORMAT_PCM = 1
WAVE_MAPPER = 0xFFFFFFFF
CALLBACK_NULL = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
CURSOR_SHOWING = 0x00000001
SW_RESTORE = 9
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
PREFERRED_READABLE_CLIENT_WIDTH = 960
PREFERRED_READABLE_CLIENT_HEIGHT = 540
DEFAULT_LOG_TERMS = (
    "fish",
    "fishing",
    "reel",
    "loot",
    "catch",
    "caught",
    "not fishable",
    "area is not fishable",
    "lure",
    "bait",
)
SIGNAL_DECISIONS = ("promote", "fallback-only", "retire", "needs-more-evidence")
SIGNAL_NAMES = (
    "reticle",
    "oneCast",
    "boundedSession",
    "fishabilityFan",
    "fishabilityCandidate",
    "chromalinkWorldState",
    "coordinateCrosscheck",
    "facingDelta",
    "log",
    "layout",
    "audio",
    "inventory",
    "slash",
)
DEFAULT_CHROMALINK_BASE_URL = "http://127.0.0.1:7337"
DEFAULT_STOP_FILE = ".autofish-live/STOP.txt"
REVIEW_SCOPE_SCHEMA = "autofish.reviewScope.v1"
ADDON_COORD_RE = re.compile(r"\b([xyz])\s*=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
ADDON_PLAYER_UNIT_RE = re.compile(r"\bplayerUnit\s*=\s*(\S+)", re.IGNORECASE)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HCURSOR),
        ("ptScreenPos", POINT),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_void_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", wintypes.DWORD),
        ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_size_t),
    ]


user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
user32.mouse_event.restype = None
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]
user32.keybd_event.restype = None
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = wintypes.SHORT
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

winmm.waveInGetNumDevs.argtypes = []
winmm.waveInGetNumDevs.restype = wintypes.UINT
winmm.waveInGetErrorTextW.argtypes = [wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
winmm.waveInGetErrorTextW.restype = wintypes.UINT
winmm.waveInOpen.argtypes = [
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.UINT,
    ctypes.POINTER(WAVEFORMATEX),
    ctypes.c_size_t,
    ctypes.c_size_t,
    wintypes.DWORD,
]
winmm.waveInOpen.restype = wintypes.UINT
winmm.waveInPrepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveInPrepareHeader.restype = wintypes.UINT
winmm.waveInAddBuffer.argtypes = [wintypes.HANDLE, ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveInAddBuffer.restype = wintypes.UINT
winmm.waveInStart.argtypes = [wintypes.HANDLE]
winmm.waveInStart.restype = wintypes.UINT
winmm.waveInStop.argtypes = [wintypes.HANDLE]
winmm.waveInStop.restype = wintypes.UINT
winmm.waveInReset.argtypes = [wintypes.HANDLE]
winmm.waveInReset.restype = wintypes.UINT
winmm.waveInUnprepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveInUnprepareHeader.restype = wintypes.UINT
winmm.waveInClose.argtypes = [wintypes.HANDLE]
winmm.waveInClose.restype = wintypes.UINT


def last_error_message(action: str) -> str:
    err = ctypes.get_last_error()
    return f"{action} failed with Win32 error {err}"


def mm_error_message(result: int, action: str) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    text_result = winmm.waveInGetErrorTextW(result, buffer, len(buffer))
    detail = buffer.value if text_result == 0 and buffer.value else f"MMRESULT {result}"
    return f"{action} failed: {detail}"


def mm_check(result: int, action: str) -> None:
    if result != 0:
        raise RuntimeError(mm_error_message(result, action))


def parse_hwnd(value: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError("HWND cannot be empty")
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text, 10)


def hwnd_hex(hwnd: int) -> str:
    return f"0x{hwnd:X}"


def validate_target(hwnd: int, expected_pid: int, *, require_foreground: bool) -> dict[str, Any]:
    if not user32.IsWindow(hwnd):
        raise RuntimeError(f"Target HWND {hwnd_hex(hwnd)} is not a valid window")

    owner_pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
    if int(owner_pid.value) != expected_pid:
        raise RuntimeError(
            f"Target HWND {hwnd_hex(hwnd)} belongs to PID {owner_pid.value}, not expected PID {expected_pid}"
        )

    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError(last_error_message("GetClientRect"))

    foreground = int(user32.GetForegroundWindow())
    foreground_matches = foreground == hwnd
    if require_foreground and not foreground_matches:
        raise RuntimeError(
            f"Foreground mismatch: foreground={hwnd_hex(foreground)}, expected={hwnd_hex(hwnd)}"
        )

    client_width = int(rect.right - rect.left)
    client_height = int(rect.bottom - rect.top)
    is_minimized = bool(user32.IsIconic(hwnd))
    below_readable_preference = (
        client_width < PREFERRED_READABLE_CLIENT_WIDTH
        or client_height < PREFERRED_READABLE_CLIENT_HEIGHT
    )

    return {
        "hwnd": hwnd_hex(hwnd),
        "ownerProcessId": int(owner_pid.value),
        "clientWidth": client_width,
        "clientHeight": client_height,
        "isMinimized": is_minimized,
        "foregroundWindow": hwnd_hex(foreground),
        "foregroundMatches": foreground_matches,
        "readability": {
            "preferredMinimumClientWidth": PREFERRED_READABLE_CLIENT_WIDTH,
            "preferredMinimumClientHeight": PREFERRED_READABLE_CLIENT_HEIGHT,
            "belowPreferredMinimum": below_readable_preference,
            "warning": (
                "Client is below preferred proof-capture size; enlarge Rift before evidence runs if readable screenshots matter."
                if below_readable_preference
                else None
            ),
        },
    }


def assert_client_point(target: dict[str, Any], x: int, y: int) -> None:
    width = int(target["clientWidth"])
    height = int(target["clientHeight"])
    if x < 0 or y < 0 or x >= width or y >= height:
        raise RuntimeError(f"Client point ({x},{y}) is outside target client rect {width}x{height}")


def client_to_screen(hwnd: int, x: int, y: int) -> tuple[int, int]:
    point = POINT(x, y)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise RuntimeError(last_error_message("ClientToScreen"))
    return int(point.x), int(point.y)


def focus_target(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        raise RuntimeError("Target is minimized; restore/maximize Rift manually before live input to avoid changing the saved window size.")
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.20)


def focus_visible_target_without_restore(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        raise RuntimeError("Target is minimized; restore/focus Rift manually before movement proof to avoid changing the saved window size.")
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.20)


def get_cursor_state() -> dict[str, Any]:
    info = CURSORINFO()
    info.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(info)):
        return {"available": False, "error": last_error_message("GetCursorInfo")}
    handle = int(info.hCursor or 0)
    return {
        "available": True,
        "showing": bool(info.flags & CURSOR_SHOWING),
        "cursorHandle": hwnd_hex(handle) if handle else "0x0",
        "screenX": int(info.ptScreenPos.x),
        "screenY": int(info.ptScreenPos.y),
    }


def virtual_key_for(key: str) -> int:
    aliases = {
        "space": 0x20,
        "enter": 0x0D,
        "return": 0x0D,
        "escape": 0x1B,
        "esc": 0x1B,
    }
    lowered = key.lower()
    if lowered in aliases:
        return aliases[lowered]
    if len(key) != 1:
        raise ValueError(f"Unsupported key {key!r}. Use one character, Space, Enter, or Escape.")
    scan = user32.VkKeyScanW(key)
    if scan == -1:
        raise ValueError(f"Unable to map key {key!r} to a virtual key")
    return int(scan) & 0xFF


def press_key_once(key: str, hold_ms: int) -> dict[str, Any]:
    vk = virtual_key_for(key)
    user32.keybd_event(vk, 0, 0, None)
    time.sleep(max(hold_ms, 0) / 1000.0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)
    return {"key": key, "virtualKey": f"0x{vk:02X}", "holdMs": hold_ms}


def hold_key_safely(key: str, hold_ms: int) -> dict[str, Any]:
    vk = virtual_key_for(key)
    user32.keybd_event(vk, 0, 0, None)
    try:
        time.sleep(max(hold_ms, 0) / 1000.0)
    finally:
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)
    return {"key": key, "virtualKey": f"0x{vk:02X}", "holdMs": hold_ms}


def virtual_key_sequence_for_character(character: str) -> tuple[int, list[int]]:
    if len(character) != 1:
        raise ValueError("Expected exactly one character")
    scan = user32.VkKeyScanW(character)
    if scan == -1:
        raise ValueError(f"Unable to map character {character!r} to a virtual key")
    modifiers = (int(scan) >> 8) & 0xFF
    unsupported = modifiers & ~0x07
    if unsupported:
        raise ValueError(f"Unsupported modifier state 0x{modifiers:02X} for character {character!r}")
    modifier_keys: list[int] = []
    if modifiers & 0x01:
        modifier_keys.append(VK_SHIFT)
    if modifiers & 0x02:
        modifier_keys.append(VK_CONTROL)
    if modifiers & 0x04:
        modifier_keys.append(VK_MENU)
    return int(scan) & 0xFF, modifier_keys


def press_virtual_key(vk: int, hold_ms: int) -> None:
    user32.keybd_event(vk, 0, 0, None)
    time.sleep(max(hold_ms, 0) / 1000.0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)


def type_text_keys(text: str, *, key_hold_ms: int, inter_key_delay_ms: int) -> None:
    for character in text:
        if character in ("\r", "\n"):
            raise ValueError("Slash command text must not contain newlines")
        vk, modifier_keys = virtual_key_sequence_for_character(character)
        for modifier in modifier_keys:
            user32.keybd_event(modifier, 0, 0, None)
        try:
            press_virtual_key(vk, key_hold_ms)
        finally:
            for modifier in reversed(modifier_keys):
                user32.keybd_event(modifier, 0, KEYEVENTF_KEYUP, None)
        time.sleep(max(inter_key_delay_ms, 0) / 1000.0)


def validate_slash_command(command: str, *, allow_reload_key: bool, allow_non_autofish: bool) -> str:
    normalized = command.strip()
    if not normalized:
        raise ValueError("Slash command cannot be empty")
    if "\r" in normalized or "\n" in normalized:
        raise ValueError("Slash command must be one line")
    if not normalized.startswith("/"):
        raise ValueError(f"Slash command must start with '/': {command!r}")
    if "-" in normalized and not allow_reload_key:
        raise ValueError("Refusing a command containing '-' because that key triggers reloadui on this setup")
    if not allow_non_autofish and not normalized.lower().startswith("/autofish"):
        raise ValueError("Refusing non-/autofish command without --allow-non-autofish")
    if len(normalized) > 160:
        raise ValueError("Slash command is too long for this bounded proof helper")
    return normalized


def safe_file_stem(value: str, fallback: str) -> str:
    text = value.strip().lower().replace("/", "")
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in text)
    safe = "-".join(part for part in safe.split("-") if part)
    return safe[:48] or fallback


def move_cursor_to(screen_x: int, screen_y: int) -> None:
    if not user32.SetCursorPos(screen_x, screen_y):
        raise RuntimeError(last_error_message("SetCursorPos"))


def left_click() -> None:
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)


def assert_stop_file_absent(stop_file: str | None) -> None:
    if stop_file and Path(stop_file).exists():
        raise RuntimeError(f"Stop file exists: {stop_file}")


def wait_seconds_with_stop(seconds: float, stop_file: str | None) -> None:
    deadline = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < deadline:
        assert_stop_file_absent(stop_file)
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))


def capture_screen_rect(left: int, top: int, width: int, height: int) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError("Capture dimensions must be positive")

    screen_dc = user32.GetDC(0)
    if not screen_dc:
        raise RuntimeError(last_error_message("GetDC"))
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    if not mem_dc:
        user32.ReleaseDC(0, screen_dc)
        raise RuntimeError(last_error_message("CreateCompatibleDC"))
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    if not bitmap:
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, screen_dc)
        raise RuntimeError(last_error_message("CreateCompatibleBitmap"))

    old_obj = gdi32.SelectObject(mem_dc, bitmap)
    try:
        if not gdi32.BitBlt(mem_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY):
            raise RuntimeError(last_error_message("BitBlt"))

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        buffer = ctypes.create_string_buffer(width * height * 4)
        rows = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)
        if rows != height:
            raise RuntimeError(last_error_message("GetDIBits"))
        return buffer.raw
    finally:
        if old_obj:
            gdi32.SelectObject(mem_dc, old_obj)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, screen_dc)


def write_bmp_24(path: Path, width: int, height: int, bgra_top_down: bytes) -> None:
    row_stride = ((width * 3 + 3) // 4) * 4
    image_size = row_stride * height
    file_size = 14 + 40 + image_size
    with path.open("wb") as f:
        f.write(struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54))
        f.write(
            struct.pack(
                "<IiiHHIIiiII",
                40,
                width,
                height,
                1,
                24,
                BI_RGB,
                image_size,
                0,
                0,
                0,
                0,
            )
        )
        padding = b"\x00" * (row_stride - width * 3)
        for y in range(height - 1, -1, -1):
            row = bytearray()
            base = y * width * 4
            for x in range(width):
                i = base + x * 4
                b = bgra_top_down[i]
                g = bgra_top_down[i + 1]
                r = bgra_top_down[i + 2]
                row.extend((b, g, r))
            f.write(row)
            f.write(padding)


def classify_reticle_pixel(r: int, g: int, b: int) -> tuple[str, ...]:
    matches: list[str] = []
    if r >= 150 and g <= 115 and b <= 115 and r >= g + 35 and r >= b + 35:
        matches.append("red")
    if r >= 150 and g >= 135 and b <= 130 and abs(r - g) <= 90:
        matches.append("yellow")
    if b >= 135 and g >= 90 and r <= 135 and b >= r + 25:
        matches.append("blueCyan")
    if g >= 135 and r <= 140 and b <= 150 and g >= r + 25:
        matches.append("green")
    return tuple(matches)


def choose_reticle_color(counts: dict[str, int]) -> tuple[str, str, bool]:
    red = counts.get("red", 0)
    yellow = counts.get("yellow", 0)
    blue_cyan = counts.get("blueCyan", 0)
    green = counts.get("green", 0)

    # Invalid Rift reticles are red/orange and may also satisfy the broad
    # yellow threshold. Prefer red when both channels are strong enough.
    if red >= 500 and red >= int(yellow * 0.45):
        return "red", "red_orange_pixels_met_invalid_reticle_threshold", False
    if yellow >= 500:
        return "yellow", "yellow_pixels_met_valid_reticle_threshold", False
    if green >= 500:
        return "green", "green_pixels_met_reticle_threshold", False

    # Water/highlight backgrounds can dominate blue/cyan counts. Only suggest
    # blue/cyan when the evidence is strong and not mixed with red/yellow/green.
    if blue_cyan >= 500 and red < 100 and yellow < 100 and green < 100:
        return "blueCyan", "strong_isolated_blue_cyan_pixels", True

    legacy_candidates = {"red": red, "yellow": yellow, "blueCyan": blue_cyan, "green": green}
    legacy = max(legacy_candidates, key=legacy_candidates.get)
    if legacy == "blueCyan" and blue_cyan >= 20:
        return "unknown", "blue_cyan_requires_manual_review_due_to_water_background_risk", True
    if legacy_candidates[legacy] >= 20:
        return "unknown", f"{legacy}_pixels_below_reticle_threshold", False
    return "unknown", "no_color_threshold_met", False


def color_stats(width: int, height: int, bgra_top_down: bytes) -> dict[str, Any]:
    counts = {"red": 0, "yellow": 0, "blueCyan": 0, "green": 0, "bright": 0}
    center_counts = {"red": 0, "yellow": 0, "blueCyan": 0, "green": 0, "bright": 0}
    total_r = total_g = total_b = 0
    center_left = max(0, int(width * 0.25))
    center_right = min(width, int(width * 0.75))
    center_top = max(0, int(height * 0.25))
    center_bottom = min(height, int(height * 0.75))
    for pixel_index in range(width * height):
        i = pixel_index * 4
        b = bgra_top_down[i]
        g = bgra_top_down[i + 1]
        r = bgra_top_down[i + 2]
        x = pixel_index % width
        y = pixel_index // width
        in_center = center_left <= x < center_right and center_top <= y < center_bottom
        total_r += r
        total_g += g
        total_b += b
        if max(r, g, b) >= 130:
            counts["bright"] += 1
            if in_center:
                center_counts["bright"] += 1
        for color in classify_reticle_pixel(r, g, b):
            counts[color] += 1
            if in_center:
                center_counts[color] += 1

    legacy_candidates = {k: counts[k] for k in ("red", "yellow", "blueCyan", "green")}
    legacy_suggested = max(legacy_candidates, key=legacy_candidates.get)
    if legacy_candidates[legacy_suggested] < 20:
        legacy_suggested = "unknown"
    suggested, suggestion_reason, review_required = choose_reticle_color(counts)
    pixels = width * height
    return {
        "pixels": pixels,
        "centerRect": {
            "left": center_left,
            "top": center_top,
            "right": center_right,
            "bottom": center_bottom,
            "width": center_right - center_left,
            "height": center_bottom - center_top,
        },
        "averageRgb": {
            "r": round(total_r / pixels, 2),
            "g": round(total_g / pixels, 2),
            "b": round(total_b / pixels, 2),
        },
        "counts": counts,
        "centerCounts": center_counts,
        "suggestedReticleColor": suggested,
        "legacySuggestedReticleColor": legacy_suggested,
        "suggestionReason": suggestion_reason,
        "manualReviewRequired": review_required,
    }


def capture_client_crop(hwnd: int, expected_pid: int, client_x: int, client_y: int, crop_size: int, output_path: Path) -> dict[str, Any]:
    target = validate_target(hwnd, expected_pid, require_foreground=False)
    width = int(target["clientWidth"])
    height = int(target["clientHeight"])
    half = crop_size // 2
    crop_left_client = max(0, min(client_x - half, max(0, width - crop_size)))
    crop_top_client = max(0, min(client_y - half, max(0, height - crop_size)))
    crop_width = min(crop_size, width - crop_left_client)
    crop_height = min(crop_size, height - crop_top_client)
    screen_left, screen_top = client_to_screen(hwnd, crop_left_client, crop_top_client)
    pixels = capture_screen_rect(screen_left, screen_top, crop_width, crop_height)
    write_bmp_24(output_path, crop_width, crop_height, pixels)
    stats = color_stats(crop_width, crop_height, pixels)
    return {
        "path": str(output_path),
        "clientRect": {
            "left": crop_left_client,
            "top": crop_top_client,
            "width": crop_width,
            "height": crop_height,
        },
        "screenRect": {
            "left": screen_left,
            "top": screen_top,
            "width": crop_width,
            "height": crop_height,
        },
        "cursor": get_cursor_state(),
        "colorStats": stats,
    }


def parse_region_spec(spec: str) -> dict[str, Any]:
    if ":" not in spec:
        raise ValueError(f"Region must use name:left,top,width,height format: {spec!r}")
    name, raw_values = spec.split(":", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"Region name cannot be empty: {spec!r}")
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
    parts = [part.strip() for part in raw_values.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region must have four numeric values: {spec!r}")
    left, top, width, height = (int(part, 10) for part in parts)
    if left < 0 or top < 0 or width <= 0 or height <= 0:
        raise ValueError(f"Region values must be non-negative with positive width/height: {spec!r}")
    return {
        "name": name,
        "safeName": safe_name,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    }


def capture_client_region(
    hwnd: int,
    expected_pid: int,
    region: dict[str, Any],
    output_path: Path,
    *,
    require_foreground: bool,
) -> dict[str, Any]:
    target = validate_target(hwnd, expected_pid, require_foreground=require_foreground)
    client_width = int(target["clientWidth"])
    client_height = int(target["clientHeight"])
    left = int(region["left"])
    top = int(region["top"])
    width = int(region["width"])
    height = int(region["height"])
    if left + width > client_width or top + height > client_height:
        raise RuntimeError(
            f"Region {region['name']!r} ({left},{top},{width},{height}) exceeds client rect {client_width}x{client_height}"
        )
    screen_left, screen_top = client_to_screen(hwnd, left, top)
    pixels = capture_screen_rect(screen_left, screen_top, width, height)
    write_bmp_24(output_path, width, height, pixels)
    return {
        "name": region["name"],
        "path": str(output_path),
        "clientRect": {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        },
        "screenRect": {
            "left": screen_left,
            "top": screen_top,
            "width": width,
            "height": height,
        },
        "cursor": get_cursor_state(),
        "colorStats": color_stats(width, height, pixels),
    }



def write_manifest(output_root: Path, manifest: dict[str, Any]) -> None:
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}.")
    return value


def resolve_profile_path(profile: str, profile_root: str | None) -> Path:
    candidate = Path(profile)
    if candidate.exists() or candidate.suffix.lower() == ".json" or any(separator in profile for separator in ("\\", "/")):
        return candidate

    root = Path(profile_root) if profile_root else Path("profiles")
    return root / f"{profile}.json"


def load_fishing_profile(profile: str | None, profile_root: str | None) -> dict[str, Any] | None:
    if not profile:
        return None

    path = resolve_profile_path(profile, profile_root)
    if not path.exists():
        raise RuntimeError(f"Fishing profile not found: {path}")

    data = load_json_object(path)
    pacing = data.get("pacing")
    if not isinstance(pacing, dict):
        raise RuntimeError(f"Fishing profile {path} does not define pacing.")

    return {
        "path": str(path),
        "id": data.get("id"),
        "displayName": data.get("displayName"),
        "zoneName": data.get("zoneName"),
        "baitName": data.get("baitName"),
        "pacing": pacing,
        "thresholds": data.get("thresholds") if isinstance(data.get("thresholds"), dict) else {},
        "guardrails": data.get("guardrails") if isinstance(data.get("guardrails"), dict) else {},
    }


def apply_fishing_runtime_defaults(args: argparse.Namespace, *, include_session_defaults: bool) -> dict[str, Any]:
    profile_info = load_fishing_profile(getattr(args, "profile", None), getattr(args, "profile_root", None))
    pacing = profile_info.get("pacing") if isinstance(profile_info, dict) else {}
    applied: dict[str, Any] = {}

    def apply_default(name: str, value: Any) -> None:
        if getattr(args, name) is None:
            setattr(args, name, value)
            applied[name] = value

    apply_default("key", "8")
    apply_default("pull_clicks", 1)
    apply_default("cast_wait_seconds", float(pacing.get("biteTimeoutMs", 18000)) / 1000.0)
    apply_default("post_pull_delay_ms", int(pacing.get("lootTimeoutMs", 1200)))
    apply_default("crop_size", 220)
    apply_default("key_hold_ms", 80)
    apply_default("post_hover_delay_ms", 150)
    apply_default("post_key_delay_ms", 350)
    apply_default("post_click_delay_ms", 800)
    if include_session_defaults:
        apply_default("max_casts", 3)
        apply_default("max_allowed_casts", 10)
        apply_default("inter_cast_delay_ms", 800)

    return {
        "profile": profile_info,
        "appliedDefaults": applied,
    }


def load_session_plan(path_text: str | None) -> dict[str, Any] | None:
    if not path_text:
        return None

    path = Path(path_text)
    plan = load_json_object(path)
    schema = str(plan.get("schema") or "")
    if schema != "autofish.sessionPlan.v1":
        raise RuntimeError(f"Unsupported session plan schema in {path}: {schema or '<missing>'}")
    return {"path": str(path), "plan": plan}


def apply_session_plan_defaults(args: argparse.Namespace, *, include_session_defaults: bool) -> dict[str, Any]:
    loaded = load_session_plan(getattr(args, "session_plan", None))
    if not loaded:
        return {"sessionPlan": None, "appliedDefaults": {}}

    plan = loaded["plan"]
    applied: dict[str, Any] = {}
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    point = plan.get("fishablePoint") if isinstance(plan.get("fishablePoint"), dict) else {}
    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    defaults = plan.get("defaults") if isinstance(plan.get("defaults"), dict) else {}

    def apply_default(name: str, value: Any) -> None:
        if value is None:
            return
        if getattr(args, name, None) is None:
            setattr(args, name, value)
            applied[name] = value

    apply_default("pid", target.get("pid"))
    apply_default("hwnd", target.get("hwnd"))
    apply_default("x", point.get("x"))
    apply_default("y", point.get("y"))
    apply_default("profile", profile.get("id") or profile.get("path"))
    apply_default("key", defaults.get("key"))
    apply_default("pull_clicks", defaults.get("pullClicks"))
    apply_default("cast_wait_seconds", defaults.get("castWaitSeconds"))
    apply_default("post_pull_delay_ms", defaults.get("postPullDelayMs"))
    apply_default("stop_file", defaults.get("stopFile") or DEFAULT_STOP_FILE)
    if include_session_defaults:
        apply_default("max_casts", defaults.get("maxCasts"))
        apply_default("max_allowed_casts", defaults.get("maxAllowedCasts"))
        apply_default("inter_cast_delay_ms", defaults.get("interCastDelayMs"))

    return {
        "sessionPlan": loaded,
        "appliedDefaults": applied,
    }


def require_runtime_values(args: argparse.Namespace, names: tuple[str, ...], *, context: str) -> None:
    missing = [name for name in names if getattr(args, name, None) is None]
    if missing:
        flags = ", ".join("--" + name.replace("_", "-") for name in missing)
        raise RuntimeError(f"{context} requires {flags}, either directly or through --session-plan.")


def build_session_review_scope(plan: dict[str, Any]) -> dict[str, Any]:
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    point = plan.get("fishablePoint") if isinstance(plan.get("fishablePoint"), dict) else {}
    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    defaults = plan.get("defaults") if isinstance(plan.get("defaults"), dict) else {}
    source = plan.get("source") if isinstance(plan.get("source"), dict) else None

    scope: dict[str, Any] = {
        "schema": REVIEW_SCOPE_SCHEMA,
        "target": {
            "pid": target.get("pid"),
            "hwnd": target.get("hwnd"),
        },
        "fishablePoint": {
            "x": point.get("x"),
            "y": point.get("y"),
            "coordinateSpace": point.get("coordinateSpace", "client"),
        },
        "profile": {
            "id": profile.get("id"),
            "root": profile.get("root"),
        },
        "defaults": {
            "key": defaults.get("key"),
            "maxCasts": defaults.get("maxCasts"),
            "pullClicks": defaults.get("pullClicks"),
            "castWaitSeconds": defaults.get("castWaitSeconds"),
        },
    }
    if source:
        scope["source"] = {
            "type": source.get("type"),
            "manifest": source.get("manifest"),
            "candidateIndex": source.get("candidateIndex"),
            "candidateName": source.get("candidateName"),
        }
    return scope


def compute_review_scope_token(scope: dict[str, Any]) -> str:
    payload = json.dumps(scope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"afscope-{digest}"


def attach_session_review_scope(plan: dict[str, Any]) -> dict[str, Any]:
    scope = build_session_review_scope(plan)
    plan["review"] = {
        "schema": REVIEW_SCOPE_SCHEMA,
        "scopeToken": compute_review_scope_token(scope),
        "scope": scope,
        "requiresScopedDecisions": True,
    }
    return plan


def get_session_plan_review_token(session_plan_info: dict[str, Any] | None) -> str | None:
    plan = session_plan_info.get("plan") if isinstance(session_plan_info, dict) else None
    review = plan.get("review") if isinstance(plan, dict) and isinstance(plan.get("review"), dict) else None
    token = review.get("scopeToken") if isinstance(review, dict) else None
    return str(token) if token else None


def positive_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def session_plan_expected_client_size(session_plan_info: dict[str, Any] | None) -> dict[str, Any] | None:
    plan = session_plan_info.get("plan") if isinstance(session_plan_info, dict) else None
    if not isinstance(plan, dict):
        return None

    target_validation = plan.get("targetValidation") if isinstance(plan.get("targetValidation"), dict) else None
    if not target_validation:
        return None

    width = positive_int_or_none(target_validation.get("clientWidth"))
    height = positive_int_or_none(target_validation.get("clientHeight"))
    if width is None or height is None:
        return None

    return {
        "width": width,
        "height": height,
        "source": target_validation.get("clientSizeSource") or "targetValidation",
        "targetValidation": target_validation,
    }


def check_session_plan_target_freshness(
    session_plan_info: dict[str, Any] | None,
    current_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected = session_plan_expected_client_size(session_plan_info)
    if expected is None:
        return {
            "required": False,
            "passed": True,
            "reason": "Session plan has no recorded positive target client size.",
        }

    gate: dict[str, Any] = {
        "required": True,
        "passed": False,
        "expectedClientWidth": expected["width"],
        "expectedClientHeight": expected["height"],
        "expectedClientSizeSource": expected["source"],
    }

    if current_target is None:
        plan = session_plan_info.get("plan") if isinstance(session_plan_info, dict) else None
        target = plan.get("target") if isinstance(plan, dict) and isinstance(plan.get("target"), dict) else {}
        pid = target.get("pid")
        hwnd_text = target.get("hwnd")
        if pid is None or not hwnd_text:
            gate["reason"] = "Session plan cannot be target-freshness checked because target.pid or target.hwnd is missing."
            return gate
        try:
            current_target = validate_target(parse_hwnd(str(hwnd_text)), int(pid), require_foreground=False)
        except Exception as exc:
            gate["reason"] = f"Current target validation failed: {exc}"
            return gate

    current_width = positive_int_or_none(current_target.get("clientWidth"))
    current_height = positive_int_or_none(current_target.get("clientHeight"))
    gate.update(
        {
            "currentClientWidth": current_width,
            "currentClientHeight": current_height,
            "currentTarget": current_target,
        }
    )
    if current_width is None or current_height is None:
        minimized_note = " Target appears minimized." if current_target.get("isMinimized") else ""
        gate["reason"] = f"Current target client size is unavailable.{minimized_note}"
        return gate

    gate["passed"] = current_width == expected["width"] and current_height == expected["height"]
    if gate["passed"]:
        gate["reason"] = "Current target client size matches the session plan."
    else:
        gate["reason"] = (
            "Session plan target size is stale: expected "
            f"{expected['width']}x{expected['height']} but current target is {current_width}x{current_height}. "
            "Recreate the session plan and recalibrate the fishable client coordinate after window resize."
        )
    return gate


def build_session_plan(args: argparse.Namespace) -> dict[str, Any]:
    stop_file = args.stop_file or DEFAULT_STOP_FILE
    defaults: dict[str, Any] = {
        "key": args.key,
        "maxCasts": args.max_casts,
        "maxAllowedCasts": args.max_allowed_casts,
        "pullClicks": args.pull_clicks,
        "castWaitSeconds": args.cast_wait_seconds,
        "postPullDelayMs": args.post_pull_delay_ms,
        "interCastDelayMs": args.inter_cast_delay_ms,
        "stopFile": stop_file,
    }
    defaults = {key: value for key, value in defaults.items() if value is not None}
    plan: dict[str, Any] = {
        "schema": "autofish.sessionPlan.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Local AutoFish live proof session plan. Do not treat PID/HWND or fishable point as durable across Rift restarts/resizes.",
        "target": {
            "pid": int(args.pid),
            "hwnd": hwnd_hex(parse_hwnd(args.hwnd)),
        },
        "fishablePoint": {
            "x": int(args.x),
            "y": int(args.y),
            "coordinateSpace": "client",
            "requiresRecalibrationAfterResize": True,
        },
        "profile": {
            "id": args.profile,
            "root": args.profile_root,
        }
        if args.profile
        else None,
        "defaults": defaults,
        "safety": {
            "requiresExactPidHwnd": True,
            "noMovement": True,
            "requiresDryRunBeforeConfirmInput": True,
            "blocksReloadKeyByDefault": True,
            "doNotUseIfRiftRestartedOrResized": True,
        },
        "targetValidation": None,
    }
    if args.validate_target:
        plan["targetValidation"] = validate_target(parse_hwnd(args.hwnd), int(args.pid), require_foreground=False)
    attach_session_review_scope(plan)
    return plan


def run_session_plan_create(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plan = build_session_plan(args)
    output_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(output_path), "schema": plan["schema"]}, indent=2))
    return 0


def select_fan_candidate(manifest: dict[str, Any], *, candidate_index: int | None, candidate_name: str | None) -> dict[str, Any]:
    candidates = manifest.get("candidates") if isinstance(manifest.get("candidates"), list) else []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_index_value = candidate.get("index")
        if candidate_index is not None and candidate_index_value is not None and int(candidate_index_value) == int(candidate_index):
            return candidate
        if candidate_name is not None and str(candidate.get("name") or "") == str(candidate_name):
            return candidate

    selector = f"index {candidate_index}" if candidate_index is not None else f"name {candidate_name}"
    raise RuntimeError(f"Fishability fan manifest has no candidate with {selector}.")


def target_validation_from_fan_manifest(manifest: dict[str, Any]) -> dict[str, Any] | None:
    target = manifest.get("target") if isinstance(manifest.get("target"), dict) else None
    if not target:
        return None

    snapshot = dict(target)
    effective_client = manifest.get("effectiveClient") if isinstance(manifest.get("effectiveClient"), dict) else {}
    width = positive_int_or_none(effective_client.get("width")) or positive_int_or_none(snapshot.get("clientWidth"))
    height = positive_int_or_none(effective_client.get("height")) or positive_int_or_none(snapshot.get("clientHeight"))
    if width is not None and height is not None:
        snapshot["clientWidth"] = width
        snapshot["clientHeight"] = height
        snapshot["clientSizeSource"] = effective_client.get("source") or snapshot.get("clientSizeSource") or "fan-manifest-target"
    return snapshot


def build_session_plan_from_fan(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.manifest)
    manifest = load_json_object(manifest_path)
    schema = str(manifest.get("schema") or "")
    if schema != "autofish.signalProof.fishabilityFan.v1":
        raise RuntimeError(f"Unsupported fishability fan manifest schema in {manifest_path}: {schema or '<missing>'}")

    candidate = select_fan_candidate(
        manifest,
        candidate_index=getattr(args, "candidate_index", None),
        candidate_name=getattr(args, "candidate_name", None),
    )
    if candidate.get("inBounds") is not True:
        raise RuntimeError("Refusing to create a session plan from an out-of-bounds fishability fan candidate.")

    request = manifest.get("request") if isinstance(manifest.get("request"), dict) else {}
    pid = request.get("pid")
    hwnd = request.get("hwnd")
    if pid is None or hwnd is None:
        raise RuntimeError("Fishability fan manifest is missing request.pid or request.hwnd.")

    create_args = argparse.Namespace(
        pid=int(pid),
        hwnd=str(hwnd),
        x=int(candidate["clientX"]),
        y=int(candidate["clientY"]),
        profile=args.profile,
        profile_root=args.profile_root,
        key=args.key or request.get("key") or "8",
        max_casts=args.max_casts,
        max_allowed_casts=args.max_allowed_casts,
        pull_clicks=args.pull_clicks,
        cast_wait_seconds=args.cast_wait_seconds,
        post_pull_delay_ms=args.post_pull_delay_ms,
        inter_cast_delay_ms=args.inter_cast_delay_ms,
        stop_file=args.stop_file,
        validate_target=args.validate_target,
    )
    plan = build_session_plan(create_args)
    plan["source"] = {
        "type": "fishabilityFanCandidate",
        "manifest": str(manifest_path),
        "candidateIndex": candidate.get("index"),
        "candidateName": candidate.get("name"),
        "classification": candidate.get("plannedClassification"),
        "requiresReticleOrGameFeedbackReview": True,
    }
    if plan.get("targetValidation") is None:
        plan["targetValidation"] = target_validation_from_fan_manifest(manifest)
    plan["safety"]["sourceCandidateIsPlanningOnly"] = True
    plan["safety"]["requiresReviewedFishableCandidateBeforeConfirmInput"] = True
    attach_session_review_scope(plan)
    return plan


def run_session_plan_from_fan(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plan = build_session_plan_from_fan(args)
    output_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(output_path),
                "schema": plan["schema"],
                "source": plan.get("source"),
            },
            indent=2,
        )
    )
    return 0


def run_session_plan_show(args: argparse.Namespace) -> int:
    loaded = load_session_plan(args.path)
    assert loaded is not None
    print(json.dumps(loaded["plan"], indent=2))
    return 0


def run_session_plan_gates(args: argparse.Namespace) -> int:
    loaded = load_session_plan(args.path)
    assert loaded is not None
    plan = loaded["plan"]
    one_cast_gate_args = argparse.Namespace(
        allow_unreviewed_one_cast=False,
        decision_register=args.decision_register,
    )
    fishability_gate = check_fan_candidate_review_gate(
        loaded,
        args.decision_register,
        allow_unreviewed=False,
    )
    one_cast_gate = check_one_cast_review_gate(one_cast_gate_args, loaded)
    target_gate = check_session_plan_target_freshness(loaded)
    report = {
        "schema": "autofish.sessionPlan.reviewGates.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "path": loaded["path"],
        "review": plan.get("review") if isinstance(plan.get("review"), dict) else None,
        "source": plan.get("source") if isinstance(plan.get("source"), dict) else None,
        "decisionRegister": args.decision_register,
        "gates": {
            "targetCurrent": target_gate,
            "fishabilityCandidate": fishability_gate,
            "oneCast": one_cast_gate,
        },
        "readiness": {
            "targetCurrent": bool(target_gate.get("passed")),
            "confirmedOneCast": bool(fishability_gate.get("passed")),
            "confirmedBoundedSession": bool(one_cast_gate.get("passed")),
        },
        "requiredReadiness": args.require or [],
        "notes": [
            "This command sends no game input.",
            "targetCurrent compares the current Rift client size with the session plan targetValidation when a size was recorded.",
            "confirmedOneCast covers fan-derived candidate review only; one-cast still requires exact PID/HWND and --confirm-input.",
            "confirmedBoundedSession requires a scoped reviewed oneCast decision.",
        ],
    }
    print(json.dumps(report, indent=2))
    readiness_name_by_flag = {
        "target-current": "targetCurrent",
        "confirmed-one-cast": "confirmedOneCast",
        "confirmed-bounded-session": "confirmedBoundedSession",
    }
    for required in args.require or []:
        readiness_name = readiness_name_by_flag[required]
        if report["readiness"].get(readiness_name) is not True:
            return 1
    return 0


def quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render_session_plan_runbook(plan_path: str, proof_root: str) -> str:
    loaded = load_session_plan(plan_path)
    assert loaded is not None
    plan = loaded["plan"]
    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    point = plan.get("fishablePoint") if isinstance(plan.get("fishablePoint"), dict) else {}
    defaults = plan.get("defaults") if isinstance(plan.get("defaults"), dict) else {}
    source = plan.get("source") if isinstance(plan.get("source"), dict) else {}
    is_fan_candidate_plan = source.get("type") == "fishabilityFanCandidate"
    helper = "python tools\\autofish-helper-py\\autofish_helper.py"
    plan_arg = quote_ps(plan_path)
    proof_root_arg = quote_ps(proof_root)
    stop_file = defaults.get("stopFile") or DEFAULT_STOP_FILE
    stop_file_arg = quote_ps(str(stop_file))
    one_cast_evidence = proof_root.rstrip("\\/") + "\\<one-cast-proof>\\manifest.json"
    fan_candidate_evidence = proof_root.rstrip("\\/") + "\\<candidate-reticle-proof>\\manifest.json"
    review = plan.get("review") if isinstance(plan.get("review"), dict) else {}
    scope_token = review.get("scopeToken")
    lines = [
        "# AutoFish Session Plan Runbook",
        "",
        f"- plan: `{plan_path}`",
        f"- target: PID `{target.get('pid')}`, HWND `{target.get('hwnd')}`",
        f"- fishable client point: `({point.get('x')},{point.get('y')})`",
        f"- profile: `{profile.get('id') or '-'}`",
        f"- key: `{defaults.get('key', '8')}`; max casts: `{defaults.get('maxCasts', 3)}`",
        f"- emergency stop file: `{stop_file}`",
    ]
    if scope_token:
        lines.append(f"- review scope token: `{scope_token}`")
    if is_fan_candidate_plan:
        lines.append(
            f"- source: `fishabilityFanCandidate` index `{source.get('candidateIndex')}` name `{source.get('candidateName')}`"
        )
    lines.extend([
        "",
        "## 1. Review the plan",
        "",
        "```powershell",
        f"{helper} session-plan show --path {plan_arg}",
        "```",
        "",
        "Check scoped review gates:",
        "",
        "```powershell",
        f"{helper} session-plan gates --path {plan_arg}",
        "```",
        "",
        "Fail closed if the current target client size no longer matches the plan:",
        "",
        "```powershell",
        f"{helper} session-plan gates --path {plan_arg} --require target-current",
        "```",
        "",
    ])
    if is_fan_candidate_plan:
        lines.extend(
            [
                "## Fan-candidate review gate",
                "",
                "Before confirmed one-cast input, review the candidate reticle/game-feedback proof and record it:",
                "",
                "```powershell",
                f"{helper} signal-proof decide `",
                "  --signal fishabilityCandidate `",
                "  --decision fallback-only `",
                "  --reason \"Reviewed fan candidate as fishable enough for one supervised one-cast proof.\" `",
                f"  --evidence {quote_ps(fan_candidate_evidence)} `",
                f"  --session-plan {plan_arg} `",
                f"  --proof-root {proof_root_arg}",
                "```",
                "",
            ]
        )
    lines.extend([
        "## 2. One-cast dry-run",
        "",
        "```powershell",
        f"{helper} signal-proof one-cast --session-plan {plan_arg} --dry-run",
        "```",
        "",
        "## 3. One supervised one-cast proof",
        "",
        "```powershell",
        f"{helper} signal-proof one-cast --session-plan {plan_arg} --confirm-input",
        "```",
        "",
        "## 4. Record reviewed one-cast decision after screenshot/manifest review",
        "",
        "```powershell",
        f"{helper} signal-proof decide `",
        "  --signal oneCast `",
        "  --decision fallback-only `",
        "  --reason \"Reviewed one-cast proof is acceptable for a small supervised bounded session.\" `",
        f"  --evidence {quote_ps(one_cast_evidence)} `",
        f"  --session-plan {plan_arg} `",
        f"  --proof-root {proof_root_arg}",
        "```",
        "",
        "## 5. Bounded-session dry-run",
        "",
        "```powershell",
        f"{helper} signal-proof bounded-session --session-plan {plan_arg} --dry-run",
        "```",
        "",
        "## 6. Confirmed bounded-session proof",
        "",
        "```powershell",
        f"{helper} signal-proof bounded-session --session-plan {plan_arg} --confirm-input",
        "```",
        "",
        "## Emergency stop",
        "",
        "Create the stop file before the next action should abort:",
        "",
        "```powershell",
        f"New-Item -ItemType File -Force -Path {stop_file_arg}",
        "```",
        "",
        "Clear it before a later supervised rerun:",
        "",
        "```powershell",
        f"Remove-Item -Force -ErrorAction SilentlyContinue -Path {stop_file_arg}",
        "```",
        "",
        "Safety notes:",
        "",
        "- Do not use this plan after Rift restarts, the window is resized, or the fishable point changes.",
        "- Confirmed commands still require exact PID/HWND and foreground target.",
        "- Bounded-session confirmed mode requires a reviewed oneCast decision unless explicitly bypassed.",
        "- The stop file is checked before each bounded action and during wait periods.",
        "- No command in this runbook sends movement.",
    ])
    if is_fan_candidate_plan:
        lines.append("- Fan-derived plans also require a reviewed fishabilityCandidate decision before confirmed one-cast input.")
    return "\n".join(lines).rstrip() + "\n"


def run_session_plan_runbook(args: argparse.Namespace) -> int:
    markdown = render_session_plan_runbook(args.path, args.proof_root)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print(json.dumps({"ok": True, "path": str(output_path)}, indent=2))
    else:
        print(markdown, end="")
    return 0


def decision_entry_scope_tokens(entry: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    scope_tokens = entry.get("scopeTokens")
    if isinstance(scope_tokens, list):
        tokens.extend(str(token) for token in scope_tokens if token)
    scope_token = entry.get("scopeToken")
    if scope_token:
        tokens.append(str(scope_token))
    return list(dict.fromkeys(tokens))


def latest_signal_decision(register: dict[str, Any], signal: str) -> dict[str, Any] | None:
    latest_by_signal = register.get("latestBySignal") if isinstance(register.get("latestBySignal"), dict) else {}
    latest = latest_by_signal.get(signal)
    return latest if isinstance(latest, dict) else None


def latest_accepted_decision(
    register: dict[str, Any],
    *,
    signal: str,
    accepted_decisions: tuple[str, ...] = ("promote", "fallback-only"),
    scope_token: str | None = None,
) -> dict[str, Any] | None:
    entries = register.get("entries") if isinstance(register.get("entries"), list) else []
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("signal") != signal:
            continue
        if entry.get("decision") not in accepted_decisions:
            continue
        if scope_token and scope_token not in decision_entry_scope_tokens(entry):
            continue
        return entry
    return None


def decision_scope_hint(session_plan_info: dict[str, Any] | None, scope_token: str | None) -> str:
    if not scope_token:
        return ""
    plan_path = session_plan_info.get("path") if isinstance(session_plan_info, dict) else None
    if plan_path:
        return f" --session-plan {plan_path}"
    return f" --scope-token {scope_token}"


def check_one_cast_review_gate(args: argparse.Namespace, session_plan_info: dict[str, Any] | None = None) -> dict[str, Any]:
    if getattr(args, "allow_unreviewed_one_cast", False):
        return {
            "required": False,
            "passed": True,
            "overridden": True,
            "reason": "--allow-unreviewed-one-cast was supplied.",
        }

    register_path = Path(getattr(args, "decision_register", ".autofish-live/signal-proof-decisions.json"))
    register = load_decision_register(register_path)
    scope_token = get_session_plan_review_token(session_plan_info)
    latest = (
        latest_accepted_decision(register, signal="oneCast", scope_token=scope_token)
        if scope_token
        else latest_signal_decision(register, "oneCast")
    )
    decision = latest.get("decision") if latest else None
    passed = decision in ("promote", "fallback-only")
    gate = {
        "required": True,
        "passed": passed,
        "overridden": False,
        "register": str(register_path),
        "acceptedDecisions": ["promote", "fallback-only"],
        "scopeToken": scope_token,
        "requiresScopeMatch": bool(scope_token),
        "latestOneCastDecision": latest,
    }
    if not passed:
        gate["reason"] = (
            "Confirmed bounded-session requires a reviewed oneCast decision of promote or fallback-only in "
            f"{register_path}. Run one-cast proof, record it with signal-proof decide --signal oneCast"
            + decision_scope_hint(session_plan_info, scope_token)
            + ", or intentionally bypass with --allow-unreviewed-one-cast."
        )
    return gate


def check_fan_candidate_review_gate(
    session_plan_info: dict[str, Any] | None,
    register_path: str,
    allow_unreviewed: bool,
) -> dict[str, Any]:
    plan = session_plan_info.get("plan") if isinstance(session_plan_info, dict) else None
    if not isinstance(plan, dict):
        return {
            "required": False,
            "passed": True,
            "reason": "No session plan source requires a reviewed fishability candidate.",
        }

    source = plan.get("source") if isinstance(plan.get("source"), dict) else {}
    safety = plan.get("safety") if isinstance(plan.get("safety"), dict) else {}
    required = (
        source.get("type") == "fishabilityFanCandidate"
        or safety.get("requiresReviewedFishableCandidateBeforeConfirmInput") is True
    )
    gate: dict[str, Any] = {
        "required": bool(required),
        "passed": True,
        "source": source,
        "register": register_path,
    }
    if not required:
        gate["reason"] = "Session plan was not created from a fishability-fan candidate."
        return gate
    if allow_unreviewed:
        gate.update(
            {
                "passed": True,
                "overridden": True,
                "reason": "--allow-unreviewed-fan-candidate was supplied.",
            }
        )
        return gate

    register = load_decision_register(Path(register_path))
    scope_token = get_session_plan_review_token(session_plan_info)
    latest = (
        latest_accepted_decision(register, signal="fishabilityCandidate", scope_token=scope_token)
        if scope_token
        else latest_signal_decision(register, "fishabilityCandidate")
    )
    decision = latest.get("decision") if latest else None
    passed = decision in ("promote", "fallback-only")
    gate.update(
        {
            "passed": passed,
            "overridden": False,
            "acceptedDecisions": ["promote", "fallback-only"],
            "scopeToken": scope_token,
            "requiresScopeMatch": bool(scope_token),
            "latestFishabilityCandidateDecision": latest,
        }
    )
    if not passed:
        gate["reason"] = (
            "Confirmed one-cast from a fishability-fan session plan requires a reviewed fishabilityCandidate "
            f"decision of promote or fallback-only in {register_path}. Run reticle skip-click/cancel proof for the "
            "candidate, then record it with signal-proof decide --signal fishabilityCandidate"
            + decision_scope_hint(session_plan_info, scope_token)
            + ", or intentionally bypass with --allow-unreviewed-fan-candidate."
        )
    return gate


def read_text_from_offset(path: Path, offset: int, max_bytes: int) -> tuple[str, int, bool]:
    current_size = path.stat().st_size
    start = offset if offset <= current_size else 0
    truncated = False
    with path.open("rb") as f:
        f.seek(start)
        data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    return data.decode("utf-8", errors="replace"), start + len(data), truncated


def tail_lines(path: Path, line_count: int, max_bytes: int = 65536) -> list[str]:
    if line_count <= 0 or not path.exists():
        return []
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - max_bytes))
        text = f.read(max_bytes).decode("utf-8", errors="replace")
    return text.splitlines()[-line_count:]


def scan_text_terms(text: str, terms: list[str]) -> dict[str, Any]:
    lowered = text.lower()
    term_counts = {term: lowered.count(term.lower()) for term in terms}
    matched_lines: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        line_lower = line.lower()
        hits = [term for term in terms if term.lower() in line_lower]
        if hits:
            matched_lines.append(
                {
                    "lineNumberInCapture": index,
                    "terms": hits,
                    "text": line[:500],
                }
            )
    return {
        "termCounts": term_counts,
        "matchedLineCount": len(matched_lines),
        "matchedLines": matched_lines[:100],
        "matchedLinesTruncated": len(matched_lines) > 100,
    }


def write_wav_pcm16(path: Path, pcm_data: bytes, *, sample_rate: int, channels: int) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)


def analyze_pcm16_windows(pcm_data: bytes, *, sample_rate: int, channels: int, window_ms: int) -> dict[str, Any]:
    bytes_per_frame = channels * 2
    complete_bytes = len(pcm_data) - (len(pcm_data) % bytes_per_frame)
    pcm_data = pcm_data[:complete_bytes]
    total_frames = len(pcm_data) // bytes_per_frame
    window_frames = max(1, int(sample_rate * max(window_ms, 1) / 1000))
    windows: list[dict[str, Any]] = []
    aggregate_peak = 0
    aggregate_sum_sq = 0
    aggregate_samples = 0

    for start_frame in range(0, total_frames, window_frames):
        end_frame = min(total_frames, start_frame + window_frames)
        chunk = pcm_data[start_frame * bytes_per_frame : end_frame * bytes_per_frame]
        sample_count = len(chunk) // 2
        if sample_count == 0:
            continue
        peak = 0
        sum_sq = 0
        for (sample,) in struct.iter_unpack("<h", chunk):
            magnitude = abs(int(sample))
            if magnitude > peak:
                peak = magnitude
            sum_sq += int(sample) * int(sample)
        aggregate_peak = max(aggregate_peak, peak)
        aggregate_sum_sq += sum_sq
        aggregate_samples += sample_count
        rms = (sum_sq / sample_count) ** 0.5
        windows.append(
            {
                "startMs": round(start_frame * 1000 / sample_rate, 2),
                "endMs": round(end_frame * 1000 / sample_rate, 2),
                "peak": peak,
                "peakNormalized": round(peak / 32768, 6),
                "rms": round(rms, 2),
                "rmsNormalized": round(rms / 32768, 6),
            }
        )

    aggregate_rms = (aggregate_sum_sq / aggregate_samples) ** 0.5 if aggregate_samples else 0.0
    loudest_windows = sorted(windows, key=lambda item: item["peak"], reverse=True)[:10]
    return {
        "sampleRate": sample_rate,
        "channels": channels,
        "bytes": len(pcm_data),
        "durationSeconds": round(total_frames / sample_rate, 3) if sample_rate else 0,
        "aggregate": {
            "peak": aggregate_peak,
            "peakNormalized": round(aggregate_peak / 32768, 6),
            "rms": round(aggregate_rms, 2),
            "rmsNormalized": round(aggregate_rms / 32768, 6),
        },
        "windowMs": window_ms,
        "windowCount": len(windows),
        "loudestWindows": loudest_windows,
        "windows": windows,
    }


def record_audio_pcm16(*, seconds: float, sample_rate: int, channels: int, device_id: int) -> bytes:
    if seconds <= 0:
        raise ValueError("Audio proof duration must be greater than zero seconds.")
    if channels not in (1, 2):
        raise ValueError("Audio proof supports mono or stereo PCM only.")
    if sample_rate < 8000 or sample_rate > 192000:
        raise ValueError("Sample rate must be between 8000 and 192000 Hz.")

    device_count = int(winmm.waveInGetNumDevs())
    resolved_device_id = WAVE_MAPPER if device_id < 0 else device_id
    if device_id >= device_count:
        raise RuntimeError(f"Requested audio input device {device_id}, but only {device_count} device(s) are available.")

    block_align = channels * 2
    buffer_length = int(seconds * sample_rate * block_align)
    buffer_length -= buffer_length % block_align
    if buffer_length <= 0:
        raise ValueError("Audio buffer length resolved to zero bytes.")

    fmt = WAVEFORMATEX()
    fmt.wFormatTag = WAVE_FORMAT_PCM
    fmt.nChannels = channels
    fmt.nSamplesPerSec = sample_rate
    fmt.nAvgBytesPerSec = sample_rate * block_align
    fmt.nBlockAlign = block_align
    fmt.wBitsPerSample = 16
    fmt.cbSize = 0

    handle = wintypes.HANDLE()
    mm_check(
        winmm.waveInOpen(ctypes.byref(handle), resolved_device_id, ctypes.byref(fmt), 0, 0, CALLBACK_NULL),
        "waveInOpen",
    )
    buffer = ctypes.create_string_buffer(buffer_length)
    header = WAVEHDR()
    header.lpData = ctypes.cast(buffer, ctypes.c_void_p)
    header.dwBufferLength = buffer_length
    header.dwBytesRecorded = 0

    prepared = False
    try:
        mm_check(winmm.waveInPrepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveInPrepareHeader")
        prepared = True
        mm_check(winmm.waveInAddBuffer(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveInAddBuffer")
        mm_check(winmm.waveInStart(handle), "waveInStart")
        time.sleep(seconds)
        stop_result = winmm.waveInStop(handle)
        if stop_result != 0:
            mm_check(stop_result, "waveInStop")
        reset_result = winmm.waveInReset(handle)
        if reset_result != 0:
            mm_check(reset_result, "waveInReset")
        recorded = min(int(header.dwBytesRecorded), buffer_length)
        return bytes(buffer.raw[:recorded])
    finally:
        if prepared:
            winmm.waveInUnprepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header))
        winmm.waveInClose(handle)


def run_signal_proof_reticle(args: argparse.Namespace) -> int:
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-reticle-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)

    if not args.dry_run and not args.confirm_input:
        raise RuntimeError("Use --dry-run or --confirm-input. Live input is never implicit.")
    if args.dry_run and args.confirm_input:
        raise RuntimeError("Use only one of --dry-run or --confirm-input.")
    if args.key == "-" and args.confirm_input and not args.allow_reload_key:
        raise RuntimeError("Refusing to send '-' because it triggers reloadui on this setup. Use --allow-reload-key only intentionally.")
    if args.cancel_after_key and not args.skip_click:
        raise RuntimeError("--cancel-after-key is only valid with --skip-click.")

    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.reticle.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry-run" if args.dry_run else "confirm-input",
        "safety": {
            "sendsMovement": False,
            "sendsLoop": False,
            "requiresExactPidHwnd": True,
            "sendsFishingKeyOnce": bool(args.confirm_input),
            "clickCount": 1 if args.confirm_input and not args.skip_click else 0,
            "cancelKeySent": bool(args.confirm_input and args.skip_click and args.cancel_after_key),
            "blocksReloadKeyByDefault": True,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "clientX": args.x,
            "clientY": args.y,
            "key": args.key,
            "cropSize": args.crop_size,
            "watchSeconds": args.watch_seconds,
            "watchIntervalMs": args.watch_interval_ms,
            "skipClick": bool(args.skip_click),
            "cancelAfterKey": bool(args.cancel_after_key),
        },
        "target": None,
        "captures": [],
        "actions": [],
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "Reticle color classification is heuristic and must be manually reviewed before promotion.",
                "Cursor handle values are useful within a run, but not guaranteed stable across sessions.",
            ],
        },
    }

    try:
        if args.confirm_input:
            focus_target(hwnd)
        target = validate_target(hwnd, args.pid, require_foreground=args.confirm_input)
        assert_client_point(target, args.x, args.y)
        manifest["target"] = target

        def capture(label: str, extra: dict[str, Any] | None = None) -> None:
            path = output_root / f"{label}.bmp"
            capture_info = capture_client_crop(hwnd, args.pid, args.x, args.y, args.crop_size, path)
            capture_info["label"] = label
            capture_info["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            if extra:
                capture_info.update(extra)
            manifest["captures"].append(capture_info)
            write_manifest(output_root, manifest)

        capture("baseline")

        if args.confirm_input:
            screen_x, screen_y = client_to_screen(hwnd, args.x, args.y)
            validate_target(hwnd, args.pid, require_foreground=True)
            move_cursor_to(screen_x, screen_y)
            time.sleep(args.post_hover_delay_ms / 1000.0)
            manifest["actions"].append({"name": "move-cursor", "screenX": screen_x, "screenY": screen_y})
            capture("after-hover")

            validate_target(hwnd, args.pid, require_foreground=True)
            key_info = press_key_once(args.key, args.key_hold_ms)
            manifest["actions"].append({"name": "press-key", **key_info})
            time.sleep(args.post_key_delay_ms / 1000.0)
            capture("after-key")

            if args.skip_click:
                manifest["actions"].append({"name": "skip-click", "reason": "--skip-click"})
            else:
                validate_target(hwnd, args.pid, require_foreground=True)
                move_cursor_to(screen_x, screen_y)
                time.sleep(0.05)
                left_click()
                manifest["actions"].append({"name": "left-click", "screenX": screen_x, "screenY": screen_y})
                time.sleep(args.post_click_delay_ms / 1000.0)
                capture("after-click")
            if args.watch_seconds > 0:
                watch_started = time.monotonic()
                deadline = watch_started + args.watch_seconds
                index = 0
                while time.monotonic() <= deadline:
                    validate_target(hwnd, args.pid, require_foreground=True)
                    elapsed_ms = int((time.monotonic() - watch_started) * 1000)
                    phase = "after-key" if args.skip_click else "after-click"
                    capture(f"watch-{index:03d}", {"elapsedSinceWatchStartMs": elapsed_ms, "watchPhase": phase})
                    index += 1
                    time.sleep(max(args.watch_interval_ms, 50) / 1000.0)
            if args.skip_click and args.cancel_after_key:
                validate_target(hwnd, args.pid, require_foreground=True)
                cancel_info = press_key_once("escape", args.key_hold_ms)
                manifest["actions"].append({"name": "cancel-after-key", **cancel_info})
                time.sleep(0.2)
                capture("after-cancel")
        else:
            would_capture_labels = ["baseline", "after-hover", "after-key"]
            if not args.skip_click:
                would_capture_labels.append("after-click")
            elif args.cancel_after_key:
                would_capture_labels.append("after-cancel")
            manifest["actions"].append(
                {
                    "name": "dry-run-plan",
                    "wouldMoveCursor": True,
                    "wouldPressKey": args.key,
                    "wouldLeftClick": not args.skip_click,
                    "wouldPressCancelKey": bool(args.skip_click and args.cancel_after_key),
                    "wouldCaptureLabels": would_capture_labels,
                    "wouldWatchSeconds": args.watch_seconds,
                }
            )

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_one_cast(args: argparse.Namespace) -> int:
    plan_defaults = apply_session_plan_defaults(args, include_session_defaults=False)
    require_runtime_values(args, ("pid", "hwnd", "x", "y"), context="one-cast")
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-one-cast-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    runtime_defaults = apply_fishing_runtime_defaults(args, include_session_defaults=False)

    if args.key == "-" and args.confirm_input and not args.allow_reload_key:
        raise RuntimeError("Refusing to send '-' because it triggers reloadui on this setup. Use --allow-reload-key only intentionally.")
    if args.pull_clicks < 0:
        raise RuntimeError("--pull-clicks must be zero or greater.")
    if args.cast_wait_seconds < 0 or args.cast_wait_seconds > 120:
        raise RuntimeError("--cast-wait-seconds must be between 0 and 120.")

    mode = "confirm-input" if args.confirm_input else "dry-run"
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.oneCast.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "safety": {
            "sendsMovement": False,
            "sendsLoop": False,
            "maxCasts": 1,
            "requiresExactPidHwnd": True,
            "requiresForegroundForInput": True,
            "doesNotRestoreMinimizedWindow": True,
            "sendsFishingKeyOnce": bool(args.confirm_input),
            "clickCount": (0 if args.dry_run else ((0 if args.skip_confirm_click else 1) + int(args.pull_clicks))),
            "blocksReloadKeyByDefault": True,
            "stopFile": args.stop_file,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "clientX": args.x,
            "clientY": args.y,
            "key": args.key,
            "cropSize": args.crop_size,
            "keyHoldMs": args.key_hold_ms,
            "postKeyDelayMs": args.post_key_delay_ms,
            "postClickDelayMs": args.post_click_delay_ms,
            "castWaitSeconds": args.cast_wait_seconds,
            "pullClicks": args.pull_clicks,
            "postPullDelayMs": args.post_pull_delay_ms,
            "skipConfirmClick": bool(args.skip_confirm_click),
            "dryRun": bool(args.dry_run),
            "confirmInput": bool(args.confirm_input),
        },
        "sessionPlan": plan_defaults["sessionPlan"],
        "sessionPlanAppliedDefaults": plan_defaults["appliedDefaults"],
        "profile": runtime_defaults["profile"],
        "appliedDefaults": runtime_defaults["appliedDefaults"],
        "target": None,
        "captures": [],
        "actions": [],
        "result": {
            "classification": "unproven",
            "completed": False,
        },
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "This is one bounded cast/click/wait/pull proof, not an unattended loop.",
                "Success still requires review of game feedback such as castbar, chat, inventory, or visible loot.",
            ],
        },
        "reviewGates": {},
    }

    try:
        manifest["reviewGates"]["fishabilityCandidate"] = (
            check_fan_candidate_review_gate(
                plan_defaults["sessionPlan"],
                args.decision_register,
                args.allow_unreviewed_fan_candidate,
            )
            if args.confirm_input
            else {
                "required": False,
                "passed": True,
                "reason": "Dry-run sends no input.",
            }
        )
        if args.confirm_input and not manifest["reviewGates"]["fishabilityCandidate"].get("passed"):
            raise RuntimeError(
                str(manifest["reviewGates"]["fishabilityCandidate"].get("reason") or "Fishability candidate review gate failed.")
            )

        def validate_current_target(*, require_foreground: bool) -> dict[str, Any]:
            current = validate_target(hwnd, args.pid, require_foreground=require_foreground)
            target_gate = check_session_plan_target_freshness(plan_defaults["sessionPlan"], current)
            manifest["reviewGates"]["targetCurrent"] = target_gate
            if not target_gate.get("passed"):
                raise RuntimeError(str(target_gate.get("reason") or "Session plan target freshness gate failed."))
            return current

        if args.confirm_input:
            focus_target(hwnd)
        target = validate_current_target(require_foreground=args.confirm_input)
        assert_client_point(target, args.x, args.y)
        if target.get("isMinimized") and args.confirm_input:
            raise RuntimeError("Target is minimized; restore/maximize Rift manually before live one-cast proof.")
        manifest["target"] = target

        def capture(label: str, extra: dict[str, Any] | None = None) -> None:
            path = output_root / f"{label}.bmp"
            capture_info = capture_client_crop(hwnd, args.pid, args.x, args.y, args.crop_size, path)
            capture_info["label"] = label
            capture_info["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            if extra:
                capture_info.update(extra)
            manifest["captures"].append(capture_info)
            write_manifest(output_root, manifest)

        capture("baseline")

        if args.dry_run:
            manifest["actions"].append(
                {
                    "name": "dry-run-plan",
                    "wouldMoveCursor": True,
                    "wouldPressKey": args.key,
                    "wouldConfirmClick": not args.skip_confirm_click,
                    "wouldWaitSeconds": args.cast_wait_seconds,
                    "wouldPullClicks": args.pull_clicks,
                    "wouldCaptureLabels": [
                        "baseline",
                        "after-hover",
                        "after-key",
                        "after-confirm-click",
                        "before-pull",
                        "after-pull-001",
                    ],
                }
            )
            manifest["result"] = {
                "classification": "dry-run-ready",
                "completed": True,
                "liveInputSent": False,
            }
        else:
            assert_stop_file_absent(args.stop_file)
            validate_current_target(require_foreground=True)
            screen_x, screen_y = client_to_screen(hwnd, args.x, args.y)
            move_cursor_to(screen_x, screen_y)
            time.sleep(args.post_hover_delay_ms / 1000.0)
            manifest["actions"].append({"name": "move-cursor", "screenX": screen_x, "screenY": screen_y})
            capture("after-hover")

            assert_stop_file_absent(args.stop_file)
            validate_current_target(require_foreground=True)
            key_info = press_key_once(args.key, args.key_hold_ms)
            manifest["actions"].append({"name": "press-fishing-key", **key_info})
            time.sleep(args.post_key_delay_ms / 1000.0)
            capture("after-key")

            if args.skip_confirm_click:
                manifest["actions"].append({"name": "skip-confirm-click", "reason": "--skip-confirm-click"})
            else:
                assert_stop_file_absent(args.stop_file)
                validate_current_target(require_foreground=True)
                move_cursor_to(screen_x, screen_y)
                time.sleep(0.05)
                left_click()
                manifest["actions"].append({"name": "confirm-cast-click", "screenX": screen_x, "screenY": screen_y})
                time.sleep(args.post_click_delay_ms / 1000.0)
                capture("after-confirm-click")

            wait_seconds_with_stop(float(args.cast_wait_seconds), args.stop_file)
            capture("before-pull")

            for pull_index in range(1, int(args.pull_clicks) + 1):
                assert_stop_file_absent(args.stop_file)
                validate_current_target(require_foreground=True)
                move_cursor_to(screen_x, screen_y)
                time.sleep(0.05)
                left_click()
                manifest["actions"].append(
                    {"name": f"pull-or-loot-click-{pull_index:03d}", "screenX": screen_x, "screenY": screen_y}
                )
                time.sleep(args.post_pull_delay_ms / 1000.0)
                capture(f"after-pull-{pull_index:03d}")

            manifest["result"] = {
                "classification": "bounded-one-cast-evidence",
                "completed": True,
                "liveInputSent": True,
                "actionCount": len(manifest["actions"]),
                "captureCount": len(manifest["captures"]),
            }

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json"), "classification": manifest["result"]["classification"]}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_bounded_session(args: argparse.Namespace) -> int:
    plan_defaults = apply_session_plan_defaults(args, include_session_defaults=True)
    require_runtime_values(args, ("pid", "hwnd", "x", "y"), context="bounded-session")
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-bounded-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    runtime_defaults = apply_fishing_runtime_defaults(args, include_session_defaults=True)

    if args.key == "-" and args.confirm_input and not args.allow_reload_key:
        raise RuntimeError("Refusing to send '-' because it triggers reloadui on this setup. Use --allow-reload-key only intentionally.")
    if args.max_casts < 1 or args.max_casts > args.max_allowed_casts:
        raise RuntimeError(f"--max-casts must be between 1 and --max-allowed-casts ({args.max_allowed_casts}).")
    if args.max_allowed_casts < 1 or args.max_allowed_casts > 50:
        raise RuntimeError("--max-allowed-casts must be between 1 and 50.")
    if args.pull_clicks < 0 or args.pull_clicks > 5:
        raise RuntimeError("--pull-clicks must be between 0 and 5.")
    if args.cast_wait_seconds < 0 or args.cast_wait_seconds > 120:
        raise RuntimeError("--cast-wait-seconds must be between 0 and 120.")

    mode = "confirm-input" if args.confirm_input else "dry-run"
    per_cast_clicks = (0 if args.skip_confirm_click else 1) + int(args.pull_clicks)
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.boundedSession.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "safety": {
            "sendsMovement": False,
            "sendsLoop": bool(args.confirm_input and args.max_casts > 1),
            "requiresExactPidHwnd": True,
            "requiresForegroundForInput": True,
            "doesNotRestoreMinimizedWindow": True,
            "requiresPriorOneCastPromotion": True,
            "requiresSupervision": True,
            "sendsFishingKeyCount": int(args.max_casts) if args.confirm_input else 0,
            "maxCasts": int(args.max_casts),
            "maxAllowedCasts": int(args.max_allowed_casts),
            "maxClickCount": int(args.max_casts) * per_cast_clicks if args.confirm_input else 0,
            "blocksReloadKeyByDefault": True,
            "stopFile": args.stop_file,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "clientX": args.x,
            "clientY": args.y,
            "key": args.key,
            "maxCasts": args.max_casts,
            "cropSize": args.crop_size,
            "keyHoldMs": args.key_hold_ms,
            "postHoverDelayMs": args.post_hover_delay_ms,
            "postKeyDelayMs": args.post_key_delay_ms,
            "postClickDelayMs": args.post_click_delay_ms,
            "castWaitSeconds": args.cast_wait_seconds,
            "pullClicks": args.pull_clicks,
            "postPullDelayMs": args.post_pull_delay_ms,
            "interCastDelayMs": args.inter_cast_delay_ms,
            "skipConfirmClick": bool(args.skip_confirm_click),
            "captureEachCast": bool(args.capture_each_cast),
            "dryRun": bool(args.dry_run),
            "confirmInput": bool(args.confirm_input),
        },
        "sessionPlan": plan_defaults["sessionPlan"],
        "sessionPlanAppliedDefaults": plan_defaults["appliedDefaults"],
        "profile": runtime_defaults["profile"],
        "appliedDefaults": runtime_defaults["appliedDefaults"],
        "reviewGate": None,
        "targetGate": None,
        "target": None,
        "captures": [],
        "casts": [],
        "result": {
            "classification": "unproven",
            "completed": False,
        },
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "This is a supervised bounded session proof, not an unattended runtime loop.",
                "Use only after one-cast proof has been reviewed for the current fishable coordinate.",
                "Success still requires review of game feedback such as castbar, chat, inventory, or visible loot.",
            ],
        },
    }

    try:
        manifest["reviewGate"] = (
            check_one_cast_review_gate(args, plan_defaults["sessionPlan"])
            if args.confirm_input
            else {
                "required": False,
                "passed": True,
                "reason": "Dry-run sends no input.",
            }
        )
        if args.confirm_input and not manifest["reviewGate"].get("passed"):
            raise RuntimeError(str(manifest["reviewGate"].get("reason") or "One-cast review gate failed."))

        def validate_current_target(*, require_foreground: bool) -> dict[str, Any]:
            current = validate_target(hwnd, args.pid, require_foreground=require_foreground)
            target_gate = check_session_plan_target_freshness(plan_defaults["sessionPlan"], current)
            manifest["targetGate"] = target_gate
            if not target_gate.get("passed"):
                raise RuntimeError(str(target_gate.get("reason") or "Session plan target freshness gate failed."))
            return current

        if args.confirm_input:
            focus_target(hwnd)
        target = validate_current_target(require_foreground=args.confirm_input)
        assert_client_point(target, args.x, args.y)
        if target.get("isMinimized") and args.confirm_input:
            raise RuntimeError("Target is minimized; restore/maximize Rift manually before live bounded-session proof.")
        manifest["target"] = target

        def capture(label: str, extra: dict[str, Any] | None = None) -> None:
            path = output_root / f"{label}.bmp"
            capture_info = capture_client_crop(hwnd, args.pid, args.x, args.y, args.crop_size, path)
            capture_info["label"] = label
            capture_info["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            if extra:
                capture_info.update(extra)
            manifest["captures"].append(capture_info)
            write_manifest(output_root, manifest)

        capture("baseline")

        if args.dry_run:
            manifest["casts"].append(
                {
                    "castNumber": 1,
                    "name": "dry-run-plan",
                    "wouldRepeatCasts": int(args.max_casts),
                    "wouldMoveCursor": True,
                    "wouldPressKey": args.key,
                    "wouldConfirmClick": not args.skip_confirm_click,
                    "wouldWaitSecondsPerCast": args.cast_wait_seconds,
                    "wouldPullClicksPerCast": args.pull_clicks,
                    "wouldCaptureEachCast": bool(args.capture_each_cast),
                }
            )
            manifest["result"] = {
                "classification": "dry-run-ready",
                "completed": True,
                "liveInputSent": False,
                "castCount": int(args.max_casts),
            }
        else:
            screen_x, screen_y = client_to_screen(hwnd, args.x, args.y)
            for cast_number in range(1, int(args.max_casts) + 1):
                assert_stop_file_absent(args.stop_file)
                cast: dict[str, Any] = {
                    "castNumber": cast_number,
                    "startedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "actions": [],
                    "completed": False,
                }

                validate_current_target(require_foreground=True)
                move_cursor_to(screen_x, screen_y)
                time.sleep(args.post_hover_delay_ms / 1000.0)
                cast["actions"].append({"name": "move-cursor", "screenX": screen_x, "screenY": screen_y})
                if args.capture_each_cast:
                    capture(f"cast-{cast_number:03d}-after-hover", {"castNumber": cast_number})

                assert_stop_file_absent(args.stop_file)
                validate_current_target(require_foreground=True)
                key_info = press_key_once(args.key, args.key_hold_ms)
                cast["actions"].append({"name": "press-fishing-key", **key_info})
                time.sleep(args.post_key_delay_ms / 1000.0)
                if args.capture_each_cast:
                    capture(f"cast-{cast_number:03d}-after-key", {"castNumber": cast_number})

                if args.skip_confirm_click:
                    cast["actions"].append({"name": "skip-confirm-click", "reason": "--skip-confirm-click"})
                else:
                    assert_stop_file_absent(args.stop_file)
                    validate_current_target(require_foreground=True)
                    move_cursor_to(screen_x, screen_y)
                    time.sleep(0.05)
                    left_click()
                    cast["actions"].append({"name": "confirm-cast-click", "screenX": screen_x, "screenY": screen_y})
                    time.sleep(args.post_click_delay_ms / 1000.0)
                    if args.capture_each_cast:
                        capture(f"cast-{cast_number:03d}-after-confirm-click", {"castNumber": cast_number})

                wait_seconds_with_stop(float(args.cast_wait_seconds), args.stop_file)

                for pull_index in range(1, int(args.pull_clicks) + 1):
                    assert_stop_file_absent(args.stop_file)
                    validate_current_target(require_foreground=True)
                    move_cursor_to(screen_x, screen_y)
                    time.sleep(0.05)
                    left_click()
                    cast["actions"].append(
                        {"name": f"pull-or-loot-click-{pull_index:03d}", "screenX": screen_x, "screenY": screen_y}
                    )
                    time.sleep(args.post_pull_delay_ms / 1000.0)

                capture(f"cast-{cast_number:03d}-complete", {"castNumber": cast_number})
                cast["completed"] = True
                cast["completedAtUtc"] = datetime.now(timezone.utc).isoformat()
                manifest["casts"].append(cast)
                write_manifest(output_root, manifest)

                if cast_number < int(args.max_casts) and args.inter_cast_delay_ms > 0:
                    wait_seconds_with_stop(args.inter_cast_delay_ms / 1000.0, args.stop_file)

            manifest["result"] = {
                "classification": "bounded-session-evidence",
                "completed": True,
                "liveInputSent": True,
                "castCount": len(manifest["casts"]),
                "captureCount": len(manifest["captures"]),
            }

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json"), "classification": manifest["result"]["classification"]}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def parse_int_list(values: list[int] | None, default: list[int]) -> list[int]:
    if not values:
        return list(default)
    return [int(value) for value in values]


def generate_fan_candidates(
    *,
    origin_x: int,
    origin_y: int,
    forward_x: int,
    forward_y: int,
    distances: list[int],
    laterals: list[int],
    max_points: int,
    client_width: int,
    client_height: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dx = forward_x - origin_x
    dy = forward_y - origin_y
    length = math.hypot(dx, dy)
    if length < 1.0:
        raise RuntimeError("Forward point must differ from origin by at least 1 client pixel.")

    unit_x = dx / length
    unit_y = dy / length
    right_x = -unit_y
    right_y = unit_x

    candidates: list[dict[str, Any]] = []
    for distance in distances:
        for lateral in laterals:
            x = int(round(origin_x + unit_x * distance + right_x * lateral))
            y = int(round(origin_y + unit_y * distance + right_y * lateral))
            candidates.append(
                {
                    "index": len(candidates),
                    "name": f"d{distance}_l{lateral}",
                    "clientX": x,
                    "clientY": y,
                    "distancePx": distance,
                    "lateralPx": lateral,
                    "inBounds": 0 <= x < client_width and 0 <= y < client_height,
                    "plannedClassification": "unproven-pending-game-feedback",
                    "notes": [
                        "This is a screen-space candidate point, not a water claim.",
                        "Fishability must be classified by castbar, chat/error, item, inventory, or other game feedback.",
                    ],
                }
            )
            if len(candidates) >= max_points:
                break
        if len(candidates) >= max_points:
            break

    geometry = {
        "origin": {"clientX": origin_x, "clientY": origin_y},
        "forwardPoint": {"clientX": forward_x, "clientY": forward_y},
        "forwardVector": {"dx": round(unit_x, 6), "dy": round(unit_y, 6)},
        "rightVector": {"dx": round(right_x, 6), "dy": round(right_y, 6)},
        "distancesPx": distances,
        "lateralsPx": laterals,
        "maxPoints": max_points,
    }
    return candidates, geometry


def build_reticle_candidate_commands(
    *,
    pid: int,
    hwnd: int,
    x: int,
    y: int,
    key: str,
    watch_seconds: float,
) -> dict[str, Any]:
    helper = "python tools\\autofish-helper-py\\autofish_helper.py"
    base = (
        f"{helper} signal-proof reticle "
        f"--pid {pid} "
        f"--hwnd {quote_ps(hwnd_hex(hwnd))} "
        f"--x {x} "
        f"--y {y} "
        f"--key {quote_ps(str(key))}"
    )
    return {
        "reticleDryRun": f"{base} --dry-run",
        "reticleSkipClickCancel": (
            f"{base} --watch-seconds {watch_seconds:g} --confirm-input --skip-click --cancel-after-key"
        ),
        "notes": [
            "Run the dry-run command first.",
            "The skip-click command sends one cursor move and one fishing keypress, captures the reticle, then presses Escape; it sends no left click.",
            "Only run confirmed commands while supervised and after exact PID/HWND/foreground are current.",
        ],
    }


def render_fishability_fan_runbook(manifest_path: str) -> str:
    path = Path(manifest_path)
    manifest = load_json_object(path)
    schema = str(manifest.get("schema") or "")
    if schema != "autofish.signalProof.fishabilityFan.v1":
        raise RuntimeError(f"Unsupported fishability fan manifest schema in {path}: {schema or '<missing>'}")

    request = manifest.get("request") if isinstance(manifest.get("request"), dict) else {}
    target = manifest.get("target") if isinstance(manifest.get("target"), dict) else {}
    candidates = manifest.get("candidates") if isinstance(manifest.get("candidates"), list) else []
    lines = [
        "# AutoFish Fishability Fan Runbook",
        "",
        f"- manifest: `{path}`",
        f"- generated: `{manifest.get('generatedAtUtc', '-')}`",
        f"- target PID/HWND: `{request.get('pid', '-')}` / `{target.get('hwnd', request.get('hwnd', '-'))}`",
        f"- fan origin: `({request.get('originX', '-')},{request.get('originY', '-')})`",
        f"- forward point: `({request.get('forwardX', '-')},{request.get('forwardY', '-')})`",
        "",
        "Safety notes:",
        "",
        "- Run candidate commands strictly one candidate at a time.",
        "- Run each candidate dry-run before any confirmed skip-click/cancel proof.",
        "- Confirmed skip-click/cancel commands send one cursor move, one fishing keypress, short captures, and Escape; they send no left click and no movement.",
        "- Stop if PID/HWND, foreground, window size, character position, or fishable context changed.",
        "",
    ]

    if not candidates:
        lines.append("No candidates were found in this manifest.")
        return "\n".join(lines).rstrip() + "\n"

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        index = candidate.get("index", "?")
        name = candidate.get("name", "candidate")
        x = candidate.get("clientX", "?")
        y = candidate.get("clientY", "?")
        in_bounds = bool(candidate.get("inBounds"))
        lines.extend(
            [
                f"## Candidate {index}: {name}",
                "",
                f"- client point: `({x},{y})`",
                f"- in bounds: `{str(in_bounds).lower()}`",
            ]
        )
        commands = candidate.get("suggestedCommands") if isinstance(candidate.get("suggestedCommands"), dict) else {}
        if not in_bounds:
            lines.extend(["", "Skipped: candidate is outside the effective client bounds.", ""])
            continue
        dry_run = commands.get("reticleDryRun")
        skip_click = commands.get("reticleSkipClickCancel")
        if not dry_run or not skip_click:
            lines.extend(["", "Blocked: this candidate has no suggested reticle commands in the manifest.", ""])
            continue
        session_plan_path = f".autofish-live/session-plan-candidate-{index}.json"
        lines.extend(
            [
                "",
                "Dry-run:",
                "",
                "```powershell",
                str(dry_run),
                "```",
                "",
                "Supervised skip-click/cancel proof:",
                "",
                "```powershell",
                str(skip_click),
                "```",
                "",
                "If reviewed as fishable, create a one-cast session plan from this candidate:",
                "",
                "```powershell",
                (
                    "python tools\\autofish-helper-py\\autofish_helper.py session-plan from-fan "
                    f"--manifest {quote_ps(str(path))} "
                    f"--candidate-index {index} "
                    "--profile starter-pond "
                    f"--output {quote_ps(session_plan_path)}"
                ),
                "```",
                "",
                "Then print that session plan's scoped runbook and record the fishabilityCandidate decision with its review scope token:",
                "",
                "```powershell",
                (
                    "python tools\\autofish-helper-py\\autofish_helper.py session-plan runbook "
                    f"--path {quote_ps(session_plan_path)}"
                ),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def run_signal_proof_fishability_fan_runbook(args: argparse.Namespace) -> int:
    try:
        markdown = render_fishability_fan_runbook(args.manifest)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")
            print(json.dumps({"ok": True, "path": str(output_path)}, indent=2))
        else:
            print(markdown, end="")
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_fishability_fan(args: argparse.Namespace) -> int:
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-fishability-fan-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        raise RuntimeError("fishability-fan currently supports --dry-run only; no probe input is implemented.")
    if args.key == "-":
        raise RuntimeError("Refusing to generate '-' reticle probe commands because it triggers reloadui on this setup.")
    if args.probe_watch_seconds < 0 or args.probe_watch_seconds > 10:
        raise RuntimeError("--probe-watch-seconds must be between 0 and 10.")

    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.fishabilityFan.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry-run",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsFishingKey": False,
            "clickCount": 0,
            "requiresExactPidHwnd": True,
            "requiresCoordinateSourceForActorFacing": True,
            "movementCalibrationImplemented": False,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "originX": args.origin_x,
            "originY": args.origin_y,
            "forwardX": args.forward_x,
            "forwardY": args.forward_y,
            "clientWidth": args.client_width,
            "clientHeight": args.client_height,
            "distancePx": args.distance_px,
            "lateralPx": args.lateral_px,
            "maxPoints": args.max_points,
            "cropSize": args.crop_size,
            "captureCrops": not args.no_capture_crops,
            "key": args.key,
            "probeWatchSeconds": args.probe_watch_seconds,
        },
        "target": None,
        "geometry": None,
        "candidates": [],
        "captures": [],
        "decision": {
            "classification": "planning-only",
            "notes": [
                "This command plans a screen-space fishability fan; it does not prove water.",
                "Use game feedback such as castbar, chat/error text, item events, and inventory deltas to classify candidate points.",
                "Coordinate-backed facing calibration requires a reliable before/after player position source before any micro-step movement is useful.",
            ],
        },
    }

    try:
        target = validate_target(hwnd, args.pid, require_foreground=False)
        manifest["target"] = target
        if (args.client_width is None) != (args.client_height is None):
            raise RuntimeError("--client-width and --client-height must be supplied together.")

        live_width = int(target["clientWidth"])
        live_height = int(target["clientHeight"])
        using_operator_size = False
        if live_width > 0 and live_height > 0:
            width = live_width
            height = live_height
        elif args.client_width is not None and args.client_height is not None:
            if not args.no_capture_crops:
                raise RuntimeError(
                    "Target client rect is unavailable; use --no-capture-crops with --client-width/--client-height for planning-only."
                )
            if args.client_width <= 0 or args.client_height <= 0:
                raise RuntimeError("--client-width and --client-height must be positive.")
            width = int(args.client_width)
            height = int(args.client_height)
            using_operator_size = True
        else:
            minimized_note = " Target appears minimized." if target.get("isMinimized") else ""
            raise RuntimeError(
                f"Target client rect is unavailable ({live_width}x{live_height}).{minimized_note} "
                "Restore/maximize Rift before capture planning, or pass --client-width/--client-height "
                "with --no-capture-crops for geometry-only planning."
            )

        effective_target = dict(target)
        effective_target["clientWidth"] = width
        effective_target["clientHeight"] = height
        effective_target["clientSizeSource"] = "operator-supplied" if using_operator_size else "live-target"
        manifest["effectiveClient"] = {
            "width": width,
            "height": height,
            "source": effective_target["clientSizeSource"],
            "liveWidth": live_width,
            "liveHeight": live_height,
            "targetMinimized": bool(target.get("isMinimized")),
        }
        assert_client_point(effective_target, args.origin_x, args.origin_y)
        assert_client_point(effective_target, args.forward_x, args.forward_y)

        distances = parse_int_list(args.distance_px, [180, 280, 380])
        laterals = parse_int_list(args.lateral_px, [-120, 0, 120])
        if args.max_points < 1:
            raise RuntimeError("--max-points must be at least 1")

        candidates, geometry = generate_fan_candidates(
            origin_x=args.origin_x,
            origin_y=args.origin_y,
            forward_x=args.forward_x,
            forward_y=args.forward_y,
            distances=distances,
            laterals=laterals,
            max_points=args.max_points,
            client_width=width,
            client_height=height,
        )
        manifest["geometry"] = geometry
        for candidate in candidates:
            if candidate["inBounds"]:
                candidate["suggestedCommands"] = build_reticle_candidate_commands(
                    pid=args.pid,
                    hwnd=hwnd,
                    x=int(candidate["clientX"]),
                    y=int(candidate["clientY"]),
                    key=args.key,
                    watch_seconds=float(args.probe_watch_seconds),
                )
        manifest["candidates"] = candidates
        if using_operator_size:
            manifest["decision"]["notes"].append(
                "Candidate bounds used operator-supplied client dimensions because the live target client rect was unavailable."
            )

        if not args.no_capture_crops:
            for candidate in candidates:
                if not candidate["inBounds"]:
                    continue
                label = safe_file_stem(candidate["name"], f"candidate-{candidate['index']:02d}")
                path = output_root / f"{candidate['index']:02d}-{label}.bmp"
                capture_info = capture_client_crop(
                    hwnd,
                    args.pid,
                    int(candidate["clientX"]),
                    int(candidate["clientY"]),
                    args.crop_size,
                    path,
                )
                capture_info["candidateIndex"] = candidate["index"]
                capture_info["candidateName"] = candidate["name"]
                capture_info["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
                manifest["captures"].append(capture_info)

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def normalize_base_url(base_url: str) -> str:
    text = str(base_url or "").strip()
    if not text:
        raise RuntimeError("ChromaLink base URL cannot be empty.")
    if not text.endswith("/"):
        text += "/"
    return text


def chromalink_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(normalize_base_url(base_url), path.lstrip("/"))


def fetch_json(url: str, *, timeout_seconds: float, max_bytes: int = 1_048_576) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AutoFish-helper/1 read-only",
        },
        method="GET",
    )
    result: dict[str, Any] = {
        "url": url,
        "status": None,
        "ok": False,
        "elapsedMs": None,
        "bodyTruncated": False,
        "json": None,
        "parseError": None,
        "error": None,
    }

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            result["status"] = int(response.status)
            body = response.read(max_bytes + 1)
            result["ok"] = 200 <= int(response.status) < 300
    except urllib.error.HTTPError as exc:
        result["status"] = int(exc.code)
        body = exc.read(max_bytes + 1)
        result["error"] = str(exc)
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        result["elapsedMs"] = round((time.perf_counter() - started) * 1000.0, 2)
        result["error"] = str(exc)
        return result

    result["elapsedMs"] = round((time.perf_counter() - started) * 1000.0, 2)
    if len(body) > max_bytes:
        body = body[:max_bytes]
        result["bodyTruncated"] = True
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        result["parseError"] = "Response body was empty."
        return result
    try:
        result["json"] = json.loads(text)
    except json.JSONDecodeError as exc:
        result["parseError"] = str(exc)
        result["bodyPreview"] = text[:400]
    return result


def get_object(value: Any, key: str) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get(key), dict):
        return value[key]
    return {}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def classify_chromalink_world_state(health: dict[str, Any], ready: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    health_json = health.get("json") if isinstance(health.get("json"), dict) else {}
    ready_json = ready.get("json") if isinstance(ready.get("json"), dict) else {}
    world_json = world.get("json") if isinstance(world.get("json"), dict) else {}
    navigation = get_object(world_json, "navigation")
    player = get_object(world_json, "player")
    position = get_object(player, "position")

    health_ready_fresh = (
        bool(health.get("ok"))
        and health_json.get("ok") is True
        and health_json.get("ready") is True
        and health_json.get("fresh") is True
        and health_json.get("stale") is not True
    )
    ready_ready_fresh = (
        bool(ready.get("ok"))
        and (not isinstance(ready_json, dict) or ready_json.get("ready", True) is not False)
    )
    world_ready_fresh = (
        bool(world.get("ok"))
        and world_json.get("ok") is True
        and world_json.get("ready") is True
        and world_json.get("fresh") is True
        and world_json.get("stale") is not True
    )
    player_position_available = navigation.get("playerPositionAvailable") is True
    player_position_present = all(is_number(position.get(axis)) for axis in ("x", "y", "z"))
    player_position_fresh = position.get("fresh") is True
    player_position_stale = position.get("stale") is True
    coordinate_ready = (
        health_ready_fresh
        and ready_ready_fresh
        and world_ready_fresh
        and player_position_available
        and player_position_present
        and player_position_fresh
        and not player_position_stale
    )

    if coordinate_ready:
        classification = "fresh-player-position"
    elif health.get("status") is None and world.get("status") is None and health.get("error") and world.get("error"):
        classification = "bridge-down-or-unreachable"
    elif not health_ready_fresh:
        classification = "provider-health-not-fresh"
    elif not world_ready_fresh:
        classification = "world-state-not-fresh"
    elif not player_position_available or not player_position_present:
        classification = "player-position-missing"
    elif not player_position_fresh or player_position_stale:
        classification = "player-position-stale"
    else:
        classification = "needs-review"

    return {
        "classification": classification,
        "coordinateReady": coordinate_ready,
        "healthReadyFresh": health_ready_fresh,
        "readyEndpointOk": bool(ready.get("ok")),
        "worldReadyFresh": world_ready_fresh,
        "playerPositionAvailable": player_position_available,
        "playerPositionPresent": player_position_present,
        "playerPositionFresh": player_position_fresh,
        "playerPositionStale": player_position_stale,
        "snapshotAgeSeconds": world_json.get("snapshotAgeSeconds"),
        "playerPosition": {
            "x": position.get("x"),
            "y": position.get("y"),
            "z": position.get("z"),
            "observedAtUtc": position.get("observedAtUtc"),
            "ageMs": position.get("ageMs"),
            "fresh": position.get("fresh"),
            "stale": position.get("stale"),
        }
        if player_position_present
        else None,
        "navigation": {
            "playerPositionAvailable": navigation.get("playerPositionAvailable"),
            "headingAvailable": navigation.get("headingAvailable"),
            "facingAvailable": navigation.get("facingAvailable"),
            "routeAvailable": navigation.get("routeAvailable"),
            "controlAvailable": navigation.get("controlAvailable"),
            "limitations": navigation.get("limitations") if isinstance(navigation.get("limitations"), list) else [],
        },
    }


def query_chromalink_world_state(base_url: str, *, timeout_seconds: float) -> dict[str, Any]:
    health = fetch_json(chromalink_url(base_url, "/health"), timeout_seconds=timeout_seconds)
    ready = fetch_json(chromalink_url(base_url, "/ready"), timeout_seconds=timeout_seconds)
    world = fetch_json(chromalink_url(base_url, "/api/v1/riftreader/world-state"), timeout_seconds=timeout_seconds)
    classification = classify_chromalink_world_state(health, ready, world)
    return {
        "observedAtUtc": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "ready": ready,
        "worldState": world,
        "classification": classification,
    }


def wait_for_chromalink_position(
    base_url: str,
    *,
    timeout_seconds: float,
    wait_seconds: float,
    poll_interval_ms: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.0, float(wait_seconds))
    attempts: list[dict[str, Any]] = []
    while True:
        attempt = query_chromalink_world_state(base_url, timeout_seconds=timeout_seconds)
        attempt["index"] = len(attempts) + 1
        attempts.append(attempt)
        classification = attempt["classification"]
        if classification.get("coordinateReady") or time.monotonic() >= deadline:
            return {
                "attempts": attempts,
                "summary": classification,
                "coordinateReady": bool(classification.get("coordinateReady")),
                "position": classification.get("playerPosition"),
            }
        time.sleep(max(0.05, poll_interval_ms / 1000.0))


def compute_facing_delta(before: dict[str, Any], after: dict[str, Any], *, min_distance: float) -> dict[str, Any]:
    dx = float(after["x"]) - float(before["x"])
    dy = float(after["y"]) - float(before["y"])
    dz = float(after["z"]) - float(before["z"])
    distance_xy = math.hypot(dx, dy)
    distance_xyz = math.sqrt((dx * dx) + (dy * dy) + (dz * dz))
    if distance_xy > 0:
        unit_x = dx / distance_xy
        unit_y = dy / distance_xy
        angle_degrees = math.degrees(math.atan2(unit_y, unit_x))
        if angle_degrees < 0:
            angle_degrees += 360.0
    else:
        unit_x = 0.0
        unit_y = 0.0
        angle_degrees = None

    usable = distance_xy >= min_distance
    if usable:
        classification = "usable-coordinate-delta"
    elif distance_xyz > 0:
        classification = "vertical-or-too-small-delta"
    else:
        classification = "no-coordinate-delta"

    return {
        "classification": classification,
        "usable": usable,
        "minDistance": min_distance,
        "delta": {
            "x": round(dx, 6),
            "y": round(dy, 6),
            "z": round(dz, 6),
            "distanceXY": round(distance_xy, 6),
            "distanceXYZ": round(distance_xyz, 6),
        },
        "operationalFacing": {
            "basis": "coordinate-delta-after-forward-pulse",
            "worldVectorXY": {
                "x": round(unit_x, 6),
                "y": round(unit_y, 6),
            },
            "angleDegreesMath": round(angle_degrees, 3) if angle_degrees is not None else None,
            "angleConvention": "0 degrees = +X, 90 degrees = +Y; coordinate-system semantic north is unknown.",
            "isNativeActorFacing": False,
        },
    }


def parse_addon_coord_line(line: str) -> dict[str, Any]:
    values: dict[str, float] = {}
    for axis, value in ADDON_COORD_RE.findall(line or ""):
        values[axis.lower()] = float(value)

    if not all(axis in values for axis in ("x", "y", "z")):
        raise RuntimeError(
            "Could not parse x/y/z from addon coordinate line. "
            'Expected text like: coords x=1.23 y=4.56 z=7.89 playerUnit=...'
        )

    unit_match = ADDON_PLAYER_UNIT_RE.search(line or "")
    return {
        "source": "autofish-addon-slash-output",
        "line": line,
        "x": values["x"],
        "y": values["y"],
        "z": values["z"],
        "playerUnit": unit_match.group(1) if unit_match else None,
    }


def addon_coordinate_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    numeric_values = (args.addon_x, args.addon_y, args.addon_z)
    has_any_numeric = any(value is not None for value in numeric_values)
    if has_any_numeric and not all(value is not None for value in numeric_values):
        raise RuntimeError("--addon-x, --addon-y, and --addon-z must be supplied together.")

    if has_any_numeric:
        return {
            "source": "manual-addon-coordinate-values",
            "line": args.addon_line,
            "x": float(args.addon_x),
            "y": float(args.addon_y),
            "z": float(args.addon_z),
            "playerUnit": None,
        }

    if args.addon_line:
        return parse_addon_coord_line(args.addon_line)

    return None


def compare_coordinates(addon_position: dict[str, Any], bridge_position: dict[str, Any], *, tolerance: float) -> dict[str, Any]:
    deltas = {
        axis: round(float(bridge_position[axis]) - float(addon_position[axis]), 6)
        for axis in ("x", "y", "z")
    }
    abs_deltas = {axis: round(abs(value), 6) for axis, value in deltas.items()}
    max_abs_delta = max(abs_deltas.values())
    matched = all(value <= tolerance for value in abs_deltas.values())
    return {
        "matched": matched,
        "tolerance": tolerance,
        "deltas": deltas,
        "absoluteDeltas": abs_deltas,
        "maxAbsoluteDelta": round(max_abs_delta, 6),
        "classification": "coordinate-match" if matched else "coordinate-mismatch",
    }


def run_signal_proof_coordinate_crosscheck(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-coordinate-crosscheck-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)

    base_url = normalize_base_url(args.base_url)
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.coordinateCrosscheck.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsFishingKey": False,
            "clickCount": 0,
            "modifiesChromaLink": False,
            "usesChromaLinkAsReadOnlyProvider": True,
            "requiresManualAddonCoordinateEvidence": True,
            "headingFacingYawExpected": False,
        },
        "request": {
            "baseUrl": base_url,
            "timeoutSeconds": args.timeout_seconds,
            "waitSeconds": args.wait_seconds,
            "pollIntervalMs": args.poll_interval_ms,
            "tolerance": args.tolerance,
            "requireMatch": bool(args.require_match),
            "pid": args.pid,
            "hwnd": args.hwnd,
            "addonLine": args.addon_line,
            "addonValuesProvided": any(value is not None for value in (args.addon_x, args.addon_y, args.addon_z)),
        },
        "target": None,
        "addonPosition": None,
        "chromalink": None,
        "result": {
            "classification": "unproven",
            "matched": False,
        },
        "decision": {
            "classification": "unproven",
            "notes": [
                "This proof compares manual /autofish coords output against ChromaLink player.position.",
                "It sends no game input and does not modify ChromaLink.",
                "A match proves coordinate-source agreement only; it does not prove native actor-facing/yaw.",
            ],
        },
    }

    try:
        if args.tolerance < 0:
            raise RuntimeError("--tolerance must be zero or greater.")
        if (args.pid is None) != (args.hwnd is None):
            raise RuntimeError("--pid and --hwnd must be supplied together when target validation is requested.")
        if args.pid is not None and args.hwnd is not None:
            manifest["target"] = validate_target(parse_hwnd(args.hwnd), int(args.pid), require_foreground=False)

        addon_position = addon_coordinate_from_args(args)
        manifest["addonPosition"] = addon_position

        chromalink_position = wait_for_chromalink_position(
            base_url,
            timeout_seconds=args.timeout_seconds,
            wait_seconds=args.wait_seconds,
            poll_interval_ms=args.poll_interval_ms,
        )
        manifest["chromalink"] = chromalink_position

        if addon_position is None:
            result = {
                "classification": "missing-addon-coordinate",
                "matched": False,
                "reason": "Run /autofish coords after reloading the addon, then pass the printed line with --addon-line or the numbers with --addon-x/--addon-y/--addon-z.",
            }
        elif not chromalink_position.get("coordinateReady"):
            result = {
                "classification": "chromalink-not-fresh",
                "matched": False,
                "reason": "ChromaLink did not provide fresh player.position.",
                "chromalinkClassification": (chromalink_position.get("summary") or {}).get("classification"),
            }
        else:
            bridge_position = chromalink_position.get("position")
            if not isinstance(bridge_position, dict):
                raise RuntimeError("ChromaLink reported coordinateReady without a player position object.")
            result = compare_coordinates(addon_position, bridge_position, tolerance=float(args.tolerance))

        manifest["result"] = result
        manifest["decision"]["classification"] = result["classification"]
        write_manifest(output_root, manifest)

        response = {
            "ok": bool(result.get("matched")),
            "outputRoot": str(output_root),
            "manifest": str(output_root / "manifest.json"),
            "classification": result.get("classification"),
            "matched": bool(result.get("matched")),
            "addonPosition": addon_position,
            "chromalinkPosition": chromalink_position.get("position"),
            "result": result,
        }
        print(json.dumps(response, indent=2))
        if args.require_match and not result.get("matched"):
            return 1
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_chromalink(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-chromalink-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)

    base_url = normalize_base_url(args.base_url)
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.chromalinkWorldState.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsFishingKey": False,
            "clickCount": 0,
            "modifiesChromaLink": False,
            "usesChromaLinkAsReadOnlyProvider": True,
            "usesPublishedHttpContract": True,
            "requiresFreshPlayerPositionForCoordinateTruth": True,
            "headingFacingYawExpected": False,
        },
        "request": {
            "baseUrl": base_url,
            "timeoutSeconds": args.timeout_seconds,
            "waitSeconds": args.wait_seconds,
            "pollIntervalMs": args.poll_interval_ms,
            "requireFresh": bool(args.require_fresh),
            "pid": args.pid,
            "hwnd": args.hwnd,
        },
        "target": None,
        "attempts": [],
        "summary": None,
        "decision": {
            "classification": "unproven",
            "notes": [
                "ChromaLink is consumed read-only through its published local HTTP bridge.",
                "Reachability is not enough; AutoFish requires fresh player.position before using coordinates as live truth.",
                "ChromaLink world-state does not provide player heading/facing/yaw in the current contract.",
            ],
        },
    }

    try:
        if (args.pid is None) != (args.hwnd is None):
            raise RuntimeError("--pid and --hwnd must be supplied together when target validation is requested.")
        if args.pid is not None and args.hwnd is not None:
            manifest["target"] = validate_target(parse_hwnd(args.hwnd), int(args.pid), require_foreground=False)

        deadline = time.monotonic() + max(0.0, float(args.wait_seconds))
        attempt_index = 0
        while True:
            attempt_index += 1
            attempt = query_chromalink_world_state(base_url, timeout_seconds=args.timeout_seconds)
            attempt["index"] = attempt_index
            classification = attempt["classification"]
            manifest["attempts"].append(attempt)
            manifest["summary"] = classification
            manifest["decision"]["classification"] = classification["classification"]
            if classification["coordinateReady"] or time.monotonic() >= deadline:
                break
            time.sleep(max(0.05, args.poll_interval_ms / 1000.0))

        write_manifest(output_root, manifest)
        ok = bool(manifest["summary"] and manifest["summary"].get("coordinateReady"))
        result = {
            "ok": ok,
            "outputRoot": str(output_root),
            "manifest": str(output_root / "manifest.json"),
            "classification": manifest["decision"]["classification"],
            "coordinateReady": ok,
            "playerPosition": manifest["summary"].get("playerPosition") if isinstance(manifest.get("summary"), dict) else None,
        }
        print(json.dumps(result, indent=2))
        if args.require_fresh and not ok:
            return 1
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_facing_delta(args: argparse.Namespace) -> int:
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-facing-delta-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    base_url = normalize_base_url(args.base_url)
    mode = "confirm-movement" if args.confirm_movement else "dry-run"
    movement_key = str(args.movement_key)

    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.facingDelta.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "safety": {
            "sendsInput": bool(args.confirm_movement),
            "sendsMovement": bool(args.confirm_movement),
            "sendsFishingKey": False,
            "clickCount": 0,
            "movementPulseCount": 1 if args.confirm_movement else 0,
            "requiresExactPidHwnd": True,
            "requiresForegroundForMovement": True,
            "requiresFreshChromaLinkBeforeMovement": True,
            "modifiesChromaLink": False,
            "usesChromaLinkAsReadOnlyProvider": True,
            "isNativeActorFacing": False,
            "blocksReloadKeyByDefault": True,
            "doesNotRestoreMinimizedWindow": True,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "baseUrl": base_url,
            "movementKey": movement_key,
            "holdMs": args.hold_ms,
            "maxHoldMs": args.max_hold_ms,
            "postMoveSettleMs": args.post_move_settle_ms,
            "timeoutSeconds": args.timeout_seconds,
            "waitFreshSeconds": args.wait_fresh_seconds,
            "pollIntervalMs": args.poll_interval_ms,
            "minDistance": args.min_distance,
            "focusIfVisible": bool(args.focus_if_visible),
        },
        "target": None,
        "before": None,
        "movement": None,
        "after": None,
        "result": None,
        "decision": {
            "classification": "unproven",
            "notes": [
                "This estimates operational facing from ChromaLink coordinate delta after a tiny forward movement pulse.",
                "It does not prove native Rift actor facing/yaw.",
                "ChromaLink is consumed read-only and must be fresh before any movement is sent.",
            ],
        },
    }

    try:
        if len(movement_key) != 1:
            raise RuntimeError("--movement-key must be exactly one character.")
        if movement_key == "-":
            raise RuntimeError("'-' is blocked because this local setup binds it to reloadui.")
        if args.hold_ms < 1:
            raise RuntimeError("--hold-ms must be at least 1.")
        if args.max_hold_ms < 1:
            raise RuntimeError("--max-hold-ms must be at least 1.")
        if args.hold_ms > args.max_hold_ms:
            raise RuntimeError(f"--hold-ms {args.hold_ms} exceeds --max-hold-ms {args.max_hold_ms}.")
        if args.min_distance < 0:
            raise RuntimeError("--min-distance must be non-negative.")

        if args.focus_if_visible:
            focus_visible_target_without_restore(hwnd)
        target = validate_target(hwnd, args.pid, require_foreground=bool(args.confirm_movement))
        if args.confirm_movement and target.get("isMinimized"):
            raise RuntimeError("Target is minimized; restore/focus Rift manually before movement proof.")
        manifest["target"] = target

        before = wait_for_chromalink_position(
            base_url,
            timeout_seconds=args.timeout_seconds,
            wait_seconds=args.wait_fresh_seconds,
            poll_interval_ms=args.poll_interval_ms,
        )
        manifest["before"] = before
        if not before["coordinateReady"]:
            manifest["decision"]["classification"] = "blocked-no-fresh-before-position"
            write_manifest(output_root, manifest)
            print(
                json.dumps(
                    {
                        "ok": False,
                        "outputRoot": str(output_root),
                        "manifest": str(output_root / "manifest.json"),
                        "classification": manifest["decision"]["classification"],
                        "reason": "Fresh ChromaLink before-position is required.",
                    },
                    indent=2,
                )
            )
            return 0

        if args.dry_run:
            manifest["movement"] = {
                "wouldSendMovement": True,
                "movementKey": movement_key,
                "holdMs": args.hold_ms,
                "reason": "Dry run only; no movement input sent.",
            }
            manifest["decision"]["classification"] = "dry-run-ready-for-confirmed-movement"
            write_manifest(output_root, manifest)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "outputRoot": str(output_root),
                        "manifest": str(output_root / "manifest.json"),
                        "classification": manifest["decision"]["classification"],
                        "beforePosition": before["position"],
                    },
                    indent=2,
                )
            )
            return 0

        movement_started = datetime.now(timezone.utc).isoformat()
        movement_action = hold_key_safely(movement_key, args.hold_ms)
        movement_action["sentAtUtc"] = movement_started
        movement_action["completedAtUtc"] = datetime.now(timezone.utc).isoformat()
        movement_action["kind"] = "tiny-forward-pulse"
        manifest["movement"] = movement_action
        time.sleep(max(0, args.post_move_settle_ms) / 1000.0)

        after = wait_for_chromalink_position(
            base_url,
            timeout_seconds=args.timeout_seconds,
            wait_seconds=args.wait_fresh_seconds,
            poll_interval_ms=args.poll_interval_ms,
        )
        manifest["after"] = after
        if not after["coordinateReady"]:
            manifest["decision"]["classification"] = "blocked-no-fresh-after-position"
            write_manifest(output_root, manifest)
            print(
                json.dumps(
                    {
                        "ok": False,
                        "outputRoot": str(output_root),
                        "manifest": str(output_root / "manifest.json"),
                        "classification": manifest["decision"]["classification"],
                        "reason": "Fresh ChromaLink after-position is required.",
                    },
                    indent=2,
                )
            )
            return 0

        result = compute_facing_delta(before["position"], after["position"], min_distance=args.min_distance)
        manifest["result"] = result
        manifest["decision"]["classification"] = result["classification"]
        write_manifest(output_root, manifest)
        print(
            json.dumps(
                {
                    "ok": bool(result["usable"]),
                    "outputRoot": str(output_root),
                    "manifest": str(output_root / "manifest.json"),
                    "classification": result["classification"],
                    "delta": result["delta"],
                    "operationalFacing": result["operationalFacing"],
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_log(args: argparse.Namespace) -> int:
    log_path = Path(args.log_path)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-log-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    terms = args.term or list(DEFAULT_LOG_TERMS)
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.log.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsLoop": False,
            "requiresExactPidHwnd": False,
        },
        "request": {
            "logPath": str(log_path),
            "durationSeconds": args.duration_seconds,
            "pollIntervalMs": args.poll_interval_ms,
            "terms": terms,
            "pid": args.pid,
            "hwnd": args.hwnd,
        },
        "observations": [],
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "Current log output must be proven during manual fishing before any runtime use.",
                "Language, settings, log path, and patch drift can make log signals fallback-only or retired.",
            ],
        },
    }

    try:
        if not log_path.exists():
            raise RuntimeError(f"Log path does not exist: {log_path}")
        if not log_path.is_file():
            raise RuntimeError(f"Log path is not a file: {log_path}")

        start_stat = log_path.stat()
        start_offset = start_stat.st_size
        manifest["logStart"] = {
            "sizeBytes": start_stat.st_size,
            "modifiedTimeUtc": datetime.fromtimestamp(start_stat.st_mtime, timezone.utc).isoformat(),
            "initialTail": tail_lines(log_path, args.initial_tail_lines),
        }
        write_manifest(output_root, manifest)

        offset = start_offset
        captured_chunks: list[str] = []
        deadline = time.monotonic() + args.duration_seconds
        while time.monotonic() < deadline:
            if log_path.exists():
                text, offset, truncated = read_text_from_offset(log_path, offset, args.max_bytes)
                if text:
                    captured_chunks.append(text)
                    manifest["observations"].append(
                        {
                            "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
                            "bytesCapturedApprox": len(text.encode("utf-8", errors="replace")),
                            "truncated": truncated,
                            "scan": scan_text_terms(text, terms),
                        }
                    )
                    write_manifest(output_root, manifest)
            time.sleep(max(args.poll_interval_ms, 100) / 1000.0)

        if log_path.exists():
            text, offset, truncated = read_text_from_offset(log_path, offset, args.max_bytes)
            if text:
                captured_chunks.append(text)
                manifest["observations"].append(
                    {
                        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
                        "bytesCapturedApprox": len(text.encode("utf-8", errors="replace")),
                        "truncated": truncated,
                        "scan": scan_text_terms(text, terms),
                    }
                )

        captured_text = "".join(captured_chunks)
        appended_path = output_root / "appended-log.txt"
        appended_path.write_text(captured_text, encoding="utf-8", errors="replace")
        manifest["logEnd"] = {
            "offset": offset,
            "appendedTextPath": str(appended_path),
            "appendedCharacterCount": len(captured_text),
            "aggregateScan": scan_text_terms(captured_text, terms),
        }
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_layout(args: argparse.Namespace) -> int:
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-layout-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    require_foreground = not args.allow_not_foreground

    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.layout.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsLoop": False,
            "requiresExactPidHwnd": True,
            "requiresForegroundByDefault": True,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "regions": args.region or [],
            "captureFullClient": args.full_client,
            "allowNotForeground": args.allow_not_foreground,
        },
        "target": None,
        "captures": [],
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "Fixed hotbar and bag coordinates are fallback-only unless the layout remains stable across live sessions.",
                "Prefer addon inventory and profile keybinds over fixed bag/actionbar pixels whenever possible.",
            ],
        },
    }

    try:
        target = validate_target(hwnd, args.pid, require_foreground=require_foreground)
        manifest["target"] = target
        regions = [parse_region_spec(spec) for spec in (args.region or [])]
        if args.full_client or not regions:
            regions.insert(
                0,
                {
                    "name": "full-client",
                    "safeName": "full-client",
                    "left": 0,
                    "top": 0,
                    "width": int(target["clientWidth"]),
                    "height": int(target["clientHeight"]),
                },
            )

        for region in regions:
            output_path = output_root / f"{region['safeName']}.bmp"
            capture = capture_client_region(
                hwnd,
                args.pid,
                region,
                output_path,
                require_foreground=require_foreground,
            )
            capture["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            manifest["captures"].append(capture)
            write_manifest(output_root, manifest)

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_slash(args: argparse.Namespace) -> int:
    hwnd = parse_hwnd(args.hwnd)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-slash-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    commands = list(args.command or [])
    if args.default_api_probes:
        commands.extend(["/autofish api", "/autofish apis", "/autofish events"])
    if not commands:
        raise RuntimeError("Provide --command at least once, or use --default-api-probes.")
    commands = [
        validate_slash_command(
            command,
            allow_reload_key=args.allow_reload_key,
            allow_non_autofish=args.allow_non_autofish,
        )
        for command in commands
    ]

    mode = "dry-run" if args.dry_run else "confirm-input"
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.slash.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "safety": {
            "sendsInput": bool(args.confirm_input),
            "sendsMovement": False,
            "sendsLoop": False,
            "requiresExactPidHwnd": True,
            "requiresForegroundForInput": True,
            "blocksReloadKeyByDefault": True,
            "restrictsToAutofishByDefault": True,
        },
        "request": {
            "pid": args.pid,
            "hwnd": hwnd_hex(hwnd),
            "commands": commands,
            "defaultApiProbes": bool(args.default_api_probes),
            "regions": args.region or [],
            "dryRun": bool(args.dry_run),
            "confirmInput": bool(args.confirm_input),
            "postCommandDelayMs": args.post_command_delay_ms,
            "interKeyDelayMs": args.inter_key_delay_ms,
            "keyHoldMs": args.key_hold_ms,
        },
        "target": None,
        "captures": [],
        "actions": [],
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "Slash proof only captures visual addon/chat output.",
                "Human review must read screenshots before promoting any API or chat signal.",
            ],
        },
    }
    write_manifest(output_root, manifest)

    def capture_regions(label: str, target: dict[str, Any], regions: list[dict[str, Any]]) -> None:
        full_region = {
            "name": "full-client",
            "safeName": "full-client",
            "left": 0,
            "top": 0,
            "width": int(target["clientWidth"]),
            "height": int(target["clientHeight"]),
        }
        for region in [full_region, *regions]:
            output_path = output_root / f"{label}-{region['safeName']}.bmp"
            capture = capture_client_region(
                hwnd,
                args.pid,
                region,
                output_path,
                require_foreground=bool(args.confirm_input),
            )
            capture["label"] = label
            capture["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            manifest["captures"].append(capture)
            write_manifest(output_root, manifest)

    try:
        if args.confirm_input:
            focus_target(hwnd)
        target = validate_target(hwnd, args.pid, require_foreground=bool(args.confirm_input))
        manifest["target"] = target
        regions = [parse_region_spec(spec) for spec in (args.region or [])]
        capture_regions("baseline", target, regions)

        if args.dry_run:
            manifest["actions"].append(
                {
                    "name": "dry-run",
                    "wouldSendCommands": commands,
                    "wouldCaptureAfterEachCommand": True,
                }
            )
            write_manifest(output_root, manifest)
            print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
            return 0

        for index, command in enumerate(commands, start=1):
            validate_target(hwnd, args.pid, require_foreground=True)
            type_text_keys(
                command,
                key_hold_ms=args.key_hold_ms,
                inter_key_delay_ms=args.inter_key_delay_ms,
            )
            press_key_once("enter", args.key_hold_ms)
            manifest["actions"].append(
                {
                    "name": "send-slash-command",
                    "index": index,
                    "command": command,
                    "sentAtUtc": datetime.now(timezone.utc).isoformat(),
                }
            )
            write_manifest(output_root, manifest)
            time.sleep(max(args.post_command_delay_ms, 0) / 1000.0)
            target = validate_target(hwnd, args.pid, require_foreground=True)
            capture_regions(f"command-{index:03d}-{safe_file_stem(command, 'slash')}", target, regions)

        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def run_signal_proof_audio(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-audio-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.audio.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "safety": {
            "sendsInput": False,
            "sendsMovement": False,
            "sendsLoop": False,
            "recordsAudioOnly": True,
        },
        "request": {
            "label": args.label,
            "seconds": args.seconds,
            "sampleRate": args.sample_rate,
            "channels": args.channels,
            "deviceId": args.device_id,
            "windowMs": args.window_ms,
            "pid": args.pid,
            "hwnd": args.hwnd,
        },
        "target": None,
        "audio": None,
        "decision": {
            "classification": "evidence-only",
            "notes": [
                "Audio is machine/device dependent and should stay fallback-only unless bite cues separate clearly from ambient sound.",
                "The default Windows recording device may be a microphone, not Rift system audio; configure Stereo Mix or a loopback device if needed.",
            ],
        },
    }

    try:
        if args.pid is not None and args.hwnd:
            manifest["target"] = validate_target(parse_hwnd(args.hwnd), args.pid, require_foreground=False)

        wav_path = output_root / f"{args.label}.wav"
        pcm_data = record_audio_pcm16(
            seconds=args.seconds,
            sample_rate=args.sample_rate,
            channels=args.channels,
            device_id=args.device_id,
        )
        write_wav_pcm16(wav_path, pcm_data, sample_rate=args.sample_rate, channels=args.channels)
        manifest["audio"] = {
            "path": str(wav_path),
            "recordedBytes": len(pcm_data),
            "analysis": analyze_pcm16_windows(
                pcm_data,
                sample_rate=args.sample_rate,
                channels=args.channels,
                window_ms=args.window_ms,
            ),
        }
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": True, "outputRoot": str(output_root), "manifest": str(output_root / "manifest.json")}, indent=2))
        return 0
    except Exception as exc:
        manifest["error"] = str(exc)
        write_manifest(output_root, manifest)
        print(json.dumps({"ok": False, "outputRoot": str(output_root), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def signal_from_schema(schema: str) -> str:
    parts = schema.split(".")
    if len(parts) >= 3 and parts[0] == "autofish" and parts[1] == "signalProof":
        return parts[2]
    return "unknown"


def load_signal_proof_manifests(proof_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    if proof_root.is_file() and proof_root.name == "manifest.json":
        candidates = [proof_root]
    else:
        candidates = sorted(proof_root.rglob("manifest.json")) if proof_root.exists() else []
    for path in candidates:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        schema = str(manifest.get("schema") or "")
        if schema.startswith("autofish.signalProof."):
            manifests.append((path, manifest))
    return manifests


def nonzero_counts(counts: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, value in counts.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count:
            result[str(key)] = count
    return result


def suggest_review(signal: str, summary: dict[str, Any]) -> str:
    if summary.get("hasError"):
        return "rerun"
    if signal == "reticle":
        if summary.get("manualReviewRequiredCount", 0) > 0:
            return "manual-review-required"
        if summary.get("watchCaptureCount", 0) > 0 and summary.get("cursorHandleCount", 0) > 1:
            return "fallback-candidate-review"
        if summary.get("nonUnknownColorCount", 0) > 0:
            return "fallback-candidate-review"
        return "needs-more-evidence"
    if signal == "oneCast":
        if summary.get("completed") and summary.get("liveInputSent"):
            return "manual-review-one-cast-feedback"
        if summary.get("completed"):
            return "ready-for-bounded-live-proof"
        return "needs-rerun"
    if signal == "boundedSession":
        if summary.get("completed") and summary.get("liveInputSent"):
            return "manual-review-bounded-session-feedback"
        if summary.get("completed"):
            return "ready-after-one-cast-review"
        return "needs-rerun"
    if signal == "fishabilityFan":
        if summary.get("candidateCount", 0) > 0:
            return "planning-only-needs-game-feedback"
        return "needs-candidates"
    if signal == "chromalinkWorldState":
        if summary.get("coordinateReady"):
            return "coordinate-source-candidate-review"
        if summary.get("classification") in ("bridge-down-or-unreachable", "provider-health-not-fresh", "world-state-not-fresh"):
            return "provider-blocked-rerun-freshness"
        return "needs-fresh-player-position"
    if signal == "coordinateCrosscheck":
        if summary.get("matched"):
            return "coordinate-source-agreement-review"
        if summary.get("classification") == "missing-addon-coordinate":
            return "needs-autofish-coords-output"
        if summary.get("classification") == "chromalink-not-fresh":
            return "provider-blocked-rerun-freshness"
        if summary.get("classification") == "coordinate-mismatch":
            return "coordinate-source-mismatch-review"
        return "needs-more-evidence"
    if signal == "facingDelta":
        if summary.get("usable"):
            return "operational-facing-candidate-review"
        if summary.get("sendsMovement") and summary.get("classification") in ("no-coordinate-delta", "vertical-or-too-small-delta"):
            return "movement-delta-too-small-review"
        if summary.get("classification", "").startswith("blocked-"):
            return "blocked-rerun-prerequisites"
        return "needs-confirmed-movement"
    if signal == "log":
        if summary.get("matchedLineCount", 0) > 0:
            return "fallback-candidate-review"
        if summary.get("appendedCharacterCount", 0) > 0:
            return "retire-candidate-unless-manual-review-finds-useful-text"
        return "needs-manual-cast-evidence"
    if signal == "layout":
        if summary.get("captureCount", 0) > 0:
            return "profile-candidate-only-after-repeat"
        return "needs-more-evidence"
    if signal == "audio":
        if summary.get("recordedBytes", 0) > 0:
            return "fallback-candidate-only-if-loud-windows-align-with-bite"
        return "needs-recording-evidence"
    if signal == "inventory":
        if summary.get("changeCount", 0) > 0:
            return "promote-candidate-review"
        return "needs-catch-delta-evidence"
    if signal == "slash":
        if summary.get("captureCount", 0) > 0 and summary.get("commandCount", 0) > 0:
            return "manual-review-addon-output"
        return "needs-slash-output-evidence"
    return "manual-review"


def summarize_signal_proof_manifest(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    schema = str(manifest.get("schema") or "unknown")
    signal = signal_from_schema(schema)
    summary: dict[str, Any] = {
        "manifestPath": str(path),
        "outputRoot": str(path.parent),
        "schema": schema,
        "signal": signal,
        "generatedAtUtc": manifest.get("generatedAtUtc"),
        "mode": manifest.get("mode"),
        "hasError": "error" in manifest,
        "error": manifest.get("error"),
    }

    if signal == "reticle":
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        colors: list[str] = []
        legacy_colors: list[str] = []
        suggestion_reasons: list[str] = []
        cursor_handles: list[str] = []
        watch_count = 0
        manual_review_count = 0
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            label = str(capture.get("label") or "")
            if label.startswith("watch-"):
                watch_count += 1
            is_reticle_phase = label in ("after-key", "after-click") or label.startswith("watch-")
            stats = capture.get("colorStats") if isinstance(capture.get("colorStats"), dict) else {}
            color = stats.get("suggestedReticleColor")
            if color:
                colors.append(str(color))
            legacy_color = stats.get("legacySuggestedReticleColor")
            if legacy_color:
                legacy_colors.append(str(legacy_color))
            reason = stats.get("suggestionReason")
            if reason:
                suggestion_reasons.append(str(reason))
            if is_reticle_phase and stats.get("manualReviewRequired"):
                manual_review_count += 1
            cursor = capture.get("cursor") if isinstance(capture.get("cursor"), dict) else {}
            handle = cursor.get("cursorHandle")
            if handle:
                cursor_handles.append(str(handle))
        summary.update(
            {
                "captureCount": len(captures),
                "watchCaptureCount": watch_count,
                "suggestedColors": sorted(set(colors)),
                "legacySuggestedColors": sorted(set(legacy_colors)),
                "suggestionReasons": sorted(set(suggestion_reasons)),
                "nonUnknownColorCount": len([color for color in colors if color != "unknown"]),
                "manualReviewRequiredCount": manual_review_count,
                "cursorHandles": sorted(set(cursor_handles)),
                "cursorHandleCount": len(set(cursor_handles)),
                "actionNames": [action.get("name") for action in manifest.get("actions", []) if isinstance(action, dict)],
            }
        )
    elif signal == "oneCast":
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        actions = manifest.get("actions") if isinstance(manifest.get("actions"), list) else []
        request = manifest.get("request") if isinstance(manifest.get("request"), dict) else {}
        result = manifest.get("result") if isinstance(manifest.get("result"), dict) else {}
        safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
        profile = manifest.get("profile") if isinstance(manifest.get("profile"), dict) else None
        review_gate = manifest.get("reviewGate") if isinstance(manifest.get("reviewGate"), dict) else {}
        summary.update(
            {
                "classification": result.get("classification"),
                "completed": bool(result.get("completed")),
                "liveInputSent": bool(result.get("liveInputSent")),
                "captureCount": len(captures),
                "captureLabels": [
                    capture.get("label")
                    for capture in captures
                    if isinstance(capture, dict) and capture.get("label")
                ],
                "actionCount": len(actions),
                "actionNames": [
                    action.get("name")
                    for action in actions
                    if isinstance(action, dict) and action.get("name")
                ],
                "clickCount": safety.get("clickCount"),
                "pullClicks": request.get("pullClicks"),
                "castWaitSeconds": request.get("castWaitSeconds"),
                "profileId": profile.get("id") if profile else None,
                "profilePath": profile.get("path") if profile else None,
                "reviewGateRequired": bool(review_gate.get("required")),
                "reviewGatePassed": bool(review_gate.get("passed")),
                "reviewGateOverridden": bool(review_gate.get("overridden")),
                "target": manifest.get("target"),
            }
        )
    elif signal == "boundedSession":
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        casts = manifest.get("casts") if isinstance(manifest.get("casts"), list) else []
        request = manifest.get("request") if isinstance(manifest.get("request"), dict) else {}
        result = manifest.get("result") if isinstance(manifest.get("result"), dict) else {}
        safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
        profile = manifest.get("profile") if isinstance(manifest.get("profile"), dict) else None
        completed_casts = [
            cast
            for cast in casts
            if isinstance(cast, dict) and cast.get("completed")
        ]
        action_names: list[str] = []
        for cast in casts:
            if not isinstance(cast, dict):
                continue
            for action in cast.get("actions", []):
                if isinstance(action, dict) and action.get("name"):
                    action_names.append(str(action.get("name")))
        summary.update(
            {
                "classification": result.get("classification"),
                "completed": bool(result.get("completed")),
                "liveInputSent": bool(result.get("liveInputSent")),
                "castCount": len(casts),
                "completedCastCount": len(completed_casts),
                "maxCasts": request.get("maxCasts"),
                "captureCount": len(captures),
                "captureLabels": [
                    capture.get("label")
                    for capture in captures
                    if isinstance(capture, dict) and capture.get("label")
                ],
                "actionCount": len(action_names),
                "actionNames": sorted(set(action_names)),
                "maxClickCount": safety.get("maxClickCount"),
                "pullClicks": request.get("pullClicks"),
                "castWaitSeconds": request.get("castWaitSeconds"),
                "profileId": profile.get("id") if profile else None,
                "profilePath": profile.get("path") if profile else None,
                "target": manifest.get("target"),
            }
        )
    elif signal == "fishabilityFan":
        candidates = manifest.get("candidates") if isinstance(manifest.get("candidates"), list) else []
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
        effective_client = manifest.get("effectiveClient") if isinstance(manifest.get("effectiveClient"), dict) else {}
        in_bounds = [candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("inBounds")]
        summary.update(
            {
                "candidateCount": len(candidates),
                "inBoundsCandidateCount": len(in_bounds),
                "captureCount": len(captures),
                "sendsInput": bool(safety.get("sendsInput")),
                "movementCalibrationImplemented": bool(safety.get("movementCalibrationImplemented")),
                "clientSizeSource": effective_client.get("source"),
                "targetMinimized": bool(effective_client.get("targetMinimized")),
            }
        )
    elif signal == "chromalinkWorldState":
        chromalink_summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
        attempts = manifest.get("attempts") if isinstance(manifest.get("attempts"), list) else []
        player_position = chromalink_summary.get("playerPosition") if isinstance(chromalink_summary.get("playerPosition"), dict) else None
        navigation = chromalink_summary.get("navigation") if isinstance(chromalink_summary.get("navigation"), dict) else {}
        summary.update(
            {
                "classification": chromalink_summary.get("classification"),
                "coordinateReady": bool(chromalink_summary.get("coordinateReady")),
                "healthReadyFresh": bool(chromalink_summary.get("healthReadyFresh")),
                "worldReadyFresh": bool(chromalink_summary.get("worldReadyFresh")),
                "playerPositionAvailable": bool(chromalink_summary.get("playerPositionAvailable")),
                "playerPositionFresh": bool(chromalink_summary.get("playerPositionFresh")),
                "attemptCount": len(attempts),
                "snapshotAgeSeconds": chromalink_summary.get("snapshotAgeSeconds"),
                "playerPosition": player_position,
                "headingAvailable": navigation.get("headingAvailable"),
                "facingAvailable": navigation.get("facingAvailable"),
                "controlAvailable": navigation.get("controlAvailable"),
            }
        )
    elif signal == "coordinateCrosscheck":
        result = manifest.get("result") if isinstance(manifest.get("result"), dict) else {}
        addon_position = manifest.get("addonPosition") if isinstance(manifest.get("addonPosition"), dict) else None
        chromalink = manifest.get("chromalink") if isinstance(manifest.get("chromalink"), dict) else {}
        chromalink_summary = chromalink.get("summary") if isinstance(chromalink.get("summary"), dict) else {}
        chromalink_position = chromalink.get("position") if isinstance(chromalink.get("position"), dict) else None
        summary.update(
            {
                "classification": result.get("classification"),
                "matched": bool(result.get("matched")),
                "tolerance": result.get("tolerance"),
                "deltas": result.get("deltas"),
                "absoluteDeltas": result.get("absoluteDeltas"),
                "maxAbsoluteDelta": result.get("maxAbsoluteDelta"),
                "addonPosition": addon_position,
                "chromalinkPosition": chromalink_position,
                "chromalinkClassification": chromalink_summary.get("classification"),
                "chromalinkCoordinateReady": bool(chromalink.get("coordinateReady")),
            }
        )
    elif signal == "facingDelta":
        safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
        result = manifest.get("result") if isinstance(manifest.get("result"), dict) else {}
        before = manifest.get("before") if isinstance(manifest.get("before"), dict) else {}
        after = manifest.get("after") if isinstance(manifest.get("after"), dict) else {}
        delta = result.get("delta") if isinstance(result.get("delta"), dict) else {}
        facing = result.get("operationalFacing") if isinstance(result.get("operationalFacing"), dict) else {}
        summary.update(
            {
                "classification": result.get("classification") or (manifest.get("decision") or {}).get("classification"),
                "usable": bool(result.get("usable")),
                "sendsMovement": bool(safety.get("sendsMovement")),
                "beforeCoordinateReady": bool(before.get("coordinateReady")),
                "afterCoordinateReady": bool(after.get("coordinateReady")),
                "delta": delta,
                "operationalFacing": facing,
                "movement": manifest.get("movement"),
            }
        )
    elif signal == "log":
        log_end = manifest.get("logEnd") if isinstance(manifest.get("logEnd"), dict) else {}
        aggregate = log_end.get("aggregateScan") if isinstance(log_end.get("aggregateScan"), dict) else {}
        summary.update(
            {
                "appendedCharacterCount": int(log_end.get("appendedCharacterCount") or 0),
                "matchedLineCount": int(aggregate.get("matchedLineCount") or 0),
                "termCounts": nonzero_counts(aggregate.get("termCounts") if isinstance(aggregate.get("termCounts"), dict) else {}),
            }
        )
    elif signal == "layout":
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        summary.update(
            {
                "captureCount": len(captures),
                "captureNames": [capture.get("name") for capture in captures if isinstance(capture, dict)],
                "target": manifest.get("target"),
            }
        )
    elif signal == "audio":
        audio = manifest.get("audio") if isinstance(manifest.get("audio"), dict) else {}
        analysis = audio.get("analysis") if isinstance(audio.get("analysis"), dict) else {}
        aggregate = analysis.get("aggregate") if isinstance(analysis.get("aggregate"), dict) else {}
        summary.update(
            {
                "recordedBytes": int(audio.get("recordedBytes") or 0),
                "durationSeconds": analysis.get("durationSeconds"),
                "peakNormalized": aggregate.get("peakNormalized"),
                "rmsNormalized": aggregate.get("rmsNormalized"),
                "loudestWindows": analysis.get("loudestWindows", [])[:5] if isinstance(analysis.get("loudestWindows"), list) else [],
            }
        )
    elif signal == "inventory":
        changes = manifest.get("changes") if isinstance(manifest.get("changes"), list) else []
        summary.update({"changeCount": len(changes), "changes": changes[:10]})
    elif signal == "slash":
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), list) else []
        actions = manifest.get("actions") if isinstance(manifest.get("actions"), list) else []
        sent_commands = [
            action.get("command")
            for action in actions
            if isinstance(action, dict) and action.get("name") == "send-slash-command"
        ]
        requested = manifest.get("request") if isinstance(manifest.get("request"), dict) else {}
        requested_commands = requested.get("commands") if isinstance(requested.get("commands"), list) else []
        summary.update(
            {
                "captureCount": len(captures),
                "captureLabels": sorted(
                    set(str(capture.get("label")) for capture in captures if isinstance(capture, dict) and capture.get("label"))
                ),
                "commandCount": len(sent_commands) or len(requested_commands),
                "commands": sent_commands or requested_commands,
                "target": manifest.get("target"),
            }
        )

    summary["suggestedReview"] = suggest_review(signal, summary)
    return summary


def render_signal_proof_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AutoFish Signal Proof Summary",
        "",
        f"Generated: {report['generatedAtUtc']}",
        f"Proof root: `{report['proofRoot']}`",
        f"Manifest count: {report['manifestCount']}",
        "",
        "| Signal | Count | Suggested review buckets |",
        "|---|---:|---|",
    ]
    for signal, bucket in sorted(report["bySignal"].items()):
        reviews = ", ".join(f"{name}={count}" for name, count in sorted(bucket["suggestedReviews"].items()))
        lines.append(f"| {signal} | {bucket['count']} | {reviews or '-'} |")
    lines.extend(["", "## Manifests", ""])
    for summary in report["summaries"]:
        lines.append(f"### {summary['signal']} - `{summary['manifestPath']}`")
        lines.append("")
        lines.append(f"- suggested review: `{summary['suggestedReview']}`")
        if summary.get("hasError"):
            lines.append(f"- error: `{summary.get('error')}`")
        if summary["signal"] == "reticle":
            lines.append(f"- captures: {summary.get('captureCount', 0)}; watch captures: {summary.get('watchCaptureCount', 0)}")
            lines.append(f"- colors: {', '.join(summary.get('suggestedColors', [])) or '-'}")
            legacy = summary.get("legacySuggestedColors", [])
            if legacy:
                lines.append(f"- legacy colors: {', '.join(legacy)}")
            if summary.get("manualReviewRequiredCount", 0):
                lines.append(f"- manual review required captures: {summary.get('manualReviewRequiredCount', 0)}")
            reasons = summary.get("suggestionReasons", [])
            if reasons:
                lines.append(f"- color reasons: {', '.join(reasons)}")
            lines.append(f"- cursor handles: {summary.get('cursorHandleCount', 0)}")
        elif summary["signal"] == "oneCast":
            lines.append(f"- classification: {summary.get('classification')}")
            lines.append(f"- completed: {summary.get('completed')}; live input sent: {summary.get('liveInputSent')}")
            lines.append(f"- actions: {summary.get('actionCount', 0)} ({', '.join(str(name) for name in summary.get('actionNames', [])) or '-'})")
            lines.append(f"- captures: {summary.get('captureCount', 0)} ({', '.join(str(label) for label in summary.get('captureLabels', [])) or '-'})")
            lines.append(f"- click count: {summary.get('clickCount')}; pull clicks: {summary.get('pullClicks')}; wait seconds: {summary.get('castWaitSeconds')}")
            if summary.get("profileId"):
                lines.append(f"- profile: {summary.get('profileId')} (`{summary.get('profilePath')}`)")
        elif summary["signal"] == "boundedSession":
            lines.append(f"- classification: {summary.get('classification')}")
            lines.append(f"- completed: {summary.get('completed')}; live input sent: {summary.get('liveInputSent')}")
            lines.append(f"- casts: {summary.get('completedCastCount', 0)}/{summary.get('maxCasts')}")
            lines.append(f"- actions: {summary.get('actionCount', 0)} ({', '.join(str(name) for name in summary.get('actionNames', [])) or '-'})")
            lines.append(f"- captures: {summary.get('captureCount', 0)} ({', '.join(str(label) for label in summary.get('captureLabels', [])) or '-'})")
            lines.append(f"- max clicks: {summary.get('maxClickCount')}; pull clicks: {summary.get('pullClicks')}; wait seconds: {summary.get('castWaitSeconds')}")
            lines.append(f"- one-cast review gate required/passed/overridden: {summary.get('reviewGateRequired')}/{summary.get('reviewGatePassed')}/{summary.get('reviewGateOverridden')}")
            if summary.get("profileId"):
                lines.append(f"- profile: {summary.get('profileId')} (`{summary.get('profilePath')}`)")
        elif summary["signal"] == "fishabilityFan":
            lines.append(f"- candidates: {summary.get('candidateCount', 0)}; in bounds: {summary.get('inBoundsCandidateCount', 0)}")
            lines.append(f"- captures: {summary.get('captureCount', 0)}")
            lines.append(f"- client size source: {summary.get('clientSizeSource')}")
            lines.append(f"- target minimized: {summary.get('targetMinimized')}")
            lines.append(f"- sends input: {summary.get('sendsInput')}")
            lines.append(f"- movement calibration implemented: {summary.get('movementCalibrationImplemented')}")
        elif summary["signal"] == "chromalinkWorldState":
            lines.append(f"- classification: {summary.get('classification')}")
            lines.append(f"- coordinate ready: {summary.get('coordinateReady')}")
            lines.append(f"- health fresh: {summary.get('healthReadyFresh')}; world fresh: {summary.get('worldReadyFresh')}")
            lines.append(f"- player position available/fresh: {summary.get('playerPositionAvailable')}/{summary.get('playerPositionFresh')}")
            lines.append(f"- attempts: {summary.get('attemptCount', 0)}; snapshot age seconds: {summary.get('snapshotAgeSeconds')}")
            position = summary.get("playerPosition") if isinstance(summary.get("playerPosition"), dict) else {}
            if position:
                lines.append(f"- player position: x={position.get('x')} y={position.get('y')} z={position.get('z')} ageMs={position.get('ageMs')}")
            lines.append(f"- heading/facing/control available: {summary.get('headingAvailable')}/{summary.get('facingAvailable')}/{summary.get('controlAvailable')}")
        elif summary["signal"] == "coordinateCrosscheck":
            lines.append(f"- classification: {summary.get('classification')}")
            lines.append(f"- matched: {summary.get('matched')}; tolerance: {summary.get('tolerance')}")
            addon_position = summary.get("addonPosition") if isinstance(summary.get("addonPosition"), dict) else {}
            chromalink_position = summary.get("chromalinkPosition") if isinstance(summary.get("chromalinkPosition"), dict) else {}
            if addon_position:
                lines.append(f"- addon coords: x={addon_position.get('x')} y={addon_position.get('y')} z={addon_position.get('z')} source={addon_position.get('source')}")
            if chromalink_position:
                lines.append(f"- ChromaLink coords: x={chromalink_position.get('x')} y={chromalink_position.get('y')} z={chromalink_position.get('z')} ageMs={chromalink_position.get('ageMs')}")
            if summary.get("absoluteDeltas"):
                lines.append(f"- absolute deltas: {summary.get('absoluteDeltas')} max={summary.get('maxAbsoluteDelta')}")
            lines.append(f"- ChromaLink classification/ready: {summary.get('chromalinkClassification')}/{summary.get('chromalinkCoordinateReady')}")
        elif summary["signal"] == "facingDelta":
            lines.append(f"- classification: {summary.get('classification')}")
            lines.append(f"- usable: {summary.get('usable')}")
            lines.append(f"- sends movement: {summary.get('sendsMovement')}")
            lines.append(f"- before/after coordinate ready: {summary.get('beforeCoordinateReady')}/{summary.get('afterCoordinateReady')}")
            delta = summary.get("delta") if isinstance(summary.get("delta"), dict) else {}
            if delta:
                lines.append(f"- delta: dx={delta.get('x')} dy={delta.get('y')} dz={delta.get('z')} distanceXY={delta.get('distanceXY')}")
            facing = summary.get("operationalFacing") if isinstance(summary.get("operationalFacing"), dict) else {}
            if facing:
                vector = facing.get("worldVectorXY") if isinstance(facing.get("worldVectorXY"), dict) else {}
                lines.append(f"- operational facing vector: x={vector.get('x')} y={vector.get('y')} angle={facing.get('angleDegreesMath')}")
        elif summary["signal"] == "log":
            lines.append(f"- appended chars: {summary.get('appendedCharacterCount', 0)}")
            lines.append(f"- matched lines: {summary.get('matchedLineCount', 0)}")
            lines.append(f"- nonzero terms: {summary.get('termCounts', {})}")
        elif summary["signal"] == "layout":
            lines.append(f"- captures: {summary.get('captureCount', 0)}")
            lines.append(f"- names: {', '.join(str(name) for name in summary.get('captureNames', [])) or '-'}")
        elif summary["signal"] == "audio":
            lines.append(f"- recorded bytes: {summary.get('recordedBytes', 0)}")
            lines.append(f"- duration seconds: {summary.get('durationSeconds')}")
            lines.append(f"- peak normalized: {summary.get('peakNormalized')}; rms normalized: {summary.get('rmsNormalized')}")
        elif summary["signal"] == "inventory":
            lines.append(f"- changes: {summary.get('changeCount', 0)}")
        elif summary["signal"] == "slash":
            lines.append(f"- commands: {summary.get('commandCount', 0)}")
            lines.append(f"- captures: {summary.get('captureCount', 0)}")
            lines.append(f"- labels: {', '.join(str(label) for label in summary.get('captureLabels', [])) or '-'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_signal_proof_summarize(args: argparse.Namespace) -> int:
    proof_root = Path(args.proof_root)
    output_root = Path(args.output_root) if args.output_root else Path(".autofish-live") / f"signal-proof-summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_root.mkdir(parents=True, exist_ok=True)

    summaries = [
        summarize_signal_proof_manifest(path, manifest)
        for path, manifest in load_signal_proof_manifests(proof_root)
    ]
    by_signal: dict[str, dict[str, Any]] = {}
    for summary in summaries:
        signal = str(summary["signal"])
        bucket = by_signal.setdefault(signal, {"count": 0, "suggestedReviews": {}})
        bucket["count"] += 1
        review = str(summary.get("suggestedReview") or "manual-review")
        bucket["suggestedReviews"][review] = bucket["suggestedReviews"].get(review, 0) + 1

    report = {
        "schema": "autofish.signalProof.summary.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "proofRoot": str(proof_root),
        "manifestCount": len(summaries),
        "bySignal": by_signal,
        "summaries": summaries,
        "notes": [
            "Suggested review buckets are not final decisions.",
            "Promotion still requires repeated live evidence and operator review.",
            "Unstable or single-environment signals should remain fallback-only.",
        ],
    }

    json_path = output_root / "summary.json"
    markdown_path = output_root / "summary.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path.write_text(render_signal_proof_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "manifestCount": len(summaries), "outputRoot": str(output_root), "summary": str(json_path), "markdown": str(markdown_path)}, indent=2))
    return 0


def load_decision_register(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": "autofish.signalProof.decisions.v1",
            "createdAtUtc": datetime.now(timezone.utc).isoformat(),
            "updatedAtUtc": None,
            "entries": [],
            "latestBySignal": {},
        }
    try:
        register = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Decision register is not valid JSON: {path}: {exc}") from exc
    if not isinstance(register, dict):
        raise RuntimeError(f"Decision register root must be a JSON object: {path}")
    register.setdefault("schema", "autofish.signalProof.decisions.v1")
    register.setdefault("createdAtUtc", datetime.now(timezone.utc).isoformat())
    register.setdefault("entries", [])
    register.setdefault("latestBySignal", {})
    if not isinstance(register["entries"], list):
        raise RuntimeError(f"Decision register entries must be a list: {path}")
    if not isinstance(register["latestBySignal"], dict):
        raise RuntimeError(f"Decision register latestBySignal must be an object: {path}")
    return register


def collect_decision_scopes(args: argparse.Namespace) -> tuple[list[str], list[dict[str, Any]]]:
    tokens: list[str] = []
    plan_scopes: list[dict[str, Any]] = []

    for token in getattr(args, "scope_token", None) or []:
        if token and str(token) not in tokens:
            tokens.append(str(token))

    for plan_path in getattr(args, "session_plan", None) or []:
        loaded = load_session_plan(plan_path)
        assert loaded is not None
        token = get_session_plan_review_token(loaded)
        if not token:
            raise RuntimeError(f"Session plan has no review.scopeToken: {plan_path}")
        if token not in tokens:
            tokens.append(token)
        plan = loaded["plan"]
        review = plan.get("review") if isinstance(plan.get("review"), dict) else {}
        plan_scopes.append(
            {
                "path": loaded["path"],
                "scopeToken": token,
                "scope": review.get("scope"),
            }
        )

    return tokens, plan_scopes


def run_signal_proof_decide(args: argparse.Namespace) -> int:
    register_path = Path(args.register)
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register = load_decision_register(register_path)
    recorded_at = datetime.now(timezone.utc).isoformat()
    scope_tokens, session_plan_scopes = collect_decision_scopes(args)
    entry = {
        "recordedAtUtc": recorded_at,
        "signal": args.signal,
        "decision": args.decision,
        "reason": args.reason,
        "evidence": args.evidence or [],
        "proofRoot": args.proof_root,
        "operator": args.operator,
        "notes": args.note or [],
        "scopeTokens": scope_tokens,
    }
    if scope_tokens:
        entry["scopeToken"] = scope_tokens[-1]
    if session_plan_scopes:
        entry["sessionPlanScopes"] = session_plan_scopes
    register["entries"].append(entry)
    register["latestBySignal"][args.signal] = entry
    register["updatedAtUtc"] = recorded_at
    register_path.write_text(json.dumps(register, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "register": str(register_path), "entry": entry}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AutoFish helper diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    session_plan = subparsers.add_parser("session-plan", help="Create or inspect local live-proof session plans")
    session_plan_sub = session_plan.add_subparsers(dest="session_plan_command", required=True)
    session_plan_create = session_plan_sub.add_parser("create", help="Create a local session plan from current PID/HWND/fishable point")
    session_plan_create.add_argument("--pid", type=int, required=True, help="Expected Rift process ID for this local session")
    session_plan_create.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    session_plan_create.add_argument("--x", type=int, required=True, help="Calibrated fishable client X")
    session_plan_create.add_argument("--y", type=int, required=True, help="Calibrated fishable client Y")
    session_plan_create.add_argument("--profile", help="Fishing profile id or JSON path to include in the plan")
    session_plan_create.add_argument("--profile-root", default="profiles", help="Profile folder for profile ids; default: profiles")
    session_plan_create.add_argument("--key", default="8", help="Fishing key default; default: 8")
    session_plan_create.add_argument("--max-casts", type=int, default=3, help="Bounded-session cast default; default: 3")
    session_plan_create.add_argument("--max-allowed-casts", type=int, default=10, help="Bounded-session safety cap default; default: 10")
    session_plan_create.add_argument("--pull-clicks", type=int, default=1, help="Pull/loot click default; default: 1")
    session_plan_create.add_argument("--cast-wait-seconds", type=float, help="Optional cast wait override; otherwise profile/default command pacing applies")
    session_plan_create.add_argument("--post-pull-delay-ms", type=int, help="Optional post-pull delay override; otherwise profile/default command pacing applies")
    session_plan_create.add_argument("--inter-cast-delay-ms", type=int, default=800, help="Inter-cast delay default; default: 800")
    session_plan_create.add_argument("--stop-file", help=f"Stop file path to include; default: {DEFAULT_STOP_FILE}")
    session_plan_create.add_argument("--validate-target", action="store_true", help="Validate PID/HWND now and record target geometry without sending input")
    session_plan_create.add_argument("--output", default=".autofish-live/session-plan-latest.json", help="Output session plan JSON path")
    session_plan_create.set_defaults(func=run_session_plan_create)
    session_plan_from_fan = session_plan_sub.add_parser("from-fan", help="Create a session plan from a fishability-fan candidate")
    session_plan_from_fan.add_argument("--manifest", required=True, help="Path to a fishability-fan manifest.json")
    fan_selector = session_plan_from_fan.add_mutually_exclusive_group(required=True)
    fan_selector.add_argument("--candidate-index", type=int, help="Candidate index from the fishability-fan manifest")
    fan_selector.add_argument("--candidate-name", help="Candidate name from the fishability-fan manifest")
    session_plan_from_fan.add_argument("--profile", help="Fishing profile id or JSON path to include in the plan")
    session_plan_from_fan.add_argument("--profile-root", default="profiles", help="Profile folder for profile ids; default: profiles")
    session_plan_from_fan.add_argument("--key", help="Fishing key default; default: manifest request key or 8")
    session_plan_from_fan.add_argument("--max-casts", type=int, default=3, help="Bounded-session cast default; default: 3")
    session_plan_from_fan.add_argument("--max-allowed-casts", type=int, default=10, help="Bounded-session safety cap default; default: 10")
    session_plan_from_fan.add_argument("--pull-clicks", type=int, default=1, help="Pull/loot click default; default: 1")
    session_plan_from_fan.add_argument("--cast-wait-seconds", type=float, help="Optional cast wait override; otherwise profile/default command pacing applies")
    session_plan_from_fan.add_argument("--post-pull-delay-ms", type=int, help="Optional post-pull delay override; otherwise profile/default command pacing applies")
    session_plan_from_fan.add_argument("--inter-cast-delay-ms", type=int, default=800, help="Inter-cast delay default; default: 800")
    session_plan_from_fan.add_argument("--stop-file", help=f"Stop file path to include; default: {DEFAULT_STOP_FILE}")
    session_plan_from_fan.add_argument("--validate-target", action="store_true", help="Validate PID/HWND now and record target geometry without sending input")
    session_plan_from_fan.add_argument("--output", default=".autofish-live/session-plan-latest.json", help="Output session plan JSON path")
    session_plan_from_fan.set_defaults(func=run_session_plan_from_fan)
    session_plan_show = session_plan_sub.add_parser("show", help="Print a session plan JSON file")
    session_plan_show.add_argument("--path", default=".autofish-live/session-plan-latest.json", help="Session plan JSON path")
    session_plan_show.set_defaults(func=run_session_plan_show)
    session_plan_gates = session_plan_sub.add_parser("gates", help="Print scoped review gate status for a session plan")
    session_plan_gates.add_argument("--path", default=".autofish-live/session-plan-latest.json", help="Session plan JSON path")
    session_plan_gates.add_argument("--decision-register", default=".autofish-live/signal-proof-decisions.json", help="Decision register path")
    session_plan_gates.add_argument(
        "--require",
        action="append",
        choices=("target-current", "confirmed-one-cast", "confirmed-bounded-session"),
        help="Return a failing exit code unless this readiness gate is true; repeatable",
    )
    session_plan_gates.set_defaults(func=run_session_plan_gates)
    session_plan_runbook = session_plan_sub.add_parser("runbook", help="Print next live-proof commands from a session plan")
    session_plan_runbook.add_argument("--path", default=".autofish-live/session-plan-latest.json", help="Session plan JSON path")
    session_plan_runbook.add_argument("--proof-root", default=".autofish-live", help="Proof root to use in suggested decision command")
    session_plan_runbook.add_argument("--output", help="Optional markdown output path")
    session_plan_runbook.set_defaults(func=run_session_plan_runbook)

    signal = subparsers.add_parser("signal-proof", help="Proof-first harness for historical/fallback signals")
    signal_sub = signal.add_subparsers(dest="signal", required=True)

    reticle = signal_sub.add_parser("reticle", help="Capture reticle/cursor evidence around a calibrated client point")
    reticle.add_argument("--pid", type=int, required=True, help="Expected Rift process ID")
    reticle.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    reticle.add_argument("--x", type=int, required=True, help="Client X coordinate of calibrated fishable point")
    reticle.add_argument("--y", type=int, required=True, help="Client Y coordinate of calibrated fishable point")
    reticle.add_argument("--key", default="8", help="Fishing key to press during --confirm-input; default: 8")
    mode = reticle.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate and capture baseline only; send no input")
    mode.add_argument("--confirm-input", action="store_true", help="Allow one cursor move, one keypress, and one left-click")
    reticle.add_argument("--allow-reload-key", action="store_true", help="Allow '-' key despite local reloadui binding")
    reticle.add_argument("--skip-click", action="store_true", help="With --confirm-input, stop after after-key capture and send no left click")
    reticle.add_argument("--cancel-after-key", action="store_true", help="With --skip-click, press Escape after after-key/watch captures and capture after-cancel")
    reticle.add_argument("--crop-size", type=int, default=180, help="Square crop size around client point; default: 180")
    reticle.add_argument("--key-hold-ms", type=int, default=80, help="Key hold duration; default: 80")
    reticle.add_argument("--post-hover-delay-ms", type=int, default=150, help="Delay after cursor move before capture")
    reticle.add_argument("--post-key-delay-ms", type=int, default=350, help="Delay after keypress before capture")
    reticle.add_argument("--post-click-delay-ms", type=int, default=800, help="Delay after click before capture")
    reticle.add_argument("--watch-seconds", type=float, default=0.0, help="Keep capturing cursor/crop evidence after click, or after key when --skip-click is used")
    reticle.add_argument("--watch-interval-ms", type=int, default=500, help="Interval between watch captures; default: 500")
    reticle.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-reticle-*.")
    reticle.set_defaults(func=run_signal_proof_reticle)

    one_cast = signal_sub.add_parser("one-cast", help="Run one bounded cast/click/wait/pull proof at a calibrated client point")
    one_cast.add_argument("--session-plan", help="Local session plan JSON providing PID/HWND/fishable point/profile defaults")
    one_cast.add_argument("--pid", type=int, help="Expected Rift process ID")
    one_cast.add_argument("--hwnd", help="Expected Rift window handle, decimal or 0x hex")
    one_cast.add_argument("--x", type=int, help="Client X coordinate of calibrated fishable point")
    one_cast.add_argument("--y", type=int, help="Client Y coordinate of calibrated fishable point")
    one_cast.add_argument("--profile", help="Fishing profile id or JSON path used for pacing defaults")
    one_cast.add_argument("--profile-root", default="profiles", help="Profile folder for profile ids; default: profiles")
    one_cast.add_argument("--key", help="Fishing key to press during --confirm-input; default: 8")
    one_cast_mode = one_cast.add_mutually_exclusive_group(required=True)
    one_cast_mode.add_argument("--dry-run", action="store_true", help="Validate and capture baseline only; send no input")
    one_cast_mode.add_argument("--confirm-input", action="store_true", help="Allow one bounded cast attempt at the calibrated point")
    one_cast.add_argument("--allow-reload-key", action="store_true", help="Allow '-' key despite local reloadui binding")
    one_cast.add_argument("--skip-confirm-click", action="store_true", help="Press the fishing key but do not left-click the cast point")
    one_cast.add_argument("--pull-clicks", type=int, help="Number of pull/loot clicks after the wait; default: 1")
    one_cast.add_argument("--cast-wait-seconds", type=float, help="Wait after cast before pull/loot clicks; default: profile biteTimeoutMs or 18")
    one_cast.add_argument("--crop-size", type=int, help="Square crop size around client point; default: 220")
    one_cast.add_argument("--key-hold-ms", type=int, help="Key hold duration; default: 80")
    one_cast.add_argument("--post-hover-delay-ms", type=int, help="Delay after cursor move before capture; default: 150")
    one_cast.add_argument("--post-key-delay-ms", type=int, help="Delay after keypress before capture; default: 350")
    one_cast.add_argument("--post-click-delay-ms", type=int, help="Delay after confirm click before capture; default: 800")
    one_cast.add_argument("--post-pull-delay-ms", type=int, help="Delay after each pull/loot click before capture; default: profile lootTimeoutMs or 1200")
    one_cast.add_argument("--stop-file", default=DEFAULT_STOP_FILE, help=f"If this file exists before/during the run, abort before the next action; default: {DEFAULT_STOP_FILE}")
    one_cast.add_argument("--decision-register", default=".autofish-live/signal-proof-decisions.json", help="Decision register used to require reviewed fishabilityCandidate proof for fan-derived session plans")
    one_cast.add_argument("--allow-unreviewed-fan-candidate", action="store_true", help="Bypass the fishabilityCandidate decision gate for fan-derived session plans intentionally")
    one_cast.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-one-cast-*.")
    one_cast.set_defaults(func=run_signal_proof_one_cast)

    bounded_session = signal_sub.add_parser("bounded-session", help="Run a supervised bounded multi-cast proof after one-cast review")
    bounded_session.add_argument("--session-plan", help="Local session plan JSON providing PID/HWND/fishable point/profile defaults")
    bounded_session.add_argument("--pid", type=int, help="Expected Rift process ID")
    bounded_session.add_argument("--hwnd", help="Expected Rift window handle, decimal or 0x hex")
    bounded_session.add_argument("--x", type=int, help="Client X coordinate of calibrated fishable point")
    bounded_session.add_argument("--y", type=int, help="Client Y coordinate of calibrated fishable point")
    bounded_session.add_argument("--profile", help="Fishing profile id or JSON path used for pacing defaults")
    bounded_session.add_argument("--profile-root", default="profiles", help="Profile folder for profile ids; default: profiles")
    bounded_session.add_argument("--key", help="Fishing key to press during --confirm-input; default: 8")
    bounded_session_mode = bounded_session.add_mutually_exclusive_group(required=True)
    bounded_session_mode.add_argument("--dry-run", action="store_true", help="Validate and capture baseline only; send no input")
    bounded_session_mode.add_argument("--confirm-input", action="store_true", help="Allow a supervised bounded session")
    bounded_session.add_argument("--allow-reload-key", action="store_true", help="Allow '-' key despite local reloadui binding")
    bounded_session.add_argument("--skip-confirm-click", action="store_true", help="Press the fishing key but do not left-click the cast point")
    bounded_session.add_argument("--max-casts", type=int, help="Number of cast attempts in this bounded session; default: 3")
    bounded_session.add_argument("--max-allowed-casts", type=int, help="Safety cap for --max-casts; default: 10")
    bounded_session.add_argument("--pull-clicks", type=int, help="Number of pull/loot clicks after each wait; default: 1")
    bounded_session.add_argument("--cast-wait-seconds", type=float, help="Wait after each cast before pull/loot clicks; default: profile biteTimeoutMs or 18")
    bounded_session.add_argument("--crop-size", type=int, help="Square crop size around client point; default: 220")
    bounded_session.add_argument("--key-hold-ms", type=int, help="Key hold duration; default: 80")
    bounded_session.add_argument("--post-hover-delay-ms", type=int, help="Delay after cursor move before optional capture; default: 150")
    bounded_session.add_argument("--post-key-delay-ms", type=int, help="Delay after keypress before optional capture; default: 350")
    bounded_session.add_argument("--post-click-delay-ms", type=int, help="Delay after confirm click before optional capture; default: 800")
    bounded_session.add_argument("--post-pull-delay-ms", type=int, help="Delay after each pull/loot click before completion capture; default: profile lootTimeoutMs or 1200")
    bounded_session.add_argument("--inter-cast-delay-ms", type=int, help="Delay between cast attempts; default: 800")
    bounded_session.add_argument("--capture-each-cast", action="store_true", help="Capture after hover/key/confirm in addition to each cast completion")
    bounded_session.add_argument("--decision-register", default=".autofish-live/signal-proof-decisions.json", help="Decision register used to require reviewed oneCast proof before confirmed sessions")
    bounded_session.add_argument("--allow-unreviewed-one-cast", action="store_true", help="Bypass the oneCast decision gate intentionally; still requires --confirm-input and all target gates")
    bounded_session.add_argument("--stop-file", default=DEFAULT_STOP_FILE, help=f"If this file exists before/during the run, abort before the next action; default: {DEFAULT_STOP_FILE}")
    bounded_session.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-bounded-session-*.")
    bounded_session.set_defaults(func=run_signal_proof_bounded_session)

    fan = signal_sub.add_parser("fishability-fan", help="Dry-run a screen-space fan of candidate fishing probe points without input")
    fan.add_argument("--pid", type=int, required=True, help="Expected Rift process ID")
    fan.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    fan.add_argument("--origin-x", type=int, required=True, help="Client X for the fan origin, typically near the player/screen anchor")
    fan.add_argument("--origin-y", type=int, required=True, help="Client Y for the fan origin, typically near the player/screen anchor")
    fan.add_argument("--forward-x", type=int, required=True, help="Client X of an operator-calibrated forward point")
    fan.add_argument("--forward-y", type=int, required=True, help="Client Y of an operator-calibrated forward point")
    fan.add_argument("--client-width", type=int, help="Planning-only client width to use when the target is minimized/unavailable; requires --client-height and --no-capture-crops")
    fan.add_argument("--client-height", type=int, help="Planning-only client height to use when the target is minimized/unavailable; requires --client-width and --no-capture-crops")
    fan.add_argument("--key", default="8", help="Fishing key to use in suggested per-candidate reticle commands; default: 8")
    fan.add_argument("--probe-watch-seconds", type=float, default=2.0, help="Watch duration for suggested skip-click reticle probe commands; default: 2")
    fan.add_argument("--distance-px", type=int, action="append", help="Forward distance in pixels; repeatable. Defaults: 180, 280, 380")
    fan.add_argument("--lateral-px", type=int, action="append", help="Right/left lateral offset in pixels; repeatable. Defaults: -120, 0, 120")
    fan.add_argument("--max-points", type=int, default=9, help="Maximum candidate points to generate; default: 9")
    fan.add_argument("--crop-size", type=int, default=140, help="No-input crop size for each in-bounds candidate; default: 140")
    fan.add_argument("--no-capture-crops", action="store_true", help="Only write candidate geometry; do not capture no-input crops")
    fan.add_argument("--dry-run", action="store_true", required=True, help="Required; fan planning sends no input")
    fan.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-fishability-fan-*.")
    fan.set_defaults(func=run_signal_proof_fishability_fan)

    fan_runbook = signal_sub.add_parser("fishability-fan-runbook", help="Print per-candidate reticle commands from a fishability-fan manifest")
    fan_runbook.add_argument("--manifest", required=True, help="Path to a fishability-fan manifest.json")
    fan_runbook.add_argument("--output", help="Optional markdown output path")
    fan_runbook.set_defaults(func=run_signal_proof_fishability_fan_runbook)

    chromalink = signal_sub.add_parser("chromalink", help="Read-only ChromaLink world-state/player-coordinate freshness proof")
    chromalink.add_argument("--base-url", default=DEFAULT_CHROMALINK_BASE_URL, help=f"ChromaLink HTTP bridge base URL; default: {DEFAULT_CHROMALINK_BASE_URL}")
    chromalink.add_argument("--timeout-seconds", type=float, default=2.0, help="HTTP timeout per endpoint; default: 2")
    chromalink.add_argument("--wait-seconds", type=float, default=0.0, help="Poll until fresh for up to this many seconds; default: 0")
    chromalink.add_argument("--poll-interval-ms", type=int, default=500, help="Poll interval while waiting; default: 500")
    chromalink.add_argument("--require-fresh", action="store_true", help="Return a failing exit code unless fresh player.position is available")
    chromalink.add_argument("--pid", type=int, help="Optional expected Rift PID to validate and record without input; requires --hwnd")
    chromalink.add_argument("--hwnd", help="Optional expected Rift HWND to validate and record without input; requires --pid")
    chromalink.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-chromalink-*.")
    chromalink.set_defaults(func=run_signal_proof_chromalink)

    coordinate_crosscheck = signal_sub.add_parser(
        "coordinate-crosscheck",
        help="Compare manual /autofish coords output to fresh read-only ChromaLink player.position",
    )
    coordinate_crosscheck.add_argument("--addon-line", help='Exact in-game /autofish coords line, for example: coords x=1.23 y=4.56 z=7.89 playerUnit=...')
    coordinate_crosscheck.add_argument("--addon-x", type=float, help="Manual addon coordX value from /autofish coords; requires --addon-y and --addon-z")
    coordinate_crosscheck.add_argument("--addon-y", type=float, help="Manual addon coordY value from /autofish coords; requires --addon-x and --addon-z")
    coordinate_crosscheck.add_argument("--addon-z", type=float, help="Manual addon coordZ value from /autofish coords; requires --addon-x and --addon-y")
    coordinate_crosscheck.add_argument("--base-url", default=DEFAULT_CHROMALINK_BASE_URL, help=f"ChromaLink HTTP bridge base URL; default: {DEFAULT_CHROMALINK_BASE_URL}")
    coordinate_crosscheck.add_argument("--timeout-seconds", type=float, default=2.0, help="HTTP timeout per ChromaLink endpoint; default: 2")
    coordinate_crosscheck.add_argument("--wait-seconds", type=float, default=2.0, help="Poll until fresh for up to this many seconds; default: 2")
    coordinate_crosscheck.add_argument("--poll-interval-ms", type=int, default=500, help="Poll interval while waiting; default: 500")
    coordinate_crosscheck.add_argument("--tolerance", type=float, default=0.5, help="Maximum allowed absolute delta on each axis; default: 0.5")
    coordinate_crosscheck.add_argument("--require-match", action="store_true", help="Return a failing exit code unless addon and ChromaLink coordinates match within tolerance")
    coordinate_crosscheck.add_argument("--pid", type=int, help="Optional expected Rift PID to validate and record without input; requires --hwnd")
    coordinate_crosscheck.add_argument("--hwnd", help="Optional expected Rift HWND to validate and record without input; requires --pid")
    coordinate_crosscheck.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-coordinate-crosscheck-*.")
    coordinate_crosscheck.set_defaults(func=run_signal_proof_coordinate_crosscheck)

    facing = signal_sub.add_parser("facing-delta", help="Estimate operational facing from fresh ChromaLink coordinate delta after a tiny confirmed movement pulse")
    facing.add_argument("--pid", type=int, required=True, help="Expected Rift process ID")
    facing.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    facing.add_argument("--base-url", default=DEFAULT_CHROMALINK_BASE_URL, help=f"ChromaLink HTTP bridge base URL; default: {DEFAULT_CHROMALINK_BASE_URL}")
    facing.add_argument("--timeout-seconds", type=float, default=2.0, help="HTTP timeout per ChromaLink endpoint; default: 2")
    facing.add_argument("--wait-fresh-seconds", type=float, default=2.0, help="Wait this long for fresh before/after player.position; default: 2")
    facing.add_argument("--poll-interval-ms", type=int, default=250, help="ChromaLink poll interval while waiting for freshness; default: 250")
    facing.add_argument("--movement-key", default="w", help="Single-character forward movement key; default: w")
    facing.add_argument("--hold-ms", type=int, default=120, help="Movement key hold duration for --confirm-movement; default: 120")
    facing.add_argument("--max-hold-ms", type=int, default=250, help="Safety cap for movement key hold duration; default: 250")
    facing.add_argument("--post-move-settle-ms", type=int, default=800, help="Delay after movement before reading after-position; default: 800")
    facing.add_argument("--min-distance", type=float, default=0.01, help="Minimum X/Y coordinate delta required to mark facing usable; default: 0.01")
    facing.add_argument("--focus-if-visible", action="store_true", help="Try SetForegroundWindow without restoring minimized Rift before validation")
    facing_mode = facing.add_mutually_exclusive_group(required=True)
    facing_mode.add_argument("--dry-run", action="store_true", help="Validate exact target and fresh before-position only; send no movement")
    facing_mode.add_argument("--confirm-movement", action="store_true", help="Allow one tiny movement-key pulse after exact foreground and fresh-coordinate gates pass")
    facing.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-facing-delta-*.")
    facing.set_defaults(func=run_signal_proof_facing_delta)

    log = signal_sub.add_parser("log", help="Capture and scan newly appended Rift log text without sending input")
    log.add_argument("--log-path", required=True, help="Path to the Rift log file to watch")
    log.add_argument("--duration-seconds", type=float, default=20.0, help="How long to watch for appended lines; default: 20")
    log.add_argument("--poll-interval-ms", type=int, default=500, help="Polling interval; default: 500")
    log.add_argument("--term", action="append", help="Fishing term to scan for; can be repeated")
    log.add_argument("--initial-tail-lines", type=int, default=0, help="Include this many existing tail lines for context")
    log.add_argument("--max-bytes", type=int, default=1_048_576, help="Maximum bytes to read per poll; default: 1 MiB")
    log.add_argument("--pid", type=int, help="Optional Rift PID to record in evidence metadata")
    log.add_argument("--hwnd", help="Optional Rift HWND to record in evidence metadata")
    log.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-log-*.")
    log.set_defaults(func=run_signal_proof_log)

    layout = signal_sub.add_parser("layout", help="Read-only screenshots for fixed hotbar/bag/layout proof")
    layout.add_argument("--pid", type=int, required=True, help="Expected Rift process ID")
    layout.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    layout.add_argument(
        "--region",
        action="append",
        help="Client region to capture as name:left,top,width,height; repeat for hotbar/bag slots",
    )
    layout.add_argument("--full-client", action="store_true", help="Also capture the full client area")
    layout.add_argument("--allow-not-foreground", action="store_true", help="Allow capture when Rift is not foreground; screenshots may include occlusion")
    layout.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-layout-*.")
    layout.set_defaults(func=run_signal_proof_layout)

    slash = signal_sub.add_parser("slash", help="Send bounded /autofish slash commands and capture visual addon/chat output")
    slash.add_argument("--pid", type=int, required=True, help="Expected Rift process ID")
    slash.add_argument("--hwnd", required=True, help="Expected Rift window handle, decimal or 0x hex")
    slash.add_argument("--command", action="append", help="Slash command to send; repeat for multiple commands")
    slash.add_argument("--default-api-probes", action="store_true", help="Send /autofish api, /autofish apis, and /autofish events")
    slash_mode = slash.add_mutually_exclusive_group(required=True)
    slash_mode.add_argument("--dry-run", action="store_true", help="Validate target and capture baseline only; send no input")
    slash_mode.add_argument("--confirm-input", action="store_true", help="Allow bounded slash-command input")
    slash.add_argument("--region", action="append", help="Extra client region to capture as name:left,top,width,height; full client is always captured")
    slash.add_argument("--post-command-delay-ms", type=int, default=800, help="Delay before capturing after each command; default: 800")
    slash.add_argument("--inter-key-delay-ms", type=int, default=20, help="Delay between typed keys; default: 20")
    slash.add_argument("--key-hold-ms", type=int, default=25, help="Key hold duration while typing; default: 25")
    slash.add_argument("--allow-reload-key", action="store_true", help="Allow '-' in command text despite local reloadui binding")
    slash.add_argument("--allow-non-autofish", action="store_true", help="Allow commands outside /autofish")
    slash.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-slash-*.")
    slash.set_defaults(func=run_signal_proof_slash)

    audio = signal_sub.add_parser("audio", help="Read-only audio proof for bite/splash cue experiments")
    audio.add_argument("--seconds", type=float, required=True, help="Recording duration in seconds")
    audio.add_argument("--label", default="manual-cast", help="Output WAV label; default: manual-cast")
    audio.add_argument("--sample-rate", type=int, default=44100, help="PCM sample rate; default: 44100")
    audio.add_argument("--channels", type=int, choices=(1, 2), default=1, help="PCM channels; default: mono")
    audio.add_argument("--device-id", type=int, default=-1, help="waveIn device id; -1 uses Windows wave mapper/default input")
    audio.add_argument("--window-ms", type=int, default=250, help="Analysis window size; default: 250")
    audio.add_argument("--pid", type=int, help="Optional Rift PID to validate/record with --hwnd")
    audio.add_argument("--hwnd", help="Optional Rift HWND to validate/record with --pid")
    audio.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-audio-*.")
    audio.set_defaults(func=run_signal_proof_audio)

    summarize = signal_sub.add_parser("summarize", help="Summarize proof manifests into review buckets")
    summarize.add_argument("--proof-root", default=".autofish-live", help="Directory or manifest.json to summarize; default: .autofish-live")
    summarize.add_argument("--output-root", help="Summary output folder; default: .autofish-live/signal-proof-summary-*.")
    summarize.set_defaults(func=run_signal_proof_summarize)

    decide = signal_sub.add_parser("decide", help="Record a reviewed promote/fallback/retire decision for a proof signal")
    decide.add_argument("--signal", choices=SIGNAL_NAMES, required=True, help="Signal being classified")
    decide.add_argument("--decision", choices=SIGNAL_DECISIONS, required=True, help="Reviewed decision")
    decide.add_argument("--reason", required=True, help="Short human-reviewed reason for the decision")
    decide.add_argument("--evidence", action="append", help="Evidence path, manifest, summary, screenshot, or note; repeat as needed")
    decide.add_argument("--scope-token", action="append", help="Session-plan review scope token this decision applies to; repeatable")
    decide.add_argument("--session-plan", action="append", help="Attach this session plan's review scope token to the decision; repeatable")
    decide.add_argument("--proof-root", default=".autofish-live", help="Proof root used for the decision; default: .autofish-live")
    decide.add_argument("--operator", help="Optional operator/reviewer name")
    decide.add_argument("--note", action="append", help="Extra note; repeat as needed")
    decide.add_argument("--register", default=".autofish-live/signal-proof-decisions.json", help="Decision register path")
    decide.set_defaults(func=run_signal_proof_decide)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
