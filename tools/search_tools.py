def search_tools(query: str) -> str:
    """Search for a tool you don't currently have — the house, media, house
    extras (broadcast/timers), and research groups all live here. Call this
    BEFORE telling Stephan you can't do something (check the house, control
    media, dig into something) — don't assume; search first, it's cheap and
    instant. Then call the match with call_tool(name, args) — no loading step,
    same turn. Search always sees everything, so if it's genuinely not in the
    results, that's a real "I can't right now," not a guess.

    Args:
        query: what you're trying to do, in your own words (e.g. "turn off
            the lights" or "play something on the speakers").
    """
    import json
    import os
    import re
    import urllib.request

    base = (os.environ.get("LETTA_API_BASE") or "http://localhost:8283").rstrip("/")
    # Injected from toolsets.json by register-toolsets.sh (single source of truth).
    GROUPS = {}  # __INJECT_GROUPS__
    names = {t for tools in GROUPS.values() for t in tools}
    if not names:
        return "(tool registry not injected — ask Stephan to run register-toolsets.sh)"

    all_tools = json.loads(urllib.request.urlopen(
        base + "/v1/tools/?limit=300", timeout=12).read().decode() or "[]")
    by_name = {t["name"]: t.get("description") or "" for t in all_tools if t.get("name") in names}

    words = [w for w in re.split(r"\W+", (query or "").lower()) if w]
    scored = []
    for name in sorted(names):
        desc = by_name.get(name, "")
        haystack = (name + " " + desc).lower()
        score = sum(1 for w in words if w in haystack)
        if score or not words:
            scored.append((score, name, desc))
    scored.sort(key=lambda x: -x[0])
    top = scored[:8] if words else scored
    if not top:
        return json.dumps({
            "matches": [],
            "hint": "no match — try different words, or call_tool anyway if you already know the exact name",
        })
    return json.dumps({"matches": [{"name": n, "description": d} for _, n, d in top]})
