def use_toolset(name: str) -> str:
    """Load a set of tools you need for a task, then let them go when you're done.

    You keep a small everyday set of tools always at hand (memory, web search, the
    shared list). Anything else lives in a named set you pull in only when you need
    it — this keeps you fast and sharp instead of drowning in options. Call this
    BEFORE acting in an area you don't currently have the tools for, then continue
    and use them. Loading one set puts away the others; pass 'none' to go back to
    just your everyday tools.

    Args:
        name: which set to load — 'home', 'media', 'house_extras', or 'none'.
    """
    import os
    import json
    import urllib.request

    # Injected from toolsets.json by register-toolsets.sh (single source of truth).
    GROUPS = {}  # __INJECT_GROUPS__

    managed = sorted({t for tools in GROUPS.values() for t in tools})
    base = (os.environ.get("LETTA_API_BASE") or "http://localhost:8283").rstrip("/")
    aid = os.environ.get("LETTA_AGENT_ID", "")
    if not aid:
        return "(couldn't tell which agent I am — LETTA_AGENT_ID missing)"

    want_name = (name or "none").strip().lower()
    if want_name != "none" and want_name not in GROUPS:
        return "(no set called %r — I have: %s)" % (want_name, ", ".join(GROUPS))
    want = set(GROUPS.get(want_name, []))

    # Resolve tool name -> id across the whole registry, and see what's attached now.
    all_tools = json.loads(urllib.request.urlopen(
        base + "/v1/tools/?limit=300", timeout=12).read().decode() or "[]")
    id_by_name = {t["name"]: t["id"] for t in all_tools if t.get("name") and t.get("id")}
    ag_tools = json.loads(urllib.request.urlopen(
        base + "/v1/agents/" + aid + "/tools?limit=300", timeout=12).read().decode() or "[]")
    attached = {t["name"] for t in ag_tools}

    added, removed = [], []
    # Put away managed tools we don't want right now (never touches the everyday core).
    for tn in managed:
        if tn in attached and tn not in want and tn in id_by_name:
            urllib.request.urlopen(urllib.request.Request(
                base + "/v1/agents/" + aid + "/tools/detach/" + id_by_name[tn],
                method="PATCH"), timeout=12).read()
            removed.append(tn)
    # Pull in the requested set.
    for tn in sorted(want):
        if tn not in attached and tn in id_by_name:
            urllib.request.urlopen(urllib.request.Request(
                base + "/v1/agents/" + aid + "/tools/attach/" + id_by_name[tn],
                method="PATCH"), timeout=12).read()
            added.append(tn)

    return json.dumps({"loaded": want_name, "added": added, "put_away": removed})
