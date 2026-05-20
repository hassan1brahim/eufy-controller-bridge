# eufy/

Vacuum-side cloud layer. Handles authentication with the eufy REST API, command
encoding, and the MQTT session that talks to the vacuum.

| File | Role |
|---|---|
| `protocol.py` | DPS constants, protobuf encoding, direction map, app identity strings |
| `auth.py` | Three-step REST login → X.509 client certificate + MQTT endpoint |
| `client.py` | MQTT session lifecycle, RC mode, drive/dock/suction commands |

## How they connect

```
auth.py  ──uses──▶  protocol.py   (OPENUDID, APP_NAME for request headers)
client.py ──uses──▶  auth.py      (fetch_mqtt_credentials on startup)
client.py ──uses──▶  protocol.py  (DPS keys, START_RC/STOP_RC/GO_HOME encoding)
```

`main.py` only imports `EufyClient` from `client.py` - everything else is internal.

## Protocol notes

- eufy uses AWS IoT Core MQTT with mutual TLS, **not** the standard Tuya local protocol.
- Auth is three REST calls; the third returns a per-user X.509 certificate valid for `aiot-mqtt-us.anker.com:8883`.
- Commands are double-JSON envelopes. `DPS 152` (mode) uses a length-prefixed protobuf blob. `DPS 155` (direction) is a **plain integer** - discovered via `tools/sniff.py`.
- `msg_seq` must increment on every publish or the firmware silently deduplicates and drops the command.
