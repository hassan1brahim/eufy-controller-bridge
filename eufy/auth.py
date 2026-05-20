"""
auth.py — Three-step eufy cloud login → AWS IoT MQTT credentials.

eufy robot vacuums do NOT use the standard Tuya local protocol.  They
connect to a private AWS IoT Core MQTT broker using mutual TLS.  There
is no "local key" — all communication goes through the cloud.

Authentication is a three-step REST flow:
  1. email + password  →  access_token
  2. access_token      →  user_center_id + user_center_token
  3. user tokens       →  per-user X.509 client certificate + private key

The X.509 certificate authenticates the MQTT session.  The AWS IoT policy
attached to the certificate enforces which topics the client may publish
to and subscribe from.
"""

import hashlib

import requests

import config
from eufy.protocol import OPENUDID, APP_NAME


def fetch_mqtt_credentials() -> dict:
    """Perform the three-step eufy cloud login and return MQTT credentials.

    Returns a dict with:
        user_id         — hashed user identifier (used in topics + envelopes)
        thing_name      — AWS IoT Thing name (used as MQTT username)
        certificate_pem — X.509 client certificate (PEM)
        private_key     — RSA private key for the certificate (PEM)
        endpoint        — MQTT broker hostname
    """
    # Step 1: email/password → short-lived access_token
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
    access_token = login_resp["access_token"]

    # Step 2: access_token → user_center_id + user_center_token
    # user_center_id is MD5-hashed to produce the gtoken required in step 3.
    user_resp = requests.get(
        "https://api.eufylife.com/v1/user/user_center_info",
        headers={
            "user-agent": "EufyHome-Android-3.1.3-753",
            "category":   "Home",
            "token":      access_token,
            "openudid":   OPENUDID,
            "clienttype": "2",
        },
        timeout=10,
    ).json()
    user_id = user_resp["user_center_id"]
    gtoken  = hashlib.md5(user_id.encode()).hexdigest()

    # Step 3: user tokens → per-user X.509 certificate + MQTT endpoint
    mqtt_resp = requests.post(
        "https://aiot-clean-api-pr.eufylife.com/app/devicemanage/get_user_mqtt_info",
        headers={
            "content-type": "application/json",
            "user-agent":   "EufyHome-Android-3.1.3-753",
            "openudid":     OPENUDID,
            "os-version":   "Android",
            "model-type":   "PHONE",
            "app-name":     APP_NAME,
            "x-auth-token": user_resp["user_center_token"],
            "gtoken":       gtoken,
        },
        timeout=10,
    ).json()["data"]

    return {
        "user_id":         user_id,
        "thing_name":      mqtt_resp["thing_name"],
        "certificate_pem": mqtt_resp["certificate_pem"],
        "private_key":     mqtt_resp["private_key"],
        "endpoint":        mqtt_resp["endpoint_addr"],
    }
