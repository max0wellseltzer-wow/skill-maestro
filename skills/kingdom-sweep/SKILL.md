---
name: kingdom-sweep
description: Mine a concept for ideas the way the user ordered on 10-13 - sweep it across every kingdom of life and beyond (animals, plants, fungi, protists, bacteria, archaea, viruses, stars, planets, atmosphere and ocean, chemistry, physics, society and economy, software, hardware, mathematics, the imagined) at six stretch levels (literal, functional, structural, abstract, inverted, imaginary) - 102 concrete questions per concept - and keep a coverage ledger of what each mined cell yielded (built / folded / killed / empty), so you can see which kingdoms are exhausted, which were never visited, and where inspiration actually survived. Use this whenever the user asks to draw inspiration from nature, life, the kingdoms, flora and fauna, or "stretch the definition of X", or to generate many skills or ideas from one concept. Pairs with metaphor-to-algorithm (gate each idea before building), novelty-meter (know when to stop), lineage-ledger and wave-yield.
---

# kingdom-sweep

the user, 10-13: *"Model these skills from both the flora and the fauna and all the kingdoms besides and inbetween … stretch the definitions of reproduce … software, hardware, stars … the continued homeostasis of a planet … real, or imagined."* That order has two axes: **where to look** (17 domains) and **how far to stretch** (6 levels). This folds in `stretch-definition` as the second axis.

The 10-14 waves mined this ground without a map, and the 10-15 merge showed the cost: 15 of the 22 merged skills came from those waves. The sweep adds a map, and each cell should pass two gates before anything gets built:
1. `metaphor-to-algorithm`: what is this really, and does the library already have it?
2. `source-labels`: is it real, imagined or fabricated?

Use `novelty-meter` to know when a concept is spent.

## The tool (ships with this skill)

`sweep.py` - pure stdlib, selftest 7/7:

```
from sweep import grid, record, coverage, DOMAINS, LEVELS
grid("homeostasis")                                            # 102 questions
record(ledger, "homeostasis", "Planetary", "functional", "built", name="osmosis")
coverage(ledger, "homeostasis")                                # mined/total, unmined cells, yield per domain
python sweep.py "reproduction"                                 # print the grid
```

## Uses and limits

The grid asks the questions; it doesn't answer them, and most cells honestly come back empty. Record the empty ones too, so the map shows they were visited. Domains and levels are lists, so extend them freely.
