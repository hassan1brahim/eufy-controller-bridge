"""
find_device.py — Print all eufy devices on your account.

Logs in with your config.py credentials and calls the device list API.
Use this to find the DEVICE_ID and DEVICE_MODEL values to put in config.py.

Usage:
    python tools/find_device.py
"""

import sys
import json
import requests

sys.path.insert(0, ".")
import config
from eufy.protocol import OPENUDID


def main():
    print("Logging in...")
    login_resp = requests.post(
        "https://home-api.eufylife.com/v1/user/email/login",
        headers={
            "category":     "Home",
            "openudid":     OPENUDID,
            "Content-Type": "application/json",
            "clientType":   "1",
            "User-Agent":   "EufyHome-Android-3.1.3-753",
        },
        json={
            "email":         config.EMAIL,
            "password":      config.PASSWORD,
            "client_id":     "eufyhome-app",
            "client_secret": "GQCpr9dSp3uQpsOMgJ4xQ",
        },
        timeout=10,
    ).json()

    if "access_token" not in login_resp:
        print("Login failed:")
        print(json.dumps(login_resp, indent=2))
        sys.exit(1)

    token = login_resp["access_token"]
    print("Login OK. Fetching device list...\n")

    devices_resp = requests.get(
        "https://home-api.eufylife.com/v1/device/v2",
        headers={
            "token":      token,
            "category":   "Home",
            "openudid":   OPENUDID,
            "clientType": "1",
            "User-Agent": "EufyHome-Android-3.1.3-753",
        },
        timeout=10,
    ).json()

    items = devices_resp.get("devices", devices_resp.get("items", []))
    if not items:
        print("No devices found. Raw response:")
        print(json.dumps(devices_resp, indent=2))
        sys.exit(1)

    print(f"{'Name':<30} {'DEVICE_ID':<20} {'DEVICE_MODEL'}")
    print("-" * 65)
    for device in items:
        name  = device.get("device_name") or device.get("name", "?")
        did   = device.get("device_sn")   or device.get("id", "?")
        model = device.get("product_code") or device.get("model", "?")
        print(f"{name:<30} {did:<20} {model}")

    print("\nCopy DEVICE_ID and DEVICE_MODEL into config.py.")


if __name__ == "__main__":
    main()
