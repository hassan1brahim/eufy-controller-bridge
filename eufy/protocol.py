"""
protocol.py — DPS constants, command encoding, and direction mapping.

All numeric DPS keys and their valid values were reverse-engineered from
the Android app's control.proto definitions and confirmed via tools/sniff.py.

Key discovery: DPS 155 (direction) is a plain integer, not a protobuf blob.
Sending a protobuf for DPS 155 is silently ignored by the firmware — this
was the main bug that blocked movement and was found by comparing sniff.py
output against our encoded payloads.
"""

import base64

# Android app identity — used in auth headers and MQTT client_id construction.
# These values are validated by eufy's backend; changing them may break login.
OPENUDID = "sdk_gphone64_arm64"
APP_NAME  = "eufy_home"

# ── DPS (Data Point State) key numbers ───────────────────────────────────────
DPS_MODE      = "152"   # ModeCtrlRequest — controls operating mode
DPS_DIRECTION = "155"   # RemoteCtrl      — direction command (plain int)
DPS_SPEED     = "158"   # Fan speed string: "0"=Quiet … "4"=Boost_IQ

# ── ModeCtrlRequest.Method enum values (field 1 of the protobuf) ─────────────
METHOD_START_RC = 5    # enter remote-control mode
METHOD_STOP_RC  = 16   # exit remote-control mode
METHOD_GOHOME   = 6    # return to dock

# ── RemoteCtrl direction values (plain integers sent as DPS 155) ─────────────
# These are plain integers — NOT a protobuf blob.  Confirmed by sniffing the
# official eufy app.  The firmware also supports BACK (2) but the controller
# binding does not use it.
DIRECTION = {
    "forward": 1,
    "stop":    0,
    "left":    3,
    "right":   4,
    "back":    2,
}


def encode_protobuf(field1_value: int) -> str:
    """Encode a single-field protobuf message for use in DPS 152 (mode control).

    Wire format: [varint_length][0x08][value]
      0x08 = field number 1, wire type 0 (varint).
      The leading length byte is eufy's own framing — not standard protobuf.

    Only DPS 152 uses this encoding.  DPS 155 uses plain integers instead.
    """
    body = bytes([0x08, field1_value])
    return base64.b64encode(bytes([len(body)]) + body).decode()


# Pre-encode the mode constants so they are not recomputed on every publish.
START_RC = encode_protobuf(METHOD_START_RC)
STOP_RC  = encode_protobuf(METHOD_STOP_RC)
GO_HOME  = encode_protobuf(METHOD_GOHOME)
