---
name: metaphor-to-algorithm
description: Before building a metaphor-named skill (biology, physics, chemistry names), reduce it to the plain algorithm it names and check whether the library already has it - a curated table (refractory->cooldown/token bucket, percolation->union-find threshold, catalyst->memoization, succession->staged ladder with setbacks, ... seeded from the 2026-10-15 merges) plus algorithm cue words in the description, then a skill-finder search; verdict BUILD (nothing close) or FOLD INTO <skill>. Use this whenever the user or a generative wave proposes a new skill with a metaphor name, asks "do we already have this?", plans a merge of near-duplicate skills, or a skill pitch describes a mechanism by analogy. Pairs with skill-finder, source-labels, cross-breed and pollinator-routing.
---

# metaphor-to-algorithm

On 2026-10-15 fourteen metaphor-named skills were merged away because each was an algorithm the library already had under a plainer name (refractory was a cooldown, catalyst was memoization, convection was neighbour diffusion). A metaphor is a good way to find an idea and a bad way to file it. This step makes the reduction explicit and checks the library before anything is built.

## The tool (ships with this skill)

`metaphor.py` + `metaphor_table.json` - stdlib + skill-finder, selftest 9/9:

```
from metaphor import reduce, render
print(render(reduce("chemotaxis", "move toward the strongest signal gradient")))
python metaphor.py "chemotaxis: move toward the strongest signal gradient"
python metaphor.py --selftest
```

- Candidates: table rows hit by the name or any hyphen part of it (`buffer-pool` hits `buffer`), then description words matching the `cues` map (stemmed).
- Library check: skill-finder ranks skills for the algorithm text; `coverage` = share of one algorithm phrase's IDF weight a skill's name+description contains (best over candidates).
- Verdict: FOLD INTO the table's recorded fold target if it is in the library; else FOLD INTO the best skill with coverage >= 0.5; else BUILD. A skill is never folded into itself.

Live run: "chemotaxis: move toward the strongest signal gradient" -> gradient ascent / greedy hill-climbing + argmax; anneal covers 52% -> FOLD INTO anneal (mutation-forge 38%).

## Stress-test the analogy (merged from analogy-stress-test)

After `reduce()` says BUILD, run `stress(analogy)` before relying on the metaphor. It needs three things: an element mapping (which part of the source is which part of the target), at least one place the analogy **breaks**, and one **testable prediction** that uses only mapped elements. "Reversals follow the moon" fails, because the moon was never mapped to anything in markets. That's the metaphor doing the work instead of the mechanism.

## Uses and limits

Add a row to the table each time a metaphor skill is merged or reduced, so the next wave hits it by lookup. Limits: cue words are a short hand-curated list and coverage is word overlap, not meaning - a FOLD verdict is a prompt to read the target skill, and a BUILD verdict means "no close words", not "provably new". The threshold (0.5) is a judgement call; pass `threshold=` to tighten.
