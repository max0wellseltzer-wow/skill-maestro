# skill-maestro (Claude Code plugin package, v20)

The Maestro picks skills for a task from whatever library you have (even only Claude Code's built-ins), proves the
picks on the task's real subject, and learns from what was really used afterwards. Pure Python 3.10+, standard
library only. Nothing leaves your machine; `--no-ledger` records nothing.

v20 is the essentials only: 39 files, about 2.6 MB, most of it the cards (one meaning line per skill of the owner's
library, which `cards --auto` rebuilds for yours). The research modules moved to a second package,
`skill-maestro-extras` (see below); the histories and surveys left the package (`CHANGELOG.md` keeps one line per
version).

## Install

From a marketplace that lists this package: `/plugin install skill-maestro`.
By hand: copy `skills/skill-maestro/` into `~/.claude/skills/`, then

```
python ~/.claude/skills/skill-maestro/maestro.py doctor
python ~/.claude/skills/skill-maestro/maestro.py cards --auto
python ~/.claude/skills/skill-maestro/maestro.py score "<your task in your own words>"
```

`doctor` prints numbered fix steps for anything missing. `WELCOME.md` inside the skill is the plain-words version;
`SHARING.md` says what the optional sibling skills and the extras package add.

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

This folder is the package. To publish, the owner creates a public repository holding it (or adds it to an existing
marketplace), sets the license file beside this README (MIT is declared in `.claude-plugin/plugin.json`), and lists
it in a `marketplace.json`. Until then it is a private, installable-by-hand package.
