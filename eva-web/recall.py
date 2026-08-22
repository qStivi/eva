"""recall — the "conversational recall" half of situational context: a
lightweight, best-effort search over Eva's own past messages, refreshed into
a core-memory block before every send so relevant old context surfaces
without her having to think to call `conversation_search`.

See docs/2026-08-22-situational-context-spec.md's "Conversational recall"
section for the design rationale — short version: Letta's real semantic
search (`/v1/messages/search`) is cloud-only and unavailable to this
self-hosted instance, and `conversation_search` the tool has no standalone
callable source, so this is a plain keyword-overlap search eva-web does
itself against the message log it already has access to
(`GET /v1/agents/{id}/messages`), same posture as `search_tools.py`'s
keyword matching for tools. Loses semantic nuance a real embedding search
would give; worth revisiting only if that proves too weak in practice.

Caches the message log locally (~/.config/eva-web/recall_cache/<agent_id>.json)
and only fetches new messages since the last cached one each call — a full
history scan per turn was flagged as a real cost concern in the spec, this
avoids re-fetching+retokenizing the whole log every single message.
"""
import datetime
import json
import os
import re
import urllib.parse
import urllib.request

CACHE_DIR = os.path.expanduser(os.environ.get("RECALL_CACHE_DIR", "~/.config/eva-web/recall_cache"))
FETCH_PAGE_SIZE = 200
FETCH_TIMEOUT = 6

# Below this many meaningful words in the incoming message, there's nothing
# distinctive enough to match against — skip recall entirely rather than
# surface noise on "ok" / "thanks" / "yeah lol".
MIN_QUERY_TOKENS = 2
# Shared-token floor for a candidate to count as a real match, not a
# coincidental overlap on one common word.
MIN_MATCH_SHARED_TOKENS = 2
TOP_N = 2
SNIPPET_CHARS = 180

_STOPWORDS = frozenset("""
a an the this that these those is are was were be been being do does did
have has had i you he she it we they me him her us them my your his its our
their and or but if so to of in on at for with as by from up out about into
over after before again further then once here there when where why how
not no nor only own same too very can will just don should now what which
who whom yeah yep nope ok okay thanks thank please really actually kind
sort get got going go can't don't didn't i'm it's that's there's im ive
""".split())


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _cache_path(agent_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{agent_id}.json")


def _load_cache(agent_id: str) -> dict:
    try:
        with open(_cache_path(agent_id)) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"last_id": None, "entries": []}


def _save_cache(agent_id: str, cache: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(agent_id), "w") as f:
        json.dump(cache, f)


def _fetch_page(letta_host: str, agent_id: str, after: str = None) -> list:
    params = {"limit": FETCH_PAGE_SIZE, "order": "asc"}
    if after:
        params["after"] = after
    url = f"{letta_host}/v1/agents/{agent_id}/messages?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return json.loads(r.read().decode())


def _refresh_cache(letta_host: str, agent_id: str) -> dict:
    """Backfill on first run (no cache yet), otherwise fetch only what's new
    since the last cached message. Only user/assistant turns are indexed —
    the point is "things actually said in this conversation," not tool
    plumbing or reasoning traces."""
    cache = _load_cache(agent_id)
    cursor = cache["last_id"]
    while True:
        try:
            batch = _fetch_page(letta_host, agent_id, after=cursor)
        except Exception:  # noqa: BLE001 — best-effort; use whatever's cached already
            break
        if not batch:
            break
        for m in batch:
            t = m.get("message_type")
            if t == "user_message":
                role, text = "Stephan", m.get("content")
            elif t == "assistant_message":
                role, text = "Eva", m.get("content")
            else:
                continue
            if not text or not isinstance(text, str):
                continue
            cache["entries"].append({
                "id": m.get("id"),
                "role": role,
                "text": text.strip(),
                "ts": m.get("date") or m.get("created_at") or "",
                "tokens": sorted(_tokenize(text)),
            })
        cursor = batch[-1].get("id") or cursor
        if len(batch) < FETCH_PAGE_SIZE:
            break
    cache["last_id"] = cursor
    _save_cache(agent_id, cache)
    return cache


def _relative_date(ts: str) -> str:
    if not ts:
        return "at some point"
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return "at some point"
    days = (datetime.datetime.now(dt.tzinfo) - dt).days
    if days <= 0:
        return "earlier today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return dt.strftime("%B %-d")


def build(letta_host: str, agent_id: str, query: str, live_message_ids: list,
          block_texts: list) -> str:
    """One short plain-text block of relevant old snippets, or an explicit
    "nothing surfaced" line — never just omitted, same idle-explicit lesson
    situational_context.py learned the hard way: a missing line reads as
    "unknown" to the model, not "known and empty."

    live_message_ids: the agent's current AgentState.message_ids — anything
    already in there is skipped, it's already in context, repeating it is
    pure waste (spec's "exact and cheap" dedup layer).
    block_texts: current human/persona block values — a candidate that
    heavily overlaps one of these is presumed already folded into permanent
    memory by sleeptime and gets skipped too (spec's "fuzzy, best-effort"
    layer; approximate on purpose, not authoritative).
    """
    query_tokens = _tokenize(query)
    if len(query_tokens) < MIN_QUERY_TOKENS:
        return ""  # nothing distinctive enough to search on — say nothing at all,
        # not even the "nothing surfaced" line; this isn't a real attempt to look

    cache = _refresh_cache(letta_host, agent_id)
    live_ids = set(live_message_ids or [])
    block_tokens = set()
    for t in block_texts or []:
        block_tokens |= _tokenize(t)

    scored = []
    for e in cache["entries"]:
        if e["id"] in live_ids:
            continue
        etoks = set(e["tokens"])
        shared = query_tokens & etoks
        if len(shared) < MIN_MATCH_SHARED_TOKENS:
            continue
        if etoks and len(etoks & block_tokens) / len(etoks) > 0.6:
            continue  # looks like this already made it into permanent memory
        scored.append((len(shared), e))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [e for _, e in scored[:TOP_N]]

    if not top:
        return "Related from past conversations: nothing relevant surfaced for this message."

    lines = ["Related from past conversations (approximate keyword match, may be noise):"]
    for e in top:
        snippet = e["text"][:SNIPPET_CHARS]
        if len(e["text"]) > SNIPPET_CHARS:
            snippet += "…"
        lines.append(f'- [{e["role"]}, {_relative_date(e["ts"])}]: "{snippet}"')
    return "\n".join(lines)
