# ─────────────────────────────────────────────────────────────────────────────
# config.example.py  —  Copy this file to config.py and fill in your values.
#                        config.py is gitignored; never commit real credentials.
# ─────────────────────────────────────────────────────────────────────────────

# ── eufy account ─────────────────────────────────────────────────────────────
# The email and password you use to log in to the eufy Home app.
EMAIL    = "your@email.com"
PASSWORD = "yourpassword"

# ── Device identifiers ───────────────────────────────────────────────────────
# DEVICE_ID   : Serial number printed on the underside of your vacuum.
#               Also visible in the eufy app: Device → Settings → Device Info.
#               Format: AOTxxxxxxxxxxxx  (e.g. "AOT2802F25213500")
#
# DEVICE_MODEL: The firmware model string.  For the eufy C20 Omni this is
#               "T2280".  Check the eufy app if unsure — it shows the model
#               code next to the device name.
DEVICE_ID    = "AOT..."
DEVICE_MODEL = "T2280"

# ── Direction command tokens (do not change) ─────────────────────────────────
CMD_FORWARD = "forward"
CMD_LEFT    = "left"
CMD_RIGHT   = "right"
CMD_STOP    = "stop"

# ── Controller tuning ────────────────────────────────────────────────────────
# DEADZONE: Fraction of full-stick travel ignored at centre (0.0–1.0).
#           Increase if the vacuum drifts when the stick is released.
DEADZONE = 0.25
