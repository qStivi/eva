def search_tools(query: str) -> str:
    """Search for a tool you don't currently have — the house, media, house
    extras (broadcast/timers), and research groups all live here. Call this
    BEFORE telling Stephan you can't do something (check the house, control
    media, dig into something) — don't assume; search first, it's cheap and
    instant. A match here is NOT directly callable — you don't have it, that's
    the whole point of searching. Call it through call_tool(name, args), never
    by its own name directly (that fails). No loading step either way, same
    turn. Search always sees everything, so if it's genuinely not in the
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

    # Extra guidance for tools whose own (usually HA-authored, not ours to edit)
    # description has a real gap that's actually bitten in practice — appended,
    # not a replacement, so the original description still shows too.
    EXTRA_HINTS = {
        "GetLiveContext": (
            " HINT: 'domain' is an HA entity-type category (sensor, switch, "
            "media_player, climate, binary_sensor...), NOT a brand/integration name — "
            "e.g. Steam's data lives under domain='sensor', not domain='steam'. To find "
            "a specific device/integration, filter by 'name' instead (or alongside "
            "domain), don't guess a domain that matches the brand."
        ),
    }
    for name, hint in EXTRA_HINTS.items():
        if name in by_name:
            by_name[name] += hint
    # All Hass* tools are HA Assist *intents* (the same targeting voice commands
    # use), not generic entity API calls — they take 'name'/'area'/'floor', never
    # 'entity_id' (that's not a validation gap, it's just not part of this
    # layer's schema). A real live failure: HassClimateSetTemperature called
    # with entity_id got silently ignored, fell back to matching every climate
    # entity by domain alone, and hit an ambiguous MULTIPLE_TARGETS error.
    HASS_TARGETING_HINT = (
        " HINT: this is an HA Assist intent — target it with 'name' (and/or "
        "'area'/'floor' if the name alone is ambiguous), like a voice command "
        "would. It does NOT take 'entity_id' — passing one gets silently "
        "ignored and can make matching worse (falls back to matching "
        "everything in that domain), not better. Area names in this house are "
        "in ENGLISH (e.g. 'Bathroom') even when the device's own name is in "
        "German ('Thermostat Bad') — don't guess a translated/German area name, "
        "read the real one from a prior error's disambiguation data if you're "
        "not sure, don't invent one. If a call comes back DUPLICATE_NAME/"
        "MULTIPLE_TARGETS and this tool accepts a 'domain' filter (check its "
        "schema — not all of them do), add it to narrow the match instead of "
        "just retrying the same call — a single physical device often has many "
        "HA sub-entities (switches, sensors) sharing its name prefix across "
        "different domains, which an unscoped intent can't tell apart."
    )
    for name in by_name:
        if name.startswith("Hass"):
            by_name[name] += HASS_TARGETING_HINT

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
    return json.dumps({
        "matches": [{"name": n, "description": d} for _, n, d in top],
        "how_to_call": "these aren't attached — call_tool(name=..., args=...) for any of them, not the name directly",
    })
