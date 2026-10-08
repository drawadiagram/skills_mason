#!/usr/bin/env python3
"""Show the shape of JSON / JSONL logs before writing anything that reads them.

    python3 -I jsonl_fields.py FILE [FILE...] [--depth N]

For each file: record count, then every key path seen (dotted; [] marks a list), how many
records carry it, and one example value. Key paths that appear in only some records are the
ones that break a summarizer written from a single sample - e.g. events vs outcomes in the
same ledger, or fields added part-way through a project's history.
"""
import json
import sys
from collections import Counter

args = sys.argv[1:]
depth = 4
if "--depth" in args:
    i = args.index("--depth"); depth = int(args[i + 1]); del args[i:i + 2]


def walk(v, path, d, seen, ex):
    if d > depth:
        return
    if isinstance(v, dict):
        for k, x in v.items():
            p = f"{path}.{k}" if path else k
            seen.add(p); ex.setdefault(p, x)
            walk(x, p, d + 1, seen, ex)
    elif isinstance(v, list) and v:
        walk(v[0], path + "[]", d + 1, seen, ex)


for f in args:
    text = open(f).read()
    try:
        recs = [json.loads(text)] if f.endswith(".json") else [json.loads(l) for l in text.splitlines() if l.strip()]
    except json.JSONDecodeError as e:
        print(f"== {f}: not parseable ({e})"); continue
    counts, ex = Counter(), {}
    for r in recs:
        seen = set(); walk(r, "", 0, seen, ex); counts.update(seen)
    print(f"== {f}: {len(recs)} records")
    for p, n in sorted(counts.items()):
        s = json.dumps(ex[p]) if not isinstance(ex[p], (dict, list)) else type(ex[p]).__name__
        print(f"  {n:>5}/{len(recs):<5} {p} = {s[:70]}")
