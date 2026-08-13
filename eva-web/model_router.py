#!/usr/bin/env python3
"""Complexity-based cloud-only model router for Eva's live agent.

Classifies each incoming message with a lightweight heuristic and switches the
agent's model tier (Letta's `model` field via PATCH /v1/agents/{id}) before the
turn is sent -- cheapest tier that can plausibly handle it, escalating freely
per message (no artificial stickiness; the user chose "let it escalate freely"
over a sticky/conservative router on 2026-08-13).

**Mixes both companies** (the original ask): Mistral covers cheap+mid (it's
roughly 10x cheaper than the equivalent Anthropic tier for comparable quality
in the cloud_comparison.html bake-off), Opus 5 is reserved for genuinely hard
turns where the extra quality is worth the cost.

Mistral was broken here until 2026-08-13: Letta's OpenAI-compatible client (the
code path Mistral is routed through, since MistralProvider uses
model_endpoint_type="openai") unconditionally set an OpenAI `user` field that
Mistral's stricter schema 422s on ("extra_forbidden: body.user"). No upstream
letta-ai/letta issue existed for it, so it's patched locally -- see
~/.config/letta/openai_client.py (bind-mounted over the container's copy via
the letta.container Quadlet unit, same pattern as url_validation.py). Two call
sites needed the fix: a stray `user=str()` in the ChatCompletionRequest
constructor (this was the actual leak -- pydantic's exclude_unset=True doesn't
omit a field that was explicitly passed, even as an empty string) and the later
"always set user id" reassignment, both now guarded on
`llm_config.provider_name in (None, "openai")`, mirroring a guard Letta already
uses elsewhere in the same file for other OpenAI-specific fields.

Cost is read from Letta's own per-turn `usage` object -- real token counts,
including the prompt-cache read/write split -- not self-estimated like the
eval_cloud.py comparison harness. Letta already triggers automatic caching for
Anthropic with zero extra config (confirmed empirically 2026-08-13, a same-tier
follow-up turn hit cache for ~10.6k of ~10.7k input tokens, 10% price instead
of 100%); Mistral calls have shown nonzero `cached_input_tokens` too, though
its cache pricing isn't separately confirmed, so the same multipliers below are
applied as an approximation -- the dollar amounts on Mistral's tiers are small
enough that the error is negligible. Switching tiers forfeits that tier's cache
for the turn that switches in but does NOT invalidate the tier you left -- each
model's cache lives independently, so a detour to a harder tier and back is one
expensive turn, not an ongoing penalty. Logged to
~/.config/eva-web/cost_log.jsonl (one JSON line per turn) so spend is visible.

Stdlib only (matches eva-web). Router failure must never block a chat.
"""
import json
import os
import re
import time
import urllib.request

LOG_PATH = os.path.expanduser("~/.config/eva-web/cost_log.jsonl")

# tier -> (Letta model handle, $/MTok base input, $/MTok output)
# Confirmed 2026-08-13 against platform.claude.com/docs/en/about-claude/pricing
# and mistral.ai/pricing/api.
TIERS = {
    "cheap": ("mistral/ministral-8b-latest", 0.15, 0.15),
    "mid": ("mistral/mistral-medium-latest", 1.50, 7.50),
    "hard": ("anthropic/claude-opus-5", 5.00, 25.00),
}
CACHE_WRITE_MULT = 1.25  # Anthropic 5-min cache write multiplier (Letta's default TTL)
CACHE_READ_MULT = 0.10

# Heuristic v1 -- tune after seeing real message distribution (plan doc open Q).
REASONING = re.compile(r"\b(why|explain|compare|analyze|analyse|plan|figure out|"
                        r"help me decide|what if|how (should|do) i|pros and cons|"
                        r"trade-?off|think (it |this )?through)\b", re.I)
EMOTIONAL = re.compile(r"\b(feel(ing)?|scared|afraid|anxious|anxiety|lonely|alone|"
                        r"worried|worry|overwhelm(ed)?|hurt|cry(ing)?|depress(ed|ion)?|"
                        r"sad|hopeless|relationship|breakup|grief|griev|struggl)\b", re.I)
BOUNDARY = re.compile(r"\b(write (my|the) (entire|whole|full)|do (it|this|that) for me|"
                       r"all of it|everything for me|just do it|handle (it|this) entirely)\b", re.I)
# Identity/authenticity questions ("do you actually care", "are you just a
# program") -- the cloud comparison (docs/model-eval/cloud_comparison.html)
# showed the biggest voice-quality gap between tiers on exactly this class of
# message, so it's weighted like EMOTIONAL even though it's often short.
IDENTITY = re.compile(r"\b(do you (actually|really) (care|love)|"
                       r"are you (just|only) (a program|code|an? ai|a script|a bot)|"
                       r"do you (have feelings|feel anything)|"
                       r"am i (just|only) (a user|talking to a bot))\b", re.I)

_last_tier = {}  # agent_id -> tier name, in-process cache to skip redundant PATCHes


def classify(message: str) -> str:
    """Heuristic complexity score -> tier name. Cheapest tier by default."""
    msg = message or ""
    score = 0
    n = len(msg)
    if n > 400:
        score += 2
    elif n > 150:
        score += 1
    if REASONING.search(msg):
        score += 1
    if EMOTIONAL.search(msg):
        score += 2
    if BOUNDARY.search(msg):
        score += 2
    if IDENTITY.search(msg):
        score += 2
    if msg.count("?") >= 2:
        score += 1
    if score == 0:
        return "cheap"
    if score <= 2:
        return "mid"
    return "hard"


def _patch(host, agent_id, handle):
    body = json.dumps({"model": handle}).encode()
    req = urllib.request.Request(f"{host.rstrip('/')}/v1/agents/{agent_id}",
        data=body, headers={"Content-Type": "application/json"}, method="PATCH")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def route_before_send(message, agent_id, host="http://localhost:8283"):
    """Switch the agent to the tier this message calls for, if not already
    there. Returns the tier name. Callers should treat this as best-effort."""
    tier = classify(message)
    if _last_tier.get(agent_id) == tier:
        return tier
    _patch(host, agent_id, TIERS[tier][0])
    _last_tier[agent_id] = tier
    return tier


def cost_for_usage(tier, usage):
    """$ cost of one turn from Letta's real usage_statistics object."""
    if not usage or tier not in TIERS:
        return 0.0
    _, price_in, price_out = TIERS[tier]
    cached = usage.get("cached_input_tokens", 0) or 0
    written = usage.get("cache_write_tokens", 0) or 0
    prompt = usage.get("prompt_tokens", 0) or 0
    base = max(prompt - cached - written, 0)
    out = usage.get("completion_tokens", 0) or 0
    return (base * price_in + written * price_in * CACHE_WRITE_MULT +
            cached * price_in * CACHE_READ_MULT + out * price_out) / 1e6


def log_turn(tier, usage, message_preview=""):
    """Append one cost-log line. Best-effort; never raises."""
    try:
        cost = cost_for_usage(tier, usage)
        line = {
            "ts": time.time(), "tier": tier, "model": TIERS.get(tier, ("?",))[0],
            "cost_usd": round(cost, 6), "usage": usage,
            "message_preview": (message_preview or "")[:80],
        }
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return cost
    except Exception:
        return 0.0


def running_total():
    """Sum of all logged turn costs, plus a per-tier breakdown."""
    total = 0.0
    by_tier = {}
    n = 0
    try:
        with open(LOG_PATH) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                total += d.get("cost_usd", 0.0)
                t = d.get("tier", "?")
                by_tier[t] = by_tier.get(t, 0.0) + d.get("cost_usd", 0.0)
                n += 1
    except FileNotFoundError:
        pass
    return {"total_usd": round(total, 5), "turns": n,
            "by_tier": {k: round(v, 5) for k, v in by_tier.items()}}


def main(argv):
    """CLI: classify a message without touching any agent."""
    msg = " ".join(argv)
    tier = classify(msg)
    print(f"{tier}  ({TIERS[tier][0]})")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
