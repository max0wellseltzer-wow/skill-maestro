# skill-maestro (Claude Code plugin package, v20.1.5)

The Maestro picks skills for a task from whatever library you have (even only Claude Code's built-ins), proves the
picks on the task's real subject, and learns from what was really used afterwards. Pure Python 3.10+, standard
library only. Nothing leaves your machine; `--no-ledger` records nothing.

v20 is the essentials only: 39 files, about 2.6 MB, most of it the cards (one meaning line per skill of the owner's
library, which `cards --auto` rebuilds for yours). The research modules moved to a second package,
`skill-maestro-extras` (see below); the histories and surveys left the package (`CHANGELOG.md` keeps one line per
version).

## Install

Public repository: https://github.com/max0wellseltzer-wow/skill-maestro (it is its own marketplace).

```
/plugin marketplace add max0wellseltzer-wow/skill-maestro
/plugin install skill-maestro@skill-maestro
```

Later: `/plugin marketplace update skill-maestro`, then `/plugin update skill-maestro@skill-maestro`; a new version
reaches you only when `version` in `.claude-plugin/plugin.json` changes.
By hand: copy `skills/skill-maestro/` into `~/.claude/skills/`, then

```
python ~/.claude/skills/skill-maestro/maestro.py doctor
python ~/.claude/skills/skill-maestro/maestro.py cards --auto
python ~/.claude/skills/skill-maestro/maestro.py score "<your task in your own words>"
```

`doctor` prints numbered fix steps for anything missing. `WELCOME.md` inside the skill is the plain-words version;
`SHARING.md` says what the optional sibling skills and the extras package add.

If a `/plugin update` seems to change nothing, the plugin cache kept the old copy: remove the package's folder under
`~/.claude/plugins/cache/` and install again. A by-hand copy has no cache.

To leave: `/plugin uninstall skill-maestro@skill-maestro`, then `/plugin marketplace remove skill-maestro`. That
removes the package, not your history: `~/.claude/skill-maestro-state/` (its `ledger.jsonl` holds every task you
scored) stays until you delete it, and the old versions in `~/.claude/plugins/cache/skill-maestro/` stay marked
orphaned. Delete both folders to leave nothing behind. A by-hand copy: delete `~/.claude/skills/skill-maestro/` and
the state folder.

## Trust: what this package does on your machine

- **Who publishes it:** Max (max0wellseltzer-wow) with Claude, from the owner's workspace; MIT. Every release is
  one line in `CHANGELOG.md` and one `version` bump in `.claude-plugin/plugin.json`.
- **It installs no hooks.** `plugin.json` declares skills only. The owner's SessionStart listing check (`listing.py`)
  and UserPromptSubmit whisper are opt-ins you would add to your own `settings.json` by hand; nothing here does it.
- **What runs without you typing it:** nothing beyond the score you asked for. A FULL `score` runs each pick's own
  `--selftest` once from an empty temp folder (its HEALTH gate; cached in `health.json`, skipped on QUICK) and reads
  the picks' scripts with an AST walk, never executing them. TRY commands run only when you type `maestro.py try ...`.
- **No network code.** No telemetry, update check or first-run ping; `grep -r urllib` finds one call that builds an
  issue link for you to open. Ratings leave your machine only as a file you attach yourself (`SHARING.md`, "What
  leaves your machine"); `DO_NOT_TRACK=1` turns off even the pointer to it.
- **Token cost:** about 200 tokens for a QUICK verdict, 400-600 for a FULL sheet; it says SKIP when a sheet is not worth it.
  `maestro.py cost --listing` prints what your whole skill listing costs at every session start (name-only, described,
  off, plugin and built-in entries, against a 200,000-token window); the package's own skills are listed with their
  descriptions, as every plugin's are.
- **Verify it yourself:** `python ~/.claude/skills/skill-maestro/maestro.py doctor` (12 checks) and
  `python ~/.claude/skills/skill-maestro/maestro.py --selftest` (prints PASS). Both read; neither writes outside
  `~/.claude/skill-maestro-state/`.

## Helping, only as much as you like

`python ~/.claude/skills/skill-maestro/maestro.py contribute` lists the ways by the time they take: 30 seconds
(`thumbs last up|down` after a score), 5 minutes (`share --preview`, then `share --issue` and attach the bundle to
the prefilled issue), an hour (an eval on your library, a description fix, a mode of your own: `modes add`). The
Maestro asks once, in `doctor`, and never again.

## Bundled skills (v20.0.10)

The core skill runs alone (a built-in word finder stands in when `skill-finder` is absent). `selfcheck`, `eval` and
`meaning.py eval` need sibling skills, so the package bundles them under `skills/`, each with its own `--selftest`:

| skill | what the Maestro uses it for |
|---|---|
| `skill-finder` | the word-reading finder (`find_skill.py`), the pinned core (`core_pin.py`) and the held-out probes `eval` scores against |
| `skills-index` | the family-grouped catalog `build_index.py` regenerates for your library |
| `skill-graph` | which skills lean on which (the `selfcheck` graph step) |
| `skill-compose` | the typed pipeline runner behind `selfcheck` |
| `skill-health` | every bundled tool's selftest from a neutral folder (the `selfcheck` health step) |
| `route-audit`, `collision-registry` | bonus: router self-test and the near-duplicate registry `skill-finder`'s pin uses |
| `kingdom-sweep` | bonus: a concept swept across kingdoms for ideas |
| `skill-foundry` | bonus: takes a seed skill idea through every library gate in order (`foundry.py`), then scaffolds it (`scaffold.py`) |
| `metaphor-to-algorithm` | bonus: reduces a metaphor-named skill idea to the plain algorithm it names and checks whether the library has it already (a foundry gate) |
| `lineage-ledger` | bonus: one append-only birth record per skill (parents, operator, prompt, who chose it); the foundry records a birth there. Ships without a ledger: yours starts empty |
| `source-labels` | bonus: tags every claim in a pitch [REAL - source] / [IMAGINED] / [FABRICATED] and checks the labels (a foundry gate) |
| `skill-maestro-extras` | the research commands listed below |

Install by plugin and they are all in place. By hand: copy every folder under `skills/` into `~/.claude/skills/`.
The skills' text names "the user" where the owner's copies name him; the example prompts in the probe files are the
owner's, kept as test data.

## See also: science-personas and maestro-companions

The same publisher's [science-personas](https://github.com/max0wellseltzer-wow/science-personas) is a pack of
fourteen expert-persona skills (statistics, causal inference, ML research, operations research, security research
and more; written by K-Dense, MIT, text-only). The Maestro ranks them like any other skill: a persona is a priced
pick, never the default reader. Install it with `/plugin marketplace add max0wellseltzer-wow/science-personas`.

[maestro-companions](https://github.com/max0wellseltzer-wow/maestro-companions) is the pack of seventy skills
the Maestro's own ledger shows were read, tried, judged to fit or rated useful in real sessions: the point-of-view
lenses (devils-advocate, steelman, future-self, worms-eye and nineteen more on pov-core), the finishing and review
checks (finish-everything, doc-truth, decorative-check, brittle-test-audit) and the skill-library tools
(demand-scan, exaptation-finder, peacock-tail). Install it with
`/plugin marketplace add max0wellseltzer-wow/maestro-companions`; its README names the five scripts that also need
skill-finder or skill-health from this plugin.

## Optional: the meaning reading and the extras

- **Meaning.** Picks rank by meaning first when a Python with `fastembed` (BAAI/bge-small-en-v1.5) is installed at
  `~/venvs/maestro-meaning`; `maestro.py meaning status` says whether the model and the resident helper
  (`meaning.py serve`) are up. Without it the skill runs by words alone, and says so.
- **Extras.** `chain`, `rehearse`, `play`, `brief`, `inverse`, `repertoire`, `anti`, `rerank`, `tune`, `ablate`,
  `why`, `odds` and `fairness.py` are research commands; they live in the package `skill-maestro-extras`, installed as
  a sibling folder of the skill (or pointed at with `MAESTRO_EXTRAS`). Without it each of them prints one line saying
  so and exits 2; `--selftest` skips them. Everything else runs from this folder alone.

## What it does not do

It never favours a skill for being used more, for having more written about it, or for where it came from
(`references/FAIRNESS.md`). It never calls a ranking verified: the sheet says ORGANIZED until a pick is run on the
subject and judged. Its own accuracy numbers, including the ones that did not improve, are in
`references/LEARNING_LIMITS_2026-10-22.md` and `references/O1_RERANK_2026-10-22.md`.

## Publishing

This folder is the package and the repository https://github.com/max0wellseltzer-wow/skill-maestro
is its public copy (MIT, `LICENSE`). `.claude-plugin/marketplace.json` lists the package at the repository root, so
the repository is also the marketplace. The copy is pushed from `plugins/skill-maestro` of the owner's workspace;
ratings and labels come back through `maestro.py share` bundles (see `SHARING.md`).
Before a push, `python skills/skill-maestro/scrub.py` (dry run) must report no leftovers: it turns the owner's
home folder, workspace and name into `~`, `<workspace>` and "the user" across the survey, and `survey build`
applies the same rules to every row it writes.
