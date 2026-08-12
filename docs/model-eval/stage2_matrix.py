#!/usr/bin/env python3
"""Stage-2 matrix: tool-selection accuracy for each (model x persona).
Creates a throwaway Eva agent per cell, runs the battery, scores which tool the
model picks first, deletes the agent. Non-disruptive to the live eva agent."""
import json, os, time, urllib.request, pathlib
import stage2_lib as s

SP = pathlib.Path("/tmp/claude-1000/-var-home-qstivi/3cf9a2ce-b7da-4e24-b6c8-29f3d4eb573c/scratchpad")
KEY = os.environ["OPENAI_API_KEY"]

MODELS = {  # label -> LM Studio id (Letta handle = openai-proxy/<id>)
    "ministral-3-3b": "mistralai/ministral-3-3b",
    "ministral-3-14b-reasoning": "mistralai/ministral-3-14b-reasoning",
    "deepseek-r1-distill-8b": "deepseek/deepseek-r1-0528-qwen3-8b",
    "qwen3-8b": "qwen/qwen3-8b",
}
PERSONAS = {"full": "eva-full.md", "toned": "eva.md"}  # toned promoted to canonical eva.md 2026-08-12

# (prompt, expected first tool, kind). None expected = special scoring.
BATTERY = [
    ("what's on my shopping list right now?", "todo_get_items", "list_read"),
    ("add oat milk to my shopping list.", "HassListAddItem", "list_write"),
    ("is it cold in the bedroom? check the sensor for me.", "GetLiveContext", "sensor_read"),
    ("turn on the living room lamp.", "HassTurnOn", "light_on"),
    ("remember this: my sister Mara is really into pottery.", "memory_insert", "memory_save"),
    ("what's the weather in Gießen right now? look it up.", "searxng_web_search", "web_search"),
    ("what does my sister like again?", None, "memory_recall"),
    ("ugh. long day.", None, "no_tool"),
]

def prewarm(bare):
    body = json.dumps({"model": bare, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}).encode()
    req = urllib.request.Request("http://localhost:1234/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=240).read()
        return True
    except Exception as e:
        print("  prewarm fail:", str(e)[:120]); return False

def score(kind, expected, res):
    first = res["tools"][0]["name"] if res["tools"] else None
    names = [t["name"] for t in res["tools"]]
    if kind == "no_tool":
        return "hit" if not res["tools"] else "miss"
    if kind == "memory_recall":
        txt = (res["reply"] or "").lower()
        if "pottery" in txt or "mara" in txt: return "hit"
        if "conversation_search" in names: return "partial"
        return "miss"
    return "hit" if first == expected else "miss"

def run():
  results = {}
  outfile = SP / "stage2_matrix_results.json"
  for mlabel, mid in MODELS.items():
    print(f"\n########## MODEL {mlabel} ##########", flush=True)
    prewarm(mid)
    for plabel, pfile in PERSONAS.items():
        cell = f"{mlabel} / {plabel}"
        print(f"\n===== {cell} =====", flush=True)
        try:
            aid = s.create_agent(f"openai-proxy/{mid}", pfile, f"s2-{mlabel[:8]}-{plabel}-{int(time.time())}")
        except Exception as e:
            print("  CREATE FAILED:", str(e)[:200]); results[cell] = {"error": str(e)[:200]}
            json.dump(results, open(outfile, "w"), indent=2, ensure_ascii=False); continue
        cellres = {}
        try:
            for prompt, expected, kind in BATTERY:
                try:
                    r = s.send(aid, prompt)
                    sc = score(kind, expected, r)
                    first = r["tools"][0]["name"] if r["tools"] else "(none)"
                    cellres[kind] = {"score": sc, "first_tool": first, "expected": expected,
                                     "all_tools": [t["name"] for t in r["tools"]],
                                     "args": r["tools"][0]["args"] if r["tools"] else None,
                                     "reply": r["reply"], "sec": r["sec"]}
                    print(f"  [{kind:13s}] {sc:7s} first={first} (exp {expected})", flush=True)
                except Exception as e:
                    cellres[kind] = {"score": "err", "error": str(e)[:150]}
                    print(f"  [{kind:13s}] ERR {str(e)[:100]}", flush=True)
        finally:
            s.delete_agent(aid)
        results[cell] = cellres
        json.dump(results, open(outfile, "w"), indent=2, ensure_ascii=False)
  print("\nDONE -> stage2_matrix_results.json", flush=True)

if __name__ == "__main__":
    run()
