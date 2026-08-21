#!/usr/bin/env python3
"""Stage-2 tool-calling eval library: create a throwaway Eva agent (persona file +
model) with her real tool set, send messages, capture tool calls + replies, delete."""
import json, os, time, urllib.request, pathlib

LETTA = "http://localhost:8283"
SP = pathlib.Path("/tmp/claude-1000/-var-home-qstivi/3cf9a2ce-b7da-4e24-b6c8-29f3d4eb573c/scratchpad")
TOOL_IDS = json.load(open(SP / "tool_ids.json"))
PERSONA_DIR = pathlib.Path("/var/home/qstivi/projects/eva/persona")

# Eva's core (minus base tools Letta adds itself) + the SAFE home subset.
# Deliberately NO HassClimateSetTemperature (thermostats/space-heaters).
# use_toolset is dropped for the clean selection test: it detaches pre-attached
# tools, which would confound "given these tools, which does the model pick?".
ATTACH = ["searxng_web_search", "web_url_read", "GetDateTime", "todo_get_items",
          "HassListAddItem", "HassListCompleteItem", "HassListRemoveItem",
          "GetLiveContext", "HassTurnOn", "HassTurnOff"]

def _post(path, body, method="POST", timeout=300):
    req = urllib.request.Request(LETTA + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")

def _del(path):
    req = urllib.request.Request(LETTA + path, method="DELETE")
    urllib.request.urlopen(req, timeout=30).read()

def create_agent(model, persona_file, name):
    persona = (PERSONA_DIR / persona_file).read_text()
    body = {
        "name": name, "model": model,
        "embedding_config": {"embedding_endpoint_type": "openai",
            "embedding_endpoint": "http://localhost:1234/v1",
            "embedding_model": "text-embedding-nomic-embed-text-v1.5",
            "embedding_dim": 768, "embedding_chunk_size": 300},
        "memory_blocks": [
            {"label": "persona", "value": persona, "limit": 8000},
            {"label": "human", "value": "This is Stephan (handle: qStivi). I'll learn about him over time and save what matters to this block.", "limit": 8000}],
        "include_base_tools": True,
        "tool_ids": [TOOL_IDS[n] for n in ATTACH if n in TOOL_IDS],
    }
    d = _post("/v1/agents/", body)
    if not d.get("id"):
        raise RuntimeError("create failed: " + json.dumps(d)[:400])
    return d["id"]

def send(aid, msg):
    t0 = time.time()
    d = _post(f"/v1/agents/{aid}/messages", {"messages": [{"role": "user", "content": msg}]})
    dt = round(time.time() - t0, 1)
    tools, returns, reply, reasoning = [], [], None, ""
    for m in d.get("messages", []):
        t = m.get("message_type")
        if t == "tool_call_message":
            tc = m.get("tool_call", {})
            tools.append({"name": tc.get("name"), "args": (tc.get("arguments") or "")[:300]})
        elif t == "tool_return_message":
            returns.append((m.get("status"), (str(m.get("tool_return")) or "")[:300]))
        elif t == "assistant_message":
            reply = m.get("content")
        elif t == "reasoning_message":
            reasoning = (m.get("reasoning") or "")[:200]
    return {"sec": dt, "tools": tools, "returns": returns, "reply": reply, "reasoning": reasoning}

def delete_agent(aid):
    _del(f"/v1/agents/{aid}")

if __name__ == "__main__":
    import sys
    # Discovery mode: create one agent and ask for a full house/sensor readout.
    aid = create_agent("openai-proxy/openai/gpt-oss-20b", "eva.md", f"discover-{int(time.time())}")
    print("agent:", aid)
    try:
        r = send(aid, "Do a full readout for me: list every single light, switch, climate device and sensor you can currently see — including any phone or device sensors — with their exact entity names and current states. Use your live-context tool.")
        print("TOOLS CALLED:", json.dumps(r["tools"], indent=2))
        print("\nREPLY:\n", (r["reply"] or "")[:2500])
    finally:
        delete_agent(aid)
        print("\n[deleted]", aid)
