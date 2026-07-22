#!/usr/bin/env python3
"""Intent-based toolset pre-loading for Eva.

Letta only surfaces newly-attached tools on the NEXT turn, so an agent can't load a
toolset and use it in the same breath. This closes that gap from the outside: BEFORE a
user message reaches the agent, detect which tool GROUPS the message implies (keyword
match from toolsets.json) and set the agent's attached tools so the matched groups are
present and the rest are put away — leaving the everyday 'core' untouched. The tools are
then there from the very start of the turn.

Stdlib only (matches eva-web). Usable as a module or CLI:
    from toolset_router import preload_for
    python3 toolset_router.py --agent <id> [--host URL] "message text"   # prints matched groups
Router failure must never block a chat — callers should treat it as best-effort.
"""
import json
import os
import re
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLSETS = os.path.normpath(os.path.join(_HERE, "..", "toolsets.json"))


def load_toolsets(path=_TOOLSETS):
    with open(path) as f:
        return json.load(f)


def match_groups(message, ts):
    """Return the list of group names whose keywords appear in the message."""
    message = message or ""
    hits = []
    for group, words in ts.get("keywords", {}).items():
        parts = [re.escape(w.strip()) for w in words if w.strip()]
        if not parts:
            continue
        if re.search(r"\b(" + "|".join(parts) + r")\b", message, re.I):
            hits.append(group)
    return hits


def _api(host, method, path):
    req = urllib.request.Request(host.rstrip("/") + path, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as r:
        body = r.read().decode()
    return json.loads(body) if body else None


def preload_for(message, agent_id, host="http://localhost:8283", ts=None):
    """Attach the groups the message implies, detach the other managed groups.

    Never touches non-managed (core) tools. Returns the matched group names.
    """
    ts = ts or load_toolsets()
    groups = ts["groups"]
    managed = sorted({t for tools in groups.values() for t in tools})
    hits = match_groups(message, ts)
    want = set()
    for g in hits:
        want.update(groups.get(g, []))

    id_by_name = {t["name"]: t["id"]
                  for t in (_api(host, "GET", "/v1/tools/?limit=300") or [])
                  if t.get("name") and t.get("id")}
    attached = {t["name"] for t in (_api(host, "GET",
                "/v1/agents/%s/tools?limit=300" % agent_id) or [])}

    for tn in managed:
        if tn in attached and tn not in want and tn in id_by_name:
            _api(host, "PATCH", "/v1/agents/%s/tools/detach/%s" % (agent_id, id_by_name[tn]))
    for tn in sorted(want):
        if tn not in attached and tn in id_by_name:
            _api(host, "PATCH", "/v1/agents/%s/tools/attach/%s" % (agent_id, id_by_name[tn]))
    return hits


def main(argv):
    import argparse
    p = argparse.ArgumentParser(description="Pre-attach Eva's toolsets for a message.")
    p.add_argument("--agent", default=os.environ.get("EVA_AGENT_ID", ""))
    p.add_argument("--host", default=os.environ.get("LETTA_HOST", "http://localhost:8283"))
    p.add_argument("message", nargs="+")
    a = p.parse_args(argv)
    if not a.agent:
        return 0  # nothing we can do without an agent; don't block the chat
    try:
        print(" ".join(preload_for(" ".join(a.message), a.agent, a.host)))
    except Exception as e:  # noqa: BLE001 — best-effort; never block a chat
        sys.stderr.write("toolset-router: %s\n" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
