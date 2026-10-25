# Fairness in the SKILL Maestro (v14, 2026-10-21)

The rule: a skill's chance of being picked depends on how well it fits the task, and on nothing else. That means not
how often it was used, not how much is written about it, not where it came from, and not how its description talks
about itself.

the user's words: "make sure skill maestro does not favor skills because they are used more often or because there is more
information known about some skills more so then others ... or adjacent to that or parallel to that or opposite to
that or around that".

Re-run the measurements with `python fairness.py all --out FILE`. The records are in
`skill-maestro-workspace/fairness/`: `fairness_before_*.json`, `fair_exp*.json` and `fairness_after_*.json`.

## The checks (fairness.py)

| check | question | method |
|---|---|---|
| F1 popularity | does history move picks that fit would not? | the same tasks picked with the real ledger and with none (a blind audition) |
| F2 information | is a thinly described skill harder to find? | every skill searched by its own synthetic query, hit rate by quartile of body, description and links |
| F3 sources | does one source crowd the others out? | pool and top-6 share per source (custom, plugin, built-in, synced) against library share, on the probes and on 20 odd tasks |
| F4 wording | do asking words favour self-describing skills? | pool share of skills whose description says "skill", when the task says "skill" vs when it does not |
| thin | can a skill with a short description win when it plainly fits? | 8 tasks, each fitted by one built-in skill |

## What was found, and what was done

| finding (before) | fix | kept? | evidence |
|---|---|---|---|
| Asking words: skills whose description says "skill" were 16% of the library but 38% of the pool when the task said "skill" | A: "skill", "skills" and "maestro" never reach the ranking (dial M30) | yes | 38% -> 23%; accuracy level |
| Popularity: history changed the picks on 8 of 113 tasks; a rating on one kind of work moved unrelated work (bench E13) | C: a skill's record counts only from past tasks similar to this one (dial M32) | yes | held-out @1 5 -> 7, custom-only 6 -> 8 |
| Information: fusion added nothing for a reading a skill could not appear in (built-ins have no body and no links), so dataviz ranked 16th and init 25th on tasks they plainly fit | B: rescale each skill to the readings it is eligible for (dial M31) | no | top-6 rose from 4/8 to 6/8 thin skills, but creative @1 fell from 10 to 4 (at full strength) or 5-6 (at square-root strength). Over-correction is the "opposite" unfairness |
| Information, at the source: the built-in descriptions had been trimmed by hand (update-config lost "allow npm commands") | full official descriptions restored in builtins.json, never trimmed | yes | see the final record |
| Information, meaning: only the 687 hand-carded skills could be read by meaning; plugins, built-ins and another person's library could not | `cards --auto` builds a meaning line for every skill without one, by one rule for all; hand lines win | yes | 348 skills gained a line (281 plugin, 16 built-in, 15 synced, 36 custom) |
| Tool vs guide: a skill with a script gets a small bonus | D: no bonus (dial M33) | no | held-out @3 13 -> 10 with no measured unfairness fixed; creative task kinds already drop the bonus |
| Self-pick: the Maestro picked itself | never a pick (v11) | yes | selftest |

## Still open (honest)

- **The labels.** The held-out labels name only custom skills (they were written before plugins existed), so any fix
  that helps plugins or built-ins looks worse on them. the user's ratings of real sheets (`maestro.py forward`) are the
  unbiased measure.
- **F2 is saturated.** Every skill's own synthetic query finds it 98.7% of the time, so it cannot show a small
  information bias. A harder test needs queries written without seeing the description.
- **Vocabulary mismatch.** A thin skill whose job is described in other words than the task's ("allow npm commands"
  vs "permissions") is reached by meaning (`--concepts`) rather than by words.
