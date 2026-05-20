"""
sniff.py — Live MQTT traffic monitor.

Run this script, then use the official eufy app to drive the vacuum.
Every command the app sends (and every response the vacuum echoes back)
is printed to stdout with the DPS key, value, and raw hex bytes decoded
from any base64 payload.

This was the primary reverse-engineering tool for this project.  It is
how we discovered that:

  1. DPS 155 (direction) is a plain integer — not a protobuf blob.
     The app sends {"155": 1} for FORWARD, not a base64 string.

  2. DPS 152 (mode control) uses a length-prefixed single-field protobuf,
     base64-encoded.  Wire format: [varint_len][0x08][value].

Run alongside the app whenever you want to inspect what a new button or
feature sends.  Also useful for confirming that your own commands are
reaching the firmware by watching the /res echo.

Usage
-----
    python tools/sniff.py

Then drive the vacuum with the eufy app.  Press Ctrl-C to stop.
"""

import asyncio
import base64
import json
import os
import ssl
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paho.mqtt.client as mqtt_lib

import config
from eufy.auth import fetch_mqtt_credentials
from eufy.protocol import OPENUDID, APP_NAME


async def main() -> None:
    print("Fetching credentials...")
    creds = fetch_mqtt_credentials()

    # The AWS IoT policy requires client_id to match android-eufy_home-*.
    # Using a timestamp suffix prevents collisions if the app is also connected.
    client_id = (
        f"android-{APP_NAME}-eufy_android_{OPENUDID}"
        f"_{creds['user_id']}-{int(time.time() * 1000)}"
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as f:
        f.write(creds["certificate_pem"])
        cert_path = f.name
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".key") as f:
        f.write(creds["private_key"])
        key_path = f.name
    os.chmod(key_path, 0o600)

    connected = asyncio.Event()
    loop      = asyncio.get_running_loop()

    mqtt = mqtt_lib.Client(
        callback_api_version=mqtt_lib.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        transport="tcp",
    )
    mqtt.username_pw_set(creds["thing_name"])
    mqtt.tls_set(
        certfile=cert_path,
        keyfile=key_path,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )

    def on_connect(client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[!] MQTT connect failed: {reason_code}")
        else:
            loop.call_soon_threadsafe(connected.set)

    def on_message(client, userdata, msg):
        """Decode and pretty-print an MQTT message from the req or res topic."""
        try:
            outer   = json.loads(msg.payload)
            tag     = "REQ" if msg.topic.endswith("/req") else "RES"
            head    = outer.get("head", {})
            payload = outer.get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload)
            data = payload.get("data", {})
            if data:
                print(f"\n[{tag}] cmd={head.get('cmd')}  seq={head.get('msg_seq')}")
                for k, v in data.items():
                    extra = ""
                    if isinstance(v, str):
                        try:
                            extra = f"  raw_hex={base64.b64decode(v).hex()}"
                        except Exception:
                            pass
                    print(f"  DPS {k} = {v!r}{extra}")
        except Exception as e:
            print(f"[parse error] {e}: {msg.payload[:200]}")

    mqtt.on_connect = on_connect
    mqtt.on_message = on_message

    await loop.run_in_executor(None, lambda: mqtt.connect(creds["endpoint"], 8883, 60))
    mqtt.loop_start()
    await asyncio.wait_for(connected.wait(), timeout=15.0)

    req_topic = f"cmd/eufy_home/{config.DEVICE_MODEL}/{config.DEVICE_ID}/req"
    res_topic = f"cmd/eufy_home/{config.DEVICE_MODEL}/{config.DEVICE_ID}/res"
    mqtt.subscribe(req_topic)
    mqtt.subscribe(res_topic)

    print(f"Subscribed to /req and /res topics for {config.DEVICE_ID}.")
    print("Drive the vacuum with the eufy app now.  Press Ctrl-C to stop.\n")

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        mqtt.loop_stop()
        mqtt.disconnect()
        os.unlink(cert_path)
        os.unlink(key_path)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDone.")
