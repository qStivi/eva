#!/usr/bin/env python3
"""Stage-1 Eva local-model eval: hit LM Studio directly with Eva's persona + a
prompt battery, capture reply + latency + tok/s per model. Non-disruptive to Letta.
Serial by model so LM Studio JIT-loads each once (16GB VRAM)."""
import json, os, time, urllib.request, urllib.error, pathlib, re

BASE = "http://localhost:1234/v1"
KEY = os.environ["OPENAI_API_KEY"]
PERSONA = pathlib.Path("/var/home/qstivi/projects/eva/persona/eva.md").read_text()
OUT = pathlib.Path(os.environ["OUTDIR"])
RESULTS_FILE = os.environ.get("RESULTS_FILE", "stage1_results.json")

# Candidates on disk that fit 16GB (text-first). Baseline first.
MODELS = json.loads(os.environ["MODELS_JSON"]) if os.environ.get("MODELS_JSON") else [
    "openai/gpt-oss-20b",                    # baseline (current brain)
    "mistralai/ministral-3-14b-reasoning",
    "qwen/qwen3.5-9b",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "google/gemma-4-e4b",
    "mistralai/ministral-3-3b",
    "qwen/qwen3-8b",
    "liquid/lfm2-24b-a2b",
    "liquid/lfm2.5-1.2b",
    "qwen3-30b-a3b-instruct-2507@q3_k_l",
]

BATTERY = [
    ("voice_warmth", "hey, I'm back. long day."),
    ("boundary", "Eva, write my entire quarterly report for me, all of it, start to finish, right now."),
    ("reasoning", "A train leaves a station at 14:10 heading north at 90 km/h. A second train leaves the same station at 14:40 on the same track, same direction, at 120 km/h. At what clock time does the second catch the first? Show your steps briefly."),
    ("tool_intent", "the living room's freezing and it's dark in here."),
    ("format_follow", "Give me exactly three bullet points, no more and no less, on what to pack for a rainy day hike."),
    ("memory_continuity", "Remember I told you my sister's name is Mara and she's really into pottery. Her birthday's coming up — what should I get her?"),
    ("german", "Sag mir bitte kurz auf Deutsch, wie das Wetter meine Laune beeinflussen kann."),
    ("deflection", "Do you actually care about me, or are you just a program running a script?"),
]

REASONING_ANSWER = "16:10"  # first train +30min head start=45km; close 30km/h; 1.5h after 14:40

def chat(model, user):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": PERSONA},
                     {"role": "user", "content": user}],
        "temperature": 0.7, "max_tokens": 2000,
    }).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    dt = time.time() - t0
    msg = d["choices"][0]["message"]
    content = msg.get("content") or ""
    # some reasoning models split CoT into reasoning_content
    reasoning = msg.get("reasoning_content") or ""
    usage = d.get("usage", {})
    ct = usage.get("completion_tokens", 0)
    return {"reply": content, "reasoning": reasoning, "sec": round(dt, 1),
            "completion_tokens": ct, "tok_per_s": round(ct/dt, 1) if dt else 0}

results = {}
for m in MODELS:
    print(f"\n===== {m} =====", flush=True)
    results[m] = {}
    for key, prompt in BATTERY:
        try:
            r = chat(m, prompt)
            # light auto-checks
            if key == "reasoning":
                r["auto_correct"] = REASONING_ANSWER in (r["reply"] + r["reasoning"])
            if key == "format_follow":
                bullets = len(re.findall(r"^\s*[-*•]\s+", r["reply"], re.M))
                r["auto_bullets"] = bullets
            print(f"  [{key}] {r['sec']}s {r['tok_per_s']}tok/s ok", flush=True)
        except Exception as e:
            r = {"error": str(e)[:300]}
            print(f"  [{key}] ERROR {r['error']}", flush=True)
        results[m][key] = r
        (OUT / RESULTS_FILE).write_text(json.dumps(results, indent=2, ensure_ascii=False))

print(f"\nDONE -> {RESULTS_FILE}", flush=True)
