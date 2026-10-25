# What we have, can, will, can't and will not learn (v15, 2026-10-22)

Every number here was printed by a command named next to it on 2026-10-22, code a798cef98227 (maestro.py sha prefix
as `eval` prints it). Re-run the command to check it.

## What we HAVE learned (measured)

| claim | number | command |
|---|---|---|
| the ranking reads the prompt (not luck) | top-3 12/58 vs a shuffled answer key 1.9 +- 1.3 (max 5 in 200 permutations), z 8.0, p < 0.005 | `maestro.py eval --null 200` |
| but the number is wide | bootstrap 95% interval of top-3 hits: 6 to 19 of 58 | `maestro.py eval --ci` |
| the eval itself can see a planted answer | 5 of 5 planted probes found at top-3 | `maestro.py eval --armed` |
| real prompts are harder than the held-out set | 109 real labelled prompts: top-1 9, top-3 16, pool 45; null 3.3 +- 1.7 | `maestro.py eval --probes <state>/probes_hindsight.tsv --null 200 --ci` |
| the pool holds the answer far more often than the top 3 shows it | pool@40 46/58 vs top-3 12-13/58 | `maestro.py eval` |
| the Maestro equals the plain finder at the top | finder@1 8, finder@3 13 vs maestro@1 8, maestro@3 12-13 | `maestro.py eval` |
| what sessions really ran | 863 runs of 64 commands in the transcripts; `--selftest` 175, `score` 114, `eval` 45, `rate` 39 | `maestro.py hindsight commands` |
| which parts earn their keep | ablation: raw words, body, network, pins, tool bonus, fair context EARN; memory, margin, ask-words, stabilize FREE; lexicon, feedback, intents, eligible rescale COST | `maestro.py ablate` (row 2026-10-22 06:31 in `trend`) |

## What we CAN learn next (built, not yet decisive)

- **Fusion weights from real use.** `tune --split 2026-10-16` (50 real prompts to train, 59 to test) proposed network 2.0,
  body 0.25. Test top-3 7 -> 8, held-out top-3 12 -> 14 but top-1 8 -> 6 and pool 46 -> 45. NOT APPLIED: one unseen set fell.
  The rule in `tune` ("only if every unseen set is at least level") held.
- **Family cap off.** The ablation said removing the family cap raises hits. Tried (dial M12 = 99): top-3 12 -> 13, McNemar on
  the paired vectors p = 1.0, NOT DISTINGUISHABLE. Reverted. Diversity stays because the number does not argue against it.
- **Owner lexicon.** `hindsight propose --write-lexicon` writes the words Max really uses per skill; dial M37 keeps it at 0
  until an eval says otherwise (ablation: lexicon reading COSTS).

## What we WILL learn with time (the loop is closed, data accrues)

- `hindsight build` labels every new session's prompts by what the assistant then reached for. 109 labels today; each
  week of work adds more without anyone rating anything. `eval --probes` on that file is the honest number.
- `grade` reads the ledger monthly: picks tried, worked, owner ratings, debt, drift by week.
- `trend --compare` tells whether a code change moved the paired vector or only the count.

## What we CAN'T learn from this record

- **Whether a pick was right when nothing was reached for.** 633 of 742 prompts have no skill use after them. Silence is
  not "no skill would have helped".
- **Top-1 on 58 probes.** The bootstrap interval spans 6 to 19 hits at top-3; a one-hit change is noise. Changes must
  be judged on the paired vector (`trend --compare`) and still need more probes than exist.
- **Whether the owner found it useful.** 37 ratings in 30 days, 0 by the owner. Claude's ratings are self-reports and the
  tool says so. Only `rate ... --by user` is evidence.
- **Concept tags from the task text.** `suggest` works by word overlap with 70 tag meanings; "audit a module for dead
  globals" matched no tag (the play run on concert.py shows it). Claude's own reading beats it; the tool cannot replace it.
- **The Maestro's picks for its own design.** SELF_SERIES: right in 1 of 5 runs. The finder named skill-maestro itself
  on 3 of 4 (refused by the no-self-pick rule, correctly).

## What we WILL NOT learn (by rule, not by limit)

- Nothing from fame: use counts, description length and source never move a rank (FAIRNESS.md, dials M30-M33).
- Nothing from Claude's own praise: `useful` is refused without a read and a FIT; ratings by Claude never enter the book.
- Nothing from a prompt the owner did not write (`hindsight` skips NOT_OWNER and sidechains).

## Take-away list (item 44; evidence, no deletions: questions are not rulings)

From `hindsight commands --switches` over every transcript on this PC:

- Documented commands no transcript ever ran as a real tool call: see the NEVER RUN line of the command (today: none of the
  documented commands was at zero; the least-run are `taste` 3, `anti` 2, `suggest` 2, `whisper` 3, `plan` 5).
- Dead switches (globals maestro.py defines and never reads): printed by `--switches`; each is a one-line removal candidate.
- Readings the ablation marks COSTS (lexicon, feedback, intents, eligible rescale) are already at weight 0; their code
  is the take-away candidate with the strongest evidence. Removing code needs Max's word.
