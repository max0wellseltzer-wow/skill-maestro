---
name: collision-registry
description: Append-only JSONL registry of ideas and skills where every new entry is scored against all earlier ones (word-shingle Jaccard) and each collision (score >= threshold) is written down with both ids and the score; register(name, text) returns new, collision (with whom) or exists (idempotent re-register). Use this whenever a new skill, idea or venture is proposed during a generative wave, the user asks "do we already have this?", or you want a permanent record of which ideas duplicated which. Pairs with novelty-meter, skill-finder, lineage-ledger, simhash and minhash.
---

# collision-registry

A brainstorm forgets what it already said; a registry does not. Each registration is compared with every earlier entry on shingles of 1-2 content words, and anything at or above the threshold (default 0.4) is a collision, recorded as its own JSONL line next to the entry. The file is only ever appended to, so the history of "who duplicated whom" survives.

## The tool (ships with this skill)

`collisions.py` - pure stdlib, selftest 8/8:

```
python collisions.py register NAME "what it does..."     # -> new / collision <-> #id name (score)
python collisions.py check NAME "text"                    # dry run, writes nothing
python collisions.py seed-skills [SKILLS_DIR]             # register every SKILL.md description
python collisions.py list [--registry FILE]
from collisions import register, similarity, shingles
register("x", "text", registry=path, threshold=0.4)       # {"status", "id", "collisions": [{id,name,score}]}
```

Default registry: `~/.claude/collision-registry.jsonl`. Same name + same text again returns `exists` with the original collisions and writes nothing. Same name with new text is a new revision. Corrupt lines are skipped and counted by `list`.

## Uses and limits

Exact Jaccard over all entries is fine up to a few thousand short texts. Past that, put simhash or minhash in front as a candidate filter. It measures shared words, not meaning, so two descriptions of the same idea in different vocabulary will not collide, and two different tools that use the same jargon may. Treat a collision as a prompt to look, then decide whether to merge, extend or keep both.

Calibration (measured 2026-10-15 on the 235 live SKILL.md descriptions): long descriptions score low. The closest pair is skills-index vs skill-health at 0.20, and the 99th percentile of all pairs is 0.06. Seeding at the default 0.4 gives 0 collisions. Seeding at `--threshold 0.15` gives 3: pbo-overfit/deflated-sharpe, skill-health/skill-finder and skills-index with both. Use 0.4 for one-line ideas and about 0.15 for full skill descriptions.
