def create_timer(minutes: int, reminder: str) -> str:
    """Set a one-off reminder/alarm — the way you'd set one on a phone. Fires
    later on its own: Stephan gets a push notification, and you get a quiet
    background nudge in this conversation so you can bring it up naturally
    next time you talk. Use this either when he asks you to remind him of
    something, or on your own if it's clearly useful (e.g. he mentions
    something with a natural follow-up time). One-shot only — no recurring
    reminders yet.

    Args:
        minutes: how many minutes from now it should fire (whole minutes).
        reminder: the reminder text itself, e.g. "hang up the laundry" —
            this is what shows up in the push notification and the nudge.
    """
    import json
    import os
    import urllib.request

    base = (os.environ.get("EVA_RUNNER_URL") or "http://localhost:8286").rstrip("/")
    body = json.dumps({"minutes": minutes, "reminder": reminder}).encode()
    req = urllib.request.Request(base + "/timers", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 — surface as a normal reply, not a crash
        return "(couldn't set that reminder: %s)" % e
    return json.dumps(data)
