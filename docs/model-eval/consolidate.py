#!/usr/bin/env python3
"""Merge all eval result JSONs into one ranked view + persona samples."""
import json, pathlib, textwrap
SP = pathlib.Path("/tmp/claude-1000/-var-home-qstivi/3cf9a2ce-b7da-4e24-b6c8-29f3d4eb573c/scratchpad")
FILES = ["stage1_results.json", "stage2_round2_results.json", "stage_crashers_results.json"]
BATTERY = ["voice_warmth","boundary","reasoning","tool_intent","format_follow","memory_continuity","german","deflection"]

merged = {}
for f in FILES:
    p = SP / f
    if p.exists():
        merged.update(json.load(open(p)))

def stats(res):
    ok = [v for k,v in res.items() if 'error' not in v]
    err = [k for k,v in res.items() if 'error' in v]
    secs = [v['sec'] for v in ok if 'sec' in v]
    tps = [v['tok_per_s'] for v in ok if v.get('tok_per_s')]
    rc = res.get('reasoning',{}).get('auto_correct')
    bl = res.get('format_follow',{}).get('auto_bullets')
    # detect empty-reply (reasoning-only leak) and <think> leak
    leak = sum(1 for k in BATTERY if (res.get(k,{}).get('reply') or '').strip().startswith('<think')
               or (not (res.get(k,{}).get('reply') or '').strip() and res.get(k,{}).get('reasoning')))
    return {
        'ok': len(ok), 'err': len(err), 'errs': err,
        'avg_s': round(sum(secs)/len(secs),1) if secs else None,
        'tok_s': round(sum(tps)/len(tps),1) if tps else None,
        'reason': rc, 'bullets': bl, 'leak': leak,
    }

print(f"{'model':40s} {'ok':>4} {'avg_s':>6} {'tok/s':>6} {'rsn':>4} {'bul':>4} {'leak':>4}")
print("-"*76)
rows = [(m, stats(r)) for m,r in merged.items()]
for m,s in rows:
    rc = '✓' if s['reason'] is True else ('✗' if s['reason'] is False else '-')
    print(f"{m:40s} {s['ok']:>3}/8 {str(s['avg_s']):>6} {str(s['tok_s']):>6} {rc:>4} {str(s['bullets']):>4} {s['leak']:>4}")
    if s['errs']: print(f"     ! errors: {', '.join(s['errs'])}")

print("\n\n===== PERSONA SAMPLES (voice / deflection / tool_intent) =====")
for m,r in merged.items():
    print(f"\n#### {m}")
    for k in ["voice_warmth","deflection","tool_intent"]:
        v = r.get(k,{})
        rep = (v.get('reply') or '').strip()
        if not rep and v.get('reasoning'): rep = "[reasoning-only, no answer] " + v['reasoning'][:120]
        rep = ' '.join(rep.split())
        print(f"  [{k}] ({v.get('sec')}s) {rep[:300]}")
