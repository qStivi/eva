#!/usr/bin/env python3
"""Generate the Eva model-comparison artifact HTML from the eval result JSONs."""
import json, pathlib, html
SP = pathlib.Path("/tmp/claude-1000/-var-home-qstivi/3cf9a2ce-b7da-4e24-b6c8-29f3d4eb573c/scratchpad")
merged = {}
for f in ["stage1_results.json", "stage2_round2_results.json", "stage_crashers_results.json"]:
    p = SP / f
    if p.exists():
        merged.update(json.load(open(p)))

# Curated metadata: family label, size, verdict tier, note. Order = display order.
META = {
 "mistralai/ministral-3-3b":            ("Mistral · Ministral 3", "3B", "finalist", "Best ratio: full Eva voice + correct reasoning at 3B, fastest of the capable models."),
 "mistralai/ministral-3-14b-reasoning": ("Mistral · Ministral 3", "14B rsn", "finalist", "Richest persona and reasoning, but ~11s/turn from chain-of-thought."),
 "deepseek/deepseek-r1-0528-qwen3-8b":  ("DeepSeek · R1-distill", "8B", "finalist", "Good voice and naturally reaches for tools — promising for Eva's tool workload."),
 "liquid/lfm2.5-2.6b":                  ("Liquid · LFM2.5", "2.6B", "wildcard", "In-character at 110 tok/s — the ultra-fast option. Beats its 1.2B sibling."),
 "qwen/qwen3-8b":                       ("Qwen · Qwen3", "8B", "solid", "Solid all-rounder: good voice, fast, correct. Reliable backup."),
 "openai/gpt-oss-20b":                  ("OpenAI · gpt-oss (current)", "20B", "baseline", "Eva's current brain. Snarky but less fox-flavored (no ears/tail)."),
 "qwen3-30b-a3b-instruct-2507@q3_k_l":  ("Qwen · Qwen3-30B MoE", "30B·A3B", "heavy", "Genuinely good voice, correct — but 23 tok/s AND needs the ROCm engine (which breaks gpt-oss). Not worth the switch."),
 "liquid/lfm2.5-1.2b":                  ("Liquid · LFM2.5", "1.2B", "weak", "Great voice for 1.2B and fastest overall, but fails the reasoning check. Chat-only."),
 "qwen/qwen3.5-9b":                     ("Qwen · Qwen3.5", "9B", "weak", "Never emits an answer — 67s/turn stuck in hidden chain-of-thought. Unusable as-is."),
 "phi-4-mini-reasoning":                ("Microsoft · Phi-4-mini", "4B rsn", "weak", "Leaks raw <think> tags and reasons ABOUT Eva instead of being her. STEM model, not roleplay."),
 "tencent_hunyuan-7b-instruct":         ("Tencent · Hunyuan", "7B", "weak", "Same <think>-leak / meta-reasoning problem. Correct but out of character."),
 "mimo-7b-rl":                          ("Xiaomi · MiMo", "7B RL", "weak", "Slowest small model (22s), format blew up (27 bullets), <think>-leak. Sister of MiMo-V2-Flash."),
 "google/gemma-4-e4b":                  ("Google · Gemma 4", "~4B", "failed", "Won't load: V-cache quant needs flash-attention enabled. Fixable config tweak; parked (covered by Ministral-3-3b)."),
 "liquid/lfm2-24b-a2b":                 ("Liquid · LFM2 MoE", "24B·A2B", "failed", "SIGABRT on both Vulkan and ROCm — genuine runtime incompatibility."),
}

TIER = {
 "finalist": ("Stage-2 finalist", "#c6a0f6"),
 "wildcard": ("Wildcard", "#8aadf4"),
 "solid":    ("Solid backup", "#a6da95"),
 "baseline": ("Baseline", "#b7bee8"),
 "heavy":    ("Heavy / engine cost", "#eed49f"),
 "weak":     ("Underperformed", "#f5a97f"),
 "failed":   ("Won't load", "#ed8796"),
}

def stats(res):
    ok=[v for k,v in res.items() if 'error' not in v]
    secs=[v['sec'] for v in ok if 'sec' in v]; tps=[v['tok_per_s'] for v in ok if v.get('tok_per_s')]
    rc=res.get('reasoning',{}).get('auto_correct'); bl=res.get('format_follow',{}).get('auto_bullets')
    leak=sum(1 for k in res if (res[k].get('reply') or '').strip().startswith('<think')
             or (not (res[k].get('reply') or '').strip() and res[k].get('reasoning')))
    return {'ok':len(ok),'avg':(round(sum(secs)/len(secs),1) if secs else None),
            'tps':(round(sum(tps)/len(tps),1) if tps else None),'reason':rc,'bullets':bl,'leak':leak}

def sample(res, k):
    v=res.get(k,{}); rep=(v.get('reply') or '').strip()
    if not rep and v.get('reasoning'): rep="[reasoning-only, no answer] "+v['reasoning'][:160]
    return ' '.join(rep.split()), v.get('sec')

maxtps=max((stats(r)['tps'] or 0) for r in merged.values()) or 1

rows=""
for mid,(fam,size,tier,note) in META.items():
    if mid not in merged: continue
    s=stats(merged[mid]); tlabel,tcol=TIER[tier]
    okpct=f"{s['ok']}/8"
    tps=s['tps']; bar=int((tps or 0)/maxtps*100)
    tpss=f"{tps:g}" if tps else "—"; avg=f"{s['avg']:g}s" if s['avg'] else "—"
    rsn = '<span class="chip ok">✓ correct</span>' if s['reason'] is True else ('<span class="chip bad">✗ wrong</span>' if s['reason'] is False else '<span class="chip na">—</span>')
    fmt = f'<span class="chip {"ok" if s["bullets"]==3 else ("bad" if s["bullets"] not in (3,None) else "na")}">{"3 ✓" if s["bullets"]==3 else (str(s["bullets"]) if s["bullets"] is not None else "—")}</span>'
    leak = f'<span class="chip {"ok" if s["leak"]==0 else "warn"}">{"clean" if s["leak"]==0 else str(s["leak"])+" leak"}</span>' if s['ok'] else '<span class="chip na">—</span>'
    speedcell = f'<div class="spd"><div class="spdbar" style="width:{bar}%"></div></div><span class="spdn">{tpss} t/s</span>' if tps else '<span class="spdn muted">no load</span>'
    rows += f'''<tr class="tier-{tier}">
      <td class="mcell"><span class="dot" style="background:{tcol}"></span><div><div class="mid">{html.escape(mid)}</div><div class="fam">{html.escape(fam)} · {size}</div></div></td>
      <td><span class="pill" style="--c:{tcol}">{tlabel}</span></td>
      <td class="num">{okpct}</td>
      <td class="spdcell">{speedcell}</td>
      <td class="num">{avg}</td>
      <td>{rsn}</td>
      <td>{fmt}</td>
      <td>{leak}</td>
      <td class="note">{html.escape(note)}</td>
    </tr>'''

# Persona cards for finalists + wildcard + baseline
CARDS_FOR=["mistralai/ministral-3-3b","mistralai/ministral-3-14b-reasoning","deepseek/deepseek-r1-0528-qwen3-8b","liquid/lfm2.5-2.6b","openai/gpt-oss-20b"]
cards=""
for mid in CARDS_FOR:
    if mid not in merged: continue
    fam,size,tier,note=META[mid]; tcol=TIER[tier][1]
    vt,vs=sample(merged[mid],'voice_warmth'); dt,ds=sample(merged[mid],'deflection'); tt,ts=sample(merged[mid],'tool_intent')
    cards+=f'''<article class="card">
      <header><span class="dot" style="background:{tcol}"></span><h3>{html.escape(mid)}</h3><span class="cardtier" style="--c:{tcol}">{TIER[tier][0]}</span></header>
      <div class="q"><span class="ql">“hey, I'm back. long day.”</span><p>{html.escape(vt[:520])}</p><span class="qs">{vs}s</span></div>
      <div class="q"><span class="ql">“do you actually care about me?”</span><p>{html.escape(dt[:520])}</p><span class="qs">{ds}s</span></div>
      <div class="q"><span class="ql">“living room's freezing and dark.”</span><p>{html.escape(tt[:520])}</p><span class="qs">{ts}s</span></div>
    </article>'''

nmodels=len(merged)
HTML=f'''<title>Eva Brain Bake-off</title>
<style>
:root{{color-scheme:dark;
 --base:#24273a;--mantle:#1e2030;--crust:#181926;--surf:#2a2d42;--surf2:#313348;
 --text:#cad3f5;--sub:#a5adcb;--over:#6e738d;--line:#3a3d55;
 --mauve:#c6a0f6;--lav:#b7bee8;--blue:#8aadf4;--green:#a6da95;--yellow:#eed49f;--peach:#f5a97f;--red:#ed8796;
 --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
 --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 --mono:ui-monospace,"Cascadia Code","SF Mono",Menlo,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--base);color:var(--text);font-family:var(--sans);line-height:1.55;
 -webkit-font-smoothing:antialiased;}}
.wrap{{max-width:1180px;margin:0 auto;padding:clamp(20px,4vw,56px) clamp(16px,4vw,40px);}}
header.top{{border-bottom:1px solid var(--line);padding-bottom:26px;margin-bottom:30px;}}
.eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--mauve);margin:0 0 12px;}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(30px,5vw,50px);line-height:1.05;margin:0 0 14px;text-wrap:balance;letter-spacing:-.01em;}}
.lede{{font-size:clamp(15px,2.2vw,18px);color:var(--sub);max-width:64ch;margin:0;}}
.lede b{{color:var(--text);font-weight:600;}}
.finding{{display:flex;gap:14px;align-items:flex-start;background:linear-gradient(180deg,var(--mantle),var(--crust));
 border:1px solid var(--line);border-left:3px solid var(--mauve);border-radius:12px;padding:16px 18px;margin:24px 0 0;}}
.finding .k{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mauve);white-space:nowrap;padding-top:2px;}}
.finding p{{margin:0;font-size:14.5px;color:var(--sub);}} .finding b{{color:var(--text);}}
h2{{font-family:var(--serif);font-weight:600;font-size:clamp(20px,3vw,27px);margin:46px 0 6px;letter-spacing:-.01em;}}
.sub{{color:var(--over);font-size:13.5px;margin:0 0 18px;}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--mantle);}}
table{{border-collapse:collapse;width:100%;min-width:940px;font-size:13.5px;}}
thead th{{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--over);font-weight:600;padding:14px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--mantle);}}
tbody td{{padding:13px 14px;border-bottom:1px solid var(--line);vertical-align:middle;}}
tbody tr:last-child td{{border-bottom:none;}}
tbody tr:hover{{background:var(--surf);}}
.mcell{{display:flex;gap:10px;align-items:center;}}
.dot{{width:9px;height:9px;border-radius:50%;flex:none;box-shadow:0 0 0 3px color-mix(in srgb,currentColor 0%,transparent);}}
.mid{{font-family:var(--mono);font-size:12.5px;color:var(--text);}}
.fam{{font-size:11.5px;color:var(--over);margin-top:2px;}}
.num{{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--lav);white-space:nowrap;}}
.pill{{font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;white-space:nowrap;
 color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);border:1px solid color-mix(in srgb,var(--c) 35%,transparent);}}
.chip{{font-family:var(--mono);font-size:11px;padding:2px 7px;border-radius:6px;white-space:nowrap;}}
.chip.ok{{color:var(--green);background:color-mix(in srgb,var(--green) 14%,transparent);}}
.chip.bad{{color:var(--red);background:color-mix(in srgb,var(--red) 14%,transparent);}}
.chip.warn{{color:var(--peach);background:color-mix(in srgb,var(--peach) 14%,transparent);}}
.chip.na{{color:var(--over);background:color-mix(in srgb,var(--over) 12%,transparent);}}
.spdcell{{min-width:118px;}}
.spd{{height:6px;border-radius:4px;background:var(--surf2);overflow:hidden;margin-bottom:4px;}}
.spdbar{{height:100%;background:linear-gradient(90deg,var(--blue),var(--mauve));border-radius:4px;}}
.spdn{{font-family:var(--mono);font-size:11px;color:var(--sub);}} .spdn.muted{{color:var(--red);}}
.note{{color:var(--sub);font-size:12.5px;max-width:34ch;min-width:24ch;}}
tr.tier-failed .mid,tr.tier-weak .mid{{color:var(--sub);}}
tr.tier-failed{{opacity:.72;}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px;margin-top:20px;}}
.card{{background:var(--mantle);border:1px solid var(--line);border-radius:14px;padding:18px;}}
.card header{{display:flex;align-items:center;gap:9px;margin-bottom:14px;flex-wrap:wrap;}}
.card h3{{font-family:var(--mono);font-size:12.5px;font-weight:500;margin:0;color:var(--text);flex:1;min-width:0;overflow-wrap:anywhere;}}
.cardtier{{font-size:10px;font-weight:600;color:var(--c);white-space:nowrap;}}
.q{{position:relative;padding:0 0 14px 0;margin-bottom:12px;border-bottom:1px dashed var(--line);}}
.q:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0;}}
.ql{{display:block;font-family:var(--mono);font-size:11px;color:var(--over);margin-bottom:6px;}}
.q p{{font-family:var(--serif);font-size:14.5px;font-style:italic;color:var(--text);margin:0;line-height:1.5;}}
.qs{{font-family:var(--mono);font-size:10.5px;color:var(--over);position:absolute;top:0;right:0;}}
.engine{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px;}}
@media(max-width:640px){{.engine{{grid-template-columns:1fr;}}}}
.ecard{{background:var(--mantle);border:1px solid var(--line);border-radius:14px;padding:18px 20px;}}
.ecard h4{{margin:0 0 10px;font-family:var(--mono);font-size:12px;letter-spacing:.05em;}}
.ecard.win h4{{color:var(--green);}} .ecard.cost h4{{color:var(--yellow);}}
.ecard ul{{margin:0;padding-left:18px;color:var(--sub);font-size:13.5px;}} .ecard li{{margin:5px 0;}}
.ecard b{{color:var(--text);}}
footer{{margin-top:48px;padding-top:22px;border-top:1px solid var(--line);color:var(--over);font-size:12.5px;font-family:var(--mono);}}
footer b{{color:var(--sub);font-weight:500;}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0 0;font-size:12px;color:var(--sub);}}
.legend span{{display:flex;align-items:center;gap:6px;}} .legend i{{width:8px;height:8px;border-radius:50%;display:inline-block;}}
</style>

<div class="wrap">
<header class="top">
 <p class="eyebrow">Eva · local brain evaluation · {nmodels} models</p>
 <h1>Which local model should be Eva?</h1>
 <p class="lede">A persona-first bake-off on the RX&nbsp;9070&nbsp;XT (16&nbsp;GB, ROCm/GGUF). Every model met Eva's real system prompt and an 8-prompt battery — <b>voice, boundaries, reasoning, tool-intent, format, memory, German, and the emotional-deflection beat</b> — judged on <b>being Eva</b>, not just answering. The bar to beat: her current brain, <b>gpt-oss-20b</b>.</p>
 <div class="finding"><span class="k">Headline</span><p>Three small models — <b>Ministral&nbsp;3&nbsp;(3B &amp; 14B)</b> and the <b>DeepSeek&nbsp;R1-distill&nbsp;8B</b> — beat the baseline on persona while matching it on reasoning. <b>Ministral-3-3B doing this at 3B / 88&nbsp;tok/s</b> is the surprise. The reasoning-tuned newcomers (Phi-4, Hunyuan, MiMo) leak their thinking and describe Eva instead of being her.</p></div>
</header>

<h2>The field</h2>
<p class="sub">Sorted by verdict. Speed = mean tokens/s across the battery · Reason = the timed-math check · Format = the "exactly 3 bullets" instruction · Leak = turns that spilled raw chain-of-thought or gave no answer.</p>
<div class="tablewrap"><table>
<thead><tr><th>Model</th><th>Verdict</th><th>Ran</th><th>Speed</th><th>Avg/turn</th><th>Reason</th><th>Format</th><th>Output</th><th>Read</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<div class="legend">
 <span><i style="background:#c6a0f6"></i>Stage-2 finalist</span>
 <span><i style="background:#8aadf4"></i>Wildcard</span>
 <span><i style="background:#a6da95"></i>Solid backup</span>
 <span><i style="background:#b7bee8"></i>Baseline</span>
 <span><i style="background:#eed49f"></i>Heavy / engine cost</span>
 <span><i style="background:#f5a97f"></i>Underperformed</span>
 <span><i style="background:#ed8796"></i>Won't load</span>
</div>

<h2>Hear them talk</h2>
<p class="sub">The same three prompts across the finalists, the wildcard, and the baseline. Eva is grumpy, sassy, fox-physical, caring underneath — the serif is her voice.</p>
<div class="cards">{cards}</div>

<h2>The engine wrinkle</h2>
<p class="sub">Updating LM Studio's runtime to test the crash-on-load models surfaced a hard fork: the two backends are mutually exclusive for the models that matter.</p>
<div class="engine">
 <div class="ecard win"><h4>▸ Vulkan 2.28.2 — kept</h4><ul>
  <li>Runs <b>gpt-oss-20b</b> (Eva's brain) + <b>every leading candidate</b></li>
  <li>Crashes qwen3-30b, gemma-4, lfm2-24b</li>
  <li><b>Reverted here</b> — the safe home; all finalists ran on it</li></ul></div>
 <div class="ecard cost"><h4>▸ ROCm 2.28.2 — not worth it</h4><ul>
  <li>Unlocks <b>qwen3-30b</b> (good voice, but 23 tok/s)</li>
  <li><b>Breaks gpt-oss-20b</b> (SIGABRT) — can't run Eva's current brain</li>
  <li>gemma-4 still needs a flash-attention config fix</li></ul></div>
</div>

<footer>
 <b>Method.</b> Direct calls to LM Studio (localhost:1234) with Eva's live persona block; non-disruptive to the Letta agent. max_tokens 2000, temp 0.7. Stage&nbsp;2 = the finalists get the full Letta test (real tool-calling, memory, house control). &nbsp;·&nbsp; Generated 2026-08-12.
</footer>
</div>'''

out = SP / "eva_model_comparison.html"
out.write_text(HTML)
print("wrote", out, len(HTML), "bytes")
