def call_tool(name: str, args: dict = None) -> str:
    """Call a tool you found with search_tools, by its exact name. Nothing has
    to be loaded or attached first — this works the same turn you searched,
    for anything search_tools returned (or any tool name you already know).

    Args:
        name: the exact tool name, e.g. "HassTurnOn" or "research_task" — as
            returned by search_tools.
        args: the arguments that tool takes, as key/value pairs — check the
            description search_tools gave you for what it needs. Leave empty
            for a tool that takes none.
    """
    import json
    import os
    import urllib.error
    import urllib.request

    base = (os.environ.get("LETTA_API_BASE") or "http://localhost:8283").rstrip("/")
    # Injected from toolsets.json by register-toolsets.sh (single source of truth).
    GROUPS = {}  # __INJECT_GROUPS__
    MCP_SERVER = "homeassistant"  # only external_mcp source currently gated this way
    managed = {t for tools in GROUPS.values() for t in tools}
    if name not in managed:
        return "(no such tool %r — search_tools first, or it's not one I'm allowed to reach this way)" % name

    all_tools = json.loads(urllib.request.urlopen(
        base + "/v1/tools/?limit=300", timeout=12).read().decode() or "[]")
    tool = next((t for t in all_tools if t.get("name") == name), None)
    if not tool:
        return "(tool %r isn't registered in Letta)" % name

    # Catch a wrong/misremembered argument name here, before it ever reaches
    # Letta's own sandbox — confirmed live (2026-08-22) that an unrecognized
    # key doesn't fail cleanly there: Letta's generated wrapper references the
    # raw arg name as a bare Python identifier before checking it's a real
    # declared parameter, so a typo'd key crashes with a confusing
    # "NameError: name 'x' is not defined" instead of a message that's
    # actually useful to self-correct from. Only checked for our own
    # plain-python tools (json_schema shape is ours to trust); external_mcp
    # tools validate on the MCP server's own side.
    schema = tool.get("json_schema") or {}
    props = (schema.get("parameters") or {}).get("properties")
    if tool.get("tool_type") != "external_mcp" and isinstance(props, dict):
        bad = [k for k in (args or {}) if k not in props]
        if bad:
            return ("(call_tool: %r doesn't take an argument named %s — valid "
                     "arguments are: %s)" % (name, ", ".join(map(repr, bad)),
                                              ", ".join(sorted(props)) or "(none)"))

    try:
        if tool.get("tool_type") == "external_mcp":
            # MCP tools run straight against their server — no agent attachment
            # needed, so no next-turn lag either (see docs/2026-08-22-tool-discovery-spec.md).
            url = f"{base}/v1/tools/mcp/servers/{MCP_SERVER}/tools/{name}/execute"
            body = json.dumps({"args": args or {}}).encode()
        else:
            # Our own plain-python source tools run standalone from source —
            # json_schema has to come along too, or Letta's sandbox can't bind args.
            url = f"{base}/v1/tools/run"
            body = json.dumps({
                "source_code": tool.get("source_code", ""),
                "json_schema": tool.get("json_schema"),
                "name": name,
                "args": args or {},
            }).encode()
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return "(call failed: HTTP %s — %s)" % (e.code, e.read().decode()[:300])
    except Exception as e:  # noqa: BLE001 — surface as a normal reply, not a crash
        return "(call failed: %s)" % e

    # MCP execute returns {"result": ...}; source-run returns a tool_return_message.
    if isinstance(data, dict) and "result" in data:
        return str(data["result"])
    if isinstance(data, dict) and "tool_return" in data:
        return str(data["tool_return"])
    return json.dumps(data)
