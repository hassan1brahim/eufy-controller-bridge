# tools/

Standalone debug scripts used during development to reverse-engineer the protocol
and verify hardware behaviour. Run all of these from the repo root.

| Script | Needs controller | Needs vacuum | What it does |
|---|---|---|---|
| `find_device.py` | No | No | Print all devices on your account with DEVICE_ID and DEVICE_MODEL |
| `read_controller.py` | Yes | No | Print normalised controller state live |
| `sniff.py` | No | Yes (via app) | Monitor live MQTT traffic |
| `test_drive.py` | No | Yes | Pulse FORWARD commands for 3 s |

## Usage

```bash
# From the repo root:
python tools/find_device.py       # credentials in config.py required
python tools/read_controller.py   # connect controller first
python tools/sniff.py             # then drive with the eufy app
python tools/test_drive.py        # vacuum must be off dock and powered on
```

## find_device.py

Logs in with your `config.py` credentials and prints every device on your account:

```
Name                           DEVICE_ID            DEVICE_MODEL
-----------------------------------------------------------------
RoboVac C20 Omni               AOTxxxxxxxxxxxx      T2280
```

Use this during initial setup to find the `DEVICE_ID` and `DEVICE_MODEL` values
for `config.py` without having to flip the vacuum over or dig through the app.

## read_controller.py

Prints the normalised `ControllerState` (x, y, trigger, bumpers, quit, dock) in
real time. No vacuum connection needed.

Use this when:
- Verifying a new adapter reads the right bytes
- Debugging unexpected stick or button behaviour
- Porting to a new OS (byte offsets may differ)

## sniff.py

Connects to the same MQTT broker as the eufy app and subscribes to both `/req`
and `/res` topics. While it runs, drive the vacuum with the official app - every
command and every firmware response is printed with the DPS key, value, and raw
hex bytes decoded from any base64 payload.

This is how we discovered that **DPS 155 (direction) is a plain integer**, not a
protobuf blob, which was the core bug blocking all movement.

## test_drive.py

Connects to MQTT and pulses FORWARD commands for 3 seconds without needing a
controller. Use this to confirm credentials are correct and the vacuum moves
before debugging the controller side.

Unlike `EufyClient.connect()`, this script manually controls the RC mode entry
sequence so each step can be observed in isolation - useful when movement is
broken and you need to identify exactly which command is failing.
