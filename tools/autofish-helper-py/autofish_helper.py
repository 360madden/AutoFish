"""AutoFish Python helper.

Current focus: proof-first diagnostics for stale historical Rift fishing signals.

This module intentionally avoids unattended loops. Live input commands require an
exact PID/HWND and an explicit --confirm-input flag.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import struct
import sys
import time
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
SIGNAL_NAMES = ("reticle", "log", "layout", "audio", "inventory")


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

    return {
        "hwnd": hwnd_hex(hwnd),
        "ownerProcessId": int(owner_pid.value),
        "clientWidth": int(rect.right - rect.left),
        "clientHeight": int(rect.bottom - rect.top),
        "foregroundWindow": hwnd_hex(foreground),
        "foregroundMatches": foreground_matches,
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
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.05)
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


def move_cursor_to(screen_x: int, screen_y: int) -> None:
    if not user32.SetCursorPos(screen_x, screen_y):
        raise RuntimeError(last_error_message("SetCursorPos"))


def left_click() -> None:
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)


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


def color_stats(width: int, height: int, bgra_top_down: bytes) -> dict[str, Any]:
    counts = {"red": 0, "yellow": 0, "blueCyan": 0, "green": 0, "bright": 0}
    total_r = total_g = total_b = 0
    for i in range(0, width * height * 4, 4):
        b = bgra_top_down[i]
        g = bgra_top_down[i + 1]
        r = bgra_top_down[i + 2]
        total_r += r
        total_g += g
        total_b += b
        if max(r, g, b) >= 130:
            counts["bright"] += 1
        if r >= 150 and g <= 115 and b <= 115 and r >= g + 35 and r >= b + 35:
            counts["red"] += 1
        if r >= 150 and g >= 135 and b <= 130 and abs(r - g) <= 90:
            counts["yellow"] += 1
        if b >= 135 and g >= 90 and r <= 135 and b >= r + 25:
            counts["blueCyan"] += 1
        if g >= 135 and r <= 140 and b <= 150 and g >= r + 25:
            counts["green"] += 1

    color_candidates = {k: counts[k] for k in ("red", "yellow", "blueCyan", "green")}
    suggested = max(color_candidates, key=color_candidates.get)
    if color_candidates[suggested] < 20:
        suggested = "unknown"
    pixels = width * height
    return {
        "pixels": pixels,
        "averageRgb": {
            "r": round(total_r / pixels, 2),
            "g": round(total_g / pixels, 2),
            "b": round(total_b / pixels, 2),
        },
        "counts": counts,
        "suggestedReticleColor": suggested,
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

    manifest: dict[str, Any] = {
        "schema": "autofish.signalProof.reticle.v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry-run" if args.dry_run else "confirm-input",
        "safety": {
            "sendsMovement": False,
            "sendsLoop": False,
            "requiresExactPidHwnd": True,
            "sendsFishingKeyOnce": bool(args.confirm_input),
            "clickCount": 1 if args.confirm_input else 0,
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
                    capture(f"watch-{index:03d}", {"elapsedSinceWatchStartMs": elapsed_ms})
                    index += 1
                    time.sleep(max(args.watch_interval_ms, 50) / 1000.0)
        else:
            manifest["actions"].append(
                {
                    "name": "dry-run-plan",
                    "wouldMoveCursor": True,
                    "wouldPressKey": args.key,
                    "wouldLeftClick": True,
                    "wouldCaptureLabels": ["baseline", "after-hover", "after-key", "after-click"],
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
        if summary.get("watchCaptureCount", 0) > 0 and summary.get("cursorHandleCount", 0) > 1:
            return "fallback-candidate-review"
        if summary.get("nonUnknownColorCount", 0) > 0:
            return "fallback-candidate-review"
        return "needs-more-evidence"
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
        cursor_handles: list[str] = []
        watch_count = 0
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            label = str(capture.get("label") or "")
            if label.startswith("watch-"):
                watch_count += 1
            color = (
                capture.get("colorStats", {})
                .get("suggestedReticleColor")
                if isinstance(capture.get("colorStats"), dict)
                else None
            )
            if color:
                colors.append(str(color))
            cursor = capture.get("cursor") if isinstance(capture.get("cursor"), dict) else {}
            handle = cursor.get("cursorHandle")
            if handle:
                cursor_handles.append(str(handle))
        summary.update(
            {
                "captureCount": len(captures),
                "watchCaptureCount": watch_count,
                "suggestedColors": sorted(set(colors)),
                "nonUnknownColorCount": len([color for color in colors if color != "unknown"]),
                "cursorHandles": sorted(set(cursor_handles)),
                "cursorHandleCount": len(set(cursor_handles)),
                "actionNames": [action.get("name") for action in manifest.get("actions", []) if isinstance(action, dict)],
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
            lines.append(f"- cursor handles: {summary.get('cursorHandleCount', 0)}")
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


def run_signal_proof_decide(args: argparse.Namespace) -> int:
    register_path = Path(args.register)
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register = load_decision_register(register_path)
    recorded_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "recordedAtUtc": recorded_at,
        "signal": args.signal,
        "decision": args.decision,
        "reason": args.reason,
        "evidence": args.evidence or [],
        "proofRoot": args.proof_root,
        "operator": args.operator,
        "notes": args.note or [],
    }
    register["entries"].append(entry)
    register["latestBySignal"][args.signal] = entry
    register["updatedAtUtc"] = recorded_at
    register_path.write_text(json.dumps(register, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "register": str(register_path), "entry": entry}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AutoFish helper diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

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
    reticle.add_argument("--crop-size", type=int, default=180, help="Square crop size around client point; default: 180")
    reticle.add_argument("--key-hold-ms", type=int, default=80, help="Key hold duration; default: 80")
    reticle.add_argument("--post-hover-delay-ms", type=int, default=150, help="Delay after cursor move before capture")
    reticle.add_argument("--post-key-delay-ms", type=int, default=350, help="Delay after keypress before capture")
    reticle.add_argument("--post-click-delay-ms", type=int, default=800, help="Delay after click before capture")
    reticle.add_argument("--watch-seconds", type=float, default=0.0, help="After click, keep capturing cursor/crop evidence for this many seconds")
    reticle.add_argument("--watch-interval-ms", type=int, default=500, help="Interval between post-click watch captures; default: 500")
    reticle.add_argument("--output-root", help="Evidence output folder; default: .autofish-live/signal-proof-reticle-*.")
    reticle.set_defaults(func=run_signal_proof_reticle)

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
