"""
read_controller.py — Print normalised controller state live.  No vacuum needed.

Use this to verify that hidapi can see your controller and that the adapter is
reading the right values.  Useful when porting to a new OS or debugging
unexpected stick/button behaviour.

Tries each supported controller in the same priority order as controller.py.
Prints the normalised ControllerState so you can confirm the adapter is
mapping bytes correctly.

Usage
-----
    python tools/read_controller.py

Connect your controller before running.  Press Ctrl-C to quit.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters import open_any


def main():
    try:
        adapter, dev = open_any()
    except RuntimeError as e:
        raise SystemExit(e)

    print(f"{adapter.NAME} connected.  Move the stick and press buttons.  Ctrl-C to quit.\n")

    try:
        last = None
        while True:
            raw = dev.read(adapter.REPORT_SIZE, timeout_ms=0)
            if raw:
                state = adapter.parse_report(raw)
                if state is not None:
                    last = state
            if last:
                s = last
                print(
                    f"x={s.x:+.2f}  y={s.y:+.2f}  "
                    f"trig={int(s.trigger)}  "
                    f"L={int(s.bumper_l)}  R={int(s.bumper_r)}  "
                    f"quit={int(s.quit)}  dock={int(s.dock)}    ",
                    end="\r",
                )
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
