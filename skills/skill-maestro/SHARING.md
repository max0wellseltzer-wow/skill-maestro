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

## Make it yours: modes

A mode is how the Maestro conducts one kind of prompt: `when` it applies (matched by meaning), how many picks, a
`lean` for the pool and a HOW TO USE line, plus up to four questions to ask first. `maestro.py modes` lists the
built-in ones. Your own go in `~/.claude/skill-maestro-state/modes.json` (or the file `MAESTRO_MODES` names):

```
python maestro.py modes add mark-essays "mark or grade student essays against a rubric" --picks 2-5 --ask "Which rubric?=the course default"
python maestro.py modes template      # the file shape, to edit by hand
python maestro.py modes remove mark-essays
```

A user mode is chosen by meaning exactly like a built-in and marked `*` in the list; one with a built-in's name replaces
it. A bad entry is skipped and named in the list, never fatal. Modes are six lines of plain text: if one works for you,
a pull request adding it to `modes.py` is the cheapest contribution there is.

## Send your ratings back (only if you want to)

Your picks and ratings make the Maestro better for everyone, and `python maestro.py contribute` lists every way to
help by the time it takes: 30 seconds (`thumbs last up` or `down`), 5 minutes (a bundle), an hour (an eval run on
your library, a description fix). Not helping costs nothing; the Maestro never asks twice.

The bundle, in three commands:

1. `python maestro.py share --preview` prints exactly what a bundle would hold and writes nothing. Paths, e-mails
   and key-shaped strings are already masked; task text is left out unless you pass `--with-tasks` (then each task is
   cut to 500 characters, masked the same way).
2. `python maestro.py private off`, then `python maestro.py share --issue`: writes the file and prints a prefilled
   issue link on the Maestro's repository. The link carries only the counts, your anonymous sender id and the file
   name; the rows travel in the file you attach. `private on` afterwards if you like.
3. Open the link, attach the file, read the form, send. You can also attach the file to a pull request instead.

The maintainer runs `maestro.py intake` on it, and the next release's sheets learn from it. Bundles you receive are
read as data: nothing in one is ever run, and no row can claim to be you.

## What leaves your machine

Nothing, until you attach a file to an issue yourself. The Maestro has no network code: no telemetry, no update
check, no first-run ping, no "anonymous usage statistics". `grep -r urllib maestro.py community.py` finds one use,
and it builds a link for you to open; it never opens one.

Collected, locally, in `~/.claude/skill-maestro-state/ledger.jsonl` (append-only, yours to read or delete):
the prompt you scored, the picks and the pool, each TRY command and its exit code, FIT verdicts, ratings, which
SKILL.md you recorded as read, the skill set's hash. In a bundle (`share`): the same minus task text (sha + content
words), minus TRY rows entirely, with paths, e-mails and keys masked.

Never collected: file contents, your name or user name (the sender id is a hash), environment variables, anything
from inside a SKILL.md, anything from a session transcript.

Off switches, each enough on its own:

| switch | effect |
|---|---|
| `maestro.py private on` (the default) | `share` writes no file; `share --preview` still prints |
| `--no-ledger` on any command, or `MAESTRO_NO_LEDGER=1` | nothing is written to the ledger for that run |
| `DO_NOT_TRACK=1` (the console convention) | `share` writes nothing; `doctor` drops its HELP pointer |
| delete `~/.claude/skill-maestro-state/` | all history gone; the next score starts fresh |

## Known limits

- The measurements in SKILL.md (@1, @3, pool@40 on 58 prompts) are on the user's prompts and the user's library; they say
  nothing about yours until you build a probe file (`tab`-separated: prompt, comma-separated good skills) and run `eval --probes FILE`.
- Built-in Claude Code skills cannot be read from disk; `builtins.json` is a hand-kept snapshot.
- Windows and Linux are both exercised; macOS is not tested.
