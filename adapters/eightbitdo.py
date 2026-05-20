"""
eightbitdo.py — 8BitDo Ultimate 2 controller adapter.

The Ultimate 2 in Switch mode enumerates as a Nintendo Switch Pro Controller
(VID 0x057E / PID 0x2009).  It sends 0x30 input reports (64 bytes); reports
with a different report ID should be ignored.

Stick encoding — 12-bit values packed little-endian across three bytes:
  LX = report[6] | ((report[7] & 0x0F) << 8)   range 0–4095, centre ≈ 2048
  LY = (report[7] >> 4) | (report[8] << 4)      range 0–4095, centre ≈ 2048

Button bytes (confirmed via live diagnostic):
  report[3] bit 7 → ZR   (right trigger) → forward
  report[3] bit 6 → R    (right bumper)
  report[5] bit 6 → L    (left bumper)
  report[4] bit 4 → Home → quit
  report[4] bit 1 → Plus → dock / return home
"""

import hidapi

from .base import ControllerState

VID         = 0x057E   # Nintendo (reported by 8BitDo in Switch mode)
PID         = 0x2009   # Switch Pro Controller
REPORT_SIZE = 64
NAME        = "8BitDo Ultimate 2"


def open_controller() -> hidapi.Device:
    for d in hidapi.enumerate(VID, 0):
        if d.product_id == PID:
            return hidapi.Device(vendor_id=d.vendor_id, product_id=d.product_id)
    raise RuntimeError(f"{NAME} not found — set controller to Switch mode and connect via USB")


def parse_report(report: bytes) -> ControllerState | None:
    """Return normalised controller state, or None if the report ID is not 0x30."""
    if report[0] != 0x30:
        return None

    lx = report[6] | ((report[7] & 0x0F) << 8)
    ly = (report[7] >> 4) | (report[8] << 4)

    x =  (lx - 2048) / 2048.0
    y =   (ly - 2048) / 2048.0    # 8BitDo: LY increases when pushed up (no inversion needed)

    return ControllerState(
        x=x,
        y=y,
        trigger=  bool(report[3] & 0x80),   # ZR  → forward
        bumper_l= bool(report[5] & 0x40),   # L   → spin left
        bumper_r= bool(report[3] & 0x40),   # R   → spin right
        quit=     bool(report[4] & 0x10),   # Home
        dock=     bool(report[4] & 0x02),   # Plus → return to dock
    )
