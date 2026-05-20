# adapters/

Controller adapter layer. Each file is a self-contained adapter for one controller family.

| File | Controller | Connection |
|---|---|---|
| `ps5.py` | Sony DualSense (PS5) | USB-C |
| `eightbitdo.py` | 8BitDo Ultimate 2 | USB (Switch mode) |

`__init__.py` holds the adapter registry (`_ADAPTERS`) and the shared `open_any()` function -
the single place to edit when adding a controller.

## Adding a new controller

1. Create a new file in this folder (e.g. `xbox.py`).

2. Implement the adapter interface:

```python
import hidapi
from adapters.base import ControllerState

VID         = 0x...    # USB vendor ID
PID         = 0x...    # USB product ID
REPORT_SIZE = 64       # HID report size in bytes
NAME        = "Xbox Controller"


def open_controller() -> hidapi.Device:
    for d in hidapi.enumerate(VID, 0):
        if d.product_id == PID:
            return hidapi.Device(vendor_id=d.vendor_id, product_id=d.product_id)
    raise RuntimeError(f"{NAME} not found")


def parse_report(report: bytes) -> ControllerState | None:
    # Return None to skip irrelevant report IDs
    return ControllerState(
        x=..., y=...,
        trigger=...,
        bumper_l=..., bumper_r=...,
        quit=..., dock=...,
    )
```

3. Add your adapter to `_ADAPTERS` in `__init__.py`:

```python
from adapters import ps5, eightbitdo, xbox   # add import

_ADAPTERS = [ps5, eightbitdo, xbox]          # add to list
```

4. Run `python tools/read_controller.py` to verify the state looks right.

## ControllerState field reference

| Field | Type | Meaning |
|---|---|---|
| `x` | float | Left stick X - `-1.0` (full left) … `+1.0` (full right) |
| `y` | float | Left stick Y - `-1.0` (full down) … `+1.0` (full up) |
| `trigger` | bool | Primary forward trigger (R2, ZR, RT) |
| `bumper_l` | bool | Left bumper → spin vacuum left |
| `bumper_r` | bool | Right bumper → spin vacuum right |
| `quit` | bool | Exit session (PS, Home, Guide) |
| `dock` | bool | Return vacuum to dock (Touchpad, Plus, Back) |

## Finding HID byte offsets

Use `python tools/read_controller.py` with a temporary print of raw bytes to map
your controller. The existing adapters include detailed offset comments as a reference.

On macOS, some controllers prepend a Report ID byte at offset 0, shifting all
fields by +1. Always verify on your target OS.
