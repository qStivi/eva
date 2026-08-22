"""Research executor — loops web searches, decides when it has enough, writes up
a summary with sources. Runs inside eva-task-runner's background thread; never
touches Letta's conversation directly (runner.py does the result injection).

Talks to SearXNG's own JSON API directly (127.0.0.1:8088), not through the
searxng-mcp bridge — that bridge exists only because LM Studio's flatpak sandbox
can't reach loopback the normal way (see lmstudio-searxng-web-search memory);
this runner is a plain host process with no such restriction.

Synthesis/stop-condition calls go to a cloud tier (Mistral, OpenAI-compatible
API) rather than the local LM Studio model — deliberately, so a research job
never contends with Eva's foreground chat model for GPU/VRAM (the same class of
problem the sleeptime consolidator hit). The API key isn't duplicated into a new
env file: it's pulled live from Letta's own provider store (/v1/providers/,
loopback-only, same trust boundary Letta itself already uses) each time the
in-process cache is empty, and never written to disk here.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8088").rstrip("/")
LETTA_HOST = os.environ.get("LETTA_HOST", "http://localhost:8283").rstrip("/")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
CLOUD_MODEL = os.environ.get("RESEARCH_CLOUD_MODEL", "mistral-large-latest")
COST_LOG = os.path.expanduser("~/.config/eva-web/cost_log.jsonl")  # same log model_router uses
# $/MTok, matching model_router's "mid" tier pricing for this same model.
# mistral-large-latest as of 2026-08-22 (was mistral-medium-latest — same
# performance bar per Mistral's own comparison guide, a third the input cost
# and a fifth the output cost; see model_router.py's TIERS comment).
PRICE_IN, PRICE_OUT = 0.50, 1.50

# Only real constraint is context length, not an arbitrary "don't overdo it" cap —
# Mistral's context window has plenty of room for this. Env-overridable per job kind
# if that ever needs tuning without a redeploy.
MAX_RESULTS_PER_QUERY = int(os.environ.get("RESEARCH_MAX_RESULTS_PER_QUERY", "40"))
DEFAULT_MAX_ITERATIONS = 4
# Soft ceiling, not a hard cap on quality: observed real jobs cost $0.005-0.01, so
# this is ~30-50x that — a real backstop against a pathological loop (e.g. verdict
# never returning done), not a knob meant to bind in normal use. Stops issuing new
# verdict calls past this; the final write-up still runs once on whatever's in hand,
# since a job that goes over budget should still deliver something rather than fail.
MAX_COST_USD = float(os.environ.get("RESEARCH_MAX_COST_USD", "0.30"))

_key_cache = {"key": None, "ts": 0}


def _mistral_key() -> str:
    """Fetch the Mistral BYOK key from Letta's own provider store. Cached in
    memory for an hour per process — this executor may run several calls per
    job, no need to hit Letta again for each one."""
    if _key_cache["key"] and time.time() - _key_cache["ts"] < 3600:
        return _key_cache["key"]
    with urllib.request.urlopen(LETTA_HOST + "/v1/providers/", timeout=10) as r:
        providers = json.loads(r.read().decode())
    for p in providers:
        if p.get("name") == "mistral" and p.get("api_key_enc"):
            _key_cache.update(key=p["api_key_enc"], ts=time.time())
            return p["api_key_enc"]
    raise RuntimeError("no 'mistral' provider with a key configured in Letta")


def searxng_search(query: str, timeout: int = 15) -> list:
    """One SearXNG query -> [{title, url, content}, ...], best-effort."""
    url = SEARXNG_URL + "/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError):
        return []
    out = []
    for item in data.get("results", [])[:MAX_RESULTS_PER_QUERY]:
        if item.get("url") and item.get("title"):
            out.append({"title": item["title"], "url": item["url"],
                        "content": (item.get("content") or "")[:600]})
    return out


def _llm_call(system: str, user: str, timeout: int = 90) -> tuple:
    """One chat-completion call to the cloud tier (Mistral). Raises on failure —
    callers decide how to degrade (the research loop treats a synthesis failure as
    a hard stop, not a silent skip, since the whole job's output depends on it).
    Returns (content, cost_usd) so callers can track spend against a budget."""
    body = json.dumps({
        "model": CLOUD_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        MISTRAL_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + _mistral_key()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    cost = _log_cost(data.get("usage") or {})
    return data["choices"][0]["message"]["content"], cost


def _log_cost(usage: dict) -> float:
    """Append one line to the same cost log model_router.py writes, so research
    spend shows up alongside chat spend. Best-effort; never raises. Returns the
    computed cost regardless of whether the log write itself succeeded, so a
    caller's budget tracking doesn't silently stop working if disk logging fails."""
    prompt = usage.get("prompt_tokens", 0) or 0
    out = usage.get("completion_tokens", 0) or 0
    cost = (prompt * PRICE_IN + out * PRICE_OUT) / 1e6
    try:
        line = {"ts": time.time(), "tier": "research", "model": CLOUD_MODEL,
                "cost_usd": round(cost, 6), "usage": usage}
        os.makedirs(os.path.dirname(COST_LOG), exist_ok=True)
        with open(COST_LOG, "a") as f:
            f.write(json.dumps(line) + "\n")
    except Exception:  # noqa: BLE001
        pass
    return cost


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction — local models don't reliably respect a strict
    JSON-only instruction, so pull the first {...} block instead of trusting the
    whole response to parse cleanly."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


VERDICT_PROMPT = """You are screening web search results for a research task.
Topic: {topic}

Findings so far ({n} items):
{findings}

Decide: do these findings cover the topic well enough to write a good summary,
or is another search needed? Respond with ONLY a JSON object, no other text:
{{"done": true|false, "next_query": "<a new, more specific search query>" or null}}"""

WRITEUP_PROMPT = """Write up a concise research summary on: {topic}

Based on these findings:
{findings}

Respond with ONLY a JSON object, no other text:
{{"summary": "<a few paragraphs, plain text, no markdown headers>",
  "sources": [{{"title": "...", "url": "..."}}, ...]}}"""


def _format_findings(findings: list) -> str:
    return "\n".join(f"- {f['title']} ({f['url']}): {f['content']}" for f in findings)


def run(spec: dict) -> dict:
    """Entry point called by runner.py's executor dispatch. spec: {"topic": str,
    "max_iterations": int?}. Returns {"summary": str, "sources": [...], "trail": [...]}
    — trail is the full audit record: every query issued, what it returned, and
    the stop/continue verdict after each one, so a finished job is inspectable
    after the fact (via GET /jobs/<id> or check_task) and not just its summary."""
    topic = (spec.get("topic") or "").strip()
    if not topic:
        raise ValueError("research job spec needs a non-empty 'topic'")
    max_iterations = int(spec.get("max_iterations") or DEFAULT_MAX_ITERATIONS)

    queries = [topic]
    findings = []
    seen_urls = set()
    trail = []
    spent = 0.0

    for _ in range(max_iterations):
        if not queries:
            break
        if spent >= MAX_COST_USD:
            break  # over budget: stop refining, go straight to the write-up below
        q = queries.pop(0)
        hits = searxng_search(q)
        new = [h for h in hits if h["url"] not in seen_urls]
        seen_urls.update(h["url"] for h in new)
        findings.extend(new)

        entry = {"query": q, "results": [{"title": h["title"], "url": h["url"]} for h in new],
                  "verdict": None}
        trail.append(entry)

        if not findings:
            continue  # nothing yet, no point asking the model to judge an empty set

        text, cost = _llm_call(
            "You decide when web research has gathered enough to write up. "
            "Bias toward stopping once the core question is answered.",
            VERDICT_PROMPT.format(topic=topic, n=len(findings),
                                   findings=_format_findings(findings)))
        spent += cost
        verdict = _extract_json(text)
        entry["verdict"] = verdict
        if verdict.get("done"):
            break
        nq = (verdict.get("next_query") or "").strip()
        if nq and nq not in queries:
            queries.append(nq)

    if not findings:
        return {"summary": f"Couldn't find anything usable on \"{topic}\" — "
                            "SearXNG returned no results across every query tried.",
                "sources": [], "trail": trail}

    text, _cost = _llm_call(
        "You write clear, well-sourced research summaries from search findings.",
        WRITEUP_PROMPT.format(topic=topic, findings=_format_findings(findings)))
    final = _extract_json(text)
    if not final.get("summary"):
        # Synthesis didn't parse — fall back to the raw findings rather than fail
        # the whole job silently; a rough summary still beats losing the work.
        final = {"summary": _format_findings(findings), "sources": [
            {"title": f["title"], "url": f["url"]} for f in findings]}
    final["trail"] = trail
    return final
