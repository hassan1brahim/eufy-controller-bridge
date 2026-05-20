"""
ps5.py — Sony DualSense (PS5) controller adapter.

macOS byte offset note
----------------------
macOS prepends a Report ID byte (0x01) at position 0 of every USB HID
input report, shifting all fields +1 vs the hardware spec.  Bluetooth
on macOS gives a truncated 10-byte report that omits stick data — the
controller must be connected via USB-C.

DualSense USB report layout (64 bytes, macOS offsets)
  Byte  0   Report ID (0x01 — ignored)
  Byte  1   Left stick X   0=full left  128=centre  255=full right
  Byte  2   Left stick Y   0=full up    128=centre  255=full down
  Byte  6   R2 trigger     0–255 analog
  Byte  9   bits: L1(0) R1(1) L2(2) R2(3) Create(4) L3(5) R3(6) Options(7)
  Byte 10   bits: PS(0) Touchpad(1) Mute(2)

On Linux/Windows the Report ID byte is not prepended — subtract 1 from
all offsets above.
"""

import hidapi

from .base import ControllerState

VID         = 0x054C
PID         = 0x0CE6
REPORT_SIZE = 64
NAME        = "DualSense (PS5)"


def open_controller() -> hidapi.Device:
    for d in hidapi.enumerate(VID, 0):
        if d.product_id == PID:
            return hidapi.Device(vendor_id=d.vendor_id, product_id=d.product_id)
    raise RuntimeError(f"{NAME} not found — connect via USB-C (Bluetooth not supported on macOS)")


def parse_report(report: bytes) -> ControllerState:
    """Return normalised controller state from a raw 64-byte HID report."""
    b9  = report[9]
    b10 = report[10]

    x =  (report[1] - 128) / 128.0
    y = -((report[2] - 128) / 128.0)   # invert: up = positive

    return ControllerState(
        x=x,
        y=y,
        trigger=  report[6] > 50,                           # R2 analog — ignore light touches
        bumper_l= bool(b9  & 0x01),                         # L1
        bumper_r= bool(b9  & 0x02),                         # R1
        quit=     bool(b10 & 0x01),                         # PS button
        dock=     bool(b10 & 0x02) or bool(b9 & 0x80),     # Touchpad or Options
    )
