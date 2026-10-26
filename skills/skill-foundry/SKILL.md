---
name: skill-foundry
description: Take a seed skill idea (a name plus the mechanism it computes) through every library gate in order - YAML-safe description, metaphor-to-algorithm BUILD vs FOLD, skill-finder top-hit strength, collision-registry overlap, source-labels on the pitch - and only if all pass, scaffold a folder that meets the house conventions on the first try and record its birth in lineage-ledger; dry run by default, every gate's verdict returned, drain() runs a whole list without stopping. Use this whenever the user asks to make new skills, to use our skills to make skills, to check whether a skill idea already exists before building it, to scaffold a skill folder, or to work through a list of candidate skills until it is drained. Pairs with kingdom-sweep, metaphor-to-algorithm, skill-finder, collision-registry, source-labels, lineage-ledger and skill-health.
---

# skill-foundry

Two of the user's seeds, fused. The first is von Neumann's self-reproducing constructor, a machine that carries a description of itself and builds the copy, crossed with *"use our newly developed skills to make skills"*: the library's conventions are the description, and `scaffold()` is the constructor. The second is *"generate candidates then cull"* crossed with *"do not stop until drained"*: every idea walks the same gates, and the culling uses the tools the 10-15 merge showed were missing at birth time. Most nature-wave skills turned out to duplicate something that already existed.

## The tool (ships with this skill)

`foundry.py` (the pipeline) and `scaffold.py` (the constructor). Both are pure stdlib plus sibling imports. foundry has 11 selftest checks and scaffold has 9.

```
python foundry.py tide-clock "predict harbour tide heights from lunar phase" --pitch "- sailors need it [IMAGINED]"
python foundry.py NAME "mechanism" --pitch "..." --create      # actually scaffold + record the birth
python scaffold.py NAME "One-line description. Use this whenever the user ... Pairs with x." TOOL_NAME [ROOT]
from foundry import found, drain, generate                      # generate = kingdom-sweep grid (optional)
from scaffold import scaffold, validate_description
```

The gates run in this order, and each one's verdict is returned even after a failure:

1. **yaml-safe**: the description is one line, has no `: ` and no ` #`, and contains "Use this whenever".
2. **metaphor**: reduce() must say BUILD. FOLD INTO X stops the idea.
3. **finder**: the top skill-finder hit's score is divided by the query's own IDF weight, and it must stay below 0.6. On the live library a duplicate hurst idea scored 0.91 and a tide idea scored 0.24.
4. **collision**: no library description, and no entry in an optional registry, may have word-shingle Jaccard of 0.4 or more.
5. **source-labels**: the pitch must be claim lines tagged `[REAL: src]`, `[IMAGINED]` or `[FABRICATED]`, with no issues.

Only `dry_run=False` (`--create`) writes anything. It writes the folder through `scaffold()` and a lineage record with operator `skill-foundry`. The scaffold refuses an existing folder and any name that is not kebab-case.

## Uses and limits

- A pass means "not obviously a duplicate". It does not mean "worth building". The pitch and the skeleton tool still need real work, real checks and a real-data run.
- The thresholds are judgement calls set on 2026-10-15. A FOLD verdict names where the idea belongs, so fold it there with an Edit.
- `--create` writes to the real `~/.claude/skills` and the real `LINEAGE.jsonl`. The selftest uses temp copies only.
