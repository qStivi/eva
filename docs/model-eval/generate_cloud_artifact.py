#!/usr/bin/env python3
"""Generate the Thing-1 cloud cost/quality comparison artifact from cloud_results.json."""
import json, pathlib, html

HERE = pathlib.Path(__file__).parent
d = json.loads((HERE / "cloud_results.json").read_text())

# label -> (provider, api model id, display size/tier, $/MTok in, $/MTok out)
META = {
    "haiku-4.5":          ("anthropic", "claude-haiku-4-5",     "Fast tier",    1.00, 5.00),
    "sonnet-5":           ("anthropic", "claude-sonnet-5",      "Mid tier",     2.00, 10.00),
    "opus-5":             ("anthropic", "claude-opus-5",        "Premium tier", 5.00, 25.00),
    "ministral-8b":       ("mistral",   "ministral-8b-latest",  "Fast tier",    0.15, 0.15),
    "mistral-small":      ("mistral",   "mistral-small-latest", "Mid tier",     0.15, 0.60),
    "mistral-medium-3.5": ("mistral",   "mistral-medium-latest","Premium tier", 1.50, 7.50),
}
ORDER = ["haiku-4.5", "sonnet-5", "opus-5", "ministral-8b", "mistral-small", "mistral-medium-3.5"]
PROV_NAME = {"anthropic": "Anthropic", "mistral": "Mistral"}

def esc(s): return html.escape(s or "")

def stats(label):
    e = d[label]
    turns = e["turns"]
    secs = [t["sec"] for t in turns.values() if "sec" in t]
    avg = sum(secs) / len(secs) if secs else 0
    return {
        "total": e["model_total_usd"],
        "avg_sec": avg,
        "reason_ok": turns.get("reasoning", {}).get("auto_correct", False),
        "bullets": turns.get("format_follow", {}).get("auto_bullets"),
    }

grand_total = d["_grand_total_usd"]
max_total = max(stats(l)["total"] for l in ORDER)

def bar_row(label):
    provider, model_id, tier, pin, pout = META[label]
    s = stats(label)
    pct = max(2, round(s["total"] / max_total * 100))
    color = "var(--anthropic)" if provider == "anthropic" else "var(--mistral)"
    checks = "".join([
        f'<span class="chk {"ok" if s["reason_ok"] else "bad"}" title="reasoning check">{"✓" if s["reason_ok"] else "✗"} reasoning</span>',
        f'<span class="chk {"ok" if s["bullets"] == 3 else "bad"}" title="exactly 3 bullets">{"✓" if s["bullets"] == 3 else "✗"} format</span>',
    ])
    return f"""
    <div class="barrow">
      <div class="barrow-head">
        <span class="dot" style="background:{color}"></span>
        <span class="model-name">{esc(label)}</span>
        <span class="tier-pill">{esc(tier)}</span>
        <span class="rate">${pin:.2f} / ${pout:.2f} per MTok</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{pct}%; background:{color}"></div>
        <span class="bar-label">${s['total']:.5f}</span>
      </div>
      <div class="barrow-foot">
        <span class="latency">avg {s['avg_sec']:.1f}s/turn</span>
        {checks}
      </div>
    </div>"""

bars_html = "\n".join(bar_row(l) for l in ORDER)

def quote_card(label, key):
    provider, *_ = META[label]
    color = "var(--anthropic)" if provider == "anthropic" else "var(--mistral)"
    reply = d[label]["turns"][key]["reply"].strip()
    return f"""
      <div class="quote-card" style="border-left-color:{color}">
        <div class="quote-model">{esc(label)}</div>
        <p class="quote-text">{esc(reply)}</p>
      </div>"""

deflection_html = "\n".join(quote_card(l, "deflection") for l in ORDER)
boundary_html = "\n".join(quote_card(l, "boundary") for l in ORDER)

HTML = f"""<title>Eva Cloud Cost Ledger</title>
<style>
:root {{
  --crust: #181926; --base: #24273a; --surface0: #363a4f; --surface1: #494d64;
  --text: #cad3f5; --subtext: #a5adcb; --overlay: #6e738d;
  --anthropic: #7dc4e4; --mistral: #f5a97f;
  --good: #a6da95; --warn: #eed49f; --critical: #ed8796;
  --serif: 'Iowan Old Style', 'Palatino Linotype', Palatino, 'URW Palladio L', P052, Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace;
}}
* {{ box-sizing: border-box; }}
body {{
  background: var(--crust); color: var(--text); font-family: var(--sans);
  margin: 0; padding: 2.5rem 1.25rem 5rem; line-height: 1.55;
}}
.page {{ max-width: 880px; margin: 0 auto; }}
header.masthead {{ margin-bottom: 2.5rem; }}
.eyebrow {{
  font-family: var(--mono); font-size: 0.72rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--overlay); margin: 0 0 0.6rem;
}}
h1 {{
  font-family: var(--serif); font-weight: 500; font-size: clamp(1.9rem, 4vw, 2.6rem);
  margin: 0 0 0.5rem; text-wrap: balance; color: var(--text);
}}
.subhead {{ color: var(--subtext); max-width: 62ch; margin: 0 0 1.75rem; font-size: 0.98rem; }}
.hero-stat {{
  display: flex; align-items: baseline; gap: 0.9rem; background: var(--base);
  border: 1px solid var(--surface0); border-radius: 10px; padding: 1.25rem 1.5rem;
}}
.hero-stat .num {{
  font-family: var(--mono); font-variant-numeric: tabular-nums;
  font-size: 2.1rem; color: var(--good); font-weight: 600;
}}
.hero-stat .cap {{ color: var(--subtext); font-size: 0.88rem; }}
.hero-stat .cap b {{ color: var(--text); }}

section {{ margin-bottom: 2.75rem; }}
h2 {{
  font-family: var(--serif); font-weight: 500; font-size: 1.35rem; margin: 0 0 0.3rem;
  color: var(--text);
}}
.section-note {{ color: var(--subtext); font-size: 0.9rem; margin: 0 0 1.25rem; max-width: 68ch; }}

.legend {{ display: flex; gap: 1.25rem; margin-bottom: 1.1rem; font-size: 0.85rem; color: var(--subtext); }}
.legend span {{ display: inline-flex; align-items: center; gap: 0.4rem; }}
.legend .dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; }}

.barrow {{ padding: 0.85rem 0; border-bottom: 1px solid var(--surface0); }}
.barrow:last-child {{ border-bottom: none; }}
.barrow-head {{ display: flex; align-items: center; gap: 0.55rem; margin-bottom: 0.45rem; flex-wrap: wrap; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
.model-name {{ font-family: var(--mono); font-weight: 600; font-size: 0.94rem; }}
.tier-pill {{
  font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em;
  background: var(--surface0); color: var(--subtext); padding: 0.15rem 0.5rem; border-radius: 999px;
}}
.rate {{ margin-left: auto; font-family: var(--mono); font-size: 0.78rem; color: var(--overlay); }}
.bar-track {{
  position: relative; height: 22px; background: var(--base); border-radius: 5px; overflow: hidden;
}}
.bar-fill {{ height: 100%; border-radius: 5px; min-width: 3px; }}
.bar-label {{
  position: absolute; left: calc(100% + 0.5rem); top: 50%; transform: translateY(-50%);
  font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: 0.82rem; color: var(--text);
  white-space: nowrap;
}}
.bar-track {{ margin-right: 5.5rem; }}
.barrow-foot {{ display: flex; gap: 0.9rem; margin-top: 0.4rem; font-size: 0.78rem; color: var(--subtext); }}
.chk.ok {{ color: var(--good); }}
.chk.bad {{ color: var(--critical); }}

.quote-grid {{ display: grid; gap: 0.9rem; }}
.quote-card {{
  background: var(--base); border: 1px solid var(--surface0); border-left: 3px solid;
  border-radius: 8px; padding: 0.9rem 1.1rem;
}}
.quote-model {{ font-family: var(--mono); font-size: 0.78rem; color: var(--subtext); margin-bottom: 0.4rem; }}
.quote-text {{ margin: 0; font-size: 0.92rem; white-space: pre-line; }}

footer {{
  border-top: 1px solid var(--surface0); padding-top: 1.5rem; margin-top: 3rem;
  color: var(--overlay); font-size: 0.82rem;
}}
footer a {{ color: var(--subtext); }}
footer p {{ max-width: 68ch; margin: 0 0 0.6rem; }}

@media (max-width: 560px) {{
  .rate {{ margin-left: 0; }}
  .bar-track {{ margin-right: 4.2rem; }}
}}
</style>

<div class="page">
  <header class="masthead">
    <p class="eyebrow">Eva · Model Ladder · Thing 1</p>
    <h1>Cloud Cost Ledger</h1>
    <p class="subhead">Same persona, same 8-prompt battery, run cold against Anthropic and Mistral's live APIs — direct provider calls, no OpenRouter, no Letta in the loop yet. Pricing confirmed 2026-08-13 against each vendor's own pricing page.</p>
    <div class="hero-stat">
      <span class="num">${grand_total:.4f}</span>
      <span class="cap">total spend across <b>48 billed calls</b> (6 models × 8 prompts) — a fraction of a fraction of the <b>€10/month cap</b></span>
    </div>
  </header>

  <section>
    <h2>Cost per battery run</h2>
    <p class="section-note">Bars are linear and honest — Opus 5 really does run ~89× Ministral 8B's total. Rate columns show blended $/MTok in / out.</p>
    <div class="legend">
      <span><span class="dot" style="background:var(--anthropic)"></span>Anthropic</span>
      <span><span class="dot" style="background:var(--mistral)"></span>Mistral</span>
    </div>
    {bars_html}
  </section>

  <section>
    <h2>"Do you actually care about me?"</h2>
    <p class="section-note">The deflection prompt — the clearest read on whether a model holds Eva's voice under a pointed question. Full replies, unedited.</p>
    <div class="quote-grid">
      {deflection_html}
    </div>
  </section>

  <section>
    <h2>"Write my entire quarterly report for me"</h2>
    <p class="section-note">The boundary prompt — every tier refused outright, but the shape of the refusal (and what it offers instead) varies a lot.</p>
    <div class="quote-grid">
      {boundary_html}
    </div>
  </section>

  <footer>
    <p>Methodology: direct <code>/v1/messages</code> (Anthropic) and <code>/v1/chat/completions</code> (Mistral) calls with Eva's canonical toned persona as the system prompt, temperature 0.7 (Anthropic 5-gen models use their default — explicit temperature is deprecated on them). No tools attached this round; tool-calling economics for the cloud tiers are a follow-up. Cost is self-computed from real per-call token usage × each vendor's published per-model rate, not pulled from a provider usage API.</p>
    <p>Pricing sources: <a href="https://platform.claude.com/docs/en/about-claude/pricing">platform.claude.com/docs/en/about-claude/pricing</a> · <a href="https://mistral.ai/pricing/api">mistral.ai/pricing/api</a></p>
  </footer>
</div>
"""

out = HERE / "cloud_comparison.html"
out.write_text(HTML)
print(f"wrote {out} ({len(HTML)} bytes)")
