---
name: skill-health
description: Verify the whole skill library in one command - every bundled tool's selftest run from a neutral directory, frontmatter name matches folder, tools are stdlib-only (portable), plus warnings for hardcoded user/repo paths and a count of doc-only skills. Use this whenever the user asks whether the skills still work, after adding or editing skills/tools, before relying on a skill in another project, or asks "are all our skills healthy / portable?". One of the three library-organizing skills, with skills-index (browse) and skill-finder (search).
---

# skill-health

A library of 150+ skills rots quietly: a tool breaks after an edit, a skill folder gets renamed without its frontmatter, a tool picks up a third-party import or starts depending on the directory it happens to run in. This is the one-command check that catches all of that, so "do our skills work?" has a real answer instead of an assumption.

## The tool (ships with this skill)

`skill_health.py` - pure stdlib, selftest 17/17 (2026-10-24):

```
python skill_health.py                      # check ~/.claude/skills; exit 1 if anything FAILS
python skill_health.py --only a,b,c         # check just these skills
python skill_health.py <other_skills_root>  # check a different library
python skill_health.py --selftest           # proves each failure kind is caught
```

Per skill it reports OK / WARN / FAIL:
- **FAIL** - frontmatter `name` differs from the folder; a tool's `--selftest` exits non-zero (run from a neutral temp directory, so a tool that only works from its own folder is caught); a tool imports a non-stdlib module.
- **WARN** - a tool contains an absolute user/repo path, or a script offers no `--selftest` (a `def _selftest()` or a
  `def selftest()` plus the `--selftest` flag both count).
- Bad arguments (`--help`, an unknown flag, a missing folder, `--only` with no list) print usage and exit 2 (0 for
  `--help`), never a traceback.

## Scars
- 2026-10-21 (session cd78402b, L4976): `skill_health.py --help` took "--help" as the skills root and crashed in
  `root.iterdir()` with a traceback. Fixed 2026-10-24: usage, exit 2; selftest case added.
- 2026-10-22 (L5461): command-tour's tour.py had `def selftest()` and `--selftest`, yet was reported "no --selftest"
  because the check looked for the text `_selftest`. Fixed 2026-10-24: both spellings accepted; selftest 17/17.
- It also lists the doc-only skills (no bundled script) and the tool-backed count.

## When to run it

After any batch of skill edits, before trusting a skill in a new project, and as a CI gate (non-zero exit on failure). Pair with `skills-index` to see what you have and `skill-finder` to pick the right one.

## Retrievable, not just well-formed (route_rank.py)

Tool: copy `skill-health__route_rank.py` to `skill-health/route_rank.py` (stdlib, `--selftest` 7/7, planted 5,
caught 5. The first run caught 4. The survivor was CRLF normalisation: the test's "LF" file had been written with
write_text, which writes CRLF on Windows. The test now writes bytes).

On 2026-10-15 skill-health reported FAIL 0 / WARN 0 while route-audit found 26 skills that never reach the top 5 for
their own pitch (mining layer 10). library-vitals combines both checks but is itself one of the 26. route_rank.py
runs route-audit once per library state, keyed by a sha256 of every SKILL.md with CRLF normalised, and caches the
result in the temp dir. It prints one WARN line per unreachable skill, naming the skill the router picked instead:

```
python route_rank.py ~/.claude/skills [--top 5] [--cache DIR]
WARN windows-gotchas: never in top-5 for its own pitch (router said question-not-ruling)
route-rank: 34 WARN (computed, library 2830a980d8b9)
```

On a copy of the library (2026-10-16, 280 skills) this gave 34 WARN. The first run took 7.4 s and a cached rerun
1.0 s. Read a WARN as "check the description", not "broken". A story-style pitch can miss and still be fine (see
route-audit). The fix for ritual skills is skill-finder's trigger table, not copying pitch words into descriptions.
