"""fcm.py — minimal Firebase Cloud Messaging v1 sender, no google-auth/requests
dependency. Signs the service-account JWT with `cryptography` (already present
on this host) and does the OAuth2 token exchange + FCM send over stdlib
urllib. Kept as its own module so runner.py's core stays simple.

Config via environment (see ~/.config/eva-task-runner/eva-task-runner.env):
  FCM_SERVICE_ACCOUNT_FILE   path to the Firebase service-account JSON
                             (Project settings -> Service accounts -> Generate
                             new private key). Not checked into git.
"""
import base64
import json
import os
import time
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_SA_FILE = os.environ.get("FCM_SERVICE_ACCOUNT_FILE", "")

_sa = None  # lazily-loaded service account dict
_token_cache = {"access_token": None, "expires_at": 0.0}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _load_service_account():
    global _sa
    if _sa is None:
        with open(_SA_FILE) as f:
            _sa = json.load(f)
    return _sa


def _signed_jwt(sa: dict) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": sa["client_email"],
        "scope": _SCOPE,
        "aud": sa.get("token_uri", "https://oauth2.googleapis.com/token"),
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (_b64url(json.dumps(header).encode()) + "." +
                      _b64url(json.dumps(claims).encode())).encode()
    private_key = serialization.load_pem_private_key(
        sa["private_key"].encode(), password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return signing_input.decode() + "." + _b64url(signature)


def _access_token() -> str:
    """Cached OAuth2 access token, refreshed a couple minutes before expiry."""
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 120:
        return _token_cache["access_token"]
    sa = _load_service_account()
    assertion = _signed_jwt(sa)
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    req = urllib.request.Request(
        sa.get("token_uri", "https://oauth2.googleapis.com/token"),
        data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["access_token"]


def send(token: str, title: str, body: str):
    """Send one FCM push to a device token. Raises on failure — callers should
    treat this like any other best-effort push target (log and move on)."""
    sa = _load_service_account()
    access_token = _access_token()
    payload = json.dumps({
        "message": {
            "token": token,
            # Data-only, not "notification" — Android would otherwise
            # auto-display a "notification" payload itself in the
            # background/killed state *and* our own handler would show it
            # again in the foreground, producing duplicates. Data-only means
            # our code (push_service.dart) is the only thing that ever shows
            # a notification, in every app state, so there's one path to get
            # right instead of two disagreeing ones.
            "data": {"title": title, "body": body[:400]},
            # Android needs this for delivery priority while the phone is
            # dozing/backgrounded — data-only messages default to normal
            # priority otherwise, which can be delayed significantly.
            "android": {"priority": "high"},
        }
    }).encode()
    req = urllib.request.Request(
        f"https://fcm.googleapis.com/v1/projects/{sa['project_id']}/messages:send",
        data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + access_token})
    with urllib.request.urlopen(req, timeout=15):
        pass


def available() -> bool:
    return bool(_SA_FILE) and os.path.isfile(_SA_FILE)
