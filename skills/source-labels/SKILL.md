---
name: source-labels
description: Tag every idea or claim by its origin - [REAL - source] (observed or read, source required), [IMAGINED] (design, guess, extrapolation) or [FABRICATED] (invented on purpose for inspiration, an analogy or made-up scenario, never evidence) - and check a document for unlabelled claims, REAL without a source, and a fabricated analogy later used as a premise. Use this whenever brainstorming from real, imagined or wholesale-fabricated inspiration (the user, 10-13), writing idea lists, plans or skill pitches that mix observation with invention, and before an idea list becomes a decision or a report. Pairs with research-integrity labels, question-not-ruling and metaphor-to-algorithm.
---

# source-labels

the user opened the gates on 10-13: *"Use all forms of production for your inspiration be they real, or imagined, or whole sale fabricated."* That's a powerful generator, but only if the three never get mixed up later. A tide analogy that sparked a skill must not show up two weeks on as "markets reverse because of tides".

1. Write ideas as list items, each ending in a tag: `[REAL: wave-yield output]`, `[IMAGINED]` or `[FABRICATED]`.
2. Run the checker before an idea list feeds a plan, a decision or a message to the user.
3. A FABRICATED item can inspire a test. It can never be the premise of a claim.

## The tool (ships with this skill)

`source_labels.py` - pure stdlib, selftest 6/6:

```
from source_labels import check
check(markdown_text)     # claims, counts per label, issues, ok
python source_labels.py ideas.md
```

## Uses and limits

Only list items count as claims, and the premise check is word overlap, so read what it flags. This skill is about where an idea came from. Which of the user's clauses are orders and which are questions is `question-not-ruling`'s job.
