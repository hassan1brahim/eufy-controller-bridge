"""
eufy_client.py — MQTT session and drive command layer.

Handles connecting to the AWS IoT Core broker with mutual TLS and
publishing DPS commands to the vacuum.  Authentication and protocol
encoding are delegated to auth.py and protocol.py respectively.

Important MQTT invariant
------------------------
msg_seq in the envelope head must increment on every publish.  The
firmware deduplicates by sequence number and silently drops repeated
values — a common source of missing commands during development.
"""

import asyncio
import json
import os
import ssl
import tempfile
import time

from paho.mqtt import client as mqtt

import config
from eufy.auth import fetch_mqtt_credentials
from eufy.protocol import (
    OPENUDID, APP_NAME,
    DPS_MODE, DPS_DIRECTION, DPS_SPEED,
    DIRECTION, START_RC, STOP_RC, GO_HOME,
)


class EufyClient:
    """MQTT client that authenticates with eufy's cloud and drives the vacuum."""

    def __init__(self):
        print("Fetching MQTT credentials...")
        self._creds     = fetch_mqtt_credentials()
        self._user_id   = self._creds["user_id"]
        self._client_id = None
        self._mqtt      = None
        self._cert_path = None
        self._key_path  = None
        self._connected = None   # asyncio.Event — created in connect()
        self._loop      = None
        self._msg_seq   = 0

    def _write_cert_files(self):
        """Write the X.509 cert and private key to temporary files for paho."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as f:
            f.write(self._creds["certificate_pem"])
            self._cert_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".key") as f:
            f.write(self._creds["private_key"])
            self._key_path = f.name
        os.chmod(self._key_path, 0o600)

    def _publish(self, dps: dict):
        """Publish a DPS command to the device's /req topic.

        The outer envelope carries routing and sequencing metadata.  The inner
        payload (stringified JSON) carries the actual DPS command dictionary.
        msg_seq must increment per message or the device will silently drop it.
        cmd=65537 (0x10001) is the standard eufy device-command opcode.
        """
        if not self._mqtt or not self._mqtt.is_connected():
            return

        self._msg_seq += 1
        ts = int(time.time() * 1000)

        inner = json.dumps({
            "account_id": self._user_id,
            "data":       dps,
            "device_sn":  config.DEVICE_ID,
            "protocol":   2,
            "t":          ts,
        })
        outer = json.dumps({
            "head": {
                "client_id":  self._client_id,
                "cmd":        65537,
                "cmd_status": 2,
                "msg_seq":    self._msg_seq,
                "seed":       "",
                "sess_id":    self._client_id,
                "sign_code":  0,
                "timestamp":  ts,
                "version":    "1.0.0.1",
            },
            "payload": inner,
        })

        topic = f"cmd/eufy_home/{config.DEVICE_MODEL}/{config.DEVICE_ID}/req"
        self._mqtt.publish(topic, outer.encode())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self):
        """Authenticate, open the MQTT connection, and enter RC mode."""
        self._loop      = asyncio.get_running_loop()
        self._connected = asyncio.Event()

        # The AWS IoT policy enforces that client_id matches android-eufy_home-*.
        # Deviating from this pattern causes a "Not authorized" CONNACK rejection.
        self._client_id = (
            f"android-{APP_NAME}-eufy_android_{OPENUDID}_{self._user_id}"
            f"-{int(time.time() * 1000)}"
        )

        self._write_cert_files()

        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
            transport="tcp",
        )
        self._mqtt.username_pw_set(self._creds["thing_name"])
        self._mqtt.tls_set(
            certfile=self._cert_path,
            keyfile=self._key_path,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        self._mqtt.on_connect    = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect

        await self._loop.run_in_executor(
            None,
            lambda: self._mqtt.connect(self._creds["endpoint"], 8883, keepalive=60),
        )
        self._mqtt.loop_start()
        await asyncio.wait_for(self._connected.wait(), timeout=15.0)
        print(f"Connected to {self._creds['endpoint']}.")

        # Enter RC mode so the vacuum accepts direction commands.
        self._publish({DPS_MODE: START_RC})
        await asyncio.sleep(0.3)
        print("RC mode active.")

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[!] MQTT connection refused: {reason_code}")
        elif self._loop:
            self._loop.call_soon_threadsafe(self._connected.set)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if self._loop:
            self._loop.call_soon_threadsafe(self._connected.clear)

    async def close(self):
        """Stop the vacuum, exit RC mode, and disconnect cleanly."""
        self.stop()
        self._publish({DPS_MODE: STOP_RC})
        await asyncio.sleep(0.3)
        if self._mqtt:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
        for path in [self._cert_path, self._key_path]:
            if path and os.path.exists(path):
                os.unlink(path)

    # ── Drive commands ────────────────────────────────────────────────────────

    def drive(self, direction: str):
        """Send a direction command.  direction: "forward" | "stop" | "left" | "right"."""
        self._publish({DPS_DIRECTION: DIRECTION.get(direction, 0)})

    def stop(self):
        self.drive("stop")

    def set_suction(self, level: str):
        """Set fan/suction speed.  level: "Quiet" | "Standard" | "Turbo" | "Max" | "Boost"."""
        fan_map = {"Quiet": "0", "Standard": "1", "Turbo": "2", "Max": "3", "Boost": "4"}
        val = fan_map.get(level)
        if val:
            self._publish({DPS_SPEED: val})

    def return_home(self):
        """Command the vacuum to return to its dock.

        RC mode must be exited first — the device ignores GO_HOME while in
        REMOTE_CTRL state.  A brief sleep gives the firmware time to process
        the mode change before receiving the dock command.
        """
        self._publish({DPS_MODE: STOP_RC})
        time.sleep(0.3)
        self._publish({DPS_MODE: GO_HOME})
