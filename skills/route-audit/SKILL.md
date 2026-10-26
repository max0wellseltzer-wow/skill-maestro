---
name: route-audit
description: Test the skill router against itself - ask skill-finder about each skill's own body pitch (text it never indexed, with the skill's name words removed) and report top-1 / top-3 accuracy, the skills it can't find, and every confusion A -> B (A's need is described in B's words - an overlap to merge or a description to sharpen). Use this whenever the user asks whether the right skill gets picked, after adding or merging skills, when two skills feel redundant, or when a skill never seems to trigger. self-attacking-referee applied to skill-finder; pairs with skill-finder, skills-index and skill-health.
---

# route-audit

A router that is only ever tested on the words it indexed will always look perfect. This audit uses each skill's own plain-English pitch from its body, which the router never saw, with the skill's name words removed. It then checks whether the router finds its way back to that skill.

## The tool (ships with this skill)

`route_audit.py` - pure stdlib (uses skill-finder), selftest 6/6:

```
python route_audit.py              # audit ~/.claude/skills
python route_audit.py <root> --top 5
```

- First run (2026-10-15, 210 skills): top-1 79%, top-3 88%. 26 skills never reached the top 3, mostly older workflow skills whose frontmatter uses different words from their body. Confusions such as forward-score ↔ sprt-sequential and ewma-vol ↔ vol-targeting point to near-overlaps.

## Reading a miss honestly

A miss doesn't automatically mean a bad description. Many workflow skills open their body with the scar that earned them ("Repeated about 15 times…", "Each line is an incident"), and no one phrases a need that way. On 2026-10-16, most of the 33 misses were story-style pitches like these. Fix a miss only when the *description* lacks the words the need is really asked in. Rewriting descriptions just to beat this audit is Goodhart's law: optimising the metric instead of the thing it measures.

## Uses and limits

The router is word-based (TF-IDF), so a confusion can mean a real overlap or just shared vocabulary. Read both skills before merging. To fix a miss, add the pitch's key phrases to the skill's description.

## Core vs library (see also skill-finder)

Read the "never in top-k" list in two parts. On 2026-10-16 (copy of the library, 280 skills, --top 5), 24 of the 34
misses were the core ritual skills, and 2 of 26 core skills were found against 244 of 254 library skills. Their
pitches are scar stories ("Each line is an incident, not a guess."), so the miss measures the pitch, not whether the
skill can be found. `core_pin.py audit <copy>` prints the split and the before/after for skill-finder's trigger
table (core 2 -> 3 of 26 with pins, 4 of 26 with the command-tour and windows-port-audit description patches as
well; 0 library skills lost their place). For core skills, judge routing on real asks
(`core_pin.py probe probes_heldout.tsv`), not on this audit. skill-health's route_rank.py turns this list into
cached WARN lines.
