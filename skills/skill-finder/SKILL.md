---
name: skill-finder
description: Describe a need in plain words and get the best-matching skills ranked (the fast one-line lookup; for a real task worth a cycle - choosing several skills, checking each works on the subject, rating them - use skill-maestro, which runs on this engine) - TF-IDF-weighted search over every skill's name and description, with name matches boosted, each result marked [T] tool-backed or [D] doc-only. Use this whenever the user (or you) needs to find the right skill for a task, asks "which skill handles X" / "do we have something for Y", or before building something that might already exist as a skill. One of the three library-organizing skills, with skills-index (browse) and skill-health (verify). Also (formerly core-skill-pin) - "PreToolUse hook error"; "ready to commit"; "status"; "status?"; "Make the skill router find the CORE ritual skills (land-a-change, guard-respect, receipt-report, tree-status, long-job, mailbox-post...)". Also (formerly seed-bank) - "didn't we have a skill for X?"; "merged into Y"; "killed"; "Use this whenever the user asks "didn't we have a skill for X?", wants to revive a killed or merged idea, or browses what earlier waves removed".
---

# skill-finder

When the library is big, the hard part is not running a skill - it's remembering one exists. This turns "I need something that stops my alert flapping" into `hysteresis`, and "is this signal real or luck" into `signal-nulls`, by ranking every skill against your words. Rare, specific words (like "flapping", "articulation", "memoize") count more than common ones, and a word that appears in a skill's NAME counts double.

## The tool (ships with this skill)

`find_skill.py` - pure stdlib, selftest 7/7:

```
python find_skill.py "is my series trending or mean reverting"
python find_skill.py "rate limit alerts" --top 5
python find_skill.py --selftest
```

Live check on the real library: "stop my alert from flapping on and off" -> `hysteresis`; "find the single point of failure in my dependencies" -> `keystone-find`; "cache an expensive function safely" -> `lru-cache`; "two sessions writing the same repo" -> `peer-handoff` / `writer-pen`. An unrelated query returns nothing rather than noise.

## Before building anything new

Run a search first - with this many skills, a new idea often already exists (or has a close relative to extend instead of duplicating). Browse a whole family with `skills-index`; verify the library with `skill-health`.

## Core pins (see also skill-finder)

Ritual skills such as land-a-change, guard-respect, receipt-report and tree-status are asked for in short
situational words ("status?", "PreToolUse hook error", "ready to commit") that their descriptions share with many
other skills, so plain TF-IDF ranks them low. On 58 held-out the user prompts (2026-10-16) this finder put an acceptable
skill in its top 5 for 28. skill-finder's `core_pin.py find "<ask>"` runs this same search and adds a trigger-table
boost for the 26 core skills: 30/58, with no row broken and no library skill pushed out of its own top 5. Use it
when the ask is about the session itself (status, landing, a hook error, a stuck job, a mailbox post).

## pinned trigger table that ranks core skills first for their trigger phrases (merged from core-skill-pin)

### The problem

On 2026-10-15 route-audit found that 26 skills never reach the top 5 for their own pitch, and they are the workspace's
ritual skills: land-a-change, guard-respect, receipt-report, tree-status, mailbox-post, plant-the-bug, windows-gotchas
and others (mining layer 10). Layers 4-9 found misses for the same skills: 17 rm blocks with no guard-respect, 14
"status?" prompts, 11 mailbox posts with no header. A skill that is never retrieved behaves like a missing skill.

Re-measured on 2026-10-16 on a copy of the library (280 skills): only 2 of the 26 reach the top 5 for their own
pitch. The reason is in the pitches. route-audit queries with each body's first paragraph, and for ritual skills
that paragraph is the scar story: "Each line is an incident, not a guess." (windows-gotchas), "Repeated about 15
times this session..." (land-a-change). Nobody asks for help in those words. The real failure shows up when the
router gets real asks: on 58 held-out the user prompts, labelled blind by a separate agent, plain skill-finder put an
acceptable skill in its top 5 for only 28.

There is a second router. In the harness skill listing, most skills appear as a bare name with no description
(tree-status, receipt-report and land-a-change did on 2026-10-16), so an ask can only reach them through words
Claude reads somewhere else. `table` prints the trigger table as markdown for CLAUDE.md or memory.

### Procedure

1. `python core_pin.py check --root <skills>`: every core skill exists, and no phrase is empty or COLLAPSED. A
   multi-word phrase is collapsed when only one generic word survives the stopwords ("are you done" becomes "done";
   on 2026-10-16 that phrase sent "sync it to the repo when done" to receipt-report).
2. Add phrases only from a skill's description or from real asks and real tool errors (MAX_PROMPTS, the layer 9
   error table). Never take them from the body pitch that route-audit uses, because that games the audit.
3. `python core_pin.py audit <copy of skills> --top 5` reports core and library top-1/top-5 before and after, the
   skills that LOST their top-5 place because of the pins (this must be 0), and the new confusions.
4. `python core_pin.py probe probes_heldout.tsv --root <skills>` gives hit@5 before and after on real asks. FIXED or
   BROKE marks each changed row. Every BROKE row needs a fix before the table ships.
5. Ship the table. skill-finder can call `pinned_search`, and `table` gives the markdown block. Never edit the live
   library to test; copy it to a temp folder first.

### Tool

```
python core_pin.py find "status?" --root ~/.claude/skills
python core_pin.py audit <copy> --top 5
python core_pin.py probe probes_heldout.tsv --root <copy>
python core_pin.py check --root <skills>
python core_pin.py table
python core_pin.py --selftest      # 11 PASS lines, exit 0
```

A phrase fires only when all of its content words are in the ask. A one-word phrase ("status", "stuck", "windows")
fires only on asks of 8 content words or fewer. Each firing phrase (2 at most) adds 2 x the largest IDF in the
library, the score of the rarest possible word matched in a skill's name.

### Results (2026-10-16, copy of the library, 280 skills)

| measure | before | pins only | pins + #79/#81 descriptions |
|---|---|---|---|
| route-audit core top-5 (pitch) | 2/26 | 3/26 | 4/26 |
| route-audit all top-5 | 246/280 | 247/280 | 249/280 |
| library skills pushed out of top-5 by the pins | - | 0 | 0 |
| library top-1 | 204/254 | 202/254 | 202/254 |
| real asks, in-family set (probes_real.tsv) hit@5 | 17/20 | 18/20 | 18/20 |
| real asks, held-out set (probes_heldout.tsv) hit@5 | 28/58 | 30/58 | 30/58 |

The table was written before anyone looked at the pitches or the held-out set (v1 sha256 5d08cb86...). v2 dropped the
phrases that `check` flagged as COLLAPSED. v3 dropped "start session", whose two words pulled three library pitches
to autotrade-start. The gain is real but small. 22 core skills still miss on their story pitches, and that number
should not be pushed down by copying story words into descriptions (route-audit's own warning). Held-out recall of
about 50% is the number to work on. Its misses are words the tokenizer drops ("#41" has no word of 3 letters or more)
and asks that name no skill-specific word at all.

Planted 6, caught 6. The first run caught 5. The survivor (fire on ANY of a phrase's words instead of ALL) was a
missing test, and the all-words test was added.

Pairs with skill-finder (the scores it boosts), route-audit (the audit it splits), library-vitals, skill-health.

## archive of retired skills and salvage of their ideas (merged from seed-bank)

Merges and culls keep the library lean, but the removed skills held real ideas. The archives under `~/.claude/skills_archive/` keep them, and this makes them findable: search the dead by what you need, and see whether the idea still lives inside another skill before reviving it.

### The tool (ships with this skill)

`seed_bank.py` - pure stdlib + sibling imports (skill-finder for ranking, wave-yield for merge detection), selftest 9/9:

```
python seed_bank.py "rate limit cooldown"                 # search all archives in ~/.claude/skills_archive
python seed_bank.py --list                                # every seed and its fate
python seed_bank.py QUERY --archive ROOT --live ROOT --top 5
python seed_bank.py --selftest
```

Each hit shows the score, the old one-line use, its fate, and `revive from: <archive folder>`.

### Salvage (merged from nucleosynthesis)

Stars die and forge heavier elements for the next generation (nucleosynthesis). `python seed_bank.py --salvage` (or `salvage(bank(archives, live), live, timeout=60)`) takes every banked seed's public functions from exaptation-finder's index, drops each one whose normalised body already exists anywhere in the live library (convergence-detector's `fingerprint`: renamed locals and docstrings do not hide a copy), runs each remaining tool's `--selftest` from a throwaway cwd with `-B` and a timeout, and lists the raw material: functions no live tool provides, with seed, fate, file and status (`works` / `untested` / `timeout` / `broken`). It reads and runs only. Nothing is copied into the live library and nothing is written into the archive.

First run (2026-10-15, archive 2026-10-15_pre-merge): 39 public functions in the 22 banked seeds; 37 already live under another name; 2 left, both `works`: `catalyst.catalyze` and `catalyst.verify`. catalyst is labelled "merged into fast-path-proof", but its memoize-and-verify code did not survive there word for word.

### Uses and limits

- If a seed says "merged into Y", read Y's merged section first: the idea usually still works there and needs no revival.
- Reviving means copying the printed folder back into `~/.claude/skills` yourself, then running skill-health on it. The tool never copies.
- Ranking runs inside each archive's own library, so scores match what skill-finder gave back then. A seed found in several archives is listed once, from the newest archive.
- Salvage runs archived code (selftests only, with a timeout, from a temp folder). "Already live" means the same normalised body; a function rewritten in different code still counts as raw material, so check the "merged into" host before reviving it.
- Merge detection is wave-yield's: "merged from X" text or a shared file hash. A seed whose code was rewritten into a host without a label shows as "killed".
