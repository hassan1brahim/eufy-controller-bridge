"""
Generic controller → eufy drive loop.

Auto-detects whichever supported controller is plugged in (tries each adapter
in priority order).  The control loop operates entirely on ControllerState
so adding a new controller only requires a new adapter module.

Direction model (from control.proto)
-------------------------------------
The firmware is stateful — it moves continuously on FORWARD/LEFT/RIGHT and
stops on BRAKE (0).  One command is sent per 100 ms tick; the dominant stick
axis determines direction.  BRAKE fires immediately on stick release.
"""

import asyncio
import math

import config
from adapters import open_any
from eufy.client import EufyClient

_READ_INTERVAL = 0.01   # 10 ms  — HID poll cadence (reduces release-to-BRAKE lag)
_SEND_INTERVAL = 0.10   # 100 ms — MQTT heartbeat cadence for held directions


def _deadzone(x: float, y: float, dz: float) -> tuple[float, float]:
    mag = math.hypot(x, y)
    if mag < dz:
        return 0.0, 0.0
    scale = (mag - dz) / (1.0 - dz)
    return (x / mag) * scale, (y / mag) * scale


def _pick_direction(x: float, y: float) -> str:
    """Dominant axis wins; centre (after deadzone) → STOP."""
    if abs(x) > abs(y):
        return config.CMD_LEFT if x < 0 else config.CMD_RIGHT
    elif y > 0:
        return config.CMD_FORWARD
    else:
        return config.CMD_STOP


async def run_controller(eufy: EufyClient):
    loop = asyncio.get_running_loop()
    adapter, dev = await loop.run_in_executor(None, open_any)

    # Flush stale reports so first read reflects actual stick position
    for _ in range(10):
        dev.read(adapter.REPORT_SIZE, timeout_ms=0)
    eufy.stop()

    print(f"{adapter.NAME} connected. Left stick = drive | trigger = fwd | bumpers = spin | dock button = dock | quit button = exit\n")

    last      = None
    last_cmd  = None
    last_send = 0.0

    try:
        while True:
            try:
                raw = dev.read(adapter.REPORT_SIZE, timeout_ms=0)
            except OSError:
                print(f"{adapter.NAME} disconnected.")
                break

            if raw:
                state = adapter.parse_report(raw)
                if state is not None:
                    last = state

            if not last:
                await asyncio.sleep(_READ_INTERVAL)
                continue

            s = last

            if s.quit:
                print("Quit pressed — stopping.")
                break

            if s.dock:
                eufy.stop()
                await asyncio.sleep(0.1)
                eufy.return_home()
                print("→ Returning to dock...")
                await asyncio.sleep(2.0)
                last = last_cmd = None
                last_send = 0.0
                continue

            # Resolve desired direction (buttons take priority over stick)
            if s.trigger:
                cmd = config.CMD_FORWARD
            elif s.bumper_l:
                cmd = config.CMD_LEFT
            elif s.bumper_r:
                cmd = config.CMD_RIGHT
            else:
                x, y = _deadzone(s.x, s.y, config.DEADZONE)
                cmd = _pick_direction(x, y)

            now = loop.time()

            if cmd == config.CMD_STOP:
                if last_cmd != config.CMD_STOP:
                    eufy.drive(config.CMD_STOP)
                    last_cmd  = config.CMD_STOP
                    last_send = now
            elif cmd != last_cmd or (now - last_send) >= _SEND_INTERVAL:
                eufy.drive(cmd)
                last_cmd  = cmd
                last_send = now

            await asyncio.sleep(_READ_INTERVAL)

    finally:
        eufy.stop()
        dev.close()
        print("Controller closed.")
