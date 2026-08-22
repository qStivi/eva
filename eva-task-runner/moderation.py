"""Pre-approval moderation check for delegated harness tasks — see the
"Safety layer" section of docs/2026-08-22-delegate-to-claude-spec.md. Runs
BEFORE a job leaves pending_approval, so a flagged task shows up on the
approval prompt with a visible warning rather than silently gating anything
— your judgment is still the actual gate, this just surfaces something
worth a second look.

Uses Mistral Moderation 2 (`POST /v1/moderations`, free, a real
classification endpoint — not a prompted chat call) rather than Shieldstral,
since it's simpler (fixed category list, no prompt-engineering the check
itself) and needs no extra setup. See
mistral-shieldstral-moderation-model memory for both options; worth
revisiting if Moderation 2's fixed categories prove too coarse in practice.
"""
import json
import urllib.request

from executors import harness  # for _mistral_key() — same Letta-provider-store fetch, not duplicated here

MODERATION_URL = "https://api.mistral.ai/v1/moderations"
MODERATION_MODEL = "mistral-moderation-2603"
# Categories worth surfacing on an approval prompt for a *task Eva wants to
# run on the host*. Deliberately narrower than the full category list —
# "financial"/"health"/"law" advice categories don't apply to a coding/file
# task the way "dangerous"/"criminal" do.
RELEVANT_CATEGORIES = ("dangerous", "criminal", "violence_and_threats", "jailbreaking")


def check(task_text: str) -> list:
    """Returns a list of flagged category names (empty if clean, or on any
    failure — a moderation-check outage must never block approval from
    happening, only skip the extra warning)."""
    try:
        body = json.dumps({"model": MODERATION_MODEL, "input": [task_text]}).encode()
        req = urllib.request.Request(
            MODERATION_URL, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + harness._mistral_key()})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        categories = data["results"][0]["categories"]
        return [c for c in RELEVANT_CATEGORIES if categories.get(c)]
    except Exception:  # noqa: BLE001 — best-effort, see docstring
        return []
