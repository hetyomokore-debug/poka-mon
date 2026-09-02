#!/usr/bin/env python3
"""Generate .jig/contract_ids.txt from jig.json.

NAMAMONO dogfooding: the list of contract ids is never maintained by hand. It is regenerated here,
and the pr-tier gate fails if the committed file differs from the regenerated one.
Usage: python3 tools/gen_contract_ids.py <out> [config=jig.json]
"""
import json, sys

out = sys.argv[1]
cfg = sys.argv[2] if len(sys.argv) > 2 else "jig.json"
ids = sorted(c["id"] for c in json.load(open(cfg, encoding="utf-8")).get("contracts", []))
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(ids) + "\n")
