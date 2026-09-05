#!/usr/bin/env python3
"""Generate .jig/contract_ids.txt from jig.json.

NAMAMONO dogfooding: the list of contract ids is never maintained by hand. It is regenerated here,
and the pr-tier gate fails if the committed file differs from the regenerated one.
Accepts the same `contracts` forms as hakari/sakigaki: inline entries and/or registry file references.
Usage: python3 tools/gen_contract_ids.py <out> [config=jig.json]
"""
import json, os, sys

out = sys.argv[1]
cfg_path = sys.argv[2] if len(sys.argv) > 2 else "jig.json"
root = os.path.dirname(cfg_path) or "."
src = json.load(open(cfg_path, encoding="utf-8")).get("contracts", [])
ids = []
for entry in ([src] if isinstance(src, str) else src):
    items = json.load(open(os.path.join(root, entry), encoding="utf-8")).get("contracts", []) if isinstance(entry, str) else [entry]
    for c in items:
        prod = c.get("producer", "")
        ids.append(c.get("id") or c.get("name") or (prod.get("file", "") if isinstance(prod, dict) else prod))
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(ids)) + "\n")
