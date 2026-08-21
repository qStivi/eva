#!/usr/bin/env python3
"""Rerun only the (label, turn) cells that errored in cloud_results.json, merge
back in, recompute subtotals + grand total. Avoids re-billing successful calls."""
import json, os, pathlib
import eval_cloud as ec

OUT = pathlib.Path(os.environ.get("OUTDIR", "."))
RESULTS_FILE = os.environ.get("RESULTS_FILE", "cloud_results.json")
path = OUT / RESULTS_FILE
results = json.loads(path.read_text())

MODEL_BY_LABEL = {label: (provider, model, price_in, price_out)
                  for provider, model, label, price_in, price_out in ec.MODELS}
PROMPT_BY_KEY = dict(ec.BATTERY)

grand_total = 0.0
for label, entry in results.items():
    if label.startswith("_"):
        continue
    provider, model, price_in, price_out = MODEL_BY_LABEL[label]
    model_total = 0.0
    for key, r in entry["turns"].items():
        if "error" in r:
            print(f"retry [{label}/{key}] ...", flush=True)
            try:
                nr = ec.call(provider, model, PROMPT_BY_KEY[key])
                cost = nr["in_tok"] / 1e6 * price_in + nr["out_tok"] / 1e6 * price_out
                nr["cost_usd"] = round(cost, 6)
                if key == "reasoning":
                    nr["auto_correct"] = ec.REASONING_ANSWER in nr["reply"]
                if key == "format_follow":
                    import re
                    nr["auto_bullets"] = len(re.findall(r"^\s*[-*•]\s+", nr["reply"], re.M))
                entry["turns"][key] = nr
                print(f"  ok  {nr['sec']}s  {nr['in_tok']}in/{nr['out_tok']}out  ${cost:.5f}", flush=True)
            except Exception as e:
                print(f"  still failing: {str(e)[:200]}", flush=True)
        model_total += entry["turns"][key].get("cost_usd", 0.0)
    entry["model_total_usd"] = round(model_total, 5)
    grand_total += model_total
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

results["_grand_total_usd"] = round(grand_total, 5)
path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(f"\nDONE. New grand total: ${grand_total:.5f}", flush=True)
