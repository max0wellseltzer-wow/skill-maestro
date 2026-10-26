---
name: lineage-ledger
description: Keep every skill's family tree - one append-only birth record per skill with its parents, the operator that made it (cross, split, composite, merge, essentials-filter...), the user's prompt that caused it (quoted, dated) and WHO chose it (the user's order or Claude's own taste) - with ancestors/descendants walks, a list of skills that have no birth record, and the the user-vs-Claude chooser share. Use this whenever a new skill is born, when the user asks where a skill came from or what it descends from, when auditing a generative wave, or before merging (to see which skills share parents). Pairs with prompt-genealogy, cross-breed, wave-yield and collision-registry.
---

# lineage-ledger

This is the forward record of what `prompt-genealogy` had to dig up by hand on 10-16: which prompt caused which skill, and from which parents. The **chooser** field matters. After the user said *"skills that simply fascinate you"* (10-14), the choices became mine, and that's where most of the later duplicates came from. A lineage that says who chose makes that pattern visible.

## The tool (ships with this skill)

`lineage.py` - pure stdlib, selftest 6/6:

```
from lineage import record, ancestors, descendants, unrecorded, chooser_share
record(ledger, "token-thrift", parents=[], operator="essentials-filter",
       prompt="stop wasting tokens dude", prompt_date="2026-10-15", chooser="max")
ancestors(ledger, "finish-everything"); unrecorded(ledger, skills_root)
```

- The ledger is append-only. A second birth record for the same skill is refused, so put corrections in a new note record.

## Prompt attribution (merged from prompt-attribution)

`shift(ledger, at="2026-10-14T00:55", field="chooser")` compares the mix of births before and after a prompt's date: chooser, operator, or any field. It's the honest offline version of "which phrase caused what". It shows *what changed* after the 10-14 "skills that simply fascinate you", but it's correlational. Proving the phrase alone caused the change would mean re-running the prompt without it.

## Uses and limits

It starts empty: the earlier library has no records yet. `prompt-genealogy` can backfill them from the transcripts. A record is only as honest as the person writing it, so quote the user's words and never paraphrase.
