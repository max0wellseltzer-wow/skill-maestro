# Sharing the Skill Maestro

The Maestro picks the best skills from a Claude Code skill library for the task in front of it, makes the picks
prove themselves on the task's real subject, and learns from ratings. This page is for someone who is not the user
and wants it on their own library.

New here? Read `WELCOME.md` first: the same thing explained like you are five, with a dictionary.

## Install (two minutes)

1. Copy this folder, `skill-maestro/`, into your skill library: `~/.claude/skills/` (personal) or a project's
   `.claude/skills/`. Nothing else is required: pure Python 3.10+ standard library, no packages.
   On Linux and macOS, type `python3` wherever this page says `python` (cloud-port-audit, 2026-10-21).
2. Once, so every skill you have can be read by meaning: `python ~/.claude/skills/skill-maestro/maestro.py cards --auto`.
   Then, from a project folder: `python ~/.claude/skills/skill-maestro/maestro.py score "<your task in plain words>"`
   (it first says SKIP, QUICK or FULL; `--full` shows every section; `--no-ledger` records nothing).
3. Read the SKILL.md files it names, record that you did (`read`), run each pick on your subject (`try`), say whether
   it worked (`fit`), and rate (`rate`). The next score is better for it.

It says `STANDALONE` when it runs without the sibling skills below; that is a working mode, not an error.

## What it uses from the library, when present (all optional)

| sibling skill | what the Maestro gains | without it |
|---|---|---|
| skill-finder (`find_skill.py`) | the library's own search, its stop list | the Maestro's MiniFinder (same TF-IDF shape) |
| core-skill-pin (`core_pin.py`, `core_triggers.json`, probes) | trigger phrases that pin ritual skills; the held-out `eval` | plain search; `eval` needs `--probes FILE` |
| skills-index (`build_index.py`) | family names on the sheet and the DIVERSITY rule | family `?`, no diversity swaps |
| skill-graph (`skill_graph.py`) | `--graph` neighbours | the flag is ignored |
| max-lexicon (`glossary.json`) | the owner's vocabulary expanded | nothing |
| skill-compose (`skill_compose.py`) | `selfcheck` as a typed pipeline | run `--selftest` and `eval` by hand |

Files inside this folder that are this library's, and harmless elsewhere: `cards/cards.jsonl` (per-skill cards; a
foreign library gets no card lines and no ON-THE-PC-ONLY line), `builtins.json` (Claude Code's built-in skills: edit it when your session listing differs),
`maestro_dials.md` (the dial panel; the LOCKED rows are the tested spine and the tool halts if they change).

## The extras package (optional, v20)

The research commands (`chain`, `rehearse`, `play`, `brief`, `inverse`, `repertoire`, `anti`, `rerank`, `tune`, `ablate`,
`why`, `odds`) and `fairness.py` live in a second folder, `skill-maestro-extras`, in the same repository. Without it the
Maestro prints one line naming the missing module and exits 2; everything on this page runs from `skill-maestro/` alone.
To use them, put that folder beside this one (`~/.claude/skills/skill-maestro-extras/`) or set `MAESTRO_EXTRAS` to
wherever it is. The extras find the Maestro the same way: beside them, at `MAESTRO_HOME`, or the sibling `skill-maestro/`.

## What to expect on a fresh library

- The first score has no ratings, so the opening book, antibodies and menu E are empty; they fill as you rate.
- Picks are ORGANIZED, not VERIFIED: the sheet is evidence to judge, not a verdict. Judge the POOL.
- The HEALTH gate runs each pick's `--selftest` if it has one; skills without one are not penalised.
- `rate ... --by user` (or `--by max`; both are stored as the library owner) feeds memory; `--by claude` never does.
- State lives in `~/.claude/skill-maestro-state/` (`ledger.jsonl` append-only, caches, `health.json`); in a Claude
  Code cloud session with `CLAUDE_CODE_REMOTE=true` and a project, the ledger is `<project>/shared/skill-maestro/ledger.jsonl`
  so it survives the container (give it `merge=union` in `.gitattributes`).

## Tell it about your project

`MAESTRO_PROJECT.md` in the project folder, `GOAL:` and `LIMIT:` lines, one each per line. Without it the
Maestro reads CLAUDE.md (opening paragraph as the goal; bullets under a heading that names limits or rules).

## Send your ratings back

Your picks and ratings make the Maestro better for everyone. Run `python maestro.py share`, read the
file it writes (paths, e-mails and keys are masked; task text is left out unless you pass
`--with-tasks`), and attach it to an issue or pull request on the repository you installed the Maestro
from. The maintainer runs `maestro.py intake` on it, and the next release's sheets learn from it.
Bundles you receive are read as data: nothing in one is ever run.

## Known limits

- The measurements in SKILL.md (@1, @3, pool@40 on 58 prompts) are on the user's prompts and the user's library; they say
  nothing about yours until you build a probe file (`tab`-separated: prompt, comma-separated good skills) and run `eval --probes FILE`.
- Built-in Claude Code skills cannot be read from disk; `builtins.json` is a hand-kept snapshot.
- Windows and Linux are both exercised; macOS is not tested.
