"""
base.py — Shared types for all controller adapters.

Every adapter must implement:
    VID         : int    — USB vendor ID
    PID         : int    — USB product ID
    REPORT_SIZE : int    — HID report size in bytes
    NAME        : str    — Human-readable controller name

    open_controller() -> hidapi.Device
        Enumerate HID devices, find the controller by VID/PID, and return an
        open Device.  Raise RuntimeError if not found.

    parse_report(report: bytes) -> ControllerState | None
        Parse a raw HID report and return a ControllerState.  Return None for
        report IDs that should be skipped (e.g. non-0x30 reports on 8BitDo).

The control loop in controller.py only ever sees ControllerState — it has no
knowledge of byte layouts, VIDs, or hardware-specific quirks.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerState:
    """Normalised controller state returned by every adapter's parse_report()."""
    x:        float   # left stick X  — -1.0 (left)  … +1.0 (right)
    y:        float   # left stick Y  — -1.0 (down)  … +1.0 (up)
    trigger:  bool    # primary forward trigger (R2 / ZR / RT)
    bumper_l: bool    # left bumper  → spin vacuum left
    bumper_r: bool    # right bumper → spin vacuum right
    quit:     bool    # exit session (PS / Home / Guide)
    dock:     bool    # return to dock (Touchpad / Plus / Back)
