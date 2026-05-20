"""
test_drive.py — Verify vacuum movement without a controller.

Connects to the eufy MQTT broker, enters RC mode, pulses FORWARD commands
for 3 seconds, then exits RC mode.  Use this to confirm that the MQTT
connection and command encoding are working before wiring up a controller.

Steps
-----
1. Take the vacuum off its dock.
2. Press the power button on the vacuum (it beeps and connects to WiFi).
3. Run this script immediately:

       python tools/test_drive.py

The vacuum should move forward for ~3 seconds, then stop.

Why a separate _connect_raw() instead of EufyClient.connect()?
--------------------------------------------------------------
EufyClient.connect() enters RC mode automatically as part of startup.
This script bypasses that so we can control the exact command sequence
and observe the firmware's response at each step — useful for debugging
when movement is broken and you need to isolate which step is failing.

Known issues discovered during development
------------------------------------------
DPS 155 encoding bug:
  The original implementation sent DPS 155 as a base64-encoded protobuf
  blob, matching DPS 152.  The firmware accepted it silently but did not
  move — no error, just nothing.  sniff.py revealed the official app sends
  DPS 155 as a plain integer ({"155": 1}).  Fixing this unblocked movement.

RC mode timing:
  The firmware needs ~300 ms after receiving START_RC before it will act
  on direction commands.  Sending a drive command immediately after
  START_RC is silently ignored.
"""

import asyncio
import base64
import json
import os
import ssl
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt_lib

import config
from eufy.client import EufyClient
from eufy.protocol import DPS_MODE, DPS_DIRECTION, DIRECTION, START_RC, STOP_RC


async def _connect_raw(eufy: EufyClient) -> None:
    """Open MQTT connection without auto-entering RC mode."""
    eufy._loop      = asyncio.get_running_loop()
    eufy._connected = asyncio.Event()
    eufy._client_id = (
        f"android-eufy_home-eufy_android_{eufy._user_id}"
        f"-{int(time.time() * 1000)}"
    )
    eufy._write_cert_files()

    eufy._mqtt = mqtt_lib.Client(
        callback_api_version=mqtt_lib.CallbackAPIVersion.VERSION2,
        client_id=eufy._client_id,
        transport="tcp",
    )
    eufy._mqtt.username_pw_set(eufy._creds["thing_name"])
    eufy._mqtt.tls_set(
        certfile=eufy._cert_path,
        keyfile=eufy._key_path,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    eufy._mqtt.on_connect    = eufy._on_connect
    eufy._mqtt.on_disconnect = eufy._on_disconnect

    await eufy._loop.run_in_executor(
        None,
        lambda: eufy._mqtt.connect(eufy._creds["endpoint"], 8883, keepalive=60),
    )
    eufy._mqtt.loop_start()
    await asyncio.wait_for(eufy._connected.wait(), timeout=15.0)


async def main() -> None:
    print("Fetching credentials...")
    eufy = EufyClient()

    print("Connecting to MQTT (no auto RC-enter)...")
    await _connect_raw(eufy)

    # Subscribe to /res so we can see the firmware's state echoes.
    res_topic = f"cmd/eufy_home/{config.DEVICE_MODEL}/{config.DEVICE_ID}/res"

    def on_message(client, userdata, msg):
        try:
            outer   = json.loads(msg.payload)
            payload = outer.get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload)
            for k, v in payload.get("data", {}).items():
                extra = ""
                if isinstance(v, str):
                    try:
                        extra = f"  ({base64.b64decode(v).hex()})"
                    except Exception:
                        pass
                print(f"  << DPS {k} = {v}{extra}")
        except Exception:
            pass

    eufy._mqtt.on_message = on_message
    eufy._mqtt.subscribe(res_topic)
    print("Connected.  Watching /res for firmware responses.\n")

    def send(dps: dict, label: str):
        print(f">>> {label}")
        eufy._publish(dps)

    # Enter RC mode and wait for the firmware to be ready.
    send({DPS_MODE: START_RC}, "START_RC (method=5)")
    await asyncio.sleep(1.0)

    # Pulse FORWARD at 100 ms intervals for 3 seconds.
    print("Pulsing FORWARD at 100 ms intervals for 3 s...")
    t_end = time.time() + 3.0
    count = 0
    while time.time() < t_end:
        eufy._publish({DPS_DIRECTION: DIRECTION["forward"]})
        count += 1
        await asyncio.sleep(0.1)
    print(f"  Sent {count} FORWARD pulses.")

    await asyncio.sleep(0.5)

    # Exit RC mode.
    send({DPS_MODE: STOP_RC}, "STOP_RC (method=16)")
    await asyncio.sleep(0.5)

    eufy._mqtt.loop_stop()
    eufy._mqtt.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
