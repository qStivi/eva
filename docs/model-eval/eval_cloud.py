#!/usr/bin/env python3
"""Thing-1 cloud model eval: hit Anthropic + Mistral directly with Eva's persona +
the same 8-prompt Stage-1 battery, capture reply + latency + real token usage + real
$ cost per call (self-computed from official per-model pricing, not a provider usage
API). Direct provider APIs, not Letta and not OpenRouter -- matches the model-ladder
plan's decision to stay on Letta as the backend but compare raw model economics first.
Serial, one call at a time -- these are billed requests."""
import json, os, time, urllib.request, urllib.error, pathlib, re

PERSONA = pathlib.Path("/var/home/qstivi/projects/eva/persona/eva.md").read_text()
OUT = pathlib.Path(os.environ.get("OUTDIR", "."))
RESULTS_FILE = os.environ.get("RESULTS_FILE", "cloud_results.json")

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
MISTRAL_KEY = os.environ["MISTRAL_API_KEY"]

# (provider, api_model_id, label, $/MTok in, $/MTok out) -- prices confirmed 2026-08-13
# against platform.claude.com/docs/en/about-claude/pricing and mistral.ai/pricing/api.
MODELS = [
    ("anthropic", "claude-haiku-4-5", "haiku-4.5", 1.00, 5.00),
    ("anthropic", "claude-sonnet-5", "sonnet-5", 2.00, 10.00),
    ("anthropic", "claude-opus-5", "opus-5", 5.00, 25.00),
    ("mistral", "ministral-8b-latest", "ministral-8b", 0.15, 0.15),
    ("mistral", "mistral-small-latest", "mistral-small", 0.15, 0.60),
    ("mistral", "mistral-medium-latest", "mistral-medium-3.5", 1.50, 7.50),
]

# Same battery as Stage 1 (persona/voice + reasoning + tool-intent + format + memory +
# german + boundary), so cloud tiers are directly comparable to the local bake-off.
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

REASONING_ANSWER = "16:10"


def chat_anthropic(model, user):
    # Claude 5-gen models reject an explicit `temperature` (deprecated for them) --
    # omit it and take the model's default rather than pin per-model behavior.
    body = json.dumps({
        "model": model, "max_tokens": 2000,
        "system": PERSONA,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    dt = time.time() - t0
    content = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    usage = d.get("usage", {})
    return {"reply": content, "sec": round(dt, 1),
            "in_tok": usage.get("input_tokens", 0), "out_tok": usage.get("output_tokens", 0)}


def chat_mistral(model, user):
    body = json.dumps({
        "model": model, "max_tokens": 2000, "temperature": 0.7,
        "messages": [{"role": "system", "content": PERSONA},
                     {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request("https://api.mistral.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    dt = time.time() - t0
    content = d["choices"][0]["message"].get("content") or ""
    usage = d.get("usage", {})
    return {"reply": content, "sec": round(dt, 1),
            "in_tok": usage.get("prompt_tokens", 0), "out_tok": usage.get("completion_tokens", 0)}


def call(provider, model, user):
    if provider == "anthropic":
        return chat_anthropic(model, user)
    return chat_mistral(model, user)


def run():
    results = {}
    grand_total = 0.0
    for provider, model, label, price_in, price_out in MODELS:
        print(f"\n===== {label} ({provider}/{model}) =====", flush=True)
        results[label] = {"provider": provider, "model": model, "turns": {}}
        model_total = 0.0
        for key, prompt in BATTERY:
            try:
                r = call(provider, model, prompt)
                cost = r["in_tok"] / 1e6 * price_in + r["out_tok"] / 1e6 * price_out
                r["cost_usd"] = round(cost, 6)
                model_total += cost
                if key == "reasoning":
                    r["auto_correct"] = REASONING_ANSWER in r["reply"]
                if key == "format_follow":
                    r["auto_bullets"] = len(re.findall(r"^\s*[-*•]\s+", r["reply"], re.M))
                print(f"  [{key}] {r['sec']}s  {r['in_tok']}in/{r['out_tok']}out  ${cost:.5f}", flush=True)
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                r = {"error": f"HTTP {e.code}: {body}"}
                print(f"  [{key}] ERROR {r['error']}", flush=True)
            except Exception as e:
                r = {"error": str(e)[:300]}
                print(f"  [{key}] ERROR {r['error']}", flush=True)
            results[label]["turns"][key] = r
            (OUT / RESULTS_FILE).write_text(json.dumps(results, indent=2, ensure_ascii=False))
        results[label]["model_total_usd"] = round(model_total, 5)
        grand_total += model_total
        print(f"  -- {label} subtotal: ${model_total:.5f}", flush=True)

    results["_grand_total_usd"] = round(grand_total, 5)
    (OUT / RESULTS_FILE).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nDONE -> {RESULTS_FILE}   GRAND TOTAL: ${grand_total:.5f}", flush=True)
    return results


if __name__ == "__main__":
    run()
