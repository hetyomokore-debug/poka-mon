---
name: pokayoke
description: A rule written in a document is a sign; a setting, hook, or deny-list that makes it hold is a lock. Every important rule needs both, paired, and checked. Use when adding or editing a rule, policy, "never do X", CLAUDE.md / AGENTS.md guidance, or permission settings; also as a commit-tier gate to catch "sign without lock" (the most dangerous state: everyone believes they are protected).
---

# POKAYOKE — "……It doesn't fit."

A poka-yoke is a part that physically cannot be inserted the wrong way. Writing "mind the orientation" in the manual is a sign. Making the wrong orientation not fit is a lock. This jig checks that both exist.

## Register a pairing

```json
"pairings": [
  {
    "name": "no-external-hosting",
    "declaration": { "file": "CLAUDE.md",             "contains": "Do not publish deliverables externally" },
    "enforcement":  { "file": ".claude/settings.json", "contains": "\"Artifact\"" }
  }
]
```

`declaration` is where humans read the rule. `enforcement` is what makes it hold without anyone reading. `contains` is optional; without it, file existence is enough.

## Run

```
python3 <plugin>/skills/pokayoke/scripts/pokayoke.py
python3 <plugin>/skills/pokayoke/scripts/pokayoke.py --selftest
```

| Result | Meaning | What to do |
|---|---|---|
| `OK` | sign and lock both present | nothing |
| `SIGN WITHOUT LOCK` | rule is written, nothing enforces it | add the enforcement now — this is the state the rule was meant to prevent |
| `LOCK WITHOUT SIGN` | something is enforced, nobody knows why | write the declaration, or retire the lock via YAMEDOKI |

## When adding a rule

Add the declaration and the enforcement **in the same change**, then register the pairing. A rule that ships as a sign only will be believed and not obeyed.

Exit codes: `0` intact · `1` broken pairing · `2` config error.
