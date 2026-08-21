"""Research executor — loops web searches, decides when it has enough, writes up
a summary with sources. Runs inside eva-task-runner's background thread; never
touches Letta's conversation directly (runner.py does the result injection).

Talks to SearXNG's own JSON API directly (127.0.0.1:8088), not through the
searxng-mcp bridge — that bridge exists only because LM Studio's flatpak sandbox
can't reach loopback the normal way (see lmstudio-searxng-web-search memory);
this runner is a plain host process with no such restriction.

Synthesis/stop-condition calls go to the local LM Studio server (127.0.0.1:1234,
OpenAI-compatible) using the same key eva-lmstudio-status reads from
~/.config/letta/letta.env. Known open question (same class as the sleeptime
consolidator's VRAM problem): this runs on the same GPU as Eva's foreground chat
model, so a research job competing with an active chat could contend for VRAM.
Not solved here — RESEARCH_LM_MODEL is env-overridable so this can be pointed at
a cloud model later without changing the loop.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8088").rstrip("/")
LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234").rstrip("/")
LMSTUDIO_ENV = os.path.expanduser("~/.config/letta/letta.env")
# Whatever's loaded for chat by default; override once VRAM contention is worked out.
LM_MODEL = os.environ.get("RESEARCH_LM_MODEL", "openai/gpt-oss-20b")

MAX_RESULTS_PER_QUERY = 5
DEFAULT_MAX_ITERATIONS = 4


def _lmstudio_key() -> str:
    try:
        with open(LMSTUDIO_ENV) as f:
            for line in f:
                m = re.match(r"\s*OPENAI_API_KEY=(.*)", line)
                if m:
                    return m.group(1).strip()
    except OSError:
        pass
    return ""


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


def _llm_call(system: str, user: str, timeout: int = 90) -> str:
    """One chat-completion call to the local LM Studio server. Raises on failure —
    callers decide how to degrade (the research loop treats a synthesis failure as
    a hard stop, not a silent skip, since the whole job's output depends on it)."""
    body = json.dumps({
        "model": LM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        LMSTUDIO_URL + "/v1/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + _lmstudio_key()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]


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
    "max_iterations": int?}. Returns {"summary": str, "sources": [...]}."""
    topic = (spec.get("topic") or "").strip()
    if not topic:
        raise ValueError("research job spec needs a non-empty 'topic'")
    max_iterations = int(spec.get("max_iterations") or DEFAULT_MAX_ITERATIONS)

    queries = [topic]
    findings = []
    seen_urls = set()

    for _ in range(max_iterations):
        if not queries:
            break
        q = queries.pop(0)
        hits = searxng_search(q)
        new = [h for h in hits if h["url"] not in seen_urls]
        seen_urls.update(h["url"] for h in new)
        findings.extend(new)

        if not findings:
            continue  # nothing yet, no point asking the model to judge an empty set

        verdict = _extract_json(_llm_call(
            "You decide when web research has gathered enough to write up. "
            "Bias toward stopping once the core question is answered.",
            VERDICT_PROMPT.format(topic=topic, n=len(findings),
                                   findings=_format_findings(findings))))
        if verdict.get("done"):
            break
        nq = (verdict.get("next_query") or "").strip()
        if nq and nq not in queries:
            queries.append(nq)

    if not findings:
        return {"summary": f"Couldn't find anything usable on \"{topic}\" — "
                            "SearXNG returned no results across every query tried.",
                "sources": []}

    final = _extract_json(_llm_call(
        "You write clear, well-sourced research summaries from search findings.",
        WRITEUP_PROMPT.format(topic=topic, findings=_format_findings(findings))))
    if not final.get("summary"):
        # Synthesis didn't parse — fall back to the raw findings rather than fail
        # the whole job silently; a rough summary still beats losing the work.
        final = {"summary": _format_findings(findings), "sources": [
            {"title": f["title"], "url": f["url"]} for f in findings]}
    return final
