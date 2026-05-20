"""
main.py — Entry point for eufy-controller-bridge.

Connects to the eufy cloud, enters RC mode, and hands off to the controller
loop.  On exit (quit button, Ctrl-C, or any error) the vacuum is stopped and
the MQTT session is closed cleanly.
"""

import asyncio
import sys

import config
from eufy.client import EufyClient
from controller import run_controller


def _check_config() -> None:
    """Abort early if required config values are missing."""
    required = ("EMAIL", "PASSWORD", "DEVICE_ID", "DEVICE_MODEL")

    # Checks if anything is missing and if it is, then exists early
    missing = []
    for k in required:
        value = getattr(config, k, None)
        if not value:
            missing.append(k)

    if missing:
        print(f"[!] config.py is missing values for: {', '.join(missing)}")
        print("    Copy config.example.py → config.py and fill in your details.")
        sys.exit(1)


async def main() -> None:
    _check_config()

    eufy = EufyClient()
    print("Connecting to eufy MQTT broker...")
    await eufy.connect()

    try:
        await run_controller(eufy)
    finally:
        print("Shutting down...")
        await eufy.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
