---
name: skill-graph
description: Use this whenever the user asks which skills the library leans on, what breaks if a skill is removed or merged, which skills nothing connects to, or whether "Pairs with" lists point at real skills - builds a graph from Pairs-with mentions, skill names in SKILL.md text and Python imports of sibling skill folders, and labels each skill HUB, BRIDGE, LEAF or ORPHAN plus every dangling reference. Pairs with library-vitals, keystone-find, route-audit and metaphor-questions.
---

# skill-graph

Skills cite each other ("Pairs with ...") and some tools import their siblings. Together these form a network. That network shows which skills carry the library (hubs), which ones alone hold two regions together (bridges), and which ones nothing touches (orphans). It also catches "Pairs with" links that point at a skill that was renamed or merged away.

## The tool (ships with this skill)

`skill_graph.py` - pure stdlib (regex scan, BFS, Brandes betweenness), selftest 9/9:

```
python skill_graph.py live                  # graph ~/.claude/skills
python skill_graph.py live --node paper-only
python skill_graph.py ROOT
python skill_graph.py --selftest
```

From Python: `roles(build(root))` returns rows {skill, degree, betweenness, cuts_off, roles} plus thresholds, component count and `dangling` {skill: [missing names]}.

## Uses and limits

- Roles: HUB means degree >= max(4, mean + 2 sd). BRIDGE means betweenness >= max(0.02, mean + 2 sd), or an articulation point that cuts off at least 2 skills. LEAF means degree 1 and ORPHAN means degree 0. A skill can hold more than one role.
- Before merging or deleting a HUB or BRIDGE, check its neighbours with `--node`. An ORPHAN is a merge candidate or needs a "Pairs with" line.
- Text edges: a hyphenated name counts anywhere in the text. A one-word name (bud, lindy, triage) counts only inside a "Pairs with" clause or in backticks, so ordinary words do not create edges. Edges are undirected.
- Dangling refs come only from single hyphenated names in "Pairs with" lists, because one-word items there are usually prose. Plugin and built-in skills (research-integrity, update-config) show as dangling because they have no folder here, so judge each one.

## One-way pairs (merged from dangling-pairs, added 2026-10-16)

`build(root)["one_way"]` (and the `ONE-WAY pairs` line of the printout) lists every `(A, B)` where A's "Pairs with" clause names B but B's SKILL.md never names A anywhere (same text rules as the edges). It is a reading list, not an error: the exit code is unchanged and nothing is FAILed. The planted selftest check proves a mutual pair and a prose-only mention are not flagged.

Live run 2026-10-16: 2017 one-way pairs from 603 skills. The top targets are pov-core (160 skills pair with it, it names none of them back), signal-nulls 33, changepoint 26, deflated-sharpe 23, bootstrap-ci 23. A hub that every lens points at should not list them all, so a one-way pair into a hub is normal. Fix the ones between two peers of similar size, where the reverse link would actually help routing.
