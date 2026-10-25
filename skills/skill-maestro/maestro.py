"""SKILL Maestro: pick and use the best skills for a task, with receipts, without cutting corners.

Stages (the user's verbs): CONSIDER a wide pool -> WEIGH each on fit, usefulness, fascination and favour -> SELECT under
the no-corner-cutting rule -> UNDERSTAND (read receipts) -> CONSTITUTE an agenda -> USE, then RATE so the next
choice is better. It reuses the library instead of re-implementing it: skill-finder (TF-IDF search + core pins),
skills-index (families), skill-graph (neighbours, optional), max-lexicon (the user's own words), and keeps a registry so
new skills are never missed. Design notes and the evidence behind v2: brainstorm_2026-10-18.md, now in the extras package (skill-maestro-history).

    python maestro.py score "the task in plain words" [--concepts "op: ...; world: ..."] [--top 6] [--full] [--pool]
                                                                [--graph] [--json] [--project DIR] [--quick] [--budget LINES]
                     (v11: first triages SKIP / QUICK / FULL; SKIP and QUICK answer in a few lines; --full forces a sheet)
    python maestro.py triage "task"                             # the verdict alone (SKIP / QUICK / FULL) and why
    python maestro.py cost                                      # what the Maestro cost and what it bought, recent runs
    python maestro.py debt [--close-older-than DAYS]            # runs owed a rating or ponder; close stale ones as unused
    python maestro.py ponder <run_id> [--concepts2 "..."] [--note "..."]   # the second think step: blunders, quorum, missing
    python maestro.py vocab                                     # the operation tags for --concepts, with skill counts
    python maestro.py breed <run_id>                            # a proposed new skill from the run's two strongest picks
    python maestro.py lexical                                   # rebuild the list of skills that read words, not meaning
    python maestro.py used [<run_id>]                           # picks named vs picks actually used
    python maestro.py builtins [--refresh]                      # the built-in skills (simplify, dataviz, ...) the pool knows
    python maestro.py cards --auto                              # v14: a meaning line for every skill that has none
    python maestro.py findable <skill> [...]                    # v14: how findable a skill is, and what to fix
    python maestro.py newskill <name> "the job"                 # v14: a SKILL.md template when no skill fits
    (any command) --no-ledger                                   # v14: write nothing (also MAESTRO_NO_LEDGER=1)
    python fairness.py all [--out FILE]                         # v14: popularity / information / source / wording bias
    python maestro.py read <run_id> <skill> [<skill> ...]       # UNDERSTAND: record that each SKILL.md was read
    python maestro.py rate <run_id> <skill> useful|fascinating|favourite|unused|wrong
    python maestro.py rate <run_id> <skill|menu:A..E> --by max|claude inner=4 topic=5 curiosity=3 ... [why]
    python maestro.py metrics                                   # the user's metrics board, menus by idea, calibration
    python maestro.py close <run_id> "why"                      # a run never used for work: leaves the audit debt, counts for nothing
    python maestro.py plan <run_id> <skill> --on SUBJECT "what it should find"   # the pick's use-plan line (protocol step 4)
    python maestro.py baton <run_id>                            # where the run stands in the protocol, and the next move
    python maestro.py forward [--write FILE]                    # the running log of the user's ratings: Maestro vs skill-finder, forward
    (any <run_id> may be written `last`: the newest score run)
    python maestro.py try <run_id> <skill> -- <its command on the real subject>   # FIT: run it on the task's subject
    python maestro.py fit <run_id> <skill> works|misfit "why"   # works needs a TRY; misfit is an antibody
    python maestro.py taste <run_id> <skill> --subject FILE -- <command with {subject}>   # null-contrast probe
    python maestro.py new                                       # NEW / CHANGED / REMOVED skills since the last look
    python maestro.py eval [--probes FILE] [--plain]            # selection quality on held-out the user prompts
    python maestro.py trend                                     # every past eval with the code hash it ran on
    python maestro.py selfcheck                                 # the reviewer skills as one skill-compose pipeline
    python maestro.py reflect                                   # useful, traps, wallflowers, duets: the Maestro looks back
    python maestro.py hindsight build|probes|regret|propose|similar|status   # v15: learn from the transcripts (what Claude really used)
    python maestro.py chain <run_id> [--subject FILE] [--write DIR]   # v15: the score: picks ordered by phase and handoff; skill-compose files
    python maestro.py rehearse <run_id> --subject FILE [--workers N]   # v15: every pick's probe on the subject at once, TRY rows written
    python maestro.py ablate [--probes FILE] [--only a,b]       # v15: each reading / rule off (or on) in turn: EARNS / FREE / HURTS
    python maestro.py why "task" <skill> [--concepts ...]      # v15: one skill's whole account on one task (ranks, words, memory, bonuses)
    python maestro.py odds "task"|<run_id>                     # v15: the Maestro's own odds of helping here, from similar past runs
    python maestro.py index [--build]                           # v15: the prepared library index (same answers, read not recomputed)
    python maestro.py tune --split YYYY-MM-DD [--keys a,b] [--grid 0,0.5,1]   # v15: fusion weights tuned on real prompts before the date, judged after it (nothing applied)
    python maestro.py inverse <skill> | repertoire | anti "task"   # v15: the opposite function: skill -> prompts, library -> what it can play, the un-pick
    python maestro.py play "task" [--subject FILE] [--concepts ...]   # v15: the whole protocol in one command, judged report
    python maestro.py whisper "prompt" | --hook                # v15: the finder's 1-22 names by task size in one line (~free); --hook: the prompt hook
    python maestro.py doctor | welcome                          # v15: fresh-install check with numbered fixes; the quick start with your numbers
    python maestro.py digest <skill> | suggest "task" | brief [RUN]   # v15: ten-line digest; --concepts tags; a subagent brief
    python maestro.py grade [--days 30] | matrix                # v15: the report card; the Maestro's matrices from live data
    python maestro.py eval [--null N] [--ci] [--before DATE] [--armed]   # v15: permutation null, bootstrap CI, memory cut, tripwire
    python maestro.py trend [--compare]                        # v15: ABLATE rows too; --compare: McNemar on the last two evals
    python maestro.py score "task" --like RUN | --plain-words  # v15: reuse a past run's concepts; glossary footnote
    python maestro.py hindsight commands [--switches]          # v15: which Maestro commands sessions really ran; dead switches
    python maestro.py rehearse RUN --subject FILE --dry        # v15: print the probe commands, run nothing
    python maestro.py why "task" <skill> --plain               # v15: the account in plain words
    python maestro.py rerank train --split DATE [--write] | eval | status | off   # v16 O1: the learned judge over the pool (dial M40)
    python maestro.py thumbs RUN|last up|down [SKILL] ["why"]   # v16 O6: the owner's one-keystroke rating (counts as evidence)
    python maestro.py encore [RUN]                              # the next move of a run, phase by phase, until CLOSED
    python maestro.py --selftest

v20: chain, rehearse, play, brief, inverse, repertoire, anti, rerank, tune, ablate, why, odds and fairness.py are
research commands; they live in the package skill-maestro-extras (a sibling folder, or MAESTRO_EXTRAS). Without it
they print one line saying so. Everything above them runs from this folder alone.

State (append-only ledger, registry, favourites, caches) lives in ~/.claude/skill-maestro-state, shared by every
copy of the skill (user library and project mirrors), or --state DIR. It never lives inside a skill folder.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLAUDE_HOME = Path.home() / ".claude"   # the one place the user's Claude Code folder is spelled
USER_LIB = CLAUDE_HOME / "skills"
FINDER_FILES = ("find_skill.py", "core_pin.py")
FINDER_HOMES = ("skill-finder", "core-skill-pin")   # the repo keeps core_pin.py and its tables in core-skill-pin


def companion(root: Path, fname: str) -> Path:
    """Where a skill-finder companion file lives: skill-finder/ on the PC's user library, core-skill-pin/ in the
    repo (cloud sessions see only the repo, and stopped with NO_FINDER before v10)."""
    for home in FINDER_HOMES:
        if (root / home / fname).is_file():
            return root / home / fname
    return root / FINDER_HOMES[0] / fname


def has_finder(root: Path) -> bool:
    return all(companion(root, f).is_file() for f in FINDER_FILES)


if not has_finder(ROOT) and has_finder(USER_LIB):
    ROOT = USER_LIB    # a project mirror (the repo's .claude/skills) has no skill-finder: use the user library's
STATE = CLAUDE_HOME / "skill-maestro-state"
STICKY_TYPE = CLAUDE_HOME / "code-types-mode.json"   # item 7: the sticky CODE type from code-types
# A cloud session's home folder dies with its container, and with it every rating. There the ledger lives in the
# repo (committed, git merge=union so two sessions' rows both survive); caches stay in the home folder. Every copy,
# PC included, also reads the repo ledger, so cloud ratings reach the PC with no import step.
CLOUD = __import__("os").environ.get("CLAUDE_CODE_REMOTE") == "true"
SHARED_LEDGER = Path("shared") / "skill-maestro" / "ledger.jsonl"   # relative to the project folder
DIALS = HERE / "maestro_dials.md"
LOCKED = {"margin": "0.15", "book_ratings": "useful", "fascination_picks_max": "1", "rate_needs_read": "yes",
          "debt_shown": "yes", "ranking_label": "ORGANIZED", "bonuses_capped": "yes",
          "think_first": "no"}    # the spine maestro.py was tested with (think_first: the user's ruling 2026-10-24, picks without his concepts)
BOOK_RATINGS = ("useful",)
FASC_PICKS_MAX = 1


class DialError(ValueError):
    pass


def load_dials(path: Path = DIALS) -> tuple[dict[str, str], str]:
    """Read the dial panel: rows `| Mnn | name | value | locked | meaning |`. Halts (DialError) when the rows do not
    number EXPECTED_DIALS or a LOCKED dial differs from the value maestro.py was tested with."""
    if not path.is_file():
        return {}, "no-panel"
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"^EXPECTED_DIALS:\s*(\d+)", txt, re.M)
    rows = re.findall(r"^\| (M\d+) \| ([a-z_]+) \| ([^|]+?) \| (yes|no) \|", txt, re.M)
    if not m or int(m.group(1)) != len(rows):
        raise DialError(f"DIAL_COUNT: header says {m.group(1) if m else '?'}, panel has {len(rows)} rows")
    dials = {name: val.strip() for _, name, val, _ in rows}
    for _, name, val, locked in rows:
        if locked == "yes" and name in LOCKED and val.strip() != LOCKED[name]:
            raise DialError(f"LOCKED_DIAL_CHANGED: {name} = {val.strip()} (tested value {LOCKED[name]})")
    return dials, hashlib.sha256(txt.encode()).hexdigest()[:12]


def apply_dials(d: dict[str, str]) -> None:
    global MARGIN, POOL, W_USE, W_FASC, W_FAV, RRF_K, MEMORY_SIM, FAMILY_CAP, CONCEPT_PULL, WONDER_K, NEED_FLOOR
    num = lambda k, cur, f=float: f(d[k]) if k in d else cur  # noqa: E731
    MARGIN, POOL = num("margin", MARGIN), num("pool", POOL, int)
    W_USE, W_FASC, W_FAV = num("w_use", W_USE), num("w_fasc", W_FASC), num("w_fav", W_FAV)
    RRF_K, MEMORY_SIM, FAMILY_CAP = num("rrf_k", RRF_K, int), num("memory_sim", MEMORY_SIM), num("family_cap", FAMILY_CAP, int)
    global COVER_MAX, SPARK_K
    CONCEPT_PULL, WONDER_K = num("concept_pull", CONCEPT_PULL, int), num("wonder_k", WONDER_K, int)
    COVER_MAX, SPARK_K = num("cover_max", COVER_MAX, int), num("spark_k", SPARK_K, int)
    global BALLOTS, DEMOTE_LEXICAL
    BALLOTS = d.get("two_ballots", "yes" if BALLOTS else "no") == "yes"
    DEMOTE_LEXICAL = d.get("demote_lexical", "yes" if DEMOTE_LEXICAL else "no") == "yes"
    global TRIAGE_ON, BRIEF, RERANK
    TRIAGE_ON = d.get("triage", "yes" if TRIAGE_ON else "no") == "yes"
    RERANK = d.get("rerank", "on" if RERANK else "off") == "on"          # v16 O1 (dial M40)
    global CONTEXT_PROMPTS, PERSONA_PRICED
    CONTEXT_PROMPTS = num("context_prompts", CONTEXT_PROMPTS, int)       # v16 O2/O9 (dial M41)
    PERSONA_PRICED = d.get("persona_priced", "yes" if PERSONA_PRICED else "no") == "yes"   # v17 (dial M42)
    global THOMPSON_SLOTS, OVERLAP_EDGES
    THOMPSON_SLOTS = num("thompson_slots", THOMPSON_SLOTS, int)          # v18 (dial M44, harvest row 14)
    OVERLAP_EDGES = d.get("overlap_edges", "yes" if OVERLAP_EDGES else "no") == "yes"   # v18 (dial M45)
    BRIEF = d.get("brief_sheet", "yes" if BRIEF else "no") == "yes"
    global FAIR_ASKWORDS, FAIR_CONTEXT, FAIR_NO_TOOL
    FAIR_ASKWORDS = d.get("fair_askwords", "yes" if FAIR_ASKWORDS else "no") == "yes"
    FAIR_CONTEXT = d.get("fair_context", "yes" if FAIR_CONTEXT else "no") == "yes"
    FAIR_NO_TOOL = d.get("fair_no_tool", "yes" if FAIR_NO_TOOL else "no") == "yes"
    NEED_FLOOR = num("need_floor", NEED_FLOOR)
    global ODDS_SHOWN, HINDSIGHT_SHOWN, REHEARSE_WORKERS
    ODDS_SHOWN = d.get("odds_shown", "yes" if ODDS_SHOWN else "no") == "yes"
    HINDSIGHT_SHOWN = d.get("hindsight_shown", "yes" if HINDSIGHT_SHOWN else "no") == "yes"
    REHEARSE_WORKERS = num("rehearse_workers", REHEARSE_WORKERS, int)
    global THINK_FIRST, ASK_FIRST, SELF_MAX
    THINK_FIRST = d.get("think_first", "yes" if THINK_FIRST else "no") == "yes"   # dial M23 (no since 2026-10-24)
    ASK_FIRST = d.get("ask_first", "yes" if ASK_FIRST else "no") == "yes"         # dial M50
    SELF_MAX = num("self_pick_max", SELF_MAX, int)                                # dial M47 (0 = never picks itself)
    for k in ("raw", "body", "network", "concept", "family", "ncd", "owner", "asks", "meaning", "personal", "mode", "deliverable", "phase"):
        if f"weight_{k}" in d:
            WEIGHTS[k] = float(d[f"weight_{k}"])
MARGIN = 0.15          # a candidate may outrank one with better fit only if its fit is within this (fit is 0..1)
POOL = 40              # CONSIDER: candidates taken before weighing
W_USE, W_FASC, W_FAV = 0.25, 0.15, 0.15
RATINGS = ("useful", "fascinating", "favourite", "unused", "wrong")
# the user's metrics (2026-10-18), 0-5. INNER are Claude's experience of the work: only Claude can report them, so they
# are self-reports (S3) and never evidence. TOPIC are about the work and checkable: the user's TOPIC ratings feed memory.
METRICS_INNER = ("fascination", "enjoyment", "fun", "feelings", "love", "curiosity", "motivation", "creativity",
                 "abilities")
METRICS_TOPIC = ("generation", "research", "task", "relevant_research", "understanding")
METRIC_ALIAS = {"fascinating": "fascination", "enjoy": "enjoyment", "feeling": "feelings", "full_abilities": "abilities",
                "on_topic_generation": "generation", "gen": "generation", "on_topic_research": "research",
                "relevant_task_doing": "task", "task_doing": "task", "relresearch": "relevant_research",
                "understandings": "understanding", "conceptions": "understanding", "concepts": "understanding"}
MENU_IDEAS = (("A", "FIT", "the conductor's pick: best fit under the no-corner-cutting rule"),
              ("B", "CURIOSITY", "never chosen in any run; taxed: one extra check before trusting it"),
              ("C", "CREATIVE", "one skill per family not in A, builders first: the widest mix"),
              ("D", "RESEARCH", "two readers and a checker: understand the task, then try to break the answer"),
              ("E", "LOVED", "the user's best-rated skills (their topic metrics) that are in this pool"))
RRF_K = 60             # reciprocal rank fusion constant (Cormack et al. 2009)
MEMORY_SIM = 0.25      # word-Jaccard at which a past rated task counts as similar (immune memory, opening book)
NET_ALPHA, NET_SEEDS = 0.5, 8   # network reading: walk-on probability and how many top hits seed it
BM25_K1, BM25_B = 1.2, 0.75    # full-text reading (Robertson and Zaragoza 2009)
WEIGHTS = {"raw": 1.0, "network": 0.5, "body": 1.0, "concept": 2.0,
           "family": 0.0, "ncd": 0.0, "owner": 0.0, "asks": 0.0, "meaning": 3.0,
           "personal": 1.0, "mode": 0.0, "deliverable": 1.0, "phase": 1.0}   # personal: dial M48, mode: dial M49 (2026-10-24, measured)   # meaning: dial M46 (2026-10-24; 3:1 won on both answer keys)   # deliverable: dial M51 (2026-10-25, C2)   # phase: dial M52 (2026-10-25, phase.py; 1.0 measured on both keys, HISTORY_v19.md section 7)
HOOK: dict = {"transcript": None}   # 2026-10-25: the running transcript the UserPromptSubmit hook names (transcript_path), for the phase reading
# 2026-10-25 (scenario C2 "draw a chart of the equity curve"): both readers weigh the SUBJECT noun (equity curve) over
# the DELIVERABLE the making verb asks for (a chart), so two risk-number skills that draw nothing outranked the chart
# skill. The deliverable reading: when a making verb is followed within four words by an output kind from this closed
# list, the skills whose name or description names that kind keep their fused order and gain one more vote.
MAKE_VERBS = {"draw", "plot", "chart", "graph", "make", "build", "create", "render", "produce", "generate", "visualize",
              "visualise", "show", "export", "print", "write", "turn", "sketch", "design", "give", "prepare", "put"}
DELIVERABLES = {"chart": "chart", "charts": "chart", "graph": "graph", "graphs": "graph", "plot": "plot", "plots": "plot",
                "dashboard": "dashboard", "dashboards": "dashboard", "visualization": "visuali", "visualisation": "visuali",
                "figure": "figure", "figures": "figure", "diagram": "diagram", "diagrams": "diagram", "deck": "deck",
                "slide": "slide", "slides": "slide", "presentation": "presentation", "powerpoint": "powerpoint",
                "spreadsheet": "spreadsheet", "pdf": "pdf", "image": "image", "images": "image", "png": "png", "svg": "svg",
                "heatmap": "heatmap", "histogram": "histogram", "sparkline": "sparkline",
                # 2026-10-25 (artifact-diagramming): the diagram kinds; "flow chart" (two words) is folded to flowchart
                "flowchart": "flowchart", "flowcharts": "flowchart", "schematic": "schematic", "schematics": "schematic",
                "wireframe": "wireframe", "wireframes": "wireframe", "mockup": "mockup", "mockups": "mockup",
                "picture": "picture", "pictures": "picture"}
# Kinds of one family: a skill whose words start with any stem of the family makes the deliverable (a flowchart is a
# diagram; "diagramming" starts with "diagram"). Stems only: no skill is named here.
DELIVERABLE_KIN = {"diagram": ("flowchart", "schematic"), "flowchart": ("diagram",), "schematic": ("diagram",),
                   "wireframe": ("mockup",), "mockup": ("wireframe",)}
ASK_FIRST = True       # dial M50 (2026-10-24, the user: "ask clarifying questions before it does its job"): the sheet lists them
THINK_FIRST = False    # dial M23: True = no picks until Claude writes --concepts; the user 2026-10-24: picks without concepts   # v15: three readings kept at 0 until measured (dials M37-M39); v16 O10: lexicon, feedback, intents removed (ablation: COSTS)
DIAL_SHA = "defaults"
NEW_MAX = 8            # at most this many NEW skills join one pool (v11 added ~400 plugin skills at once)
HEALTH_GATE = True     # v12: run each pick's own --selftest (cached by hash); a FAIL is swapped out and shown
STABLE_AT = 0.75       # E34's bar: STABLE when the pick survives this share of leave-one-part-out readings
STABILIZE = False      # v12 experiment: re-rank within MARGIN by stability; 58 held-out: no change (13/17/46), so off
FAMILY_CAP = 2         # diversity: a third skill of one family is replaced by a near-tie from another family
# v10 concept reading (the user 10-19: "relying far to much on key words and not enough on conceptual understanding").
# The task is restated by Claude as operations (tags from cards/vocab.json) and analogies, and matched against each
# skill's mechanism line (cards/mechanisms.jsonl: does / tags / world). Values fixed before E35 ran, not tuned on it.
CONCEPT_PULL = 2       # each concept's best N mechanism matches join the pool even when they share no task word
WONDER_K = 3           # far-family concept matches shown apart; each must be run on the subject before it counts
NEED_FLOOR = 0.35      # a concept whose best match (0..1) is below this is a NEEDED skill (seed for skill-foundry)
DEMOTE_LEXICAL = True  # v10e item 5: on the meaning ballot, word-reading skills (cards/lexical.json) go last (dial M27)
BALLOTS = True         # v10d: with concepts, picks alternate between a words ballot and a meaning ballot (dial M26)
SELF = "skill-maestro" # v11 never picked itself; 2026-10-24 (the user): it may, when the prompt is about choosing skills, rarely
SELF_TOP, SELF_MAX, SELF_WINDOW = 3, 12, 20  # dial M47: meaning must rank it in the top 3, and at most 12 of the last 20 runs (the user 2026-10-24)


def self_pick_allowed(meaning_top: list[str], state_dir: Path, record: bool = True) -> tuple[bool, str]:
    """May the Maestro be one of its own picks on this prompt? Only when the meaning reading ranks it in the top
    SELF_TOP (the prompt is about choosing or using skills) and it was picked in fewer than SELF_MAX of the last
    SELF_WINDOW runs that asked (not excessively). The decision is recorded in state/self_picks.json."""
    want = SELF in list(meaning_top)[:SELF_TOP]
    p = Path(state_dir) / "self_picks.json"
    try:
        hist = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
    except (OSError, ValueError):
        hist = []
    recent = sum(1 for x in hist[-SELF_WINDOW:] if x)
    ok = want and recent < SELF_MAX
    why = ("not about choosing skills" if not want else
           f"picked {recent} of the last {SELF_WINDOW} runs: at the cap of {SELF_MAX}" if not ok else
           f"the prompt is about choosing skills (meaning top {SELF_TOP}); {recent} of the last {SELF_WINDOW} runs")
    if record and want:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps((hist + [ok])[-200:]), encoding="utf-8")
        except OSError:
            pass
    return ok, why
# v14 fairness (the user 2026-10-21: no skill favoured for being used more often or for having more written about it).
# Each switch is measured by fairness.py and by eval before it is kept; see references/FAIRNESS.md.
FAIR_ASKWORDS = True   # A (kept: pool share of self-describing skills 38% -> 23%, accuracy level): the self-referential asking words ("skill", "skills", "maestro") never reach the ranking
FAIR_CONTEXT = True    # C (kept: held-out @1 5 -> 7, custom 6 -> 8): a skill's rating record counts only from past tasks similar to this one (no global fame)
FAIR_NO_TOOL = False   # D: no bonus for having a script over being a written guide
RERANK = False         # v16 O1: the learned judge over the pool (dial M40); needs a saved model in the state folder
CONTEXT_PROMPTS = 2    # v16 O2/O9: a FULL score also reads the running session's last N prompts (dial M41); 0 = off
PERSONA_PRICED = True  # v17 (dial M42): a persona pick is shown as a priced pick that needs a FIT, never a default
THOMPSON_SLOTS = 0     # v18 (dial M44): the last N pool slots go to Thompson draws from ranks 41-120; 0 = off
OVERLAP_EDGES = False  # v18 (dial M45): the survey's overlaps (cards/tested.jsonl) join the network the readings walk


def thompson_slots(ranked: list[dict], pool: list[dict], stats: dict, seed: str, k: int | None = None) -> list[dict]:
    """v18 (harvest row 14, from ruflo's bandit routing, kept honest): exploration slots at the END of the pool. Each
    candidate just outside the pool (ranks POOL+1 .. 3*POOL) draws theta ~ Beta(good+1, bad+1) from its own record
    (useful/favourite = good; wrong/unused = bad; an untried skill draws Beta(1,1)); the k highest draws replace the
    pool's last k entries, each marked "Thompson slot". Seeded by the task text, so the same ask shows the same sheet.
    The point is data: skills the ratings never reach get a turn in the pool, so their record can start. Off (0)
    until a coverage count over weeks shows the pool@40 it costs buys ratings on the long tail."""
    k = THOMPSON_SLOTS if k is None else k
    if k <= 0 or not pool or len(ranked) <= len(pool):
        return pool
    import random
    rng = random.Random(seed)
    names = {c["name"] for c in pool}
    cands = [c for c in ranked[len(pool):3 * len(pool)] if c["name"] not in names and c["name"] != SELF]
    draws = []
    for c in cands:
        r = stats.get(c["name"], {})
        good = r.get("useful", 0) + r.get("favourite", 0)
        bad = r.get("wrong", 0) + r.get("unused", 0)
        draws.append((rng.betavariate(good + 1, bad + 1), c, good, bad))
    draws.sort(key=lambda x: -x[0])
    out = pool[:max(0, len(pool) - min(k, len(draws)))]
    for theta, c, good, bad in draws[:k]:
        out.append({**c, "via": f"Thompson slot (exploration, dial M44; draw {theta:.2f} from {good} good / {bad} bad)"})
    return out
SESSION_NOTE = """SKILL MAESTRO, five lines (a reminder, not a trigger):
1. Open work (design, invent, explore, a vague card, a long ask): run `python ~/.claude/skills/skill-maestro/maestro.py score "<the ask>"` first; it answers SKIP, QUICK or FULL in ~200 tokens.
2. SKIP or QUICK: build; use at most the finder's picks it names (1-22 by the task's size).
3. FULL: restate the ask as operations with --concepts, then read only the picks that fit.
4. Prove a pick on the real subject before reading or rating it: `try`, then `fit RUN SKILL kind= question= assumes= used= "why"`.
5. A task Claude can plainly do in one step needs no Maestro."""
ODDS_SHOWN = True      # v15: every sheet forecasts the Maestro's own odds on this kind of task (dial M34)
HINDSIGHT_SHOWN = True # v15: the skills reached for after similar past prompts, shown as a self-report (dial M35)
REHEARSE_WORKERS = 2   # v15: probes `rehearse` runs at once (dial M36; a 3.9 GB PC with other sessions open)
ASK_WORDS = {"skill", "skills", "maestro"}
TRIAGE_ON = True       # v11: score first decides SKIP / QUICK / FULL and answers SKIP and QUICK in a few lines (dial M28)
BRIEF = True           # v11: the default sheet is the short one; --full prints every section (dial M29)
COVER_MAX = 3          # v10b: an operation concept with no chosen skill among its best matches gets its best one added
SPARK_K = 3            # v10b: creative operators shown on every sheet (the user 10-19: "inspire a little bit of creativity")
GENERATIVE = ("combine-parents", "analogize", "generate-variants", "explore-curiosity", "name-coin", "evolve-iterate",
              "reframe-viewpoint")
MECHS = HERE / "cards" / "mechanisms.jsonl"
MECHS_AUTO = HERE / "cards" / "mechanisms_auto.jsonl"   # v14: built by `cards --auto` for skills nobody wrote a line for
VOCAB = HERE / "cards" / "vocab.json"
# Words that describe the asking, not the task: "use your full array of skills" pulls library-housekeeping skills
# (both GT175 test runs on 2026-10-18 needed them removed by hand).
META = {"use", "using", "your", "our", "full", "array", "skill", "skills", "consider", "considering", "please", "make",
        "sure", "best", "most", "fascinating", "inspiring", "enjoyable", "favorite", "favourite", "approach", "show",
        "tell", "let", "know", "which", "should", "would", "could", "every", "entire", "really", "actually", "just",
        "help", "want", "need", "way", "things", "thing", "stuff", "all", "any", "maestro", "optimal", "useful"}
CHECKER = re.compile(r"\b(test|tests|check|checks|audit|verify|verifies|lint|plant|falsif\w*|proof|prove|proves|"
                     r"refut\w*|replicat\w*|referee|mutation|red-team|adversar\w*)\b", re.I)
ROLES = {   # the work's own phases; a skill's role is read from its name and the first sentence of its description
    "UNDERSTAND": re.compile(r"\b(read|reads|map|lens|view|eye|explain|survey|index|find|finds|inventor\w*|presuppos\w*|"
                             r"assum\w*|context|catalog\w*|browse|trace|search)\b", re.I),
    "BUILD": re.compile(r"\b(build|builds|compose|composes|forge|scaffold|write|writes|generat\w*|create|creates|design|"
                        r"implement\w*|sketch|draft|breed|splice|add)\b", re.I),
    "VERIFY": CHECKER,
    "LAND": re.compile(r"\b(land|landing|pen|commit|merge|push|branch|handoff|hand-off|report|receipt|ledger|publish|"
                       r"mailbox|release|archive)\b", re.I),
}
PHASE_ORDER = ("UNDERSTAND", "BUILD", "VERIFY", "LAND")
KINDS = {   # what a skill takes as input / what a task works on (v7b; the user: does the skill work on the task at hand?)
    "LOG": re.compile(r"\b(append-only|ledger|log|logs|chain|jsonl|ordered record|decisions\.md|errata|timestamps?)\b", re.I),
    "SERIES": re.compile(r"\b(series|returns?|prices?|bars?|ohlc\w*|candles?|time-series|signal|signals|volatility)\b", re.I),
    "CODE": re.compile(r"\b(code|python|function|functions|module|modules|repo|git|commit|tests?|mutants?|bytecode)\b", re.I),
    "PLAN": re.compile(r"\b(plan|plans|card|cards|spec|roadmap|milestones?|phases?)\b", re.I),
    "TEXT": re.compile(r"\b(text|texts|note|notes|sentences?|prose|report|reports|document|draft|reply|claims?)\b", re.I),
    "GRAPH": re.compile(r"\b(graph|graphs|network|nodes|edges|dependency|dependencies)\b", re.I),
    "SKILLS": re.compile(r"\b(skill|skills|library|SKILL\.md)\b", re.I),
}


# Withheld (rule P1: a detector that fails its own test shows nothing). Bench E26, 2026-10-18: it missed the misfit
# it was built for (cross-cutting-check's description claims "numbered plans"; the misfit was its assumption that rows
# cite only ids above them, which the plan breaks on purpose) and flagged 5/100 labelled-good skills (Wilson 95%
# up to 0.112 > 0.10). Running the pick on the subject (try / fit) is what catches such a misfit.
KIND_FLAG_SHOWN = False


def kinds_of(text: str) -> set[str]:
    return {k for k, rx in KINDS.items() if rx.search(text)}


def kind_mismatch(skill_name: str, desc: str, task: str) -> str | None:
    """KIND_MISMATCH when the task names a subject kind and the skill's input kinds share none of it. TEXT counts
    as general (a text lens reads any written subject: a plan, a report, a note)."""
    tk = kinds_of(task) - {"SKILLS"}
    sk = kinds_of(skill_name.replace("-", " ") + " " + desc.split(". ")[0])
    if not tk or not sk:
        return None
    if "TEXT" in sk and tk & {"PLAN", "TEXT", "LOG"}:
        return None
    if sk & tk:
        return None
    return f"KIND_MISMATCH: it takes {'/'.join(sorted(sk))}, the task works on {'/'.join(sorted(tk))}"
SCOPE = re.compile(r"[^.;!?\n]*\b(?:do not|don't|dont|never|only|without|not yet|no more than|stop)\b[^.;!?\n]*", re.I)


def other_skill_roots(home: Path | None = None) -> list[tuple[Path, str, str]]:
    """Every skill Claude Code can run besides the custom libraries, as (folder of skill folders, name prefix,
    source): the account's claude.ai-synced skills (run as anthropic-skills:NAME) and each installed plugin's
    skills (run as PLUGIN:NAME). Built-in skills (simplify, dataviz, ...) live inside the claude program, not on
    disk, so no script can read them."""
    home = home or CLAUDE_HOME
    out: list[tuple[Path, str, str]] = []
    synced = home / "skills" / "synced"
    if synced.is_dir():
        out += [(d, "anthropic-skills:", "synced") for d in sorted(synced.iterdir()) if d.is_dir()]
    plugins = home / "plugins"
    paths: list[Path] = []
    def install_paths(node) -> list[str]:  # every "installPath" in installed_plugins.json, whatever its version
        if isinstance(node, dict):
            return [v for k, v in node.items() if k == "installPath" and isinstance(v, str)] + \
                   [p for v in node.values() for p in install_paths(v)]
        return [p for v in node for p in install_paths(v)] if isinstance(node, list) else []
    try:                                   # the PC: installed plugins only (marketplace folders hold uninstalled ones)
        paths += [Path(p) for p in install_paths(json.loads((plugins / "installed_plugins.json").read_text(encoding="utf-8")))]
    except (OSError, ValueError):
        pass
    if (plugins / "synced").is_dir():      # claude.ai-synced plugins (cloud sessions, the desktop app)
        paths += [m.parent.parent for m in sorted((plugins / "synced").glob("*/*/.claude-plugin/plugin.json"))]
    seen: set[str] = set()
    for p in paths:
        try:
            man = json.loads((p / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = man.get("name") or p.name
        if name in seen:
            continue
        seen.add(name)
        spec = man.get("skills") or []
        spec = [spec] if isinstance(spec, str) else list(spec)
        dirs = {(p / "skills").resolve()} if (p / "skills").is_dir() else set()
        for s in spec:
            d = (p / s).resolve()
            dirs.add(d.parent if (d / "SKILL.md").is_file() else d)
        out += [(d, f"{name}:", f"plugin {name}") for d in sorted(dirs) if d.is_dir()]
    return out


class MiniFinder:
    """A shareable stand-in for skill-finder (same shapes: load, _tokens, search) so the Maestro runs in a library
    that has no skill-finder. Plain TF-IDF over name and description; the real finder's stop list is richer."""
    STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "use", "when", "whenever", "max", "any",
            "are", "its", "one", "not", "all", "each", "every", "then", "than", "them", "they", "you", "your"}

    @classmethod
    def _tokens(cls, text: str) -> list:
        return [t for t in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", str(text).lower()) if len(t) > 2 and t not in cls.STOP]

    @classmethod
    def load(cls, root) -> list:
        out = []
        for d in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
            name, desc = d.name, ""
            text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
            if text.startswith("---"):
                for line in text.splitlines()[1:60]:
                    if line.strip() == "---":
                        break
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("'\"")
                    elif line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip("'\"")
            tool = any(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
            out.append({"name": name, "desc": desc, "tool": tool, "name_toks": set(cls._tokens(name)),
                        "toks": cls._tokens(name + " " + desc)})
        return out

    @classmethod
    def search(cls, skills: list, query: str, top: int = 5) -> list:
        import math
        q = set(cls._tokens(query))
        if not q or not skills:
            return []
        df: dict[str, int] = {}
        for s in skills:
            for t in set(s["toks"]):
                df[t] = df.get(t, 0) + 1
        scored = []
        for s in skills:
            sc = sum(math.log((len(skills) + 1) / (df[t] + 0.5)) * (2.0 if t in s["name_toks"] else 1.0)
                     for t in q & set(s["toks"]))
            if sc > 0:
                scored.append((sc, s))
        scored.sort(key=lambda x: (-x[0], x[1]["name"]))
        return [{"name": s["name"], "score": round(sc, 3), "tool": s["tool"], "when": s["desc"].split(". ")[0][:160]}
                for sc, s in scored[:top]]


class MiniPin:
    """Stand-in for core-skill-pin: no trigger table, the plain search."""

    @staticmethod
    def load_triggers(path) -> dict:
        try:
            return {k: v for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items() if not k.startswith("_")}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def pinned_search(fs, skills: list, query: str, triggers: dict, top: int = 5) -> list:
        return fs.search(skills, query, top=top)


LIMIT_MARK = re.compile(r"\b(never|no|not|must not|only|until|banned|forbidden|stays? disabled|do not|don't)\b", re.I)
GOAL_MARK = re.compile(r"\b(goal|purpose|aim|mission|we are building|this project|the plan|objective)\b", re.I)
PICKS_MAX = 22
OWNER = __import__("os").environ.get("MAESTRO_OWNER", "the owner")   # who rates: "the user" on his PC (set MAESTRO_OWNER), "the owner" elsewhere


def charter(project: Path | None) -> dict:
    """The project's GOALS and LIMITS, read before any skill is chosen (the user, 2026-10-20: "it needs to understand the
    goals and limits of the project before it can understand which skills it can decide to use").
    Sources, first found wins: MAESTRO_PROJECT.md or .claude/maestro_project.md with `GOAL:` / `LIMIT:` lines (any
    project, no guessing); else CLAUDE.md: the opening paragraph and goal-worded lines are goals, bullet lines under a
    heading that names limits or rules, or that carry never/no/not/only/until, are limits."""
    out = {"goals": [], "limits": [], "source": None}
    if project is None:
        return out
    for f in (project / "MAESTRO_PROJECT.md", project / ".claude" / "maestro_project.md"):
        if f.is_file():
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if ln.upper().startswith("GOAL:"):
                    out["goals"].append(ln[5:].strip())
                elif ln.upper().startswith("LIMIT:"):
                    out["limits"].append(ln[6:].strip())
            out["source"] = f.name
            return out
    f = project / "CLAUDE.md"
    if not f.is_file():
        return out
    out["source"] = "CLAUDE.md"
    heading, first_para, strict, loose = "", [], [], []
    for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip()
            continue
        if not s:
            continue
        if not first_para and not s.startswith(("-", "*")) and not heading.lower().startswith(("process", "this machine", "where")):
            first_para.append(s)
        elif first_para and len(" ".join(first_para)) < 400 and not s.startswith(("-", "*")) and heading == "" :
            first_para.append(s)
        under_limits = (re.search(r"limit|rule|never|must|stay|boundar", heading, re.I)
                        and not re.search(r"removed|not rules|facts|history|retired", heading, re.I))
        if LIMIT_MARK.search(s) and (under_limits or s.startswith(("-", "*"))):
            (strict if under_limits else loose).append(s.lstrip("-* ").strip())
        elif GOAL_MARK.search(s) and not s.startswith(("-", "*")) and s not in first_para:
            out["goals"].append(s)
    if first_para:
        out["goals"].insert(0, " ".join(first_para)[:300])
    out["goals"] = out["goals"][:4]
    out["limits"] = (strict if strict else loose)[:8]   # a heading that names limits is the source; bullets elsewhere only when there is none
    return out


def limit_hits(limit: str, name: str, desc: str, tokens) -> list[str]:
    """Words of a limit that a skill's name and description also carry: a proper noun of the limit (Kraken,
    TradingView) is enough on its own; otherwise two of its content words. Printed, never silent: the judge decides."""
    text = set(tokens(name + " " + desc))
    # a proper noun is Capitalised-then-lowercase (Kraken, TradingView); ALL-CAPS words (PLAN, API, D22) are not
    proper = {w.lower() for w in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{3,}[A-Za-z]*\b", " " + limit)} - {"max", "claude", "also"}
    content = [w for w in tokens(limit) if len(w) >= 4 and w not in {"only", "until", "never", "real", "signs", "from", "stays", "disabled", "through"}]
    hit_proper = sorted(proper & text)
    hit_words = sorted(set(content) & text)
    if hit_proper or len(hit_words) >= 2:
        return hit_proper + [w for w in hit_words if w not in hit_proper]
    return []


def pick_count(task: str, weighed: list[dict]) -> tuple[int, str]:
    """How many skills this task deserves, 1 to PICKS_MAX (the user: "chooses 1 to 22 different /skills"): two per sentence
    of the ask, one for a task of four words or fewer, never more than the candidates whose fit is at least half
    the best. The reason is printed with the number."""
    sents = [x for x in re.split(r"(?<=[.?!;])\s+|\n+", task.strip()) if x.strip()]
    words = len(task.split())
    eligible = sum(1 for r in weighed if r.get("fit", 0) >= 0.5)
    want = 1 if words <= 4 else 2 * max(1, len(sents))
    n = max(1, min(PICKS_MAX, want, max(1, eligible)))
    return n, f"{len(sents)} sentence(s), {words} words -> {want} wanted; {eligible} candidate(s) within reach; chose {n}"


def deliverable_of(task: str) -> str | None:
    """The output kind a making verb asks for ("draw a chart of ..." -> "chart"; "make me a deck" -> "deck"), as the
    stem that a skill's words must start with; None when the prompt names no deliverable this way. A kind that is also
    a verb counts when it opens the request ("plot the equity curve"). "compute the drawdown of the equity curve" is
    None: no deliverable, the subject decides."""
    toks = re.findall(r"[a-z0-9]+", task.lower())
    toks = [("flowchart" if t == "chart" and i and toks[i - 1] == "flow" else t) for i, t in enumerate(toks)]
    for i, t in enumerate(toks):
        if t in DELIVERABLES and (any(v in MAKE_VERBS for v in toks[max(0, i - 4):i]) or (i == 0 and t in MAKE_VERBS)):
            return DELIVERABLES[t]
    return None


def deliverable_reading(task: str, ordered: list[str], desc: dict[str, str]) -> list[str]:
    """The skills (in the order they already hold) whose name or description names the deliverable the task asks for;
    empty when the task asks for none. Fused with weight_deliverable (dial M51) as one more vote: the chart skill
    gains on the risk-number skills, and nothing moves when no deliverable is named."""
    stem = deliverable_of(task)
    if not stem:
        return []
    stems = (stem,) + DELIVERABLE_KIN.get(stem, ())
    return [n for n in ordered
            if any(w.startswith(stems) for w in re.findall(r"[a-z0-9]+", (n + " " + desc.get(n, "")).lower()))]


def purpose_rank(word_search, task: str, k: int = PICKS_MAX, root: Path | None = None, state_dir: Path | None = None,
                 desc: dict[str, str] | None = None, phase: list[list[str]] | None = None) -> list[dict]:
    """the user 2026-10-24: pick by meaning and purpose, not words. The meaning reading (weight_meaning) and the finder's
    words (weight 1) fused by reciprocal rank; fit is the fused score scaled to the best. Falls back to words alone
    when the meaning vectors are missing. `word_search(task, depth)` returns the finder's rows (name, score).
    2026-10-25: with `desc` (name -> description) the deliverable reading (dial M51) adds its vote."""
    words = [r["name"] for r in word_search(task, 120)]
    mean = meaning_rank(ranking_text(task), 120, root, state_dir) or []
    self_ok, _ = self_pick_allowed([n for n, _ in mean[:SELF_TOP]], Path(state_dir or STATE))
    sc: dict[str, float] = {}
    via: dict[str, list] = {}
    for lst, w, tag in (([n for n, _ in mean], WEIGHTS.get("meaning", 3.0), "meaning"), (words, 1.0, "words")):
        for r, n in enumerate(lst, 1):
            if n == SELF and not self_ok:
                continue
            sc[n] = sc.get(n, 0.0) + w / (RRF_K + r)
            via.setdefault(n, []).append(tag)
    if not sc:
        return []
    if desc and WEIGHTS.get("deliverable"):
        ordered = [n for n, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]
        for r, n in enumerate(deliverable_reading(task, ordered, desc), 1):
            sc[n] += WEIGHTS["deliverable"] / (RRF_K + r)
            via[n].append("deliverable")
    if WEIGHTS.get("phase") and state_dir is not None:      # 2026-10-25 (M52): where sessions went next after what this one just used
        try:
            P = _load(HERE / "phase.py", "phase")
            ctx = phase if phase is not None else P.live_context(Path(state_dir), HOOK.get("transcript"))
            if ctx:
                for r, n in enumerate(P.reading(P.table(P.rows_of(Path(state_dir))), ctx), 1):
                    if n in sc or (desc and n in desc):
                        sc[n] = sc.get(n, 0.0) + WEIGHTS["phase"] / (RRF_K + r)
                        via.setdefault(n, []).append("phase")
        except Exception:  # noqa: BLE001
            pass
    best = max(sc.values())
    rows = [{"name": n, "score": round(s * 1000, 3), "fit": s / best, "via": via[n]} for n, s in sc.items()]
    rows.sort(key=lambda r: (-r["fit"], r["name"]))
    n, _ = pick_count(task, [r for r in rows if r["fit"] >= 0.5 and "meaning" in r["via"]] or rows)
    return rows[:max(k, n)]


def use_line(c: dict, phase: str, subject: str, run: str) -> str:
    """One paste-ready line on how to use a pick on THIS task (the user: "helps prompt best use of the /skills it chooses")."""
    card = c.get("card") or {}
    when = (c.get("when") or "").split(". ")[0][:120]
    cmd = c.get("first_cmd")
    run_as = f"/{c['name']}" if c.get("source") == "built-in" else c["name"]
    parts = [f"{run_as} [{phase}]: {when}" if when else f"{run_as} [{phase}]"]
    parts.append(f"RUN `{cmd}`" if cmd else ("no file to read; invoke it as /" + c["name"] if c.get("source") == "built-in" else "open its SKILL.md and follow its first command"))
    def flat(v):   # a card field is a string or {kind, shape}
        return f"{v.get('kind', '')} - {v.get('shape', '')}".strip(" -") if isinstance(v, dict) else str(v)
    parts.append(f"FEED {flat(card['input'])[:90]}" if card.get("input") else f"FEED {subject}")
    if card.get("output"):
        parts.append(f"EXPECT {flat(card['output'])[:90]}")
    elif card.get("probe"):
        parts.append(f"ASK IT '{str(card['probe'])[:80]}'")
    if card.get("assumes"):
        a = card["assumes"]
        parts.append(f"ASSUMES {(a[0] if isinstance(a, list) else str(a))[:80]}")
    if card.get("not_for"):
        parts.append(f"NOT FOR {str(card['not_for'])[:70]}")
    if card.get("cost"):
        parts.append(f"COST {str(card['cost'])[:40]}")
    if c.get("side_effects"):
        parts.append(f"SIDE EFFECTS {', '.join(c['side_effects'])} - ask first")
    for k, label in (("limit", "LIMIT"), ("health", "HEALTH"), ("switch_on", "OFF HERE")):
        v = c.get(k)
        if v and (k != "health" or v in ("FAIL", "TIMEOUT")):
            parts.append(f"{label}: {str(v)[:90]}")
    parts.append(f"THEN `maestro.py fit {run} {c['name']} works|misfit \"why\"`")
    return "  - " + " | ".join(parts)


def pc_only(cards: dict, desc: dict) -> list[str]:
    """Skills the cards know that this machine lacks, but only when the cards are THIS library's (at least half of
    them present); a stranger's library must not be told it is missing 687 of someone else's skills."""
    if not cards or sum(n in desc for n in cards) < len(cards) / 2:
        return []
    return sorted(n for n in cards if n not in desc)


def builtin_skills() -> dict[str, str]:
    """name -> description of Claude Code's built-in skills (builtins.json beside this file; keys starting with _ are notes)."""
    try:
        d = json.loads((HERE / "builtins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, str)}


def health_of(lib, st, name: str, timeout: int = 60) -> str | None:
    """OK / FAIL / TIMEOUT from the skill's own --selftest (every top-level .py that offers one), run from a neutral
    folder and cached in the state folder by the SKILL.md hash; None when the skill ships no selftest. A pick that
    cannot pass its own test is not a pick (v12)."""
    import subprocess
    import tempfile
    md = lib.skill_md(name)
    if not md.is_file():
        return None
    folder = md.parent
    tools = [p for p in sorted(folder.glob("*.py")) if "--selftest" in p.read_text(encoding="utf-8", errors="replace")]
    if not tools:
        return None
    key = f"{name}@{hashlib.sha256(b''.join(p.read_bytes() for p in [md, *tools])).hexdigest()[:16]}"
    cache_f = st.d / "health.json"
    try:
        cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.is_file() else {}
    except ValueError:
        cache = {}
    if key in cache:
        return cache[key]
    verdict = "OK"
    with tempfile.TemporaryDirectory() as neutral:
        for p in tools:
            try:
                r = subprocess.run([sys.executable, "-B", str(p), "--selftest"], cwd=neutral, capture_output=True,
                                   timeout=timeout)
                if r.returncode != 0:
                    verdict = health_verdict((r.stdout + r.stderr).decode("utf-8", "replace"))
                    break
            except subprocess.TimeoutExpired:
                verdict = "TIMEOUT"
                break
            except OSError:
                verdict = "FAIL"
                break
    cache[key] = verdict
    cache_f.write_text(json.dumps(cache, sort_keys=True), encoding="utf-8")
    return verdict


def health_verdict(output: str) -> str:
    """v17 (scientific-agent-skills tests/_contract/cli.py): a failed selftest is read, not just counted. A genuinely
    absent module is NEEDS <pkg> (the skill is whole; this PC lacks a package: shown, never swapped); `ImportError:
    cannot import name` is DRIFT (the package is there and the skill calls an API that moved: the most valuable catch,
    swapped out); anything else is FAIL."""
    for line in reversed(output.strip().splitlines()):
        line = line.strip()
        if line.startswith("ModuleNotFoundError:"):
            m = re.search(r"No module named '([^']+)'", line)
            return f"NEEDS {m.group(1).split('.')[0]}" if m else "NEEDS package"
        if line.startswith("ImportError:"):
            msg = line.split(":", 1)[1].strip()
            if "No module named" in msg:
                m = re.search(r"No module named '([^']+)'", msg)
                return f"NEEDS {m.group(1).split('.')[0]}" if m else "NEEDS package"
            return "DRIFT"
    return "FAIL"


SWAP_HEALTH = ("FAIL", "TIMEOUT", "DRIFT")                # v17: NEEDS <pkg> is shown, never swapped


def script_side_effects(folder: Path, cache_dir: Path | None = None) -> list[str]:
    """v17 (scientific-agent-skills tests/_contract/structure.py:358-390, extended): read a skill's own scripts as an
    AST, never import or run them, and name the world-changing calls they make: delete (os.remove/unlink/rmdir,
    shutil.rmtree, Path.unlink/rmdir), exec (eval/exec/os.system/os.popen), push/commit (git push/commit in a
    subprocess argument), post/send (requests.post/put/delete, urlopen with data, smtplib). Cached by the scripts' sha
    in the state folder. A description can hide a verb; the code cannot."""
    import ast
    pys = sorted(p for p in folder.glob("*.py") if p.is_file()) if folder.is_dir() else []
    if not pys:
        return []
    key = hashlib.sha256(b"".join(p.read_bytes() for p in pys)).hexdigest()[:16]
    cache_f = (cache_dir / "side_effects.json") if cache_dir else None
    cache = {}
    if cache_f and cache_f.is_file():
        try:
            cache = json.loads(cache_f.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    if key in cache:
        return cache[key]
    DELETE = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"), ("shutil", "rmtree")}
    EXEC = {("os", "system"), ("os", "popen")}
    POST = {("requests", "post"), ("requests", "put"), ("requests", "delete"), ("requests", "patch"), ("smtplib", "SMTP")}
    found: set[str] = set()

    def dotted(node) -> tuple[str, str] | None:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return (node.value.id, node.attr)
        return None

    for p in pys:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            d = dotted(f)
            if isinstance(f, ast.Name) and f.id in ("eval", "exec"):
                found.add("exec")
            if d in DELETE or (isinstance(f, ast.Attribute) and f.attr in ("unlink", "rmtree", "rmdir") and d is None):
                found.add("delete")
            if d in EXEC:
                found.add("exec")
            if d in POST:
                found.add("send" if d[0] == "smtplib" else "post")
            if d == ("urllib.request", "urlopen") or (isinstance(f, ast.Attribute) and f.attr == "urlopen"):
                if any(kw.arg == "data" for kw in node.keywords) or len(node.args) > 1:
                    found.add("post")
            if (isinstance(f, ast.Attribute) and f.attr in ("run", "check_output", "check_call", "call", "Popen")) and \
                    d and d[0] == "subprocess":
                lits = " ".join(str(getattr(c, "value", "")) for c in ast.walk(node) if isinstance(c, ast.Constant))
                if re.search(r"\bgit\b.*\bpush\b|\bpush\b.*\bgit\b", lits):
                    found.add("push")
                if re.search(r"\bgit\b.*\bcommit\b", lits):
                    found.add("commit")
                if re.search(r"\brm\s+-[rf]|\brmdir\b|\bdel\s+/", lits):
                    found.add("delete")
    out = sorted(found)
    if cache_f:
        cache[key] = out
        try:
            cache_f.write_text(json.dumps(cache, sort_keys=True), encoding="utf-8")
        except OSError:
            pass
    return out


def frontmatter_field(md: Path, field: str) -> str | None:
    """A frontmatter line's value (e.g. allowed-tools, argument-hint), or None. Read as data, never as instructions."""
    if not md.is_file():
        return None
    txt = md.read_text(encoding="utf-8", errors="replace")
    if not txt.startswith("---"):
        return None
    head = txt.split("---", 2)[1] if txt.count("---") >= 2 else ""
    m = re.search(rf"^{re.escape(field)}:\s*(.+)$", head, re.M)
    return m.group(1).strip().strip("'\"") if m else None


def switch_on(name: str, source: str, overrides: dict[str, str], plugins: dict[str, tuple[bool, str]]) -> str | None:
    """What stops this pick from running here, and the exact setting that lets it run; None when it can run."""
    on, key = plugins.get(source[7:], (True, "")) if source.startswith("plugin ") else (True, "")
    if not on:
        return (f"OFF HERE: plugin {source[7:]} is disabled for this project; set \"{key}\": true under "
                "enabledPlugins in .claude/settings.json (or follow its SKILL.md by hand)")
    if overrides.get(name) == "off":
        return (f"OFF HERE: skillOverrides sets {name} \"off\"; change it to \"name-only\" in .claude/settings.json "
                "(or follow its SKILL.md by hand)")
    return None


def settings_files(project: Path | None) -> tuple[Path, ...]:
    """Claude Code's settings files in precedence order (user, then project, then local): later files win."""
    return (CLAUDE_HOME / "settings.json",
            *((project / ".claude" / "settings.json", project / ".claude" / "settings.local.json") if project else ()))


def plugin_states(project: Path | None) -> dict[str, tuple[bool, str]]:
    """enabledPlugins ("name@marketplace": true/false) from user, project and local settings; later files win.
    Plugin name -> (enabled, the exact settings key)."""
    out: dict[str, tuple[bool, str]] = {}
    for f in settings_files(project):
        try:
            for k, v in (json.loads(f.read_text(encoding="utf-8")).get("enabledPlugins") or {}).items():
                out[k.split("@")[0]] = (bool(v), k)
        except (OSError, ValueError, AttributeError):
            pass
    return out


def skill_overrides(project: Path | None) -> dict[str, str]:
    """Claude Code's skillOverrides (user settings, then the project's, which win). "off": the harness will not run
    the skill at all, so it leaves the pool; "user-invocable-only": only the user can start it, by typing /name;
    "name-only" and "on": Claude can still run it, nothing to say."""
    out: dict[str, str] = {}
    for f in settings_files(project):
        try:
            out.update(json.loads(f.read_text(encoding="utf-8")).get("skillOverrides") or {})
        except (OSError, ValueError, AttributeError):
            pass
    return out


EXTRAS_PKG = "skill-maestro-extras"       # v20: the research modules (conduct, inverse, introspect, rerank, fairness) ship apart
EXTRA_MODULES = ("conduct", "inverse", "introspect", "rerank", "fairness")


class ExtraMissing(ImportError):
    """A command asked for a module that ships in skill-maestro-extras, and that package is not installed beside this copy."""


def _extras_dir() -> Path:
    """v20: MAESTRO_EXTRAS, else the folder skill-maestro-extras beside this skill's folder."""
    env = os.environ.get("MAESTRO_EXTRAS")
    return Path(env).expanduser() if env else HERE.parent / EXTRAS_PKG


def _module_path(name: str) -> Path | None:
    """Where module `name` lives: beside this file, else in the extras package, else None."""
    for d in (HERE, _extras_dir()):
        if (d / f"{name}.py").is_file():
            return d / f"{name}.py"
    return None


def _load(path: Path, name: str):
    path = Path(path)
    if not path.is_file():                      # v20: the module may be an extra
        alt = _module_path(path.stem)
        if alt is None:
            raise ExtraMissing(f"extra: {path.name} is part of {EXTRAS_PKG}; install it beside this folder "
                               f"({_extras_dir()}) or point MAESTRO_EXTRAS at it")
        path = alt
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _lib_load(fs, r: Path) -> list:
    """v15: the prepared index (index.py) for a root big enough to matter, else find_skill.load. Any doubt: the plain loader."""
    ix = HERE / "index.py"
    try:
        if ix.is_file():
            return _load(ix, "maestro_index").indexed_load(fs, r, STATE)
    except Exception:  # noqa: BLE001
        pass
    return fs.load(r)



_MEANING = {}
MEANING_WAIT = 90.0   # seconds score/eval wait for the resident meaning helper to start; the whisper hook sets 0


def meaning_rank(task: str, depth: int = 120, root: Path | None = None, state: Path | None = None) -> list[tuple[str, float]] | None:
    """The meaning reading (meaning.py v2): in this process when fastembed imports, else through its venv. The vector
    file keeps itself current (new or changed skills are embedded at the query). None when fastembed is nowhere."""
    if "mod" not in _MEANING:
        try:
            spec = importlib.util.spec_from_file_location("maestro_meaning", HERE / "meaning.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _MEANING["mod"] = mod
            try:
                import fastembed  # noqa: F401
                _MEANING["inproc"] = True
            except ImportError:
                _MEANING["inproc"] = False
        except Exception:  # noqa: BLE001
            _MEANING["mod"] = None
    mod = _MEANING["mod"]
    if mod is None or __import__("os").environ.get("MAESTRO_NO_MEANING") == "1":
        return None
    try:
        root = Path(root) if root else ROOT
        if _MEANING["inproc"]:
            return mod.rank([task], depth, root, Path(state) if state else None)[0]
        return mod.rank_anywhere(task, depth, root, Path(state) if state else None, wait=MEANING_WAIT)   # the resident helper
    except Exception:  # noqa: BLE001
        return None


def meaning_ok() -> bool:
    """True when the meaning model runs in this process (fastembed imports) and is not switched off."""
    if "mod" not in _MEANING:
        try:
            spec = importlib.util.spec_from_file_location("maestro_meaning", HERE / "meaning.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _MEANING["mod"] = mod
            try:
                import fastembed  # noqa: F401
                _MEANING["inproc"] = True
            except ImportError:
                _MEANING["inproc"] = False
        except Exception:  # noqa: BLE001
            _MEANING["mod"] = None
    return bool(_MEANING.get("mod")) and bool(_MEANING.get("inproc")) and __import__("os").environ.get("MAESTRO_NO_MEANING") != "1"


def select_mode(task: str, state: Path | None = None, force: str | None = None) -> dict | None:
    """The prompt's mode (modes.py): matched by meaning, or forced with --mode. None when the meaning model is absent
    and nothing was forced."""
    try:
        D = _load(HERE / "modes.py", "modes")
        if force:
            return D.select(None, task, Path(state or STATE), force)
        if not meaning_ok():
            return None
        return D.select(_MEANING["mod"], task, Path(state or STATE))
    except KeyError:
        raise
    except Exception:  # noqa: BLE001
        return None


class Library:
    """The skill library (or several: the user library plus a project's .claude/skills) seen through its own tools.
    The tools load from the first root; a skill present in two roots is taken from the first."""

    def __init__(self, root: Path, extra: tuple[Path, ...] = (), everything: bool = True) -> None:
        self.everything = everything
        self.root = Path(root)
        self.roots = [self.root] + [Path(e) for e in extra if Path(e).is_dir() and Path(e) != self.root]
        fsp, pinp = companion(self.root, "find_skill.py"), companion(self.root, "core_pin.py")
        self.fs = _load(fsp, "find_skill") if fsp.is_file() else MiniFinder()      # v12: standalone when the
        self.pin = _load(pinp, "core_pin") if pinp.is_file() else MiniPin()        # sibling skills are absent
        self.standalone = not (fsp.is_file() and pinp.is_file())
        trig = companion(self.root, "core_triggers.json")
        self.triggers = self.pin.load_triggers(trig) if trig.is_file() else {}
        seen: set[str] = set()
        self.skills = []
        self.md: dict[str, Path] = {}        # every skill's SKILL.md, by the name Claude Code runs it under
        self.source: dict[str, str] = {}     # "" for the libraries above, else plugin / synced
        for r, prefix, src in [(r, "", "") for r in self.roots] + (other_skill_roots() if self.everything else []):
            dirs = sorted(p for p in r.iterdir() if p.is_dir() and (p / "SKILL.md").exists())   # find_skill.load's order
            for d, s in zip(dirs, _lib_load(self.fs, r)):          # v15: the prepared index (index.py)
                if prefix:
                    s = {**s, "name": prefix + s["name"]}
                    s["name_toks"] = set(self.fs._tokens(s["name"]))
                    s["toks"] = self.fs._tokens(s["name"] + " " + s["desc"])
                if s["name"] not in seen:
                    seen.add(s["name"])
                    self.skills.append(s)
                    self.md[s["name"]] = d / "SKILL.md"
                    self.source[s["name"]] = src
        if self.everything:                   # Claude Code's built-in skills: not on disk, a snapshot in builtins.json
            for n, d in builtin_skills().items():
                if n not in seen:
                    seen.add(n)
                    self.skills.append({"name": n, "desc": d, "tool": False, "name_toks": set(self.fs._tokens(n)),
                                        "toks": self.fs._tokens(n + " " + d)})
                    self.source[n] = "built-in"
        self.desc = {s["name"]: s["desc"] for s in self.skills}
        idx = self.root / "skills-index" / "build_index.py"
        self.index = _load(idx, "build_index") if idx.is_file() else None
        self._body = None

    def search(self, task: str, top: int) -> list[dict]:
        return self.pin.pinned_search(self.fast, self.skills, task, self.triggers, top=top)

    @property
    def fast(self):
        """v15: the finder's search with its document frequencies computed once per library (index.FastSearch,
        proven identical by its selftest); the finder itself when it is the mini finder or index.py is absent."""
        if not hasattr(self, "_fast"):
            ix = HERE / "index.py"
            self._fast = (_load(ix, "maestro_index").FastSearch(self.fs, self.skills)
                          if ix.is_file() and hasattr(self.fs, "STOP") else self.fs)
        return self._fast

    def family(self, name: str) -> str:
        return self.index._family(name, self.desc.get(name, "")) if self.index else "?"

    def skill_md(self, name: str) -> Path:
        if name in self.md:
            return self.md[name]
        for r in self.roots:
            if (r / name / "SKILL.md").is_file():
                return r / name / "SKILL.md"
        return self.root / name / "SKILL.md"

    def snapshot(self) -> dict[str, str]:
        if self._snap is None:
            shas = {s["name"]: s["sha"] for s in self.skills if s.get("sha")}      # v15: from the prepared index
            self._snap = {n: shas.get(n) or hashlib.sha256(p.read_bytes()).hexdigest()[:16] for n, p in sorted(self.md.items())}
        return self._snap

    everything = True       # also plugin and account-synced skills (v11); False = the custom libraries only
    _snap = None

    # --- CONSIDER: several readings of the task, fused -------------------------------------------------------------
    def variants(self, task: str) -> dict[str, str]:
        """The task read three ways and fused: as written; with the user's own terms expanded to their meaning
        (max-lexicon); with the top hits' description words added (pseudo-relevance feedback). Ablation on the probe
        sets (2026-10-18, workspace ablate.py, 12 subsets): this trio was the only one that kept held-out pool recall
        (40/58) while raising top-3 (14 -> 16/58) and training pool recall (18 -> 19/20). A fourth reading without the
        asking-words is kept apart (_plain): fused, it lowered held-out recall to 38-39/58."""
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", task)
        plain = " ".join(w for w in words if w.lower() not in META) or task
        out = {"raw": task}                        # v16 O10: the lexicon and feedback variants were removed (ablation
        out["_plain"] = plain                      # 2026-10-22: both COST held-out hits at any weight; weight 0 since v14)
        return out

    cache_dir: Path | None = None

    def _cache(self, kind: str):
        if self.cache_dir is None:
            return None, None
        key = hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True).encode()).hexdigest()[:16]
        f = self.cache_dir / f"cache_{kind}_{key}.json"
        return f, (json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None)

    def _save(self, f, data) -> None:
        if f is not None:
            for old in f.parent.glob(f.name.rsplit("_", 1)[0] + "_*.json"):
                old.unlink()                         # one cache per kind: the current library only
            f.write_text(json.dumps(data), encoding="utf-8")

    def graph(self) -> dict[str, set[str]]:
        """The library as a network: skills joined by their own "Pairs with" lines and imports (skill-graph)."""
        if not hasattr(self, "_adj"):
            f, cached = self._cache("graph")
            if cached is None:
                g = self.root / "skill-graph" / "skill_graph.py"
                built = _load(g, "skill_graph").build(self.root).get("adj", {}) if g.is_file() else {}
                cached = {k: sorted(v) for k, v in built.items()}
                self._save(f, cached)
            self._adj = {k: set(v) for k, v in cached.items()}
            if OVERLAP_EDGES:                            # v18 (dial M45): the survey's look-alikes join the network
                for n, row in load_tested(self.tested_path).items():
                    for o in row.get("overlaps") or []:
                        if n in self.desc and o in self.desc and o != n:
                            self._adj.setdefault(n, set()).add(o)
                            self._adj.setdefault(o, set()).add(n)
        return self._adj

    duets: dict[str, set[str]] = {}

    def network(self, seeds: list[tuple[str, float]], steps: int = 20) -> list[str]:
        """Personalized PageRank: activation starts on the top hits (weighted by score) and flows along the
        network, so a skill the leaders all pair with rises even when the task's words never name it."""
        if getattr(self, "_net_key", None) != id(self.duets):   # O4: the merged graph once per library, same answers
            adj = {k: set(v) for k, v in self.graph().items()}
            for a, bs in self.duets.items():             # learned from use: rated useful together in one run
                if a in adj:
                    adj[a] |= {b for b in bs if b in adj}
            self._net_adj = {k: tuple(sorted(v)) for k, v in adj.items()}
            self._net_key = id(self.duets)
        adj = self._net_adj
        tot = sum(s for _, s in seeds) or 1.0
        p0 = {n: s / tot for n, s in seeds}            # an unlinked seed keeps its mass (v6b, bench E07)
        if not p0:
            return []
        p = dict(p0)
        for _ in range(steps):
            nxt = {k: (1 - NET_ALPHA) * v for k, v in p0.items()}
            for n, v in p.items():
                nb = adj.get(n, ())
                if not nb:                               # no links: a self-loop, so the mass stays (not leaked)
                    nxt[n] = nxt.get(n, 0.0) + NET_ALPHA * v
                for m in nb:
                    nxt[m] = nxt.get(m, 0.0) + NET_ALPHA * v / len(nb)
            p = nxt
        return [n for n, _ in sorted(p.items(), key=lambda x: (-x[1], x[0]))]

    def body(self, task: str, top: int) -> list[str]:
        """BM25 over each skill's whole SKILL.md (the finder reads only name and description)."""
        import math
        if self._body is None:
            f, cached = self._cache("body")
            if cached is not None:
                self._body = (cached["tf"], cached["ln"], cached["df"], cached["avg"], cached["N"])
        if self._body is None:
            docs = {}
            for s in self.skills:
                md = self.skill_md(s["name"])
                txt = md.read_text(encoding="utf-8", errors="replace")[:20000] if md.is_file() else s["desc"]
                docs[s["name"]] = self.fs._tokens(s["name"] + " " + s["desc"] + " " + txt)
            df: dict[str, int] = {}
            for toks in docs.values():
                for w in set(toks):
                    df[w] = df.get(w, 0) + 1
            avg = sum(len(v) for v in docs.values()) / max(1, len(docs))
            tf = {n: {} for n in docs}
            for n, toks in docs.items():
                for w in toks:
                    tf[n][w] = tf[n].get(w, 0) + 1
            self._body = (tf, {n: len(v) for n, v in docs.items()}, df, avg, len(docs))
            self._save(f, {"tf": tf, "ln": self._body[1], "df": df, "avg": avg, "N": len(docs)})
        tf, ln, df, avg, N = self._body
        q = set(self.fs._tokens(task))
        sc = {}
        for n, d in tf.items():
            s = 0.0
            for w in q & d.keys():
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                f = d[w]
                s += idf * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * ln[n] / avg))
            if s > 0:
                sc[n] = s
        return [n for n, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))[:top]]

    quick = False
    concept_per: list = []                           # per-concept mechanism matches (set by score when concepts given)

    # v16 O10: the intents (doc2query) reading was removed; ablation 2026-10-22 marked it COSTS at 1.0 and at 0.5.
    # v20: intents/intents.json (276 KB) and its last reader, examples(), removed with it; the pool shows descriptions only.

    _fam_docs = None
    _ncd_docs = None
    _owner = None
    _asks = None
    tested_path = None          # v17 survey: None = cards/tested.jsonl; the selftest points it at a temp file

    def family_reading(self, task: str, depth: int) -> list[str]:
        """v15: a capability tree instead of a flat list (AgentSkillOS, 2026: trees beat flat invocation and the gap
        widens with the library). Families (skills-index) are ranked by BM25 over their members' names and
        descriptions; members inherit their family's place, ordered inside it by their own words match."""
        import math
        if self._fam_docs is None:
            fams: dict[str, list] = {}
            for s in self.skills:
                fams.setdefault(self.family(s["name"]), []).append(s["name"])
            docs = {f: [t for n in ns for t in self.fs._tokens(n + " " + self.desc.get(n, ""))] for f, ns in fams.items()}
            df: dict[str, int] = {}
            for toks in docs.values():
                for w in set(toks):
                    df[w] = df.get(w, 0) + 1
            tf: dict[str, dict] = {f: {} for f in docs}
            for f, toks in docs.items():
                for w in toks:
                    tf[f][w] = tf[f].get(w, 0) + 1
            self._fam_docs = (fams, tf, {f: len(v) for f, v in docs.items()}, df,
                              sum(len(v) for v in docs.values()) / max(1, len(docs)), len(docs))
        fams, tf, ln, df, avg, N = self._fam_docs
        if N < 2:
            return []
        q = set(self.fs._tokens(task))
        sc = {}
        for f, d in tf.items():
            s = 0.0
            for w in q & d.keys():
                fq = d[w]
                s += math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * fq * (BM25_K1 + 1) / (fq + BM25_K1 * (1 - BM25_B + BM25_B * ln[f] / avg))
            if s > 0:
                sc[f] = s
        own = {r["name"]: r["score"] for r in self.search(task, len(self.skills))}
        out: list[str] = []
        for f, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0])):
            out += sorted(fams[f], key=lambda n: (-own.get(n, 0.0), n))
            if len(out) >= depth:
                break
        return out[:depth]

    def ncd_reading(self, task: str, depth: int) -> list[str]:
        """v15: normalized compression distance (Cilibrasi and Vitanyi, 2005): no tokens, no stems; two texts are
        near when one compresses the other. It meets morphology and misspellings the tokenizer splits apart."""
        import zlib
        if self._ncd_docs is None:
            self._ncd_docs = {}
            for s in self.skills:
                y = (s["name"].replace("-", " ") + " " + s["desc"]).lower().encode()
                self._ncd_docs[s["name"]] = (y, len(zlib.compress(y, 9)))
        x = task.lower().encode()
        if len(x) < 8:
            return []
        cx = len(zlib.compress(x, 9))
        sc = {n: (len(zlib.compress(x + b" " + y, 9)) - min(cx, cy)) / max(cx, cy) for n, (y, cy) in self._ncd_docs.items()}
        return [n for n, _ in sorted(sc.items(), key=lambda kv: (kv[1], kv[0]))[:depth]]

    def meaning_reading(self, task: str, depth: int) -> list[str]:
        """2026-10-24 (the user: "the picker needs to pick from meaning and purpose not words"): every skill embedded once
        from what it is FOR (description + the survey's `does` + its `asks` + the card's output), the task embedded
        the same way, ranked by cosine (meaning.py; a free local model in its own venv). Empty when the venv or the
        vectors are missing, so the other readings still rank."""
        r = meaning_rank(task, depth, self.root, getattr(self, "state_dir", None))
        return [n for n, _ in r if n in self.desc] if r else []

    def personal_reading(self, task: str, depth: int) -> list[str]:
        """2026-10-24 (the user: "build their own personal custom /skill maestro that changes based on their ratings"): the
        skills THIS person used and rated on past prompts that mean what the task means (personal.py). Learns from
        the owner's own history only, never from other people's ratings. Empty without the meaning model."""
        st, rows_fn = getattr(self, "state_dir", None), getattr(self, "personal_rows", None)
        if st is None or rows_fn is None or not meaning_ok():
            return []
        try:
            if getattr(self, "_personal", None) is None:
                P = _load(HERE / "personal.py", "personal")
                self._personal = (P, P.examples(st, rows_fn(), before=getattr(self, "personal_before", None)))
            P, exs = self._personal
            return [n for n, _ in P.reading(_MEANING["mod"], task, exs, st, depth) if n in self.desc]
        except Exception:  # noqa: BLE001
            return []

    def phase_reading(self, task: str, depth: int) -> list[str]:
        """2026-10-25 (the 48 context-driven walk-forward keys, HISTORY_v19.md section 3): the skills sessions moved to
        after using what THIS session just used (phase.py: a transition table from this machine's own hindsight rows,
        applied to the last RECENT used turns). The task's words play no part. Empty with no context set
        (`phase_context`: the eval sets it per probe, `score` and the hook from the running transcript)."""
        ctx = getattr(self, "phase_context", None)
        if not ctx:
            return []
        try:
            if getattr(self, "_phase", None) is None:
                self._phase = _load(HERE / "phase.py", "phase")
            P = self._phase
            tab = P.table(P.rows_of(getattr(self, "state_dir", None) or STATE), before=getattr(self, "phase_cut", None))
            return [n for n in P.reading(tab, ctx) if n in self.desc][:depth]
        except Exception:  # noqa: BLE001
            return []

    def mode_reading(self, task: str, depth: int) -> list[str]:
        """2026-10-24: the skills whose purpose is closest to the MODE the prompt is in (modes.py, its `lean` text)."""
        st = getattr(self, "state_dir", None) or STATE
        if not meaning_ok():
            return []
        try:
            sel = getattr(self, "mode_sel", None) or select_mode(task, st)
            if not sel:
                return []
            r = meaning_rank(sel["mode"]["name"].replace("-", " ") + ": " + sel["mode"]["lean"], depth, self.root, st) or []
            return [n for n, _ in r if n in self.desc]
        except Exception:  # noqa: BLE001
            return []

    def asks_reading(self, task: str, depth: int) -> list[str]:
        """v17 (the survey): each skill was tested for real once and given requests a person would type when it is
        the right tool, most of them without its own words (cards/tested.jsonl, `survey build`). BM25 over every
        ask as its own document; a skill scores by its best ask plus a quarter of its mean, so one close request
        counts most and a skill with many loose matches does not win by count. Broken skills are left out."""
        import math
        if self._asks is None:
            self._asks = []
            for row in load_tested(self.tested_path).values():
                if row["name"] in self.desc and row.get("verdict") != "broken":
                    for a in row.get("asks", []):
                        toks = self.fs._tokens(a)
                        if toks:
                            self._asks.append((row["name"], toks))
            df: dict[str, int] = {}
            for _, toks in self._asks:
                for w in set(toks):
                    df[w] = df.get(w, 0) + 1
            self._asks_df = df
            self._asks_avg = sum(len(t) for _, t in self._asks) / max(1, len(self._asks))
        if not self._asks:
            return []
        q = set(self.fs._tokens(task))
        N, df, avg = len(self._asks), self._asks_df, self._asks_avg
        per: dict[str, list[float]] = {}
        for n, toks in self._asks:
            tf: dict[str, int] = {}
            for w in toks:
                tf[w] = tf.get(w, 0) + 1
            s = 0.0
            for w in q & tf.keys():
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (BM25_K1 + 1) / (tf[w] + BM25_K1 * (1 - BM25_B + BM25_B * len(toks) / avg))
            per.setdefault(n, []).append(s)
        sc = {n: max(v) + 0.25 * sum(v) / len(v) for n, v in per.items()}
        return [n for n, v in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0])) if v > 0][:depth]

    def owner_reading(self, task: str, depth: int) -> list[str]:
        """v15: the owner's own words for each skill, learned from the prompts after which it was reached for
        (`hindsight propose --write-lexicon` -> cards/owner_lexicon.json). A skill scores by the rarity-weighted
        count of its learned words present in the task: fit by the owner's words, never a count of use."""
        if self._owner is None:
            f = HERE / "cards" / "owner_lexicon.json"
            try:
                data = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
            except ValueError:
                data = {}
            self._owner = {n: {w: float(v) for w, v in ws.items()} for n, ws in data.items() if n in self.desc}
        if not self._owner:
            return []
        q = set(self.fs._tokens(task))
        sc = {n: sum(v for w, v in ws.items() if w in q) for n, ws in self._owner.items()}
        return [n for n, s in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0])) if s > 0][:depth]

    def fused(self, task: str, depth: int = 120) -> list[dict]:
        if self.quick:                               # the finder's own ranking (steelman s2: no worse at @1, 6x faster)
            return self.search(task, depth)
        """Reciprocal rank fusion of every variant's ranking; fit is the fused score scaled to the best."""
        task = ranking_text(task)                    # v14 A: asking words never reach the rankers
        scores: dict[str, float] = {}
        rows: dict[str, dict] = {}
        byname = {s["name"]: s for s in self.skills}
        ran: dict[str, float] = {}                   # v14 B: the readings that ran, with their weights

        def add(vname: str, names: list[str]) -> None:
            w = WEIGHTS.get(vname, 1.0)
            if not w:
                return
            ran[vname] = w
            for rank, n in enumerate(names, 1):
                if n not in byname:
                    continue
                scores[n] = scores.get(n, 0.0) + w / (RRF_K + rank)
                rows.setdefault(n, {"name": n, "score": 0.0, "tool": byname[n]["tool"],
                                    "when": byname[n]["desc"].split(". ")[0][:160], "via_q": []})["via_q"].append(vname)

        for vname, q in self.variants(task).items():
            if vname.startswith("_"):
                continue
            hits = self.search(q, depth)
            add(vname, [r["name"] for r in hits])
            for r in hits:
                if r.get("pin") and r["name"] in rows:
                    rows[r["name"]]["pin"] = r["pin"]
        if WEIGHTS.get("body"):
            add("body", self.body(task, depth))
        for extra in ("family", "ncd", "owner", "asks", "meaning", "personal", "mode", "phase"):     # v15 readings (M37-M39), v17 survey asks (M43), meaning (M46), phase (M52, 2026-10-25); each measured by ablate and tune
            if WEIGHTS.get(extra):
                add(extra, getattr(self, extra + "_reading")(task, depth))
        if WEIGHTS.get("network") and scores:
            seeds = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:NET_SEEDS]
            add("network", self.network(seeds)[:depth])
        if WEIGHTS.get("deliverable") and scores:    # 2026-10-25 (dial M51): the output kind a making verb asks for
            ordered = [n for n, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]
            add("deliverable", deliverable_reading(task, ordered, self.desc)[:depth])
        if self.concept_per:                         # v10: only when Claude restated the task as operations
            add("concept", concept_rank(self.concept_per, depth))
        ranked = sorted(rows.values(), key=lambda r: (-scores[r["name"]], r["name"]))   # v16 O10: the v14-B eligible rescale was removed (it over-corrected: @1 9 -> 4)
        for r in ranked:
            r["score"] = round(scores[r["name"]] * 1000, 4)
        return ranked


class State:
    """Append-only ledger, the registry snapshot, the user's favourites."""

    def __init__(self, d: Path, ledger: Path | None = None, also: tuple[Path, ...] = ()) -> None:
        self.d = Path(d)
        self.d.mkdir(parents=True, exist_ok=True)
        self.ledger = Path(ledger) if ledger else self.d / "ledger.jsonl"
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.also = tuple(Path(a) for a in also if Path(a) != self.ledger)   # read-only ledgers merged into rows()
        self.registry = self.d / "registry.json"
        self.fav = self.d / "favourites.json"

    def append(self, row: dict) -> None:
        with self.ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    def rows(self) -> list[dict]:
        """Own ledger plus the read-only ones, each row once (by its exact text), oldest first. The sort is stable,
        so rows written in one second keep their order. v15: parsed once per process per file state (size, mtime)."""
        key = tuple((str(q), q.stat().st_size, q.stat().st_mtime_ns) if q.is_file() else (str(q), -1, -1)
                    for q in (self.ledger, *self.also))
        if getattr(self, "_rows_key", None) == key:
            return list(self._rows)
        seen, out = set(), []
        for p in (self.ledger, *self.also):
            if not p.is_file():
                continue
            for x in p.read_text(encoding="utf-8").splitlines():
                if x.strip() and x not in seen:
                    seen.add(x)
                    out.append(json.loads(x))
        out.sort(key=lambda r: r.get("t", 0))      # a git union merge can put a later session's rows first
        self._rows_key, self._rows = key, out
        return list(out)

    def favourites(self) -> set[str]:
        return set(json.loads(self.fav.read_text(encoding="utf-8"))) if self.fav.is_file() else set()

    def stats(self, questions: list[str] | tuple = ()) -> dict[str, dict[str, int]]:
        """Each skill's record. With `questions`, verdicts count only from runs that asked one of them (v8f: a rating
        on a planning task no longer moves a forecasting task); the 'chosen' novelty count stays global."""
        s: dict[str, dict[str, int]] = {}
        allrows = self.rows()
        keep = None
        if questions:
            keep = {r["run"] for r in allrows if r.get("kind") == "SCORE" and set(r.get("questions") or ()) & set(questions)}
        for r in allrows:
            if keep is not None and r.get("kind") != "SCORE" and r.get("run") not in keep:
                continue
            if r.get("kind") == "SCORE":
                for n in r.get("chosen", []):
                    s.setdefault(n, {}).setdefault("chosen", 0)
                    s[n]["chosen"] += 1
            elif r.get("kind") == "RATE":
                s.setdefault(r["skill"], {}).setdefault(r["rating"], 0)
                s[r["skill"]][r["rating"]] += 1
        rows = [r for r in allrows if keep is None or r.get("kind") == "SCORE" or r.get("run") in keep]
        for r in rows:                               # a pick that did not work on its task's subject (v7 FIT gate)
            if r.get("kind") == "FIT" and r.get("verdict") == "misfit":
                s.setdefault(r["skill"], {}).setdefault("wrong", 0)
                s[r["skill"]]["wrong"] += 1
        menus_of = {r["run"]: r.get("menus", {}) for r in rows if r.get("kind") == "SCORE"}
        for r in latest_metrics(rows):               # the user's topic metrics join the record (v6c, bench E13)
            tm = group_mean(r["scores"], METRICS_TOPIC)
            if r["by"] != "max" or tm is None:
                continue
            tg = r["target"]
            if tg.startswith("menu:"):
                pairs = [(m, "useful") for m in menus_of.get(r["run"], {}).get(tg[5:], [])] if tm >= 4 else []
            else:
                lab = "useful" if tm >= 4 else "wrong" if tm <= 1 else "unused" if tm < 3 else None
                pairs = [(tg, lab)] if lab else []
            for name, lab in pairs:
                s.setdefault(name, {}).setdefault(lab, 0)
                s[name][lab] += 1
        return s

    def memory(self) -> list[tuple[set[str], str, str]]:
        """(task words, skill, rating) for every rating whose run stored its task words."""
        rows = self.rows()
        words = {r["run"]: set(r["words"]) for r in rows if r.get("kind") == "SCORE" and r.get("words")}
        out = [(words[r["run"]], r["skill"], r["rating"]) for r in rows if r.get("kind") == "RATE" and r.get("run") in words]
        out += [(words[r["run"]], r["skill"], "wrong") for r in rows
                if r.get("kind") == "FIT" and r.get("verdict") == "misfit" and r.get("run") in words]
        menus_of = {r["run"]: r.get("menus", {}) for r in rows if r.get("kind") == "SCORE"}
        for r in latest_metrics(rows):              # the user's topic metrics only: Claude cannot grade its own homework
            tm = group_mean(r["scores"], METRICS_TOPIC)
            if r["by"] != "max" or tm is None or r["run"] not in words:
                continue
            tg = r["target"]
            if tg.startswith("menu:"):              # a good menu vouches for its members; a bad one blames none
                out += [(words[r["run"]], m, "useful") for m in menus_of.get(r["run"], {}).get(tg[5:], []) if tm >= 4]
            elif tm >= 4 or tm <= 1:
                out.append((words[r["run"]], tg, "useful" if tm >= 4 else "wrong"))
        return out


def is_metric_token(tok: str) -> bool:
    """v18 (pressure tests P1/P2, 2026-10-24): only `<known metric>=<number>` makes a rating the metric form. Before,
    any '=' did, so a why that said 'H=0.61, n=400' was refused twice as a malformed metric and the honest rating
    was nearly not recorded."""
    m = re.fullmatch(r"([A-Za-z_-]+)=(-?\d+(?:\.\d+)?)", tok.strip())
    if not m:
        return False
    k = m.group(1).lower().replace("-", "_")
    k = METRIC_ALIAS.get(k, k)
    return k in METRICS_INNER or k in METRICS_TOPIC or k in ("inner", "topic", "all")


def parse_metrics(tokens: list[str]) -> tuple[dict[str, float], list[str]]:
    """`key=value` words (0-5) -> scores; `inner=`/`topic=`/`all=` fill a group, a named metric overrides its group.
    Other words are the reason. Unknown keys and values outside 0-5 raise ValueError (nothing is guessed)."""
    group: dict[str, float] = {}
    named: dict[str, float] = {}
    why: list[str] = []
    for tok in tokens:
        if "=" not in tok:
            why.append(tok)
            continue
        k, v = tok.split("=", 1)
        k = METRIC_ALIAS.get(k.lower().replace("-", "_"), k.lower().replace("-", "_"))
        try:
            x = float(v)
        except ValueError:
            raise ValueError(f"METRIC_VALUE {tok}: a number 0-5") from None
        if not 0 <= x <= 5:
            raise ValueError(f"METRIC_RANGE {tok}: 0-5")
        if k in ("inner", "all"):
            group.update({m: x for m in METRICS_INNER})
        if k in ("topic", "all"):
            group.update({m: x for m in METRICS_TOPIC})
        if k in METRICS_INNER or k in METRICS_TOPIC:
            named[k] = x
        elif k not in ("inner", "topic", "all"):
            raise ValueError(f"METRIC_UNKNOWN {k}: one of {', '.join(METRICS_INNER + METRICS_TOPIC)}, inner, topic, all")
    if not group and not named:
        raise ValueError("METRIC_NONE: give at least one key=value")
    return {**group, **named}, why


def group_mean(scores: dict[str, float], names: tuple[str, ...]) -> float | None:
    xs = [scores[m] for m in names if m in scores]
    return round(sum(xs) / len(xs), 2) if xs else None


def latest_metrics(rows: list[dict]) -> list[dict]:
    """One METRIC row per (run, target, by): the latest (a re-rating replaces, the ledger keeps both)."""
    last: dict[tuple, dict] = {}
    for r in rows:
        if r.get("kind") == "METRIC":
            last[(r["run"], r["target"], r["by"])] = r
    return list(last.values())


def rated_pairs(rows: list[dict]) -> set[tuple[str, str]]:
    """(run, skill) pairs that carry a rating: RATE rows, METRIC rows on a skill, METRIC rows on a menu (its skills)."""
    menus = {r["run"]: r.get("menus", {}) for r in rows if r.get("kind") == "SCORE"}
    out = {(r.get("run"), r.get("skill")) for r in rows if r.get("kind") == "RATE"}
    for r in rows:
        if r.get("kind") == "METRIC":
            tg = r["target"]
            members = menus.get(r["run"], {}).get(tg[5:], []) if tg.startswith("menu:") else [tg]
            out |= {(r["run"], m) for m in members}
    return out


def menus(weighed: list[dict], chosen: list[dict], rows: list[dict], desc: dict, family, k: int = 3) -> dict[str, list[str]]:
    """Several answers from one pool, one idea each, no skill in two menus (so the user compares ideas, not repeats)."""
    taken: set[str] = set()

    def take(names: list[str]) -> list[str]:
        picked: list[str] = []
        for n in names:
            if n not in taken and n not in picked:
                picked.append(n)
            if len(picked) == k:
                break
        taken.update(picked)
        return picked

    by_fit = [w["name"] for w in sorted(weighed, key=lambda r: (-r["fit"], r["name"]))]
    out = {"A": take([c["name"] for c in chosen])}
    ever = {n for r in rows if r.get("kind") == "SCORE" for n in r.get("chosen", [])}
    on_sheet = {c["name"] for c in chosen}            # the sheet's own lower ranks are not wallflowers
    out["B"] = take([n for n in by_fit if n not in ever and n not in on_sheet])
    fam_a = {family(n) for n in out["A"]}
    seen: set[str] = set()
    mix: list[str] = []
    for n in [n for n in by_fit if "BUILD" in roles_of(n, desc.get(n, ""))] + by_fit:
        f = family(n)
        if n in taken or f in fam_a or f in seen:
            continue
        seen.add(f)
        mix.append(n)
    out["C"] = take(mix)
    readers = [n for n in by_fit if n not in taken and "UNDERSTAND" in roles_of(n, desc.get(n, ""))][:k - 1]
    checks = [n for n in by_fit if n not in taken and n not in readers and is_checker(n, desc.get(n, ""))][:1]
    out["D"] = take(readers + checks + by_fit)
    loved: dict[str, list[float]] = {}
    menus_of = {r["run"]: r.get("menus", {}) for r in rows if r.get("kind") == "SCORE"}
    for r in latest_metrics(rows):
        if r["by"] != "max":
            continue
        tm = group_mean(r["scores"], METRICS_TOPIC)
        if tm is None:
            continue
        tg = r["target"]
        for m in (menus_of.get(r["run"], {}).get(tg[5:], []) if tg.startswith("menu:") else [tg]):
            loved.setdefault(m, []).append(tm)
    best = sorted((n for n in by_fit if n in loved and sum(loved[n]) / len(loved[n]) >= 3),
                  key=lambda n: (-sum(loved[n]) / len(loved[n]), n))
    out["E"] = take(best)
    return out


def board(rows: list[dict]) -> list[str]:
    """the user's metrics board: each menu idea by the user and by Claude, the best skills by the user's topic ratings, and the
    calibration line (Claude's self-ratings against the user's on the same targets)."""
    M = latest_metrics(rows)
    if not M:
        return ["METRICS: none yet. After a run: `maestro.py rate RUN <skill|menu:A..E> --by max|claude inner=4 topic=5 ...`"]
    L = [f"METRICS over {len(M)} ratings (0-5). inner = {', '.join(METRICS_INNER)} (self-report when by Claude); "
         f"topic = {', '.join(METRICS_TOPIC)}"]
    L.append(f"menu idea       by {OWNER}: inner topic (n)    by Claude: inner topic (n)")
    for letter, name, _ in MENU_IDEAS:
        cells = []
        for who in ("max", "claude"):
            rs = [r for r in M if r["by"] == who and r["target"] == f"menu:{letter}"]
            im = [x for x in (group_mean(r["scores"], METRICS_INNER) for r in rs) if x is not None]
            tm = [x for x in (group_mean(r["scores"], METRICS_TOPIC) for r in rs) if x is not None]
            f = lambda xs: f"{sum(xs) / len(xs):.1f}" if xs else " -"  # noqa: E731
            cells.append(f"{f(im):>5} {f(tm):>5} ({len(rs)})")
        L.append(f"  {letter} {name:<11}  {cells[0]:<22}    {cells[1]}")
    sk: dict[str, list[float]] = {}
    for r in M:
        tm = group_mean(r["scores"], METRICS_TOPIC)
        if r["by"] == "max" and tm is not None and not r["target"].startswith("menu:"):
            sk.setdefault(r["target"], []).append(tm)
    if sk:
        L.append(f"skills {OWNER} rated on topic: " + ", ".join(f"{n} {sum(v) / len(v):.1f} (n{len(v)})" for n, v in
                                                          sorted(sk.items(), key=lambda x: -sum(x[1]) / len(x[1]))[:10]))
    L += calibration(M)
    return L


def calibration(M: list[dict]) -> list[str]:
    both: dict[tuple, dict] = {}
    for r in M:
        both.setdefault((r["run"], r["target"]), {})[r["by"]] = r["scores"]
    pairs = [v for v in both.values() if "max" in v and "claude" in v]
    if not pairs:
        return [f"CALIBRATION: nothing rated by both {OWNER} and Claude yet; Claude's numbers are unchecked self-reports (S3)"]
    out = []
    for gname, names in (("inner", METRICS_INNER), ("topic", METRICS_TOPIC)):
        d = [group_mean(p["claude"], names) - group_mean(p["max"], names) for p in pairs
             if group_mean(p["claude"], names) is not None and group_mean(p["max"], names) is not None]
        if not d:
            continue
        mean = sum(d) / len(d)
        if len(d) >= 3 and mean > 1.0:
            out.append(f"SELF_INFLATION ({gname}): Claude rates {mean:+.1f} above {OWNER} over {len(d)} shared targets; "
                       f"trust {OWNER}'s numbers")
        else:
            out.append(f"CALIBRATION ({gname}): Claude minus {OWNER} {mean:+.1f} over {len(d)} shared target(s)"
                       + ("" if len(d) >= 3 else "; too few to judge"))
    return out


SAME_AT = 0.9     # (choice) output similarity at or above which a control "says the same"; bench E27 measures it


def controls(text: str, seed: int = 0) -> dict[str, str]:
    """HALF, SALAD and BLANKED versions of a subject (seeded, so a taste reruns identically)."""
    import random
    rng = random.Random(seed)
    lines = text.splitlines()
    keep = sorted(rng.sample(range(len(lines)), max(1, len(lines) // 2))) if lines else []
    half = "\n".join(lines[i] for i in keep)
    words = text.split()
    rng.shuffle(words)
    width = max(1, round(sum(len(x) for x in lines) / max(1, len(lines)) / 6))
    salad = "\n".join(" ".join(words[i:i + width]) for i in range(0, len(words), width))
    alpha = "abcdefghijklmnopqrstuvwxyz"
    blank = "\n".join(" ".join("".join(rng.choice(alpha) for _ in w) if w.isalpha() else w for w in ln.split(" "))
                       for ln in lines)
    return {"HALF": half, "SALAD": salad, "BLANKED": blank}


TASTE_CALIBRATED = False   # rule P1: shown as UNCALIBRATED until a taste version passes its pre-registered bench test


def taste_verdict(sims: dict[str, float], question: str | None = None) -> str:
    """v8b: CONSTANT = same on all three controls; SIZE_ONLY = same on SALAD and BLANKED only; for a FIND_GAPS skill
    HALF is no evidence (deleting text cannot fill a gap) and SATURATED means the same gaps on BLANKED."""
    same = {k for k, v in sims.items() if v >= SAME_AT}
    if {"HALF", "SALAD", "BLANKED"} <= same:
        return "CONSTANT"
    if {"SALAD", "BLANKED"} <= same:
        return "SIZE_ONLY"
    if question == "FIND_GAPS":
        if "BLANKED" in same:
            return "SATURATED"
    elif "HALF" in same:
        return "SATURATED"
    if "SALAD" in same:
        return "LEXICAL"
    if "BLANKED" in same:
        return "STRUCTURAL"
    return "READS_IT"


def echo_masked(out: str, source: str) -> str:
    """The tool's own words: every 4+ character token that also occurs in the subject variant is removed (v8b)."""
    seen = set(re.findall(r"[A-Za-z0-9_'-]{4,}", source))
    return re.sub(r"\s+", " ", re.sub(r"[A-Za-z0-9_'-]{4,}", lambda mt: "" if mt.group(0) in seen else mt.group(0), out))


def taste(cmd: list[str], subject: Path, work: Path, seed: int = 0, question: str | None = None) -> dict:
    """Run cmd (with {subject}) on the subject and its three controls; return outputs' similarities and a verdict."""
    import difflib
    import subprocess
    work.mkdir(parents=True, exist_ok=True)
    text = subject.read_text(encoding="utf-8", errors="replace")
    files = {"REAL": subject}
    for k, v in controls(text, seed).items():
        f = work / f"{k.lower()}{subject.suffix}"
        f.write_text(v, encoding="utf-8")
        files[k] = f
    outs, texts = {}, {"REAL": text}
    for k, f in files.items():
        texts.setdefault(k, f.read_text(encoding="utf-8", errors="replace"))
        argv = [a.replace("{subject}", str(f)) for a in cmd]
        argv = [sys.executable if argv[0] in ("python", "py") else argv[0], *argv[1:]]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
                               env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            out = r.stdout + r.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            out = f"{type(exc).__name__}: {exc}"
        outs[k] = out.replace(str(f), "<SUBJECT>").replace(f.name, "<SUBJECT>")
    own = {k: echo_masked(v, texts[k]) for k, v in outs.items()}
    sims = {k: round(difflib.SequenceMatcher(None, own["REAL"], own[k], autojunk=False).ratio(), 3)
            for k in ("HALF", "SALAD", "BLANKED")}
    return {"sims": sims, "verdict": taste_verdict(sims, question), "real_out": outs["REAL"][:600],
            "real_lines": len(outs["REAL"].splitlines()), "calibrated": TASTE_CALIBRATED}


TESTED = HERE / "cards" / "tested.jsonl"   # v17: the survey, one row per skill tested for real (`survey build`)


def load_tested(path: Path | None = None) -> dict[str, dict]:
    """The survey's cards, flattened: {name: {does, verdict, subject, result, asks, not_asks, overlaps, side_effects}}.
    Missing file -> {} and the asks reading is off."""
    f = path or TESTED
    out: dict[str, dict] = {}
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["name"]] = r
    return out


def survey_build(src: Path, out: Path | None = None) -> tuple[int, dict[str, int], list[str]]:
    """Fold the per-skill JSON cards an agent wrote (`<src>/<name>.json`) into cards/tested.jsonl. A card missing a
    key or with fewer than 3 asks is refused and named; the rest keep their test verdict."""
    rows, bad = [], []
    for f in sorted(Path(src).glob("*.json")):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            t = c["test"]
            row = {"name": c["name"], "does": c["does"], "verdict": t["verdict"], "subject": t.get("subject", ""),
                   "command": t.get("command", ""), "result": t.get("result", ""), "asks": list(c["asks"]),
                   "not_asks": list(c.get("not_asks", [])), "overlaps": list(c.get("overlaps", [])),
                   "side_effects": list(c.get("side_effects", []))}
            if len(row["asks"]) < 3 or row["verdict"] not in ("works", "partial", "broken", "untestable"):
                raise ValueError("asks or verdict")
            rows.append(row)
        except (OSError, ValueError, KeyError, TypeError) as e:
            bad.append(f"{f.stem} ({type(e).__name__}: {e})")
    scrub_row = _load(HERE / "scrub.py", "scrub").scrub_row     # v20.0.3: no machine path or owner name reaches the survey
    rows = [scrub_row(r) for r in rows]
    (out or TESTED).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    by: dict[str, int] = {}
    for r in rows:
        by[r["verdict"]] = by.get(r["verdict"], 0) + 1
    return len(rows), by, bad


def load_mechanisms(path: Path | None = None) -> dict[str, dict]:
    """Mechanism lines per skill: {does, tags, world} (v10). Missing file -> {} and the concept reading is off.
    v14: lines built by `cards --auto` for skills nobody wrote one for (plugins, built-ins, another person's library)
    are read too; a hand-written line always wins."""
    out = {}
    for f in ([path] if path else [MECHS_AUTO, MECHS]):     # hand-written last, so it overrides
        if not f.is_file():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                out[m["name"]] = m
    return out


def auto_mechanisms(lib: "Library", vocab: dict[str, str], have: set[str], k: int = 3) -> list[dict]:
    """v14 (fairness and sharing): a mechanism line for every skill without one, by one rule for all. `does` is the
    first sentence of its description; `tags` are the operation tags whose meaning shares the most rare words with
    the description (idf over the whole library, so 'use', 'skill' and 'when' count for little). No world line: an
    analogy cannot be guessed honestly. Marked auto so the sheet can say how the skill was read."""
    import math
    docs = {s["name"]: set(lib.fs._tokens(s["desc"])) for s in lib.skills}
    df: dict[str, int] = {}
    for toks in docs.values():
        for w in toks:
            df[w] = df.get(w, 0) + 1
    N = max(1, len(docs))
    idf = lambda w: math.log(1 + N / (1 + df.get(w, 0)))  # noqa: E731
    tag_words = {t: set(lib.fs._tokens(t.replace("-", " ") + " " + meaning)) for t, meaning in vocab.items()}
    out = []
    for s in lib.skills:
        n = s["name"]
        if n in have or n == SELF:
            continue
        words = docs[n]
        scored = sorted(((sum(idf(w) for w in words & tw), t) for t, tw in tag_words.items()), reverse=True)
        tags = [t for sc, t in scored[:k] if sc >= 2.0]
        parts = re.split(r"(?<=[.!?])\s", s["desc"].strip())
        first = parts[0]
        if len(first) < 60 and len(parts) > 1:               # "Assayer - CODE type 7 of 16." says nothing: add the next
            first += " " + parts[1]
        first = first[:220]
        out.append({"name": n, "does": first, "tags": tags, "world": "", "auto": True})
    return out


def load_vocab(path: Path | None = None) -> dict[str, str]:
    f = path or VOCAB
    return json.loads(f.read_text(encoding="utf-8")).get("tags", {}) if f.is_file() else {}


def _plain_tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("-", " "))


def infer_tags(text: str, vocab: dict[str, str], tokens=None, k: int = 2, floor: float = 2.0) -> list[tuple[str, float, str]]:
    """v18 (root fix, run 6734e7c55e): the operation tags a piece of text points at, by the rule auto_mechanisms uses
    for skills - rare words shared with a tag's name and meaning, idf over the tag meanings themselves. Before this,
    a judge who did not know the tag names ('op: critique a protocol') fell silently to word overlap against the
    `does` lines, the six red-team lenses never entered the pool, and NEEDED fired for operations the library
    performs. Returns [(tag, score, meaning)] for the k best tags at or above the floor."""
    import math
    tokens = tokens or _plain_tokens
    tag_words = {t: set(tokens(t.replace("-", " ") + " " + m)) for t, m in vocab.items()}
    df: dict[str, int] = {}
    for ws in tag_words.values():
        for w in ws:
            df[w] = df.get(w, 0) + 1
    N = max(1, len(tag_words))
    idf = lambda w: math.log(1 + N / (1 + df.get(w, 0)))  # noqa: E731
    cw = set(tokens(text))
    scored = sorted(((sum(idf(w) for w in cw & ws), t) for t, ws in tag_words.items()), reverse=True)
    return [(t, round(s, 2), vocab[t]) for s, t in scored[:k] if s >= floor]


def parse_concepts(text: str, vocab: dict[str, str], tokens=None) -> list[dict]:
    """'partition: split coding into kinds; overlay-config, switch-mode: one base many profiles; world: bee castes'
    -> [{tags, text, analogy, unknown, inferred}]. Items split on ';' or newlines. Before the colon: vocabulary tags
    (comma separated) or 'world'/'analogy'. v18: a head that is not a tag, or no head at all, no longer drops the item
    to word overlap: its tags are inferred from its words by the tag meanings (`infer_tags`), the unknown head is
    still reported, and the sheet marks the tags as inferred."""
    out = []
    for item in re.split(r"[;\n]+", text or ""):
        item = item.strip()
        if not item:
            continue
        head, sep, body = item.partition(":")
        heads = [h.strip().lower() for h in head.split(",")] if sep else []
        if sep and heads and all(h in vocab or h in ("world", "analogy") for h in heads):
            out.append({"tags": [h for h in heads if h in vocab], "text": body.strip(),
                        "analogy": any(h in ("world", "analogy") for h in heads), "unknown": [], "inferred": False})
        else:
            unknown = [h for h in heads if h not in vocab] if sep else []
            words = body.strip() if sep else item
            inferred = infer_tags(words, vocab, tokens) if vocab else []
            out.append({"tags": [t for t, _, _ in inferred], "text": words if sep else item, "analogy": False,
                        "unknown": unknown, "inferred": bool(inferred)})
    return out


PLACEHOLDER_RX = re.compile(r"<[^<>]*(?:file|text|path|subject|series|table|csv|input|log|note|doc)[^<>]*>"
                            r"|\b[\w.-]+\.(?:md|csv|txt|json|jsonl)\b")


def subject_cmd(cmd: str, subject: str) -> str:
    """v18: a pick's example command with the task's subject in place of its placeholder file (`<file|text>`, `memo.md`,
    `DECISIONS.md` ...); when no placeholder is found the subject is appended. The flag it needs (--kind, --opt) is
    still the judge's to check: the sheet gives a runnable first try, not a verdict."""
    if not cmd:
        return cmd
    new, n = PLACEHOLDER_RX.subn(lambda m: subject, cmd, count=1)
    return new if n else f"{cmd} {subject}"


def concept_scores(concepts: list[dict], mechs: dict[str, dict], tokens) -> list[list[tuple[str, float]]]:
    """For each concept, every skill's match in 0..1: shared tags weighted by rarity (idf, 60%) plus word overlap of
    the concept text with the skill's domain-free `does` and `world` lines (40%; analogies match `world` first).
    Both sides are written in operation words, so this matches what a skill DOES, not the task's surface words."""
    import math
    N = max(1, len(mechs))
    df: dict[str, int] = {}
    for m in mechs.values():
        for t in set(m.get("tags", [])):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + N / c) for t, c in df.items()}
    mt = {n: (set(tokens(m.get("does", ""))), set(tokens(m.get("world", ""))), set(m.get("tags", [])))
          for n, m in mechs.items()}
    out = []
    for c in concepts:
        cw = set(tokens(c["text"]))
        ct = set(c["tags"])
        tag_den = sum(idf.get(t, math.log(1 + N)) for t in ct) or 0.0
        row = []
        for n, (does, world, tags) in mt.items():
            tag = sum(idf.get(t, 0.0) for t in ct & tags) / tag_den if tag_den else 0.0
            pool = (world | does) if c["analogy"] else (does | world)
            words = len(cw & pool) / (len(cw) ** 0.5 * max(1, len(pool)) ** 0.5) if cw and pool else 0.0
            s = (0.6 * tag + 0.4 * words) if ct else words
            if s > 0:
                row.append((n, round(s, 4)))
        row.sort(key=lambda x: (-x[1], x[0]))
        out.append(row)
    return out


def concept_rank(per: list[list[tuple[str, float]]], depth: int = 120) -> list[str]:
    """One ranking from the concepts: round-robin over each concept's own ranking, so every concept gets its leaders
    in (a task is several operations; the best match of each matters more than the 2nd of one)."""
    seen, out = set(), []
    for i in range(depth):
        for row in per:
            if i < len(row) and row[i][0] not in seen:
                seen.add(row[i][0])
                out.append(row[i][0])
    return out[:depth]


LEXICAL_FILE = HERE / "cards" / "lexical.json"
LEX_WORDS = re.compile(r"(?i)\b(lexical|keyword|word[- ]level|word overlap|word sets?|shared words|cue[- ]based|tf-?idf|"
                       r"jaccard|tallies|tally|word counts?|counts? (the )?words|most frequent words|salient terms)\b")


def build_lexical(root: Path, cards: dict, mechs: dict, desc: dict) -> dict[str, str]:
    """v10e item 5: skills that read WORDS, not meaning - {name: reason}. Two signals, each stated:
    (a) a pov-core lens whose card says it takes TEXT (the pov engine scores by cue words; on 10-19 council-of-views
        and random-lens tallied vocabulary on a protocol), or
    (b) its own card, description or mechanism line says it works by word overlap, keyword tallies, TF-IDF and the like.
    A lens on CODE or a PLAN is not flagged by (a): birds-eye and x-ray read structure."""
    out = {}
    for n in sorted(set(desc) | set(cards)):
        d = root / n
        pov = d.is_dir() and any("pov_core" in p.read_text(encoding="utf-8", errors="replace")
                                 for p in d.glob("*.py") if n != "pov-core")
        kind = ((cards.get(n) or {}).get("input") or {}).get("kind", "")
        c = cards.get(n) or {}
        txt = " ".join([" ".join(c.get("assumes", [])), c.get("not_for", ""), c.get("output", ""), desc.get(n, ""),
                        (mechs.get(n) or {}).get("does", "")])
        m = LEX_WORDS.search(txt)
        if pov and kind == "TEXT":
            out[n] = "pov-core lens on text"
        elif m:
            out[n] = f"says it works by '{m.group(0)}'"
    return out


def load_lexical() -> dict[str, str]:
    try:
        return json.loads(LEXICAL_FILE.read_text(encoding="utf-8")) if LEXICAL_FILE.is_file() else {}
    except (OSError, ValueError):
        return {}


def two_ballots(words: list[str], meaning: list[str], top: int, family, blocked: set) -> list[tuple[str, str]]:
    """v10d (the user 10-19, brainstorm item 1): pick from TWO ballots instead of one fused vote. E35 showed the concept
    reading found the right skills (#1, #2) and then lost the fused vote to four keyword readings. So the sheet takes
    turns: best of the words ballot, best of the meaning ballot, next of each ... skipping repeats, blocked skills and a
    third skill of one family. A skill on both ballots is marked 'both'. Returns [(name, 'words'|'meaning'|'both')]."""
    out: list[tuple[str, str]] = []
    fam_n: dict[str, int] = {}
    wi = mi = 0
    turn = 0
    on_both = set(words[:top * 3]) & set(meaning[:top * 3])
    while len(out) < top and (wi < len(words) or mi < len(meaning)):
        src, lst, i = ("words", words, wi) if turn % 2 == 0 else ("meaning", meaning, mi)
        if i >= len(lst):                                   # one ballot ran dry: the other fills the rest
            turn += 1
            continue
        n = lst[i]
        if src == "words":
            wi += 1
        else:
            mi += 1
        f = family(n) if family else "?"
        if n in blocked or any(n == x for x, _ in out) or fam_n.get(f, 0) >= FAMILY_CAP:
            continue
        fam_n[f] = fam_n.get(f, 0) + 1
        out.append((n, "both" if n in on_both else src))
        turn += 1
    return out


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def quote_in_tries(rows: list[dict], run: str, skill: str, quote: str) -> bool:
    """A FIT quote must be a real piece (>= 12 characters) of what that skill printed in a TRY of that run."""
    q = _norm(quote)
    return len(q) >= 12 and any(r.get("kind") == "TRY" and r.get("run") == run and r.get("skill") == skill
                                and q in _norm(r.get("out") or r.get("head") or "") for r in rows)


def ponder(rows: list[dict], run: str, mechs: dict, cards: dict, concepts2: list[dict] | None = None,
           per2: list | None = None) -> list[str]:
    """The SECOND THINK STEP (v10c, the user 10-19: "we might need a second think step of some kind somewhere"). Between
    the sheet and using the picks. Five moves, each from a skill that suggested it in the 10-19 brainstorm:
    BLUNDER CHECK (chess candidate moves + blunder check; metaphor-to-algorithm said BUILD, no skill did it),
    QUORUM (honeybee scouts; kingdom-sweep): a second reading from the failure angle, picks in both = quorum,
    MISSING PIECE (counterfactual-view / forget-the-name), TASTE (chef, tool-testing crow): a creative pick was
    actually run, EVIDENCE (adversary-eye, devils-advocate, forgery-plan: Claude grading itself is the cheapest fake)."""
    sc = next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == run), None)
    if sc is None:
        return [f"RUN_UNKNOWN {run}"]
    chosen, pool = sc.get("chosen", []), sc.get("pool_names", [])
    tried = {r["skill"] for r in rows if r.get("kind") == "TRY" and r.get("run") == run}
    fits = [r for r in rows if r.get("kind") == "FIT" and r.get("run") == run]
    L = [f"PONDER run {run} - the second think step: before using the picks, think again, differently."]
    L.append("1. BLUNDER CHECK (the opponent's best reply): for each pick, write the strongest reason it is WRONG for this task.")
    for n in chosen:
        cd = cards.get(n) or {}
        hint = (cd.get("not_for") or "")[:90] or "; ".join(a[:60] for a in (cd.get("assumes") or [])[:1])
        L.append(f"   {n:<28} its own card warns: {hint or '(no card)'}")
    L.append("2. QUORUM (bee scouts): rescore from the FAILURE angle - 'what would make this task fail, be fake, or be "
             "forgotten?' - as concepts.")
    if concepts2 is not None and per2 is not None:
        second = []
        for row in per2:
            second += [n for n, _ in row[:3] if n not in second]
        first = set(chosen) | set(sc.get("wonder", [])) | set(sc.get("spark", []))
        quorum = [n for n in second if n in first]
        scouts = [n for n in second if n not in first]
        L.append(f"   QUORUM (named by both readings): {', '.join(quorum) or 'none - the first sheet and the failure reading disagree; look harder'}")
        L.append(f"   SCOUTS (only the failure reading found them): {', '.join(scouts[:8]) or 'none'}")
        for n in scouts[:4]:
            L.append(f"     {n:<26} {mechs.get(n, {}).get('does', '')[:95]}")
    else:
        L.append(f"   run: maestro.py ponder {run} --concepts2 \"red-team: how could this fail or be faked; gap-find: what "
                 "would we forget; plant-falsify: what check would catch a wrong result\"")
    L.append("3. MISSING PIECE: if only skills NOT on the sheet were allowed, which one would you take, and why? Candidates "
             "the sheet pooled but did not choose:")
    rest = [n for n in pool if n not in chosen][:8]
    L.append("   " + (", ".join(rest) or "(no pool recorded)"))
    spark = set(sc.get("spark", []))
    L.append("4. TASTE (the chef tastes before plating): a creative pick was " +
             ("RUN in this run: " + ", ".join(sorted(tried & spark)) if tried & spark else
              "NOT run yet - try one SPARK skill on the subject before committing (`maestro.py try ...`)"))
    unev = [f["skill"] for f in fits if f["verdict"] == "works" and not f.get("evidenced")]
    L.append("5. EVIDENCE: " + (f"UNEVIDENCED works verdicts: {', '.join(unev)} - re-record each with --quote \"<a line "
                                "the skill printed>\"" if unev else "every 'works' verdict quotes the skill's real output"
                                if any(f["verdict"] == "works" for f in fits) else "no 'works' verdict yet"))
    done = any(r.get("kind") == "PONDER" and r.get("run") == run for r in rows)
    L.append(f"RECORD: maestro.py ponder {run} --note \"blunder: ...; missing: ...; surprise: ...\"" +
             ("   (a PONDER note is already recorded)" if done else "   (until then this run shows as PONDER DEBT)"))
    return L


def ponder_debt(rows: list[dict]) -> list[str]:
    """Runs scored WITH concepts (a real sheet, v10c+) whose picks were never pondered. A keyword-only sheet owes
    nothing: v10d shows it only as THINK FIRST + SPARK, so there were no picks to ponder."""
    pondered = {r["run"] for r in rows if r.get("kind") == "PONDER"} | {r["run"] for r in rows if r.get("kind") == "CLOSE"}
    return [r["run"] for r in rows if r.get("kind") == "SCORE" and "spark" in r and r.get("concepts") and r.get("chosen")
            and r["run"] not in pondered]


def scout_record(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """v10d, brainstorm item 6 (learn from ponder): for each skill, (times offered as a failure-angle SCOUT, times it then
    got FIT works in that same run). A scout that worked is promoted to the front of the meaning ballot next time it
    matches a task at all. A scout judged misfit is already an antibody through FIT."""
    offered: dict[str, set] = {}
    for r in rows:
        if r.get("kind") == "PONDER_SCAN":
            for n in r.get("scouts", []):
                offered.setdefault(n, set()).add(r["run"])
    works = {(r["run"], r["skill"]) for r in rows if r.get("kind") == "FIT" and r.get("verdict") == "works"}
    return {n: (len(runs), sum((run, n) in works for run in runs)) for n, runs in offered.items()}


CARDS_RANK = False   # set only after bench E29 shows card ranking is at least as good as the fused ranking


PERSONA_RX = re.compile(r"Reasons from (.+?)(?: through (.+?))? while (?:[^.]*?\band )?treating (.+?) as first-class failure modes", re.S)


def load_cards(path: Path | None = None) -> dict[str, dict]:
    """Hand-written cards (cards.jsonl) plus derived persona cards (cards_persona.jsonl, v17); a hand card wins."""
    f = path or (HERE / "cards" / "cards.jsonl")
    out = {}
    files = [f] if path else [HERE / "cards" / "cards_persona.jsonl", f]      # hand cards load last, so they win
    for fp in files:
        if not fp.is_file():
            continue
        for ln in fp.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                c = json.loads(ln)
                out[c["name"]] = c
    return out


def persona_card(name: str, desc: str, md: Path | None) -> dict | None:
    """v17 (K-Dense scientific-agents' summary grammar, CONTRIBUTING.md:591-596; 475 of its 503 profiles follow it):
    'Reasons from <foundations> through <tools> while treating <failure modes> as first-class failure modes' is three
    card slots in one sentence: assumes (the foundations the persona takes for granted), probe (its tools), not_for
    (the failure modes it hunts: a task that is one of them is a misfit for a reasoner, it needs a checker). Marked
    persona=True so the sheet prices it (dial M42): the repo's own paper (arXiv 2610.00084) measured such profiles at
    -0.6 pp accuracy for 2.2-4.5x the cost, so a persona is a priced pick that needs a FIT, never a default."""
    m = PERSONA_RX.search(desc)
    if not m:
        return None
    split = lambda s: [x.strip(" ,.;") for x in re.split(r",\s*(?:and\s+)?|\s+and\s+", s) if x.strip(" ,.;")]  # noqa: E731
    foundations, tools, fails = m.group(1).strip(), (m.group(2) or "").strip(), m.group(3).strip()
    tools = tools or foundations                           # some profiles fold the tools into the foundations clause
    body = md.read_text(encoding="utf-8", errors="replace") if md and md.is_file() else ""
    return {"name": name, "persona": True, "auto": "persona",
            "questions": ["EXPLAIN", "VERIFY_CLAIM", "CHOOSE"],
            "input": {"kind": "TEXT", "shape": "a question, draft, plan or result in this field, as prose; it reasons, it does not compute"},
            "assumes": [f"the task is a {name.replace('-', ' ')} question: it rests on {f}" for f in split(foundations)[:3]],
            "output": f"a {name.replace('-', ' ')}'s reading: framing, the checks the field expects, named failure modes, a verdict in the field's terms",
            "probe": f"invoke /{name} on the subject (no script); its tools of thought: {tools[:160]}",
            "not_for": "computing anything (it is prose); a task that IS one of its failure modes - "
                       f"{'; '.join(split(fails)[:4])} - needs a checker skill, not a reasoner",
            "cost": f"~{tokens_of(body)} tokens to read" if body else "a full profile read",
            "tool": False, "skill_sha": hashlib.sha256(md.read_bytes()).hexdigest()[:16] if md and md.is_file() else None}


def stamp_cards(lib: "Library", path: Path | None = None) -> dict:
    """v17 (scientific-agents' version bump on body change): write skill_sha (sha of the SKILL.md) into every card so
    `doctor` can say which cards are STALE (the skill changed since the card was written). Only the sha key is touched."""
    f = path or (HERE / "cards" / "cards.jsonl")
    if not f.is_file():
        return {"stamped": 0, "stale": 0, "missing_skill": 0}
    rows = [json.loads(ln) for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    stamped = stale = missing = 0
    for c in rows:
        md = lib.md.get(c["name"])
        if md is None or not md.is_file():
            missing += 1
            continue
        sha = hashlib.sha256(md.read_bytes()).hexdigest()[:16]
        if c.get("skill_sha") and c["skill_sha"] != sha:
            stale += 1
        c["skill_sha"] = sha
        stamped += 1
    f.write_text("".join(json.dumps(c, sort_keys=True) + "\n" for c in rows), encoding="utf-8")
    return {"stamped": stamped, "stale": stale, "missing_skill": missing}


def stale_cards(lib: "Library", cards: dict[str, dict]) -> dict:
    """{stale: [names whose skill changed since the card's skill_sha], unstamped: n, ok: n}."""
    stale, unstamped, ok = [], 0, 0
    for n, c in cards.items():
        md = lib.md.get(n)
        if md is None or not md.is_file():
            continue
        if not c.get("skill_sha"):
            unstamped += 1
        elif c["skill_sha"] != hashlib.sha256(md.read_bytes()).hexdigest()[:16]:
            stale.append(n)
        else:
            ok += 1
    return {"stale": sorted(stale), "unstamped": unstamped, "ok": ok}


def card_score(task: dict, card: dict | None) -> int:
    """2 per question the task and the skill share, 1 when the skill takes the subject's kind (PREREG Amendment 9)."""
    if not card:
        return -1
    s = 2 * len(set(task.get("questions", [])) & set(card.get("questions", [])))
    return s + (1 if task.get("kind") and task.get("kind") == card.get("input", {}).get("kind") else 0)


def card_rank(names: list[str], task: dict, cards: dict[str, dict]) -> list[str]:
    """Carded skills with score >= 2 first, by score then by their place in `names` (the fused order); then the
    remaining carded skills; uncarded skills last, in their fused order."""
    pos = {n: i for i, n in enumerate(names)}
    sc = {n: card_score(task, cards.get(n)) for n in names}
    return sorted(names, key=lambda n: (0 if sc[n] >= 2 else 1 if sc[n] >= 0 else 2, -sc[n], pos[n]))


FIT_QUESTIONS = ("kind", "question", "assumes", "used")   # v17: the four judgments a FIT verdict rests on
FIT_MEANING = {"kind": "the subject is the kind of input the skill takes",
               "question": "the skill answers one of the questions the task asks",
               "assumes": "the skill's stated assumption holds on this subject",
               "used": "its output changed what was built (no = it ran, but nothing was used)"}


def parse_fit_judgments(words: list[str]) -> tuple[dict[str, bool] | None, list[str]]:
    """v17 (typesafe-ai: judgments from the model, the decision in code). `kind=yes question=yes assumes=no used=no`
    -> {q: bool}; the remaining words are the 'why'. None when no judgment was given (the old works|misfit form)."""
    j: dict[str, bool] = {}
    rest = []
    for w in words:
        m = re.fullmatch(r"(kind|question|assumes|used)=(yes|no|y|n)", w, re.I)
        if m:
            j[m.group(1).lower()] = m.group(2).lower().startswith("y")
        else:
            rest.append(w)
    return (j or None), rest


def fit_verdict(j: dict[str, bool]) -> str:
    """works needs kind, question and assumes all yes; `used` is recorded, never decides (a right pick can go unused)."""
    return "works" if all(j.get(q) for q in ("kind", "question", "assumes")) else "misfit"


def file_sha(p: str | Path | None) -> str | None:
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] if p and Path(p).is_file() else None
    except OSError:
        return None


def subject_state(rows: list[dict], run: str, skill: str | None = None) -> dict | None:
    """v17 (k-dense-byok: hash at citation time, STALE at read time). The latest subject recorded for a run (a TRY
    --subject, a USE_PLAN --on, a taste --subject), its sha then, and whether the file differs now."""
    best = None
    for r in rows:
        if r.get("run") != run or r.get("kind") not in ("TRY", "USE_PLAN") or not r.get("subject_sha"):
            continue
        if skill and r.get("skill") != skill and best is not None and best.get("skill") == skill:
            continue
        best = r
    if best is None:
        return None
    now = file_sha(best.get("subject") or best.get("on"))
    return {"subject": best.get("subject") or best.get("on"), "then": best["subject_sha"], "now": now,
            "stale": now is not None and now != best["subject_sha"]}


def stale_line(state: dict | None, what: str) -> str | None:
    if state and state["stale"]:
        return (f"STALE: {state['subject']} changed since the subject was recorded (sha {state['then'][:8]} -> "
                f"{state['now'][:8]}); this {what} speaks about an older file - re-run `try` before trusting it")
    return None


def fit_of(rows: list[dict], run: str, skill: str) -> str | None:
    """The latest FIT verdict of a skill in a run: 'works', 'misfit' or None."""
    v = None
    for r in rows:
        if r.get("kind") == "FIT" and r.get("run") == run and r.get("skill") == skill:
            v = r["verdict"]
    return v


def diff_registry(old: dict[str, str], new: dict[str, str]) -> dict[str, list[str]]:
    return {"NEW": sorted(set(new) - set(old)), "REMOVED": sorted(set(old) - set(new)),
            "CHANGED": sorted(k for k in set(old) & set(new) if old[k] != new[k])}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def recall(memory: list, words: set[str]) -> tuple[dict[str, float], dict[str, float]]:
    """Immune memory and opening book: for each skill, the strongest similarity of a past task where it was rated
    good (book) or wrong (antibody)."""
    book: dict[str, float] = {}
    anti: dict[str, float] = {}
    for w, skill, rating in memory:
        sim = jaccard(w, words)
        if sim < MEMORY_SIM:
            continue
        if rating == "wrong":
            anti[skill] = max(anti.get(skill, 0.0), sim)
        elif rating in BOOK_RATINGS:                     # fascination and favour are never evidence (excitement tax)
            book[skill] = max(book.get(skill, 0.0), sim)
    return book, anti


def context_stats(memory: list, words: set[str]) -> dict[str, dict[str, int]]:
    """C: each skill's rating record from past tasks similar to this one only (the same similarity bar as the opening
    book). A skill rated useful a hundred times on unrelated work gains nothing here: fit, not fame."""
    s: dict[str, dict[str, int]] = {}
    for w, skill, rating in memory:
        if jaccard(w, words) >= MEMORY_SIM:
            s.setdefault(skill, {}).setdefault(rating, 0)
            s[skill][rating] += 1
    return s


def ranking_text(task: str) -> str:
    """A: the task as the rankers see it. Asking words that name the tool itself ("is there a skill for ...") matched
    every description that calls itself a skill (2026-10-21: those 16% of the library took 38% of the pool)."""
    if not FAIR_ASKWORDS:
        return task
    kept = [w for w in re.findall(r"\S+", task) if re.sub(r"[^a-z]", "", w.lower()) not in ASK_WORDS]
    return " ".join(kept) or task


def weigh(cands: list[dict], stats: dict, favs: set[str]) -> list[dict]:
    """Fit is the fused score scaled to the best candidate. The other axes multiply fit, so nothing lifts a skill
    that does not fit; ease never earns points."""
    top = max((c["score"] for c in cands), default=0.0) or 1.0
    out = []
    for c in cands:
        st = stats.get(c["name"], {})
        good, bad = st.get("useful", 0) + st.get("favourite", 0), st.get("wrong", 0) + st.get("unused", 0)
        tool_part = 0.5 * bool(c.get("tool")) if TOOL_BONUS and not FAIR_NO_TOOL else 0.25   # D: guide = tool
        use = tool_part + 0.5 * (good + 1) / (good + bad + 2)              # tool + Laplace-rated record
        fasc = 0.5 * min(1.0, st.get("fascinating", 0) / 2)   # rated fascination only (v8g: novelty drifted rank 1, E31)
        fav = 1.0 if (c["name"] in favs or st.get("favourite", 0) > 0) else 0.0
        fit = c["score"] / top
        out.append({**c, "fit": round(fit, 3), "use": round(use, 3), "fasc": round(fasc, 3), "fav": fav,
                    "total": round(fit * (1 + W_USE * use + W_FASC * fasc + W_FAV * fav), 4)})
    return sorted(out, key=lambda r: (-r["total"], r["name"]))


def select(weighed: list[dict], top: int, family=None) -> tuple[list[dict], list[dict]]:
    """The no-corner-cutting rule: a skill ranked above another by its bonuses keeps that place only when its fit is
    within MARGIN of the other's; otherwise the better-fitting skill goes first and the swap is recorded. Then
    diversity: a third skill from one family yields to a near-tie (fit within MARGIN) from a family not yet chosen.
    The rule holds for EVERY pair, not only neighbours: each place goes to the best total among the skills whose fit is
    within MARGIN of the best fit still unplaced. (v5 swapped neighbours only, so a chain of small steps could lift a
    skill above one that fit better by more than MARGIN: bench E09 found 8 such pools in 2000.)"""
    left = sorted(weighed, key=lambda r: (-r["total"], r["name"]))
    order: list[dict] = []
    notes: list[dict] = []
    while left:
        bar = max(r["fit"] for r in left) - MARGIN
        pick = next(r for r in left if r["fit"] >= bar - 1e-12)     # the best total among the eligible
        if left[0] is not pick and all(n["demoted"] != left[0]["name"] for n in notes):
            a = left[0]
            cheaper = (not a.get("tool")) and bool(pick.get("tool"))
            notes.append({"demoted": a["name"], "for": pick["name"], "fit_gap": round(pick["fit"] - a["fit"], 3),
                          "why": "EASIER_NOT_CALLED_FOR" if cheaper else "BONUS_NOT_CALLED_FOR"})
        left.remove(pick)
        order.append(pick)
    chosen: list[dict] = []
    rest = list(order)
    while rest and len(chosen) < top:
        c = rest.pop(0)
        if family:
            fam = family(c["name"])
            if sum(family(x["name"]) == fam for x in chosen) >= FAMILY_CAP:
                have = {family(x["name"]) for x in chosen}
                bar = max([c["fit"]] + [r["fit"] for r in rest]) - MARGIN
                alt = next((r for r in rest if c["fit"] - r["fit"] <= MARGIN and r["fit"] >= bar - 1e-12
                            and family(r["name"]) not in have), None)
                if alt is not None:
                    rest.remove(alt)
                    rest.insert(0, c)
                    notes.append({"demoted": c["name"], "for": alt["name"], "fit_gap": round(c["fit"] - alt["fit"], 3),
                                  "why": "DIVERSITY (third of one family; a near-tie from another family)"})
                    c = alt
        chosen.append(c)
    for r in chosen:
        better = [o for o in order if o["fit"] > r["fit"]]
        if better and r.get("tool") is False and any(o.get("tool") for o in better):
            r["kept_because"] = "EASIER_BUT_CALLED_FOR (fit within margin; record or favour higher)"
    return chosen, notes


def is_checker(name: str, desc: str) -> bool:
    return bool(CHECKER.search(name.replace("-", " ") + " " + desc[:200]))


# --- the spectrum of tasks (v12, the user: "every spectrum of skill type, every need someone has or ever will ask") -----
TOOL_BONUS = True      # set per score from the task's kind; creative kinds judge documents and tools alike
KINDS_ON = True        # eval --no-kinds measures the library as if every task were analytical
TASK_KINDS = {   # kind -> markers in the task's own words; the kind with most hits leads, ANALYZE when none
    "ANALYZE": re.compile(r"\b(analy[sz]e|measure|test|check|verify|audit|compare|estimate|statistic\w*|signal|backtest|metric|prove|detect|count|rank|honest|real)\b", re.I),
    "BUILD": re.compile(r"\b(build|implement|code|refactor|fix|debug|deploy|install|automate|pipeline|script|module|api|function|class|tool)\b", re.I),
    "CREATE": re.compile(r"\b(creative\w*|brainstorm|invent|imagine|story|stories|poem|song|lyric|art|ideas?|novel|draw|compose|sketch|illustrat\w*|fascinat\w*|inspir\w*|metaphor|name for|slogan)\b", re.I),
    "ROLEPLAY": re.compile(r"\b(role[- ]?play|act as|pretend|persona|character|in character|play the|voice of|dialogue|improv\w*|scene|npc|game master|dungeon|interview me|be my)\b", re.I),
    "WRITE": re.compile(r"\b(write|draft|essay|email|letter|blog|article|report|summar\w*|rewrite|edit|proofread|copy|memo|headline|caption)\b", re.I),
    "TEACH": re.compile(r"\b(teach|explain|learn|tutor|lesson|understand|beginner|guide|walk me through|why does|how does|eli5|course|quiz me)\b", re.I),
    "DECIDE": re.compile(r"\b(decide|choose|options?|trade-?offs?|should (i|we)|plan|roadmap|priorit\w*|strategy|risk|budget|which one)\b", re.I),
    "RESEARCH": re.compile(r"\b(research|sources?|cite|literature|papers?|survey|investigate|background|history of|what is known|compare vendors)\b", re.I),
    "COMMUNICATE": re.compile(r"\b(reply|respond|negotiat\w*|persuad\w*|pitch|present\w*|slides?|deck|meeting|audience|stakeholder|announce|apolog\w*)\b", re.I),
    "OPERATE": re.compile(r"\b(schedule|monitor|cron|job|server|backup|migrate|restore|ops|incident|alert|nightly|restart)\b", re.I),
    "DATA": re.compile(r"\b(csv|json|spreadsheet|sql|table|dataset|chart|plot|dashboard|visuali[sz]\w*|clean the data|ingest|parse)\b", re.I),
    "PLAY": re.compile(r"\b(fun|game|puzzle|riddle|joke|trivia|play with|for laughs|bedtime)\b", re.I),
}
KIND_PRIORITY = ("ROLEPLAY", "CREATE", "PLAY", "TEACH", "WRITE", "COMMUNICATE", "DATA", "OPERATE", "RESEARCH", "BUILD", "DECIDE", "ANALYZE")
CREATIVE_KINDS = {"CREATE", "ROLEPLAY", "WRITE", "TEACH", "COMMUNICATE", "PLAY"}      # no tool bias, a critic not a checker
KIND_PHASES = {     # the work's phases per kind; analytical kinds keep UNDERSTAND -> BUILD -> VERIFY -> LAND
    "CREATE": ("FRAME", "GENERATE", "SELECT", "POLISH"),
    "ROLEPLAY": ("CAST", "VOICE", "PLAY", "DEBRIEF"),
    "WRITE": ("BRIEF", "DRAFT", "CRITIQUE", "DELIVER"),
    "COMMUNICATE": ("BRIEF", "DRAFT", "CRITIQUE", "DELIVER"),
    "TEACH": ("LEVEL", "EXPLAIN", "PRACTISE", "CHECK"),
    "PLAY": ("SETUP", "PLAY", "SCORE", "ENCORE"),
}
EXTRA_ROLES = {     # how a skill's name and first sentence show which of the new phases it serves
    "FRAME": re.compile(r"\b(brief|purpose|frame|read|reads|understand|presuppos\w*|lens|view|eye|subject)\b", re.I),
    "GENERATE": re.compile(r"\b(generat\w*|brainstorm|idea|ideas|invent|breed|cross|combine|dream|free|recombin\w*|sweep|forge|kingdom|association)\b", re.I),
    "SELECT": re.compile(r"\b(rank|choose|pick|score|vote|tie|tournament|ladder|novelty|jury|council|select)\b", re.I),
    "POLISH": re.compile(r"\b(edit|polish|refine|rewrite|strip|squash|plain|clarity|rhythm|shorten|caption|audience)\b", re.I),
    "CAST": re.compile(r"\b(persona|character|role|roles|voice|audience|actor|outsider|council|stakeholder|tribe)\b", re.I),
    "VOICE": re.compile(r"\b(rewrite|first-person|second-person|tone|mood|genre|voice|valence|register|style)\b", re.I),
    "PLAY": re.compile(r"\b(play|game|turn|scene|dialogue|improv\w*|chess|swiss|arena|round|evolution)\b", re.I),
    "DEBRIEF": re.compile(r"\b(report|receipt|reflect|summar\w*|lesson|scar|ledger|epiphany|log)\b", re.I),
    "BRIEF": re.compile(r"\b(brief|purpose|audience|read|reads|ask|intent|subtext|presuppos\w*)\b", re.I),
    "DRAFT": re.compile(r"\b(write|writes|draft|generat\w*|compose|rewrite|splice|template|genre)\b", re.I),
    "CRITIQUE": re.compile(r"\b(critic\w*|review|skeptic|devil\w*|steelman|expert|flag|check|jargon|smell|confabulat\w*|opponent|inner)\b", re.I),
    "DELIVER": re.compile(r"\b(report|send|post|land|deliver|receipt|publish|mailbox|handoff|hand-off|plain)\b", re.I),
    "LEVEL": re.compile(r"\b(beginner|novice|level|jargon|reading|grade|apprentice|over-the-shoulder|plain)\b", re.I),
    "EXPLAIN": re.compile(r"\b(explain|plain|metaphor|analog\w*|concept|teach|terms|lexicon|walkthrough|why)\b", re.I),
    "PRACTISE": re.compile(r"\b(quiz|exercise|probe|test|example|drill|leitner|recheck|flash)\b", re.I),
    "CHECK": CHECKER,
    "SETUP": re.compile(r"\b(setup|set up|rules|seed|cast|symmetry|pairing|arena|tournament)\b", re.I),
    "SCORE": re.compile(r"\b(score|rank|ladder|rating|tournament|chess|swiss|elo|novelty)\b", re.I),
    "ENCORE": re.compile(r"\b(encore|next|again|momentum|resume|continue|chain)\b", re.I),
}
ALL_ROLES = {**ROLES, **EXTRA_ROLES}
CRITIC = re.compile(r"\b(critic\w*|devil\w*|steelman|skeptic|opponent|review\w*|expert|jury|inner)\b", re.I)
SIDE_EFFECTS = re.compile(r"\b(delete|deletes|remove|removes|overwrite|overwrites|push|pushes|post|posts|send|sends|publish|publishes|"
                          r"install|uninstall|commit|commits|order|orders|trade|trades|pay|pays|email|emails|drop|drops|wipe|rm)\b", re.I)


def task_kinds(task: str) -> list[tuple[str, int]]:
    """The task's kinds by marker hits, strongest first; ANALYZE alone when nothing matches."""
    hits = [(k, len(rx.findall(task))) for k, rx in TASK_KINDS.items()]
    order = {k: i for i, k in enumerate(KIND_PRIORITY)}     # on a tie the more specific kind leads
    hits = sorted([h for h in hits if h[1] > 0], key=lambda x: (-x[1], order.get(x[0], 99)))
    return hits[:3] or [("ANALYZE", 0)]


def is_critic(name: str, desc: str) -> bool:
    return bool(CRITIC.search(name.replace("-", " ") + " " + desc[:200]))


def side_effects(desc: str) -> list[str]:
    """Verbs in a skill's description that change the world outside the session: the user consents before it runs."""
    return sorted({m.lower().rstrip("s") for m in SIDE_EFFECTS.findall(desc[:400])})


def spectrum(kinds: list[tuple[str, int]], desc: dict) -> list[str]:
    """For each of the task's kinds, how many library skills serve it (name + description match its markers): a thin
    kind is where a library needs a new skill (skill-foundry) or a plugin."""
    out = []
    for k, n in kinds:
        rx = TASK_KINDS[k]
        count = sum(1 for name, d in desc.items() if rx.search(name.replace("-", " ") + " " + d[:300]))
        out.append(f"{k} ({n} marker{'s' if n != 1 else ''} in the ask; {count} skill{'s' if count != 1 else ''} in the library"
                   + (", THIN: consider skill-foundry or a plugin" if count < 5 else "") + ")")
    return out


def first_command(md: Path) -> str | None:
    """Mise en place: the first runnable line of the skill's own instructions (a fenced `python ...` line)."""
    if not md.is_file():
        return None
    inside = False
    for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        s = line.strip()
        if inside and re.match(r"(python|py|\.\\|bash|pwsh|node)\b", s) and "--selftest" not in s:
            return s[:140]
    return None


def roles_of(name: str, desc: str, phases: tuple = PHASE_ORDER) -> list[str]:
    text = name.replace("-", " ") + " " + desc.split(". ")[0]
    return [r for r in phases if ALL_ROLES[r].search(text)]


def agenda(chosen: list[dict], pool: list[dict], desc: dict, phases: tuple = PHASE_ORDER) -> list[tuple[str, str, str]]:
    """The work in phases: for each phase the best chosen skill that serves it, else the best pooled one (marked).
    The phases are the task kind's (KIND_PHASES); analytical work keeps UNDERSTAND -> BUILD -> VERIFY -> LAND."""
    out = []
    used: set[str] = set()
    for ph in phases:
        pick = next((c["name"] for c in chosen if ph in roles_of(c["name"], desc.get(c["name"], ""), phases) and c["name"] not in used), None)
        src = "chosen"
        if pick is None:
            pick = next((c["name"] for c in pool if ph in roles_of(c["name"], desc.get(c["name"], ""), phases) and c["name"] not in used), None)
            src = "from the pool"
        if pick:
            used.add(pick)
            out.append((ph, pick, src))
        else:
            out.append((ph, "-", "no skill in the pool serves this phase: do it by hand and say so"))
    return out


def context(task_words: set[str], tokens) -> list[str]:
    """The contextualizer: when the working folder holds a phased plan (plans/PLAN.md with §0 and
    plans/phase_check.py), say where the project stands and which cards the task touches, with their phases."""
    cwd = Path.cwd()
    plan, chk = cwd / "plans" / "PLAN.md", cwd / "plans" / "phase_check.py"
    if not plan.is_file():
        return []
    out = []
    if chk.is_file():
        try:
            pc = _load(chk, "phase_check")
            rows = pc.table(cwd)
            first_open = next((r for r in rows if r[1] == "OPEN"), None)      # the first phase WORK can move
            waiting = [r[0].split()[0] for r in rows if r[1] == "NEEDS_MAX"]
            out.append("project phases: " + "; ".join(f"{r[0].split()[0]} {r[1]}" for r in rows))
            if first_open:
                out.append(f"first phase work can move: {first_open[0]} ({first_open[2][:90]})")
            if waiting:
                out.append(f"phases waiting on {OWNER}: {', '.join(waiting)}")
        except Exception as exc:                     # noqa: BLE001 - context is a courtesy, never a blocker
            out.append(f"phase map unreadable ({type(exc).__name__})")
    text = plan.read_text(encoding="utf-8", errors="replace")
    phase_of: dict[str, str] = {}
    if "## 0. " in text and "## 1. " in text:
        s0 = text[text.index("## 0. "):text.index("## 1. ")]
        for line in s0.splitlines():
            mm = re.match(r"^\| (\d) [^|]+\| ([^|]*) \|", line)
            if mm and mm.group(1) != "6":
                span = mm.group(2)
                ids = set(re.findall(r"GT\d+", span))
                for a, b in re.findall(r"GT(\d+)-GT(\d+)", span):
                    ids |= {f"GT{i}" for i in range(int(a), int(b) + 1)}
                for c in ids:
                    phase_of[c] = mm.group(1)
    cards = []
    for mm in re.finditer(r"^### (GT\d+): ([^\n]+)", text, re.M):
        w = set(tokens(mm.group(2)))
        hit = len(w & task_words)
        if hit:
            cards.append((hit / (len(w) ** 0.5), mm.group(1), mm.group(2)[:70]))
    named = set(re.findall(r"GT\d+", " ".join(task_words).upper()))
    for c in named:
        mm = re.search(rf"^### {c}: ([^\n]+)", text, re.M)
        if mm:
            cards.append((99.0, c, mm.group(1)[:70]))
    best: dict[str, tuple] = {}
    for sc, c, title in cards:
        if c not in best or sc > best[c][0]:
            best[c] = (sc, c, title)
    for _, c, title in sorted(best.values(), reverse=True)[:3]:
        out.append(f"plan card {c} (phase {phase_of.get(c, '6')}): {title}")
    return out


def water_fill(need: dict[str, int], budget: int) -> dict[str, int]:
    """Share `budget` reading lines across skills the way osmosis evens a quantity out while conserving it: every
    skill gets an equal level, a skill that needs less than the level is read whole and gives the rest back, and
    the shares sum to min(budget, total need)."""
    left, out = budget, {}
    todo = sorted(need, key=lambda n: need[n])
    while todo:
        level = left // len(todo)
        n = todo[0]
        if need[n] <= level:
            out[n] = need[n]
            left -= need[n]
            todo.pop(0)
        else:
            for m in todo:
                out[m] = level
            left -= level * len(todo)
            for m in todo[:left]:
                out[m] += 1                          # hand out the remainder so the total is conserved exactly
            break
    return out


def learned_duets(rows: list[dict]) -> dict[str, set[str]]:
    """Two skills rated useful in the same run are a duet; duets join the network as edges."""
    by_run: dict[str, set[str]] = {}
    for r in rows:
        if r.get("kind") == "RATE" and r.get("rating") == "useful":
            by_run.setdefault(r["run"], set()).add(r["skill"])
    out: dict[str, set[str]] = {}
    for names in by_run.values():
        for a in names:
            out.setdefault(a, set()).update(names - {a})
    return out


def purpose(ctx: list[str]) -> str | None:
    """Motivation as focus: tie the task to the first phase work can move (OPEN; a phase waiting on the user cannot be
    moved by work), or say plainly that it does not advance it."""
    open_line = next((c for c in ctx if c.startswith("first phase work can move:")), None)
    if not open_line:
        return None
    phase = open_line.split(":", 1)[1].strip().split(" (")[0]
    num = phase.split()[0] if phase else "?"
    serving = [c for c in ctx if c.startswith("plan card ") and f"(phase {num})" in c]
    if serving:
        card = re.match(r"plan card (\S+)", serving[0])
        return (f"PURPOSE: this serves phase {phase} through {card.group(1) if card else serving[0][10:]}; that is the "
                "work that moves the project.")
    return (f"PURPOSE: the first phase work can move is {phase}; this task does not touch its cards. Say in one line "
            "why it is worth doing now, or turn to that phase.")


def reflect(rows: list[dict], top: int = 8) -> list[str]:
    """The Maestro looks back: proved useful, traps learned (wrong with reasons), wallflowers (pooled often, chosen
    never: the curiosity queue), duets."""
    from collections import Counter
    useful = Counter(r["skill"] for r in rows if r.get("kind") == "RATE" and r.get("rating") == "useful")
    wrong = [(r["skill"], r.get("why", "")) for r in rows if r.get("kind") == "RATE" and r.get("rating") == "wrong"]
    pooled = Counter(n for r in rows if r.get("kind") == "SCORE" for n in r.get("pool_names", []))
    chosen = {n for r in rows if r.get("kind") == "SCORE" for n in r.get("chosen", [])}
    wall = [(n, c) for n, c in pooled.most_common() if n not in chosen and c >= 2][:top]
    L = [f"REFLECT over {sum(1 for r in rows if r.get('kind') == 'SCORE')} runs, "
         f"{sum(1 for r in rows if r.get('kind') == 'RATE')} ratings, {sum(1 for r in rows if r.get('kind') == 'READ')} reads"]
    L.append("proved useful: " + (", ".join(f"{n} x{c}" for n, c in useful.most_common(top)) or "nothing rated useful yet"))
    L.append("traps learned (antibodies): " + ("; ".join(f"{n} ({w[:60]})" if w else n for n, w in wrong) or "none yet"))
    L.append("wallflowers (in the pool again and again, never chosen; try one): "
             + (", ".join(f"{n} x{c}" for n, c in wall) or "none yet (pools are recorded from v5 on)"))
    d = learned_duets(rows)
    pairs = sorted({tuple(sorted((a, b))) for a, bs in d.items() for b in bs})
    L.append("duets learned (rated useful together; now network edges): " + (", ".join(f"{a}+{b}" for a, b in pairs[:top]) or "none yet"))
    return L


def encore(rows: list[dict], run: str | None = None) -> list[str]:
    """The next move of a run: phases done (skill read and rated in the run), the next phase and its command, one
    wallflower as the curiosity pick, or CLOSED."""
    scores = [r for r in rows if r.get("kind") == "SCORE" and r.get("agenda")]
    if not scores:
        return ["ENCORE: no run with an agenda yet (runs record their agenda from v5 on)"]
    s = next((r for r in scores if r["run"] == run), None) if run else scores[-1]
    if s is None:
        return [f"ENCORE: run {run} not found"]
    read = {r["skill"] for r in rows if r.get("kind") == "READ" and r.get("run") == s["run"]}
    rated = {r["skill"]: r["rating"] for r in rows if r.get("kind") == "RATE" and r.get("run") == s["run"]}
    for run_, sk in rated_pairs(rows):
        if run_ == s["run"]:
            rated.setdefault(sk, "metrics")
    L = [f"ENCORE for run {s['run']}"]
    nxt = None
    for ph, name in s["agenda"]:
        if name == "-":
            L.append(f"  {ph:<10} -  (no skill served it; done by hand)")
        elif name in read and name in rated and fit_of(rows, s["run"], name):
            L.append(f"  {ph:<10} {name}: done ({rated[name]}, FIT {fit_of(rows, s['run'], name)})")
        else:
            state = ("no FIT verdict yet (`maestro.py try` it on the subject, then `fit`)" if name in read and name in rated
                     else "read, not yet rated" if name in read else "not yet read")
            L.append(f"  {ph:<10} {name}: {state}")
            nxt = nxt or (ph, name)
    agenda_names = {name for _, name in s["agenda"]}
    added = sorted({r["skill"] for r in rows if r.get("run") == s["run"] and r.get("kind") in ("TRY", "FIT")
                    and r.get("skill") and r["skill"] not in agenda_names and r["skill"] != SELF})
    for n in added:                                          # v18: the judge's own additions, sheet or not
        L.append(f"  ADDED      {n}: judge's addition, FIT {fit_of(rows, s['run'], n) or 'pending'}"
                 + (", rated" if n in rated else ", not yet rated"))
    if nxt is None:
        L.append("CLOSED: every phase was read and rated. Start the next task with `maestro.py score`.")
        return L
    cmd = (s.get("first_cmds") or {}).get(nxt[1])
    L.append(f"NEXT: {nxt[0]} with {nxt[1]}" + (f": run `{cmd}`" if cmd else ": open its SKILL.md") +
             f"; then `maestro.py read {s['run']} {nxt[1]}` and `maestro.py rate {s['run']} {nxt[1]} <rating>`")
    chosen_ever = {n for r in rows if r.get("kind") == "SCORE" for n in r.get("chosen", [])}
    on_agenda = {name for _, name in s["agenda"]}
    pick = thompson_pick(rows, s, exclude=on_agenda)
    if pick:
        L.append(f"CURIOSITY (one, taxed: one extra check before trusting it): {pick[0]} - Thompson draw {pick[1]:.2f} "
                 f"from its record on this run's questions ({pick[2]})")
    return L


def thompson_pick(rows: list[dict], s: dict, exclude: set = frozenset()) -> tuple[str, float, str] | None:
    """The curiosity pick: for each skill in the run's pool (not on its agenda), draw theta ~ Beta(good+1, bad+1) from
    its record on the run's questions (good = useful / FIT works / the user >= 4; bad = wrong, unused, misfit, the user <= 1) and
    take the highest draw. Untried skills draw from Beta(1, 1), known misfits from a low Beta: exploration with memory."""
    import random
    qs = tuple(s.get("questions") or ())
    rng = random.Random(s["run"])
    st = State.__new__(State)
    st.rows = lambda: rows                                   # reuse stats() over the given rows
    rec = State.stats(st, qs)
    works = {r["skill"] for r in rows if r.get("kind") == "FIT" and r.get("verdict") == "works"
             and (not qs or r.get("run") in {x["run"] for x in rows if x.get("kind") == "SCORE"
                                             and set(x.get("questions") or ()) & set(qs)})}
    best = None
    for n in s.get("pool_names", []):
        if n in exclude:
            continue
        r = rec.get(n, {})
        good = r.get("useful", 0) + r.get("favourite", 0) + (1 if n in works else 0)
        bad = r.get("wrong", 0) + r.get("unused", 0)
        theta = rng.betavariate(good + 1, bad + 1)
        if best is None or theta > best[1]:
            best = (n, theta, f"{good} good, {bad} bad" + (f" on {'/'.join(qs)}" if qs else " overall"))
    return best


def baton(rows: list[dict], run: str) -> list[str]:
    """The Conductor's Protocol as state: each step met or not, the two pause points, and the next move."""
    s = next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == run), None)
    if s is None:
        return [f"BATON: no run {run}"]
    mine = [r for r in rows if r.get("run") == run]
    plans = {r["skill"]: r for r in mine if r.get("kind") == "USE_PLAN"}
    picks = list(plans) or list(s.get("chosen", []))
    tried = {r["skill"] for r in mine if r.get("kind") == "TRY"}
    tasted = {r["skill"] for r in mine if r.get("kind") == "TRY" and r.get("taste")}
    read = {r["skill"] for r in mine if r.get("kind") == "READ"}
    fits = {}
    for r in mine:
        if r.get("kind") == "FIT":
            fits[r["skill"]] = r["verdict"]
    rated = {sk for (_, sk) in rated_pairs(mine)}
    added = sorted(({r["skill"] for r in mine if r.get("kind") in ("TRY", "FIT") and r.get("skill")} - set(picks)) - {SELF})
    picks = picks + added                 # v18: a skill the judge tried or judged is a pick, whether or not the sheet named it
    subject = next((pl.get("on") for pl in plans.values() if pl.get("on")), None) or \
        next((r.get("subject") for r in mine if r.get("subject")), None)
    steps = [
        ("0 SUBJECT", bool(subject), f"named: {subject}" if subject else "name the exact subject (`plan ... --on FILE`)"),
        ("1 QUESTIONS", bool(s.get("questions")), "/".join(s.get("questions") or []) or "re-score with --questions"),
        ("2 CANDIDATES", bool(s.get("chosen")), f"{len(s.get('chosen', []))} on the sheet, menus {sorted(s.get('menus', {}))}"),
        ("3 TASTE", bool(tasted), f"{len(tasted)} tasted (optional; UNCALIBRATED)"),
        ("4 COMMIT", bool(plans) and 1 <= len(plans) <= 6,
         f"{len(plans)} picks with a use-plan line" if plans else "write a use-plan line per pick (`plan`)"),
        ("5 USE", bool(picks) and all(n in read and n in tried for n in picks),
         f"read {len(read & set(picks))}/{len(picks)}, run on the subject {len(tried & set(picks))}/{len(picks)}"),
        ("6 VERDICT", bool(picks) and all(n in fits for n in picks),
         f"{sum(n in fits for n in picks)}/{len(picks)} with works|misfit"),
        ("7 LEARN", bool(picks) and any(n in rated for n in picks), f"{len(rated & set(picks))}/{len(picks)} rated"),
    ]
    L = [f"BATON for run {run}" + (" (CLOSED)" if any(r.get("kind") == "CLOSE" for r in mine) else "")]
    if added:
        L.append(f"  ADDED BY THE JUDGE (tried or judged, not on the sheet; they count as picks here): {', '.join(added)}")
    for name, met, note in steps:
        L.append(f"  [{'x' if met else ' '}] {name:<13} {note}")
    p1 = bool(subject) and bool(plans) and all(n in tried for n in plans)
    p2 = bool(picks) and all(n in fits for n in picks)
    L.append(f"  PAUSE 1 (before using): {'clear' if p1 else 'NOT clear: subject named, a use-plan line and a run on the subject for every pick'}")
    L.append(f"  PAUSE 2 (before reporting): {'clear' if p2 else 'NOT clear: every pick needs works|misfit'}; then sweep the "
             "person's own words (open-steps-sweep) before saying done")
    nxt = next((name for name, met, _ in steps if not met and not name.startswith("3")), None)
    L.append(f"NEXT: {nxt}" if nxt else "NEXT: report, with each finding beside the pick and subject that produced it")
    return L


def breed(rows: list[dict], run: str, mechs: dict, family, root: Path, task_text: str = "") -> dict:
    """v10e item 10 (fascination for the skills NEEDED): cross the run's two strongest picks from different families
    into a proposed NEW skill - cross-breed picks the reproduction operator, word-sex coins the name, and skill-foundry
    runs its gates as a DRY RUN (nothing is created). Returns the proposal and every gate's verdict."""
    sc = next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == run), None)
    if sc is None:
        return {"error": f"RUN_UNKNOWN {run}"}
    chosen = [n for n in sc.get("chosen", []) if n in mechs]
    a = chosen[0] if chosen else None
    b = next((n for n in chosen[1:] if family(n) != family(a)), None) if a else None
    if not (a and b):
        return {"error": "need two picks from different families with mechanism lines"}
    cb = _load(root / "cross-breed" / "breed_plan.py", "breed_plan")
    ws = _load(root / "word-sex" / "word_sex.py", "word_sex")
    fd = _load(root / "skill-foundry" / "foundry.py", "foundry")
    op = (cb.choose_operator("skills", "1:1") or [{"operator": "graft"}])[0]["operator"]
    seg = lambda n: max(n.split("-"), key=len)  # noqa: E731  (the most telling part of a hyphenated name)
    existing = {p.name for p in root.iterdir() if p.is_dir()}
    kids = [k for k, _ in ws.breed(seg(a), seg(b), 8) if re.fullmatch(r"[a-z][a-z0-9]{2,}", k) and k not in existing]
    name = kids[0] if kids else f"{seg(a)}-{seg(b)}"
    da, db = mechs[a]["does"].rstrip(". "), mechs[b]["does"].rstrip(". ")
    mechanism = f"{da[0].lower() + da[1:]}, then {db[0].lower() + db[1:]}"
    pitch = (f"- crosses {a} and {b} by {op} [IMAGINED]\n"
             f"- proposed for the task: {(task_text or sc.get('task', ''))[:80]} [IMAGINED]")
    res = fd.found(name, mechanism, pitch=pitch, root=root, dry_run=True)
    return {"run": run, "parents": [a, b], "operator": op, "name": name, "name_options": kids[:5],
            "mechanism": mechanism, "gates": res["gates"], "passed": res["passed"], "stopped_at": res["stopped_at"]}


def code_type_skills() -> set[str]:
    """Item 7: the skills the sticky CODE type grafts (its 'abilities' in code-types/types.json)."""
    try:
        sticky = json.loads(STICKY_TYPE.read_text(encoding="utf-8")).get("sticky") if STICKY_TYPE.is_file() else None
        if not sticky:
            return set()
        data = json.loads((ROOT / "code-types" / "types.json").read_text(encoding="utf-8"))
        return set(next((t["abilities"] for t in data["types"] if t["id"] == sticky), []))
    except (OSError, ValueError, KeyError):
        return set()


def code_type_line() -> str | None:
    """v10e item 7: the sticky CODE type (set by #marker in a prompt) changes how the sheet should be used."""
    try:
        sticky = json.loads(STICKY_TYPE.read_text(encoding="utf-8")).get("sticky") if STICKY_TYPE.is_file() else None
    except (OSError, ValueError):
        return None
    if not sticky:
        return None
    tlines = {"keelwright": "plan the interfaces first; PONDER is REQUIRED before any pick",
              "nightwatch": "PONDER is REQUIRED; add a soak check to the use plan",
              "wardsmith": "PONDER is REQUIRED; the bypass attempts are the first use",
              "quind": "keep the sheet short: take the first two picks and go, no PONDER needed",
              "spatch": "take one SPARK skill and run it; no full sheet needed",
              "marvey": "read-only: picks may be read, never used to edit"}
    return f"CODE TYPE {sticky} is sticky: {tlines.get(sticky, 'use the type profile in ~/.claude/skills/' + sticky)}"


def used_report(rows: list[dict], run: str | None) -> list[str]:
    """v10e item 9: named vs used. For each run, a chosen skill is NAMED on the sheet, and USED if it has a READ,
    a TRY (run on the subject) or a FIT verdict. Pre-v10 runs without the record say so instead of guessing."""
    runs = [r for r in rows if r.get("kind") == "SCORE" and (run is None or r.get("run") == run)]
    if run is None:
        runs = runs[-20:]
    out, tot_named, tot_used = [], 0, 0
    for sc in runs:
        chosen = sc.get("chosen", [])
        used = {r["skill"] for r in rows if r.get("run") == sc["run"] and r.get("kind") in ("READ", "TRY", "FIT")}
        ran = {r["skill"] for r in rows if r.get("run") == sc["run"] and r.get("kind") == "TRY"}
        n_used = sum(1 for c in chosen if c in used)
        tot_named += len(chosen)
        tot_used += n_used
        unused = [c for c in chosen if c not in used]
        line = f"{sc['run']}: named {len(chosen)}, used {n_used} (ran on the subject: {len(ran & set(chosen))})"
        if unused:
            line += f"  NAMED ONLY: {', '.join(unused)}"
        added = sorted(used - set(chosen) - {SELF})
        if added:
            line += f"  ADDED BY THE JUDGE: {', '.join(added)}"   # v18: used though the sheet never named them
        out.append(line)
    if runs:
        out.append(f"TOTAL over {len(runs)} run(s): named {tot_named}, used {tot_used}"
                   + (f" ({tot_used / tot_named:.0%})" if tot_named else ""))
    else:
        out.append("no score runs yet")
    return out


def task_parts(task: str) -> list[str]:
    """The task's sentences; a one-sentence task is cut into three word-thirds (E34's split)."""
    import math
    ps = [x.strip() for x in re.split(r"(?<=[.?!])\s+|\n+", task) if x.strip()]
    if len(ps) >= 2:
        return ps
    w = task.split()
    k = max(1, math.ceil(len(w) / 3))
    return [" ".join(w[i:i + k]) for i in range(0, len(w), k)]


def stability(lib, task: str, names: list[str], stats: dict, favs: set) -> dict[str, float]:
    """Share of leave-one-part-out variants whose top 6 still holds each name (STABLE at >= 0.75; E34)."""
    ps = task_parts(task)
    variants = [" ".join(ps[:i] + ps[i + 1:]) for i in range(min(4, len(ps)))] if len(ps) > 1 else []
    tops = []
    for v in variants:
        if v.strip():
            pool = lib.fused(v)[:POOL]
            tops.append({c["name"] for c in select(weigh(pool, stats, favs), 6, lib.family)[0]})
    return {n: (sum(n in tp for tp in tops) / len(tops) if tops else 1.0) for n in names}


def stabilize(lib, task: str, chosen: list[dict], order: list[dict], stats: dict, favs: set, spare: int = 3):
    """v12 experiment: a chosen pick that is unstable (< STABLE_AT of the leave-one-part-out readings) yields to the
    first unchosen candidate within MARGIN of its fit that is stable. Returns (chosen, notes, stability by name)."""
    names = [c["name"] for c in chosen]
    extra = [r for r in order if r["name"] not in names][:spare]
    stab = stability(lib, task, names + [r["name"] for r in extra], stats, favs)
    out, notes = list(chosen), []
    for i, c in enumerate(out):
        if stab.get(c["name"], 1.0) >= STABLE_AT:
            continue
        for alt in extra:
            if alt["name"] in {x["name"] for x in out} or stab.get(alt["name"], 0.0) < STABLE_AT:
                continue
            if c["fit"] - alt["fit"] <= MARGIN:
                notes.append({"demoted": c["name"], "for": alt["name"], "fit_gap": round(c["fit"] - alt["fit"], 3),
                              "why": f"STABILITY_SWAP ({stab[c['name']]:.0%} vs {stab[alt['name']]:.0%} of the readings; fit within margin)"})
                out[i] = dict(alt)
                break
    return out, notes, stab


def wilson_ci(k: int, n: int) -> str:
    import math
    if n == 0:
        return "[-]"
    z, ph = 1.96, k / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return f"[{max(0.0, c - h):.2f}, {min(1.0, c + h):.2f}]"


def forward(rows: list[dict]) -> list[str]:
    """The running log (PREREG Amendment 15): only runs the user rated; picks frozen at decision time."""
    import math
    scores = {r["run"]: r for r in rows if r.get("kind") == "SCORE"}
    appr: dict[str, set[str]] = {}
    rej: dict[str, set[str]] = {}
    for r in latest_metrics(rows):
        if r["by"] != "max" or r["run"] not in scores:
            continue
        tm = group_mean(r["scores"], METRICS_TOPIC)
        if tm is None:
            continue
        tg = r["target"]
        members = scores[r["run"]].get("menus", {}).get(tg[5:], []) if tg.startswith("menu:") else [tg]
        if tm >= 4:
            appr.setdefault(r["run"], set()).update(members)
        elif tm <= 1:
            rej.setdefault(r["run"], set()).update(members)
    rated = sorted(set(appr) | set(rej), key=lambda x: scores[x].get("t", 0))
    live = [x for x in rated if scores[x].get("finder_top") is not None]
    legacy = [x for x in rated if scores[x].get("finder_top") is None]
    L = [f"FORWARD LOG: {len(live)} rated run(s) with frozen picks, {len(legacy)} LEGACY (rated before v9a: no finder "
         f"baseline). Approved = {OWNER} topic >= 4 (or a menu he rated >= 4); rejected = <= 1."]
    m1 = m3 = f1 = f3 = 0
    b = c = 0
    wins = {k: 0 for k in "ABCDE"}
    rejected_in_a = 0
    by_code: dict[str, list[int]] = {}
    for x in live:
        s = scores[x]
        a = s.get("menus", {}).get("A", [])
        fz = s.get("finder_top", [])
        good = appr.get(x, set())
        mh1, mh3 = bool(a[:1] and a[0] in good), bool(good & set(a))
        fh1, fh3 = bool(fz[:1] and fz[0] in good), bool(good & set(fz))
        m1 += mh1
        m3 += mh3
        f1 += fh1
        f3 += fh3
        b += mh3 and not fh3
        c += fh3 and not mh3
        rejected_in_a += bool(rej.get(x, set()) & set(a))
        for k in wins:
            wins[k] += bool(good & set(s.get("menus", {}).get(k, [])))
        by_code.setdefault(s.get("code", "?"), [0, 0])
        by_code[s.get("code", "?")][0] += mh3
        by_code[s.get("code", "?")][1] += 1
        L.append(f"  {time.strftime('%m-%d %H:%M', time.gmtime(s.get('t', 0)))} {x} {s.get('code', '?')}  Maestro A "
                 f"{'@1' if mh1 else '  '}{'@3' if mh3 else '  '}  finder {'@1' if fh1 else '  '}{'@3' if fh3 else '  '}  "
                 f"approved {sorted(good)[:3]}  | {s.get('task', '')[:70]}")
    n = len(live)
    if n:
        L.append(f"Maestro@1 {m1}/{n} {wilson_ci(m1, n)}   Maestro@3 {m3}/{n} {wilson_ci(m3, n)}   "
                 f"finder@1 {f1}/{n} {wilson_ci(f1, n)}   finder@3 {f3}/{n} {wilson_ci(f3, n)}")
        L.append(f"menu A held a skill {OWNER} rejected in {rejected_in_a}/{n} run(s); menu wins "
                 + ", ".join(f"{k} {v}/{n}" for k, v in wins.items()))
        L.append("by code version (Maestro@3): " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in by_code.items()))
        if n >= 10:
            k_ = min(b, c)
            pm = min(1.0, 2 * sum(math.comb(b + c, i) for i in range(k_ + 1)) / 2 ** (b + c)) if b + c else 1.0
            L.append(f"McNemar Maestro@3 vs finder@3: Maestro-only {b}, finder-only {c}, exact p {pm:.3f}")
        else:
            L.append(f"(n {n} < 10: counts and intervals only; the McNemar test starts at 10 rated runs)")
    else:
        L.append(f"No rated run with frozen picks yet: after a run, {OWNER} rates it in chat and Claude records "
                 "`maestro.py rate last menu:A --by max topic=<0-5> \"<his words>\"`.")
    for x in legacy:
        L.append(f"  LEGACY {x}: approved {sorted(appr.get(x, set()))[:3]} rejected {sorted(rej.get(x, set()))[:3]}")
    return L


def stay_inside(task: str) -> list[str]:
    return [m.group(0).strip()[:160] for m in SCOPE.finditer(task)][:4]


# v11 TRIAGE (2026-10-21, the user: "doesn't it cost way to much to load in skill maestro?"). Measured that day on GT198,
# a card that already named its files, red tests and plants: the instructions (~8,000 tokens) plus a concept sheet
# (~5,000) plus the picks' SKILL.md files (~280 lines) bought 2 useful picks of 6, and 5 of the card's 6 operations
# came back NEEDED. So score() asks first whether a sheet is worth its cost, and says so in a few lines when it is not.
TRIAGE_OPEN = re.compile(r"\b(?:design|invent|imagine|brainstorm|explore|new (?:way|kind|idea)s?|architect\w*|strategy|"
                         r"rethink|reinvent|creative|fascinat\w*|which approach|how (?:should|could|would) (?:we|i)|"
                         r"what (?:should|could) we)\b", re.I)
TRIAGE_ASK = re.compile(r"^\s*(?:is there|are there|do (?:we|i) have|which|what)\b[^.?]{0,40}\bskills?\b|\bskills? (?:for|to)\b",
                        re.I)
CARD_ID = re.compile(r"\b(GT\d{1,4}|H-[A-G])\b", re.I)


def card_spec(card: str, project: Path | None) -> bool:
    """True when the plan card is already a full recipe: its section in plans/PLAN.md names red tests (and files or an
    outcome). A sheet adds little to such a card; a vague card still gets one."""
    plan = (project or Path.cwd()) / "plans" / "PLAN.md"
    if not plan.is_file():
        return False
    text = plan.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^### {re.escape(card.upper())}:.*?(?=^### |\Z)", text, re.M | re.S)
    if not m:
        return False
    body = m.group(0)
    return bool(re.search(r"^\s*-\s*red\b|red tests?\b", body, re.M | re.I)) and bool(
        re.search(r"^- (?:files|outcome|contract)\b", body, re.M | re.I))


def triage(task: str, project: Path | None = None) -> tuple[str, str]:
    """SKIP (the work is already specified), QUICK (a one-line need) or FULL (open work worth a sheet), with the reason.
    Open-ended wording always wins: a 'design ...' task about a card still gets the full sheet."""
    if TRIAGE_OPEN.search(task):
        return "FULL", "open-ended work (design / invent / explore): the wide net and the SPARK panel can change what gets built"
    cards = sorted({c.upper() for c in CARD_ID.findall(task)})
    if cards and all(card_spec(c, project) for c in cards):
        return "SKIP", (f"{', '.join(cards)} already name{'s' if len(cards) == 1 else ''} the files, red tests and plants: "
                        "build from the card; at most the helpers below")
    if cards:                                               # a card that is not yet a recipe is real work, however short
        return "FULL", f"{', '.join(cards)} do{'es' if len(cards) == 1 else ''} not yet name red tests: a sheet can help shape it"
    if TRIAGE_ASK.search(task) or len(task.split()) <= 8:
        return "QUICK", "a one-line need: the finder's picks (1-22 by the task's size) answer it"
    return "FULL", "a task worth a cycle: no card spells it out"


def findable(lib: "Library", name: str) -> list[str]:
    """v14, for any skill author: how findable is this skill, and what would make it fairer to find? Checks only
    what the Maestro actually reads: the description (every reading starts there), a SKILL.md body, links to other
    skills, a meaning line, and whether the skill comes back for queries written from its own purpose."""
    import statistics
    if name not in lib.desc:
        close = sorted(lib.desc, key=lambda n: -jaccard(set(n.split("-")), set(name.split("-"))))[:3]
        return [f"NO_SKILL {name}: not in this library (did you mean {', '.join(close)}?)"]
    d = lib.desc[name]
    med = statistics.median(len(x) for x in lib.desc.values())
    md = lib.md.get(name)
    body = md.read_text(encoding="utf-8", errors="replace") if md and md.is_file() else ""
    mech = load_mechanisms().get(name)
    first = re.split(r"(?<=[.!?])\s", d.strip(), maxsplit=1)[0]
    L = [f"FINDABLE {name} ({(lib.source.get(name, '') or 'custom')}):",
         f"  description {len(d)} chars (library median {int(med)}); body {len(body)} chars; "
         f"links {len(lib.graph().get(name, ()))}; meaning line {'hand-written' if mech and not mech.get('auto') else 'auto' if mech else 'none'}"]
    fixes = []
    if len(d) < 0.5 * med:
        fixes.append("the description is under half the median length: say what it does, on what input, and when to use it")
    if (len(first) < 60 and " - " in first) or len(first.split()) <= 4:   # "Assayer - CODE type 7 of 16."
        fixes.append(f"the first sentence ('{first[:50]}') is a label, not a job: start with the verb it performs")
    if not re.search(r"\b(use (this|it|when)|whenever|when (you|the user|max))\b", d, re.I):
        fixes.append("no trigger phrase ('Use this when ...'): routers match on those words")
    if mech and not mech.get("tags"):
        fixes.append("it shares no distinctive word with any operation tag: name the operation (rank, merge, detect, ...)")
    words = [w for w in lib.fs._tokens(first) if w not in META][:8]
    probe = " ".join(words) or name.replace("-", " ")
    ranked = [r["name"] for r in lib.fused(probe)]
    rank = ranked.index(name) + 1 if name in ranked else None
    L.append(f"  found for its own first sentence ('{probe[:60]}'): rank {rank if rank else 'not in the top 120'}")
    if rank is None or rank > 6:
        fixes.append("it does not come back in the top 6 even for its own words: other skills claim the same words; add "
                     "the words that make it different")
    fixes += findable_v17(lib, name, d, body, md)
    L += [f"  FIX: {f}" for f in fixes] or ["  no fix needed: it is as findable as the Maestro can make it"]
    return L


STEP_WORDS = re.compile(r"\b(then|next|after that|finally|lastly|step \d)\b", re.I)
NEG_TRIGGER = re.compile(r"\b(not for|does not (activate|apply|fire|trigger)|do not use (it |this )?(for|when)|never for|"
                         r"not when|skip (it|this) when|unlike)\b", re.I)
PERSONAL_PATH = re.compile(r"(?i)(?:[A-Za-z]:\\|/)(?:Users|home)[\\/][A-Za-z0-9._-]+[\\/]")
LINK_RX = re.compile(r"\]\(([^)\s#]+)\)|`(?:python|py)\s+((?:scripts|references|\w+)[\\/][\w./\\-]+\.py)")


def findable_v17(lib: "Library", name: str, d: str, body: str, md: Path | None) -> list[str]:
    """v17 fixes borrowed from the shared repos, each a FIX hint, never a gate: description = WHEN, not WHAT
    (science-superpowers writing-science-skills); a negative trigger (prompt-master); generic-swap filler score
    (scientific-agents CONTRIBUTING 574-589); dead links and personal paths (scientific-agent-skills structure.py);
    read-cost warning (its 500-line cap); near-duplicate body (scientific-agents validate.py 476-498)."""
    import statistics
    fixes = []
    if len(STEP_WORDS.findall(d)) >= 2:
        fixes.append("the description reads like the workflow ('then ... then ...'): say WHEN to use it, not what it does step by "
                     "step, or the reader follows the summary and never opens the skill")
    if not NEG_TRIGGER.search(d):                      # v19: only when a survey look-alike outranks it for its own words
        try:
            over = [o for o in (load_tested().get(name) or {}).get("overlaps", []) if o in lib.desc and o != name]
        except Exception:  # noqa: BLE001
            over = []
        if over:
            first_ = re.split(r"(?<=[.!?])\s", d.strip(), maxsplit=1)[0]
            probe_ = " ".join([w for w in lib.fs._tokens(first_) if w not in META][:8]) or name.replace("-", " ")
            ahead = []
            for r in lib.fused(probe_)[:12]:
                if r["name"] == name:
                    break
                if r["name"] in over:
                    ahead.append(r["name"])
            if ahead:
                fixes.append(f"no Not-for clause, and {', '.join(ahead[:2])} (a survey look-alike) outranks it for its own first "
                             f"sentence: add one clause 'Not for <{ahead[0]}'s job> (use {ahead[0]})' so the two stop claiming the same words")
    toks = [w for w in lib.fs._tokens(d) if w not in META and len(w) > 3]
    if toks:
        N = max(1, len(lib.desc))
        df: dict[str, int] = {}
        for other in lib.desc.values():
            for w in set(lib.fs._tokens(other)):
                df[w] = df.get(w, 0) + 1
        filler = sum(1 for w in toks if df.get(w, 0) > N / 2) / len(toks)
        if filler >= 0.6:
            fixes.append(f"{filler:.0%} of the description's words appear in half the library (generic-swap test: put another "
                         "skill's name in and it still reads true); name what only this skill does")
    if md is not None and body:
        folder = md.parent
        dead = []
        for m in LINK_RX.finditer(body):
            target = (m.group(1) or m.group(2) or "").strip()
            if not target or target.startswith(("http", "mailto:", "{", "<")):
                continue
            if not (folder / target).exists() and not (folder / target.split("#")[0]).exists():
                dead.append(target)
        if dead:
            fixes.append(f"{len(dead)} link(s) or script path(s) in the body do not resolve from the skill folder: {', '.join(dead[:3])}")
        leaks = sorted({m.group(0) for m in PERSONAL_PATH.finditer(body)})
        if leaks:
            fixes.append(f"a personal path is written into the body ({leaks[0]}...): another machine cannot follow it; use ~ or a relative path")
        lines = body.count("\n") + 1
        if lines > 500 or tokens_of(body) > 3000:
            fixes.append(f"the body is {lines} lines (~{tokens_of(body)} tokens) on every read: move reference detail to references/ "
                         "and keep SKILL.md under 500 lines")
        own = {ln.strip() for ln in body.splitlines() if len(ln.strip()) >= 40}
        if own and len(lib.md) <= 2000:
            boiler: dict[str, int] = {}
            bodies = {}
            for n2, p2 in lib.md.items():
                if n2 == name or not p2.is_file():
                    continue
                try:
                    b2 = {ln.strip() for ln in p2.read_text(encoding="utf-8", errors="replace").splitlines() if len(ln.strip()) >= 40}
                except OSError:
                    continue
                bodies[n2] = b2
                for ln in b2 & own:
                    boiler[ln] = boiler.get(ln, 0) + 1
            common = {ln for ln, k in boiler.items() if k >= 50}      # lines owned by 50+ skills are boilerplate, not copying
            mine = own - common
            if mine:
                worst = max(((len(mine & (b2 - common)) / len(mine), n2) for n2, b2 in bodies.items()), default=(0, ""))
                if worst[0] > 0.25:
                    fixes.append(f"{worst[0]:.0%} of its body lines also appear in {worst[1]}: a near-duplicate skill (no-repeat-skills); "
                                 "merge or make the difference explicit")
    return fixes


def tokens_of(text: str) -> int:
    return (len(text) + 3) // 4                             # ~4 characters per token (English prose and code)


def read_cost(chosen: list[dict]) -> int:
    """Tokens to read the chosen skills' SKILL.md files (the UNDERSTAND step)."""
    total = 0
    for c in chosen:
        p = Path(c.get("skill_md") or "")
        total += tokens_of(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else 0
    return total


def triage_note(lib: Library, st: State, task: str, verdict: str, why: str) -> str:
    """The short answer for SKIP and QUICK: no score run (so no audit debt), the finder's picks sized 1 to PICKS_MAX by
    pick_count (the user, 2026-10-24: "1 to 22", never a fixed top 3), the override."""
    scored = purpose_rank(lib.search, task, root=lib.root, state_dir=st.d, desc=lib.desc)   # meaning first (M46), then words, then the deliverable (M51)
    n, n_why = pick_count(task, [r for r in scored if "meaning" in r["via"]] or scored)
    top3 = scored[:n]
    L = [f"TRIAGE {verdict}: {why}.", f"PICKS {n} (1-22 by the task's size): {n_why}"]
    if verdict == "SKIP":
        L.append("THINK FIRST (only if you rescore with --full): restate the task as operations with --concepts.")
    for r in top3:
        L.append(f"  {r['name']:<28} {lib.desc.get(r['name'], '')[:100]}")
    L.append(f"OVERRIDE: maestro.py score \"{task[:60]}{'...' if len(task) > 60 else ''}\" --full   (a full sheet with "
             "concepts costs ~5,000 tokens plus ~4,000 to read its picks)")
    note = "\n".join(L)
    L.append(f"COST this note ~{tokens_of(note) + 20} tokens")
    st.append({"kind": "TRIAGE", "verdict": verdict, "why": why, "task": task[:500], "finder_top": [r["name"] for r in top3],
               "tokens": tokens_of(note), "t": int(time.time())})
    return "\n".join(L)


def render_brief(sheet: dict) -> str:
    """The default sheet (v11): what is needed to act, in about 20 lines. Every detail is still in `--full`."""
    if not sheet.get("concepts") and not sheet.get("keywords_only"):
        return render(sheet)                                 # THINK FIRST + preview + SPARK: already short
    debt = len(sheet.get("debt") or []) + len(sheet.get("ponder_debt") or [])
    L = [f"MAESTRO {sheet['run']}: {len(sheet['chosen'])} picks from {sheet['pool']} [ORGANIZED, not VERIFIED]"
         + (f"  | debt {debt} run(s): `maestro.py debt`" if debt else "")]
    named = {c.upper() for c in CARD_ID.findall(sheet.get("task", ""))}
    ctx = [c for c in sheet.get("context", []) if c.startswith("first phase")
           or (c.startswith("plan card") and c.split()[2].upper() in named)][:3]   # a card the task names, not a word match
    L += ["CONTEXT " + c for c in ctx]
    L += sheet.get("mode_lines") or []                      # 2026-10-24: the mode, how to use the picks, ASK FIRST
    if sheet.get("stay_inside"):
        L.append("STAY INSIDE: " + " | ".join(sheet["stay_inside"])[:160])
    if not sheet["chosen"]:                               # v14: say why there is nothing, and what to do
        task = sheet.get("task", "")
        foreign = sum(ch.isalpha() and not ch.isascii() for ch in task) > max(3, len(task) // 5)
        L.append("NO PICKS: no skill's description shares a word with this task. "
                 + ("The task is mostly in another language and the skills are described in English: restate it in "
                    "English, or as --concepts (Claude can translate it). " if foreign else "")
                 + "If no skill does this job, `maestro.py newskill <name> \"<the job>\"` starts one.")
    tested = load_tested()
    for i, c in enumerate(sheet["chosen"], 1):
        why = (c.get("role_added") and "verify role") or (c.get("cover") and f"cover: {c['cover'][:40]}") \
            or c.get("via") or c.get("when", "")
        probe = (c.get("card") or {}).get("probe")
        cmd = c.get("first_cmd") or (probe and probe.replace("{skill_dir}", str(Path(c["skill_md"]).parent))) \
            or f"invoke /{c['name']} (the Skill tool; it has no script of its own)"   # built-ins, plugins, guides
        L.append(f"  {i}. {c['name']:<28} {('[' + c['ballot'] + '] ') if c.get('ballot') else ''}{c.get('grade', 'S3')} "
                 f"{why[:60]}")
        L.append(f"       run: {cmd[:110]}")
        t = tested.get(c["name"])                    # v17 survey: what it did when tested, so the judge need not open it
        if t:
            L.append(f"       tested {t['verdict']}: {t['does'][:110]}")
            eff = t.get("side_effects")                  # v18: what the survey's real run saw it write or send
            eff = [e for e in (eff if isinstance(eff, list) else [eff]) if e and str(e).lower() not in ("none", "[]")]
            if eff:
                L.append(f"       tested run touched: {'; '.join(str(e) for e in eff)[:120]} (survey 2026-10-24; SCRIPTS CAN is the AST)")
    others = [n for n in sheet.get("finder_top", []) if n not in {c["name"] for c in sheet["chosen"]}]
    if others:                                       # held-out: the finder's first pick was right more often
        L.append("FINDER ALSO SAYS (judge these too): " + ", ".join(others))
    for x in sheet.get("needed", [])[:3]:
        L.append(f"NEEDED: '{x['concept'][:60]}' (best {x['best']} {x['score']:.2f})")
    if sheet.get("spark"):
        L.append("SPARK (one to invent with): " + ", ".join(f"{s['op']}={s['members'][0]}" for s in sheet["spark"]))
    for key in ("session_ctx", "odds", "hindsight"):       # v15/v16: session context, the Maestro's own odds, what was reached for
        if sheet.get(key):
            L.append(sheet[key])
    L.append(f"NEXT: try each pick on the subject (`maestro.py try {sheet['run']} <skill> -- <cmd>`), then `fit ... "
             f"works|misfit`; read only the picks that fit; `ponder {sheet['run']}`; `--full` shows everything.")
    body = "\n".join(L)
    L.append(f"COST sheet ~{tokens_of(body) + 25} tokens; reading all {len(sheet['chosen'])} picks ~{read_cost(sheet['chosen'])} "
             "tokens (read only those that FIT)")
    return "\n".join(L)


def debt_runs(rows: list[dict]) -> list[dict]:
    """Score runs with picks that were neither rated nor closed (audit debt) or concept runs never pondered."""
    rated = rated_pairs(rows)
    closed = {r["run"] for r in rows if r.get("kind") == "CLOSE"}
    pond = set(ponder_debt(rows))
    return [r for r in rows if r.get("kind") == "SCORE" and r.get("chosen") and r["run"] not in closed
            and (not any((r["run"], n) in rated for n in r["chosen"]) or r["run"] in pond)]


def cost_report(rows: list[dict], last: int = 20) -> list[str]:
    """What the Maestro cost and what it bought, over the last runs: sheet tokens, triage savings, picks that worked."""
    tri = [r for r in rows if r.get("kind") == "TRIAGE"][-last:]
    sheets = [r for r in rows if r.get("kind") == "SHEET_COST"][-last:]
    fits = {(r["run"], r["skill"]) for r in rows if r.get("kind") == "FIT" and r.get("verdict") == "works"}
    runs = [r for r in rows if r.get("kind") == "SCORE"][-last:]
    worked = sum(1 for r in runs if any((r["run"], n) in fits for n in r.get("chosen", [])))
    out = [f"COST over the last {last}: {len(sheets)} sheet(s) ~{sum(r['sheet'] for r in sheets)} tokens shown, "
           f"~{sum(r['read'] for r in sheets)} to read every pick"]
    by = {v: sum(1 for r in tri if r["verdict"] == v) for v in ("SKIP", "QUICK", "FULL")}
    out.append(f"TRIAGE: {by['SKIP']} skipped, {by['QUICK']} quick, {by['FULL']} full; each skip saved ~9,000 tokens "
               "(a concept sheet plus its reading)")
    out.append(f"VALUE: {worked} of {len(runs)} recent score run(s) had a pick that FIT works on its subject")
    return out


def score(lib: Library, st: State, task: str, top: int | None = None, graph: bool = False, questions: tuple = (),
          concepts: str = "", mechs: dict | None = None, session_ctx: str = "", subject: str | None = None,
          mode: str | None = None) -> dict:
    """`session_ctx` (v16, dial M41): the running session's last prompts; they join the task for the RANKING readings
    only (fused pool). Triage, kinds, memory recall and the sheet's words stay the task as written."""
    ch = charter(getattr(lib, "project", None))              # v12: goals and limits first, then the choosing
    msel = select_mode(task, st.d, mode)                     # 2026-10-24: the mode this prompt is in (modes.py)
    lib.mode_sel = msel
    kinds = task_kinds(task)                                 # v12: the task's place on the spectrum
    phases = KIND_PHASES.get(kinds[0][0], PHASE_ORDER)
    global TOOL_BONUS
    TOOL_BONUS = kinds[0][0] not in CREATIVE_KINDS
    snap = lib.snapshot()
    old = json.loads(st.registry.read_text(encoding="utf-8")) if st.registry.is_file() else {}
    news = diff_registry(old, snap) if old else {"NEW": [], "REMOVED": [], "CHANGED": []}
    mechs = load_mechanisms() if mechs is None else mechs
    vocab = load_vocab()
    cons = parse_concepts(concepts, vocab, lib.fs._tokens) if concepts else []
    inferred_ops = infer_tags(task, vocab, lib.fs._tokens, k=3) if vocab else []   # v18: shown on THINK FIRST
    concepts_inferred = False
    if not cons and not THINK_FIRST and inferred_ops:      # the user 2026-10-24: picks without his concepts; infer them
        cons = parse_concepts("; ".join(f"{t}: {task[:200]}" for t, _, _ in inferred_ops), vocab, lib.fs._tokens)
        concepts_inferred = bool(cons)
    subject_sha = file_sha(Path(subject)) if subject and Path(subject).is_file() else None   # v18: score --subject
    per = concept_scores(cons, {n: m for n, m in mechs.items() if n in lib.desc}, lib.fs._tokens) if cons else []
    kw_ranked = []
    rank_text = (session_ctx.strip() + " " + task).strip() if session_ctx and session_ctx.strip() else task   # v16 M41
    if per and BALLOTS:                                     # v10d: the words ballot must not contain the concept reading
        lib.concept_per = []
        kw_ranked = lib.fused(rank_text)
    lib.concept_per = per
    ranked = lib.fused(rank_text)
    allr = {r["name"]: r for r in ranked}
    var = lib.variants(task)
    words = set(lib.fs._tokens(var["_plain"]))
    book, anti = recall(st.memory(), words)
    stats_now = context_stats(st.memory(), words) if FAIR_CONTEXT and not questions else st.stats(questions)   # v14 C
    pool = maybe_rerank(lib, task, ranked[:POOL], st)       # v16 O1: no-op unless dial M40 is on and a model is saved
    pool = thompson_slots(ranked, pool, stats_now, task)    # v18: no-op unless dial M44 > 0 (exploration slots)
    names = {c["name"] for c in pool}
    new_hits = [n for n in news["NEW"] if n in allr and n not in names]
    for n in sorted(new_hits, key=lambda n: -allr[n]["score"])[:NEW_MAX]:   # a new skill that matches is considered
        pool.append({**allr[n], "new": True})
        names.add(n)
    for c, row in zip(cons, per):                           # v10: each concept's best matches are always considered
        for n, s in row[:CONCEPT_PULL]:
            if n not in names and n in lib.desc:
                base = allr.get(n, {"name": n, "score": 0.0, "tool": any(x["tool"] for x in lib.skills if x["name"] == n),
                                    "when": lib.desc[n].split(". ")[0][:160]})
                pool.append({**base, "via": f"concept '{c['text'][:40]}' ({s:.2f})"})
                names.add(n)
    for n, sim in sorted(book.items(), key=lambda x: -x[1]):   # opening book: a similar past task's good picks
        if n not in names and n in lib.desc:
            base = allr.get(n, {"name": n, "score": 0.0, "tool": any(s["tool"] for s in lib.skills if s["name"] == n),
                                "when": lib.desc[n].split(". ")[0][:160]})
            pool.append({**base, "score": max(base["score"], min(r["score"] for r in pool) if pool else 0.0),
                         "via": f"opening book (similar past task, sim {sim:.2f})"})
            names.add(n)
    if graph and pool:
        g = _load(lib.root / "skill-graph" / "skill_graph.py", "skill_graph").build(lib.root)
        for c in list(pool[:3]):
            for nb in sorted(g.get("adj", {}).get(c["name"], ())):
                if nb not in names and nb in allr:
                    pool.append({**allr[nb], "via": f"graph neighbour of {c['name']}"})
                    names.add(nb)
    self_ok, self_why = self_pick_allowed([n for n, _ in (meaning_rank(ranking_text(task), SELF_TOP, lib.root, st.d) or [])], st.d)
    pool = [c for c in pool if c["name"] != SELF or self_ok]   # 2026-10-24: itself only when the prompt is about choosing skills, rarely
    blocked = [c for c in pool if c["name"] in anti]       # immune memory: wrong on a similar task before
    pool = [c for c in pool if c["name"] not in anti]
    ov, plug = getattr(lib, "overrides", {}), getattr(lib, "plugins", {})
    switched_off = [c["name"] for c in pool if ov.get(c["name"]) == "off"]   # still suggested (the user, 2026-10-20):
    # every skill can be picked; a pick that cannot run as things are set says how to switch it on
    weighed_pool = weigh(pool, stats_now, st.favourites())
    pick_note = f"--top {top} given"
    if top is None:
        top, pick_note = pick_count(task, weighed_pool)
        try:                                                # your own Maestro: your habit scales the count (personal.py)
            scale = _load(HERE / "personal.py", "personal").profile(st.rows())["pick_scale"]
        except Exception:  # noqa: BLE001
            scale = 1.0
        if scale != 1.0:
            top2 = max(1, min(PICKS_MAX, round(top * scale)))
            if top2 != top:
                pick_note += f"; your rating habit x{scale} -> {top2}"
                top = top2
        if msel:
            top2 = _load(HERE / "modes.py", "modes").clamp(top, msel["mode"])
            if top2 != top:
                pick_note += f"; mode {msel['mode']['name']} keeps {msel['mode']['picks'][0]}-{msel['mode']['picks'][1]} -> {top2}"
                top = top2
    chosen, notes = select(weighed_pool, top, lib.family)
    scouts = scout_record(st.rows())
    if per and BALLOTS:                                     # v10d: two ballots (words, meaning) take turns
        meaning = concept_rank(per)
        proven = [n for n in meaning[:POOL] if scouts.get(n, (0, 0))[1] >= 1]   # item 6: scouts that worked go first
        meaning = proven + [n for n in meaning if n not in proven]
        if DEMOTE_LEXICAL:                                  # item 5: word-readers wait behind meaning-readers
            lex = load_lexical()
            meaning = [n for n in meaning if n not in lex or n in proven] + [n for n in meaning if n in lex and n not in proven]
        tsk = code_type_skills()                            # item 7: the sticky CODE type's grafted skills go first
        if tsk:
            meaning = [n for n in meaning if n in tsk] + [n for n in meaning if n not in tsk]
        words_b = [r["name"] for r in kw_ranked]
        picks = two_ballots(words_b, meaning, top, lib.family, set(anti))
        for n, _ in picks:
            if n not in names and n in lib.desc:
                base = allr.get(n, {"name": n, "score": 0.0, "tool": any(x["tool"] for x in lib.skills if x["name"] == n),
                                    "when": lib.desc[n].split(". ")[0][:160]})
                pool.append({**base, "via": "meaning ballot"})
                names.add(n)
        wmap = {r["name"]: r for r in weigh(pool, stats_now, st.favourites())}
        chosen = [{**wmap[n], "ballot": src, **({"via": f"proven scout ({scouts[n][1]}/{scouts[n][0]} worked)"}
                                                  if n in proven else {})} for n, src in picks if n in wmap]
        notes.append({"demoted": "-", "for": "-", "fit_gap": 0,
                      "why": "TWO BALLOTS: picks alternate words / meaning (E35: the meaning reading lost the fused vote)"})
    for c in blocked:
        notes.append({"demoted": c["name"], "for": "-", "fit_gap": 0,
                      "why": f"ANTIBODY (rated wrong on a similar task, sim {anti[c['name']]:.2f})"})
    creative = kinds[0][0] in CREATIVE_KINDS
    role_fn, role_name, role_why = ((is_critic, "critique", "no chosen skill can argue against the result; this one can")
                                    if creative else (is_checker, "verify", "no chosen skill can make the work fail a check; this one can"))
    if chosen and len(chosen) < PICKS_MAX and not any(role_fn(c["name"], lib.desc.get(c["name"], "")) for c in chosen):
        # v12: the checker must be runnable here and not a plugin's (the sheet on Maestro itself ROLE_ADDED a disabled
        # ecommerce plugin skill on the words "find evidence"); a plugin skill may serve only when the task names it
        task_words = set(lib.fs._tokens(task))
        def can_check(c):
            src = lib.source.get(c["name"], "")
            if switch_on(c["name"], src, ov, plug) is not None:
                return False
            return not src.startswith("plugin ") or src[7:].lower() in task_words
        chk = next((c for c in weigh(pool, stats_now, st.favourites())
                    if role_fn(c["name"], lib.desc.get(c["name"], "")) and c not in chosen and can_check(c)), None)
        if chk is not None:
            chosen.append({**chk, "role_added": role_name})
            notes.append({"demoted": "-", "for": chk["name"], "fit_gap": 0, "why": f"ROLE_ADDED: {role_why}"})
    covered = 0                                             # v10b COVER: every operation gets its best skill on the sheet
    for c, row in zip(cons, per):                           # (E35: concept leaders were pooled, then lost the fused vote)
        if c["analogy"] or not row or row[0][1] < NEED_FLOOR or covered >= COVER_MAX:
            continue
        best = {n for n, _ in row[:CONCEPT_PULL]}
        # v18 (run 6734e7c55e): a role-added verifier that happens to share the tag does not cover the operation;
        # cover needs a skill chosen on fit. And when the operation's leader is out of the pool (an antibody for this
        # task), the next leader covers it instead of nothing.
        if not best & {x["name"] for x in chosen if not x.get("role_added")}:
            weighed_now = weigh(pool, stats_now, st.favourites())
            for n, sc_ in row[:CONCEPT_PULL]:
                base = next((x for x in weighed_now if x["name"] == n), None)
                if base is not None and n not in {x["name"] for x in chosen}:
                    chosen.append({**base, "cover": c["text"][:60]})
                    notes.append({"demoted": "-", "for": n, "fit_gap": 0,
                                  "why": f"COVER: best skill for the operation '{c['text'][:50]}' ({sc_:.2f})"})
                    covered += 1
                    break
    fit_order = sorted(pool, key=lambda r: (-r["score"], r["name"]))
    fit_top = {r["name"] for r in fit_order[:top]}
    weighed_all = {r["name"]: r for r in weigh(pool, stats_now, st.favourites())}
    taxed = 0
    for i, c in enumerate(list(chosen)):
        w = weighed_all.get(c["name"], c)
        if c["name"] not in fit_top and not c.get("role_added") and not c.get("cover") and (w.get("fasc", 0) or w.get("fav", 0)):
            if taxed < FASC_PICKS_MAX:
                c["taxed"] = "FASCINATION PICK: its place is owed to the fascination/favour bonus; run one extra check before using it"
                taxed += 1
            else:
                alt = next((r for r in fit_order if r["name"] not in {x["name"] for x in chosen}), None)
                if alt is not None:
                    notes.append({"demoted": c["name"], "for": alt["name"], "fit_gap": 0,
                                  "why": "EXCITEMENT_TAX (a second pick owed only to fascination/favour)"})
                    chosen[i] = {**weighed_all.get(alt["name"], alt)}
    if not lib.quick and HEALTH_GATE:                     # v12: a pick that fails its own selftest is swapped out
        tried = 0
        for i, c in enumerate(list(chosen)):
            h = health_of(lib, st, c["name"])
            c["health"] = h
            if h in SWAP_HEALTH and tried < 6:               # v17: NEEDS <pkg> stays (shown), DRIFT swaps like FAIL
                for alt in fit_order:
                    if alt["name"] in {x["name"] for x in chosen} or alt["name"] == c["name"]:
                        continue
                    tried += 1
                    ah = health_of(lib, st, alt["name"])
                    w_alt = weighed_all.get(alt["name"])
                    if ah not in SWAP_HEALTH and w_alt is not None:
                        notes.append({"demoted": c["name"], "for": alt["name"], "fit_gap": round(c["fit"] - w_alt["fit"], 3),
                                      "why": f"HEALTH_SWAP (its selftest {h}; a pick must pass its own test)"})
                        chosen[i] = {**w_alt, "health": ah}
                        break
                    if tried >= 6:
                        break
    task_limits = []
    if ch["limits"]:                                       # v12: the task and each pick are read against the limits
        for lim in ch["limits"]:                           # the TASK first: work outside the limits gets no skills
            hits = limit_hits(lim, "", task, lib.fs._tokens)
            if hits:
                task_limits.append(f"{lim[:110]} (the ask shares: {', '.join(hits)})")
        for c in chosen:                                   # a pick is flagged, never swapped: paper-only shares every
            for lim in ch["limits"]:                       # word with "no real orders" because it is the guard for it
                hits = limit_hits(lim, c["name"], lib.desc.get(c["name"], ""), lib.fs._tokens)
                if hits:
                    c["limit"] = f"{lim[:90]} (shared words: {', '.join(hits)})"
                    break
    for i, c in enumerate(list(chosen)):                   # v12: within the margin, a pick that can run here beats one
        if c.get("role_added") or switch_on(c["name"], lib.source.get(c["name"], ""), ov, plug) is None:   # switched off
            continue
        for alt in fit_order:
            w_alt = weighed_all.get(alt["name"])
            if w_alt is None or alt["name"] in {x["name"] for x in chosen}:
                continue
            if switch_on(alt["name"], lib.source.get(alt["name"], ""), ov, plug) is None and c["fit"] - w_alt["fit"] <= MARGIN:
                notes.append({"demoted": c["name"], "for": alt["name"], "fit_gap": round(c["fit"] - w_alt["fit"], 3),
                              "why": "OFF_HERE (switched off in this project; a near-tie that can run takes the place; "
                                     "the pool line still shows it with its switch)"})
                chosen[i] = dict(w_alt)
                break
            if c["fit"] - w_alt["fit"] > MARGIN:
                break
    for c in chosen:
        c["side_effects"] = side_effects(lib.desc.get(c["name"], ""))     # v12: consent before a world-changing pick
        md = lib.md.get(c["name"])
        if md is not None and not lib.quick:                              # v17: the scripts' own calls, read as an AST
            c["script_effects"] = script_side_effects(md.parent, st.d)
            c["allowed_tools"] = frontmatter_field(md, "allowed-tools")
    goal_words = set()
    for g in ch["goals"]:
        goal_words |= {w for w in lib.fs._tokens(g) if len(w) >= 5}
    for c in chosen:
        shared = sorted(goal_words & set(lib.fs._tokens(c["name"] + " " + lib.desc.get(c["name"], ""))))
        c["serves_goal"] = shared[:4]
    reads = {(r["skill"], r.get("sha")) for r in st.rows() if r.get("kind") == "READ"}
    stab = stability(lib, task, [c["name"] for c in chosen], stats_now, st.favourites()) if not lib.quick else {}
    for c in chosen:
        c["stability"] = stab.get(c["name"])
    cards = load_cards()
    on_pc_only = pc_only(cards, lib.desc)                        # v12: in the cards, not on this machine
    for c in chosen:
        c["card"] = cards.get(c["name"])
        c["family"] = lib.family(c["name"])
        md = lib.skill_md(c["name"])
        c["skill_md"] = str(md)
        c["sha"] = hashlib.sha256(md.read_bytes()).hexdigest()[:16] if md.is_file() else None
        c["lines"] = len(md.read_text(encoding="utf-8", errors="replace").splitlines()) if md.is_file() else 0
        c["first_cmd"] = first_command(md)
        c["grade"] = "S1" if c["name"] in book else ("S2" if (c["name"], c["sha"]) in reads else "S3")
        c["kind_flag"] = kind_mismatch(c["name"], lib.desc.get(c["name"], ""), task) if KIND_FLAG_SHOWN else None
        c["max_types"] = ov.get(c["name"]) == "user-invocable-only"
        c["source"] = lib.source.get(c["name"], "")
        c["switch_on"] = switch_on(c["name"], c["source"], ov, plug)
    plan_ctx = context(words | {w.upper() for w in re.findall(r"gt\d+", task.lower())}, lib.fs._tokens)
    phased = agenda(chosen, weigh(pool, stats_now, st.favourites()), lib.desc, phases)
    TOOL_BONUS = True
    rated = rated_pairs(st.rows())
    offered = menus(weigh(pool, stats_now, st.favourites()), chosen, st.rows(), lib.desc, lib.family)
    closed = {r["run"] for r in st.rows() if r.get("kind") == "CLOSE"}
    debt = [r["run"] for r in st.rows() if r.get("kind") == "SCORE" and r.get("chosen") and r["run"] not in closed
            and not any((r["run"], n) in rated for n in r["chosen"])]
    wonder, needed = [], []
    if cons:                                                # v10: far-family matches and the skills still missing
        taken = {c["name"] for c in chosen}
        fams = {lib.family(n) for n in taken}
        for c, row in zip(cons, per):
            best = row[0][1] if row else 0.0
            if best < NEED_FLOOR and not c["analogy"]:     # an analogy is mined (kingdom-sweep), not a missing skill
                slug = "-".join(lib.fs._tokens(c["text"])[:3]) or "new-skill"
                seed = (f"python ~/.claude/skills/skill-foundry/foundry.py {slug} \"{c['text'][:80]}\""
                        if (lib.root / "skill-foundry").is_dir() else       # v14: a library without skill-foundry
                        f"python {Path(__file__).name} newskill {slug} \"{c['text'][:80]}\"")
                needed.append({"concept": c["text"], "best": row[0][0] if row else "-", "score": best, "seed": seed})
        for i in range(max((len(r) for r in per), default=0)):  # round-robin: each concept offers its farthest fit
            for c, row in zip(cons, per):
                if len(wonder) >= WONDER_K or i >= len(row):
                    continue
                n, s = row[i]
                f = lib.family(n)
                if n in taken or f in fams or s < NEED_FLOOR or n not in lib.desc:
                    continue
                wonder.append({"name": n, "family": f, "score": s, "concept": c["text"],
                               "sees": mechs.get(n, {}).get("does", ""), "world": mechs.get(n, {}).get("world", "")})
                taken.add(n)
                fams.add(f)
            if len(wonder) >= WONDER_K:
                break
    # v10b SPARK: the creative operators panel on EVERY sheet, concepts or not. E35 showed (a) a literal restatement
    # never asks for combining, analogy or invention, and (b) ranking creative skills by word overlap is one more
    # keyword lane. What worked in the session that caused this (2026-10-19): the user named the families and Claude found
    # all six useful skills from a plain listing. So the panel does what the user did: it names each generative operator
    # and lists its members (a skill's FIRST tag is its operator; never-shown members first), and Claude, the judge
    # with conceptual understanding, must pick one, say what it would create here, and run it.
    spark = []
    if mechs and SPARK_K:
        shown = {n for r in st.rows() if r.get("kind") == "SCORE" for n in (r.get("chosen", []) + r.get("spark", []))}
        taken = {c["name"] for c in chosen} | {w["name"] for w in wonder}
        for op in GENERATIVE:
            members = [n for n, m in mechs.items() if n in lib.desc and n not in taken and op in m.get("tags", [])[:2]]
            members.sort(key=lambda n: (n in shown, n))          # never shown first, then by name (stable, no keyword)
            if members:
                spark.append({"op": op, "members": members[:SPARK_K + 3], "of": len(members),
                              "new": [n for n in members[:SPARK_K + 3] if n not in shown]})
    run_id =hashlib.sha256(f"{task}|{time.time()}".encode()).hexdigest()[:10]
    finder_top = [r["name"] for r in lib.search(task, 3)]   # v11: shown on the brief sheet as a second opinion
    st.append({"kind": "SCORE", "dials": DIAL_SHA, "concepts": concepts or None, "mode": msel["mode"]["name"] if msel else None,
               "wonder": [w["name"] for w in wonder], "needed": [x["concept"] for x in needed],
               "spark": [n for x in spark for n in x["members"]], "pool_names": [c["name"] for c in pool[:POOL]],
               "agenda": [[ph, name] for ph, name, _ in phased], "menus": offered, "questions": list(questions),
               "task": task[:2000], "code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12],
               "finder_top": finder_top, "session_ctx": (session_ctx or "")[:600],   # v17: the brief carries it forward
               "first_cmds": {c["name"]: c.get("first_cmd") for c in chosen}, "run": run_id, "t": int(time.time()), "task_sha": hashlib.sha256(task.encode()).hexdigest()[:16],
               "subject": subject, "subject_sha": subject_sha,   # v18: the subject named at score time (STALE if it changes)
               "words": sorted(words), "chosen": [c["name"] for c in chosen], "notes": notes, "pool": len(pool)})
    st.registry.write_text(json.dumps(snap, indent=0, sort_keys=True), encoding="utf-8")
    pool_lines = [f"{r['name']} [{'T' if r.get('tool') else 'D'}] {lib.desc.get(r['name'], '')[:110]}" for r in pool]
    return {"finder_top": finder_top, "run": run_id, "task": task, "pool": len(pool), "pool_lines": pool_lines, "chosen": chosen, "notes": notes,
            "library": news, "families": sorted({c["family"] for c in chosen}), "stay_inside": stay_inside(task),
            "readings": [k for k in [*var, "body", "network"] if not k.startswith("_") and WEIGHTS.get(k, 1.0) > 0
                         and (k in var or k in ("body", "network"))],
            "context": plan_ctx, "agenda": phased, "debt": debt, "purpose": purpose(plan_ctx), "menus": offered,
            "plain_adds": [r["name"] for r in lib.search(var["_plain"], 12) if r["name"] not in names][:6],
            "concepts": cons, "concept_top": [[(n, s) for n, s in row[:3]] for row in per], "wonder": wonder,
            "needed": needed, "mechs_loaded": len(mechs), "spark": spark, "inferred_ops": inferred_ops, "subject": subject,
            "concepts_inferred": concepts_inferred,
            "mode": msel["mode"]["name"] if msel else None,
            "mode_lines": (lambda D: D.render(msel, D.ask_first(task, msel["mode"], subject)) if ASK_FIRST
                           else D.render(msel, []))(_load(HERE / "modes.py", "modes")) if msel else [],
            "ponder_debt": [r for r in ponder_debt(st.rows()) if r != run_id],
            "switched_off": switched_off, "ledger": str(st.ledger), "on_pc_only": on_pc_only,
            "ledger_shared": getattr(st, "shared", False), "charter": ch, "pick_note": pick_note, "task_limits": task_limits,
            "kinds": kinds, "phases": list(phases), "spectrum": spectrum(kinds, lib.desc),
            "subject_hint": next((m.group(0) for m in re.finditer(r"[\w./\\-]+\.(?:py|md|csv|json|jsonl|txt|toml)\b", task)), "the task's subject (name it: `plan RUN SKILL --on FILE`)")}


def render(sheet: dict) -> str:
    L = [f"MAESTRO run {sheet['run']}: {sheet['pool']} considered (task read {len(sheet['readings'])} ways: "
         f"{', '.join(sheet['readings'])}), {len(sheet['chosen'])} chosen, families {', '.join(sheet['families'])}"]
    if sheet.get("debt"):
        L.insert(0, f"AUDIT DEBT: {len(sheet['debt'])} earlier run(s) chose skills that were never rated "
                    f"(latest {', '.join(sheet['debt'][-3:])}); rate them or say they went unused")
    L[-1] = L[-1] + "  [ranking ORGANIZED, not VERIFIED: S1 useful on a similar task, S2 read at this version, S3 unread]"
    L += sheet.get("mode_lines") or []                      # 2026-10-24: the mode, how to use the picks, ASK FIRST
    ch = sheet.get("charter") or {}
    if ch.get("goals") or ch.get("limits"):
        L.append(f"PROJECT ({ch.get('source')}), read before choosing:")
        for g in ch.get("goals", []):
            L.append(f"  GOAL  {g[:160]}")
        for lim in ch.get("limits", []):
            L.append(f"  LIMIT {lim[:160]}")
    for tl in sheet.get("task_limits", []):
        L.append(f"TASK vs LIMIT: {tl} - if the work itself crosses this limit, no skill makes it allowed: stop and say so")
    if sheet.get("spectrum"):
        L.append("SPECTRUM (the task's kinds, and how many library skills serve each): " + "; ".join(sheet["spectrum"])
                 + (f". Phases for this kind: {' -> '.join(sheet.get('phases', []))}"
                    + ("; tools and documents weigh alike, a critic stands in for the checker" if sheet["kinds"][0][0] in CREATIVE_KINDS else "")))
    if sheet.get("pick_note"):
        added = sum(1 for c in sheet["chosen"] if c.get("role_added"))
        L.append(f"PICKS {len(sheet['chosen'])} (1-{PICKS_MAX} by the task's size" + (f", plus {added} verifier" if added else "")
                 + f"): {sheet['pick_note']}")
    for line in sheet.get("context", []):
        L.append("CONTEXT " + line)
    lib = sheet["library"]
    if any(lib.values()):
        L.append(f"library since last look: NEW {lib['NEW'][:8]} CHANGED {len(lib['CHANGED'])} REMOVED {lib['REMOVED'][:8]}")
    if sheet.get("purpose"):
        L.append(sheet["purpose"])
    if sheet.get("switched_off"):
        L.append("SWITCHED OFF in the pool (skillOverrides \"off\"; still suggested, each pick says how to switch it on): "
                 + ", ".join(sheet["switched_off"][:8]))
    if sheet.get("on_pc_only"):
        L.append(f"ON THE PC ONLY ({len(sheet['on_pc_only'])} skills in the cards but not on this machine; commit them from "
                 f"the PC to use them here): " + ", ".join(sheet["on_pc_only"][:8]) + (" ..." if len(sheet["on_pc_only"]) > 8 else ""))
    if sheet.get("ledger_shared"):
        L.append(f"LEDGER {sheet.get('ledger')}: cloud session, ratings are written into the repo; commit that file "
                 "with the work or they die with this container")
    if sheet.get("plain_adds"):
        L.append("PLAIN READING ADDS (the task without its asking-words finds these too; judge them with the pool): "
                 + ", ".join(sheet["plain_adds"]))
    if sheet.get("stay_inside"):
        L.append("STAY INSIDE (the task's own limits): " + " | ".join(sheet["stay_inside"]))
    def spark_lines() -> list[str]:
        if not sheet.get("spark"):
            return []
        out = ["SPARK (how could this be INVENTED, not only checked? Read the operators against the task's meaning, "
               "pick at least one skill, say in one line what it would create here, and run it on the subject; "
               "fascination, not evidence):"]
        out += [f"  {s['op']:<18} ({s['of']:>2}) " + ", ".join(n + ("*" if n in s["new"] else "") for n in s["members"])
                for s in sheet["spark"]]
        return out + ["  (* never shown on a sheet before; full list of an operator: `maestro.py vocab` then the tag)"]

    if not sheet.get("concepts"):
        L.insert(0, "THINK FIRST: restate the task as 3-6 operations and 1-2 analogies, then rescore: --concepts "
                    "\"partition: split X into kinds; overlay-config: one base, many profiles; world: where this happens "
                    "in nature or a trade\"  (tags: `maestro.py vocab`)")
        if sheet.get("inferred_ops"):                       # v18: the tag names the judge would otherwise have to know
            L.insert(1, "  INFERRED OPERATIONS (from the task's words against the tag meanings; confirm or correct them): "
                        + "; ".join(f"{t} ({m[:48]})" for t, _, m in sheet["inferred_ops"])
                        + "   -> rescore with --concepts \"" + "; ".join(f"{t}: <{m.split(':')[0][:44]} - say what, here>" for t, _, m in sheet["inferred_ops"]) + "\"")
        if not sheet.get("keywords_only"):                  # v10d (item 2): no ranked picks until the task is read by meaning
            L.append("KEYWORD PREVIEW (shared words only - NOT picks; picks come after concepts): "
                     + ", ".join(c["name"] for c in sheet["chosen"]))
            L += spark_lines()
            L.append("(the full keyword sheet: add --keywords-only; a one-line need: `score --quick` or skill-finder)")
            return "\n".join(L)
    else:
        L.append("CONCEPTS (the task as operations; matched against what each skill DOES, not its words):")
        for c, tops in zip(sheet["concepts"], sheet.get("concept_top", [])):
            lab = ("world" if c["analogy"] else ",".join(c["tags"]) or "text") + (
                f" [unknown tag: {','.join(c['unknown'])}]" if c["unknown"] else "") + (
                " [tags inferred from the words]" if c.get("inferred") else "")
            L.append(f"  {lab}: {c['text'][:60]}  -> " + ", ".join(f"{n} {s:.2f}" for n, s in tops))
    L.append("rank skill                          total  fit   use   fasc  fav  [T/D] lines grade why")
    for i, c in enumerate(sheet["chosen"], 1):
        why = (c.get("role_added") and "VERIFY role, added") or (c.get("cover") and f"COVER: {c['cover']}") \
            or (c.get("pin") and f"pinned by {c['pin']}") \
            or c.get("via") or ("NEW skill" if c.get("new") else c["when"][:56])
        why = (f"[{c['ballot']}] " if c.get("ballot") else "") + why
        L.append(f"{i:>4} {c['name']:<30} {c['total']:<6} {c['fit']:<5} {c['use']:<5} {c['fasc']:<5} {c['fav']:<4} "
                 f"[{'T' if c.get('tool') else 'D'}] {c.get('lines', 0):>4}  {c.get('grade', 'S3')}    {why}")
        if c.get("stability") is not None:
            L.append(f"       {'STABLE' if c['stability'] >= 0.75 else 'unstable'}: in {c['stability']:.0%} of the "
                     "leave-one-sentence-out readings (E34: stable picks were right 3x as often)")
        if c.get("taxed"):
            L.append(f"       {c['taxed']}")
        if c.get("source") == "built-in":
            L.append(f"       built into Claude Code (no file to read): run it as /{c['name']}")
        elif c.get("source"):
            L.append(f"       from {c['source']}: run it as {c['name']}")
        if c.get("health") in ("FAIL", "TIMEOUT"):
            L.append(f"       BROKEN: its own --selftest {c['health']}s here; fix it before use (skill-health)")
        elif c.get("health") == "DRIFT":
            L.append("       DRIFT: its selftest fails on `ImportError: cannot import name`: a package it uses moved an API; "
                     "the skill needs a fix, not this PC (swapped out when a near-tie could run)")
        elif str(c.get("health", "")).startswith("NEEDS"):
            L.append(f"       {c['health']}: the skill is whole; this PC lacks that package (pip install it, or follow the SKILL.md by hand)")
        if c.get("script_effects"):
            L.append(f"       SCRIPTS CAN: {', '.join(c['script_effects'])} (read from their code as an AST, not from the description); "
                     "ask before they run")
        if c.get("allowed_tools"):
            L.append(f"       allowed-tools: {c['allowed_tools'][:90]}")
        if c.get("switch_on"):
            L.append(f"       {c['switch_on']}")
        if c.get("limit"):
            L.append(f"       LIMIT: shares words with a project limit - {c['limit']}; judge it before use")
        if c.get("side_effects"):
            L.append(f"       SIDE EFFECTS: its description says it can {', '.join(c['side_effects'])}; ask before it runs")
        if c.get("serves_goal"):
            L.append(f"       serves the project goal through: {', '.join(c['serves_goal'])}")
        if c.get("max_types"):
            L.append(f"       MAX_TYPES: skillOverrides makes it user-invocable-only; Claude cannot start it, ask {OWNER} to "
                     f"type /{c['name']} (or follow its SKILL.md by hand)")
        if c.get("kept_because"):
            L.append(f"       {c['kept_because']}")
        cd = c.get("card")
        if cd:
            L.append(f"       card: answers {'/'.join(cd['questions'])}; takes {cd['input']['kind']} "
                     f"({cd['input']['shape'][:70]}); assumes: {'; '.join(a[:70] for a in cd['assumes'])}")
            L.append(f"       not for: {cd['not_for'][:110]}")
            if cd.get("persona") and PERSONA_PRICED:
                L.append(f"       PERSONA, a priced pick (dial M42): {cd.get('cost', 'a full profile read')}; the profiles' own paper "
                         "(arXiv 2610.00084) measured -0.6 pp accuracy at 2.2-4.5x cost, -10 pp on tool-using tasks. Use it only "
                         "for the field's judgment on a named subject, after a FIT; never as the default reader")
    for n in sheet["notes"]:
        L.append(f"SELECT {n['why']}: {n['demoted']} -> {n['for']}" + (f" (fit gap {n['fit_gap']})" if n["fit_gap"] else ""))
    if sheet.get("show_pool"):
        L.append("POOL (judge these yourself; the ranking above is keyword evidence, not the verdict):")
        L += [f"  {x}" for x in sheet["pool_lines"]]
    if sheet.get("agenda"):
        L.append("AGENDA by phase: " + "  ->  ".join(f"{i}. {ph} {name}" + ("" if src == "chosen" else f" ({src})")
                                                     for i, (ph, name, src) in enumerate(sheet["agenda"], 1)))
    if sheet["chosen"]:                                     # v12: how to use each pick on THIS task, paste-ready
        phase_of = {name: ph for ph, name, _ in sheet.get("agenda", [])}
        L.append(f"HOW TO USE EACH PICK ON THIS TASK (subject: {sheet.get('subject_hint')}):")
        for c in sheet["chosen"]:
            L.append(use_line(c, phase_of.get(c["name"], "USE"), sheet.get("subject_hint", "the subject"), sheet["run"]))
        names = [c["name"] for c in sheet["chosen"]]
        L.append("CONDUCTOR PROMPT (paste into the session that does the work): Task: " + sheet["task"][:160].replace("\n", " ")
                 + ". Name the subject in one line. Use, in this order, each on the subject: " + "; ".join(
                     f"{i}) {n} to {((c.get('card') or {}).get('output') or (c.get('when') or 'do its job'))[:60]}"
                     for i, (n, c) in enumerate(zip(names, sheet["chosen"]), 1))
                 + f". A pick that does not read the subject as the kind of thing it is becomes a misfit; after each: `maestro.py fit {sheet['run']} <skill> works|misfit \"why\"`, then `rate`. Stay inside the project limits above.")
    if sheet.get("menus"):
        L.append(f"MENUS (one idea each, no skill twice; rate any: `maestro.py rate {sheet['run']} menu:B --by max "
                 "topic=4 inner=5`):")
        for letter, name, idea in MENU_IDEAS:
            got = sheet["menus"].get(letter, [])
            L.append(f"  {letter} {name:<10} " + (", ".join(got) if got else "(empty)") + f"   [{idea}]")
    if sheet.get("wonder"):
        L.append("WONDER (far families that do the same operation; fascination, not evidence: run each on the subject "
                 f"with `maestro.py try {sheet['run']} <skill> -- ...` before it counts):")
        for w in sheet["wonder"]:
            L.append(f"  {w['name']:<26} [{w['family'][:28]}] for '{w['concept'][:40]}' ({w['score']:.2f})")
            L.append(f"       what it would see: {w['sees'][:110]}" + (f"  | like {w['world'][:60]}" if w["world"] else ""))
    L += spark_lines()
    for c in sheet.get("concepts", []):
        if c["analogy"]:
            L.append(f"ANALOGY to mine: '{c['text'][:70]}'  -> python ~/.claude/skills/kingdom-sweep/sweep.py "
                     f"\"{c['text'][:40]}\"  (what does the job there, and how?)")
    for x in sheet.get("needed", []):
        L.append(f"NEEDED (no skill does this well; best {x['best']} {x['score']:.2f}): '{x['concept'][:70]}'  "
                 f"seed: {x['seed']}")
    L.append(f"FIT CHECK (first, before trusting any pick): name the task's exact subject (file, section, data), then run "
             f"each pick ON IT: `maestro.py try {sheet['run']} <skill> -- <its command on the subject>`, and record "
             f"`maestro.py fit {sheet['run']} <skill> works|misfit \"why\"`. A skill whose input is a different kind of "
             "thing (a log, a series, code) than the subject is a misfit: drop it and take the next pick.")
    for c in sheet["chosen"]:
        probe = (c.get("card") or {}).get("probe")
        cmd = c.get("first_cmd") or (probe and probe.replace("{skill_dir}", str(Path(c["skill_md"]).parent)))
        L.append(f"  {c['name']:<30} its command: {cmd or '(none in SKILL.md: read its tool section)'}"
                 + (f"   <- {c['kind_flag']}" if c.get("kind_flag") else ""))
        if sheet.get("subject") and cmd:                    # v18: a runnable first try on the named subject
            L.append(f"       on the subject: maestro.py try {sheet['run']} {c['name']} --subject {sheet['subject']} -- "
                     f"{subject_cmd(cmd, sheet['subject'])}")
    total = sum(c.get("lines", 0) for c in sheet["chosen"])
    plan = sheet.get("reading") or {}
    L.append(f"UNDERSTAND ({total} lines" + (f", budget {sheet['budget']}" if plan else "") +
             f"): read each SKILL.md, then `maestro.py read {sheet['run']} <skills>`; a choice is not used until it is read.")
    for c in sheet["chosen"]:
        share = plan.get(c["name"])
        how = "" if share is None else ("  read whole" if share >= c.get("lines", 0) else
                                         f"  read the first {share} lines and its tool section")
        L.append(f"  {c['skill_md']}  sha {c['sha']}{how}")
    L.append(f"THEN PONDER (the second think step, before using any pick): `maestro.py ponder {sheet['run']}` - blunder "
             "check each pick, a quorum from the failure angle, the missing piece, taste a SPARK skill, quote evidence")
    if sheet.get("ponder_debt"):
        L.insert(0, f"PONDER DEBT: {len(sheet['ponder_debt'])} earlier run(s) were never pondered (latest "
                    f"{', '.join(sheet['ponder_debt'][-3:])}): `maestro.py ponder <run>` or close them")
    for key in ("odds", "hindsight"):                      # v15
        if sheet.get(key):
            L.append(sheet[key])
    if sheet["chosen"]:
        c = sheet["chosen"][0]
        cmd = c.get("first_cmd")
        L.append(f"FIRST MOVE (minutes, not hours): {('run `' + cmd + '`') if cmd else 'open ' + c['skill_md']} "
                 f"on the task; afterwards `maestro.py rate {sheet['run']} {c['name']} useful|fascinating|favourite|unused|wrong` "
                 f"or with {OWNER}'s metrics `maestro.py rate {sheet['run']} {c['name']} --by claude inner=4 topic=5 ...`")
    return "\n".join(L)


def read_receipt(lib: Library, st: State, run: str, names: list[str]) -> list[str]:
    out = []
    for n in names:
        md = lib.skill_md(n)
        if not md.is_file():
            out.append(f"NO_SKILL {n}")
            continue
        sha = hashlib.sha256(md.read_bytes()).hexdigest()[:16]
        st.append({"kind": "READ", "run": run, "skill": n, "sha": sha, "t": int(time.time())})
        out.append(f"READ {n} sha {sha}")
    return out


def evaluate(lib: Library, st: State, probes: Path, fused: bool = True, infer: bool = True) -> dict:
    rows = [ln.split("\t") for ln in probes.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#") and "\t" in ln]
    vocab = load_vocab() if (infer and fused and not THINK_FIRST and WEIGHTS.get("concept")) else {}   # v19: as score() does with think_first = no
    mechs_in = {n: m for n, m in load_mechanisms().items() if n in lib.desc} if vocab else {}
    hits = {"finder@1": 0, "finder@3": 0, "finder_pool@40": 0, "maestro@1": 0, "maestro@3": 0, f"pool@{POOL}": 0}
    detail: list[dict] = []
    stats, favs = st.stats(), st.favourites()
    memory = st.memory() if FAIR_CONTEXT else []
    global TOOL_BONUS
    for prompt, ok in rows:
        good = {x.strip() for x in ok.split(",")}
        f = lib.search(prompt, POOL)
        lib.concept_per = []
        if vocab:                                          # v19: the inferred-operations concept reading, as score() runs it
            ops = infer_tags(prompt, vocab, lib.fs._tokens, k=3)
            cons = parse_concepts("; ".join(f"{t}: {prompt[:200]}" for t, _, _ in ops), vocab, lib.fs._tokens) if ops else []
            lib.concept_per = concept_scores(cons, mechs_in, lib.fs._tokens) if cons else []
        phase_prepare(lib, prompt)                         # 2026-10-25 (M52): the session context a real prompt had, none for a bare one
        ranked_all = lib.fused(prompt) if fused else f
        lib.concept_per = []
        pool = ranked_all[:POOL]
        pool = maybe_rerank(lib, prompt, pool, st)        # v16 O1: no-op unless dial M40 is on and a model is saved
        pool = thompson_slots(ranked_all, pool, stats, prompt)   # v18: no-op unless dial M44 > 0, as score() does
        TOOL_BONUS = (task_kinds(prompt)[0][0] not in CREATIVE_KINDS) if KINDS_ON else True   # as score() does
        if FAIR_CONTEXT:                                   # v14 C: the record from similar tasks only
            stats = context_stats(memory, set(lib.fs._tokens(lib.variants(prompt)['_plain'])))
        ch, _ = select(weigh(pool, stats, favs), 3, lib.family)
        TOOL_BONUS = True
        if STABILIZE:
            ordered = sorted(weigh(pool, stats, favs), key=lambda r: (-r["total"], r["name"]))
            ch = stabilize(lib, prompt, ch, ordered, stats, favs)[0]
        m = [r["name"] for r in ch]
        hits["finder@1"] += bool(f[:1] and f[0]["name"] in good)
        hits["finder@3"] += bool(good & {r["name"] for r in f[:3]})
        hits["finder_pool@40"] += bool(good & {r["name"] for r in f})
        hits["maestro@1"] += bool(m[:1] and m[0] in good)
        hits["maestro@3"] += bool(good & set(m))
        hits[f"pool@{POOL}"] += bool(good & {r["name"] for r in pool})
        detail.append({"m": m, "good": sorted(good), "prompt": prompt,          # v15: per-probe picks, for --null / --ci / --compare
                       "pool": [r["name"] for r in pool]})                   # v18: for --misses (O9: the pool misses, named)
    return {"n": len(rows), "probes": probes.name, **{k: f"{v}/{len(rows)}" for k, v in hits.items()},
            "inferred": bool(vocab),                        # v19: whether the concept reading ran (as in a real score)
            "vec": [int(bool(set(d["good"]) & set(d["m"]))) for d in detail], "_detail": detail}


def phase_prepare(lib: Library, prompt: str) -> None:
    """2026-10-25 (phase reading, dial M52): the eval gives a probe the context it had live. A probe that is a real
    hindsight row gets the skills used on the same session's earlier prompts, and a table cut strictly before the
    probe's own row (never its own label) and before --before when given. A bare prompt (most held-out probes) gets
    no context: the reading is empty and the ranking is the one without it. No-op at weight 0."""
    lib.phase_context, lib.phase_cut = None, getattr(lib, "phase_before", None)
    if not WEIGHTS.get("phase"):
        return
    try:
        P = _load(HERE / "phase.py", "phase")
        lib.phase_context, lib.phase_cut = P.context_of(P.rows_of(getattr(lib, "state_dir", None) or STATE), prompt,
                                                        before=getattr(lib, "phase_before", None))
    except Exception:  # noqa: BLE001
        lib.phase_context = None


def maybe_rerank(lib: Library, task: str, pool: list[dict], st: State) -> list[dict]:
    """v16 O1: when dial M40 is on and <state>/rerank_model.json exists, the pool is ordered by the learned judge;
    membership never changes, so pool@40 is the same number either way."""
    if not RERANK or not pool:
        return pool
    try:
        return _load(HERE / "rerank.py", "rerank").rerank_pool(lib, task, pool, st.d)
    except Exception:  # noqa: BLE001
        return pool


def eval_null(detail: list[dict], n: int = 200, seed: int = 7) -> dict:
    """Label-permutation null for maestro@3: the picks stay, the answer keys are shuffled across probes. A top-3 hit
    rate that a shuffled key reaches as often is no evidence the ranking reads the prompt."""
    import random
    rnd = random.Random(seed)
    real = sum(1 for d in detail if set(d["good"]) & set(d["m"]))
    goods = [d["good"] for d in detail]
    nulls = []
    for _ in range(n):
        g = goods[:]
        rnd.shuffle(g)
        nulls.append(sum(1 for d, good in zip(detail, g) if set(good) & set(d["m"])))
    mean = sum(nulls) / n
    sd = (sum((x - mean) ** 2 for x in nulls) / max(1, n - 1)) ** 0.5
    p = sum(1 for x in nulls if x >= real) / n
    return {"real": real, "null_mean": round(mean, 2), "null_sd": round(sd, 2), "null_max": max(nulls), "perms": n,
            "p": round(p, 3), "z": round((real - mean) / sd, 2) if sd else None,
            "verdict": "ABOVE NULL" if p < 0.05 else "NOT ABOVE NULL"}


def eval_ci(vec: list[int], n: int = 1000, seed: int = 7) -> dict:
    """Bootstrap 95% interval of the top-3 hit count over probes (resample probes with replacement)."""
    import random
    rnd = random.Random(seed)
    k = len(vec)
    if not k:
        return {"lo": 0, "hi": 0, "n": 0}
    sums = sorted(sum(vec[rnd.randrange(k)] for _ in range(k)) for _ in range(n))
    return {"hits": sum(vec), "n": k, "lo": sums[int(0.025 * n)], "hi": sums[int(0.975 * n) - 1], "boot": n}


def eval_armed(lib: Library, st: State, k: int = 5, seed: int = 7) -> dict:
    """The tripwire: k planted probes whose prompt is a skill's own first sentence and whose answer is that skill.
    An eval that cannot find a skill from its own words is broken, whatever the held-out number says."""
    import random, tempfile
    rnd = random.Random(seed)
    cands = [s for s in lib.skills if s.get("tool") and len(s.get("desc", "")) > 80 and ":" not in s["name"]]
    picks = rnd.sample(cands, min(k, len(cands)))
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "probes_armed.tsv"
        f.write_text("".join(re.split(r"(?<=[.!?])\s+", s["desc"])[0].replace("\t", " ") + "\t" + s["name"] + "\n"
                             for s in picks), encoding="utf-8")
        res = evaluate(lib, st, f)
    hit = sum(res["vec"])
    return {"planted": [s["name"] for s in picks], "found@3": f"{hit}/{len(picks)}",
            "verdict": "ARMED" if hit >= max(1, len(picks) - 1) else "TRIPWIRE FAILED: the eval cannot see a planted skill"}


def mcnemar(a: list[int], b: list[int]) -> dict:
    """Paired comparison of two per-probe hit vectors on the same probes: exact two-sided binomial on the discordant
    pairs (b_only vs a_only). Different lengths mean different probes: refused."""
    if len(a) != len(b) or not a:
        return {"ok": False, "why": "different probe sets (or empty)"}
    from math import comb
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    b_only = sum(1 for x, y in zip(a, b) if y and not x)
    n = a_only + b_only
    if n == 0:
        return {"ok": True, "a_only": 0, "b_only": 0, "p": 1.0, "verdict": "IDENTICAL"}
    kk = min(a_only, b_only)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(kk + 1)) / 2 ** n)
    return {"ok": True, "a_only": a_only, "b_only": b_only, "p": round(p, 4),
            "verdict": "DIFFERENT" if p < 0.05 else "NOT DISTINGUISHABLE"}


def _selftest() -> bool:
    ok = []
    cands = [{"name": "deep", "score": 10.0, "tool": True}, {"name": "easy", "score": 7.0, "tool": False},
             {"name": "near", "score": 9.5, "tool": False}]
    stats = {"easy": {"favourite": 5, "useful": 9}, "near": {"useful": 3}}
    w = weigh(cands, stats, {"easy"})
    chosen, notes = select(w, 3)
    ok.append(chosen[0]["name"] in ("deep", "near"))                       # easy (fit 0.7) never leads
    ok.append(all(n["demoted"] != "deep" for n in notes))
    ok.append([c["name"] for c in chosen].index("easy") == 2)              # fit gap 0.3 > MARGIN: easy demoted
    w2 = weigh([{"name": "a", "score": 10.0, "tool": True}, {"name": "b", "score": 9.7, "tool": False}],
               {"b": {"favourite": 3}}, {"b"})
    ok.append(select(w2, 2)[0][0]["name"] == "b")                          # within margin: favour may win
    chain = [{"name": "a", "fit": 0.80, "total": 3.0}, {"name": "b", "fit": 0.93, "total": 2.0},
             {"name": "c", "fit": 1.0, "total": 1.0}]                     # bench E09: neighbours fine, a-c gap 0.20
    ok.append([r["name"] for r in select(chain, 3)[0]] == ["b", "c", "a"])
    ok.append(diff_registry({"x": "1", "y": "2"}, {"y": "3", "z": "4"}) ==
              {"NEW": ["z"], "REMOVED": ["x"], "CHANGED": ["y"]})
    ok.append(all(r["total"] <= r["fit"] * (1 + W_USE + W_FASC + W_FAV) + 1e-9 for r in w))   # bonuses bounded
    # diversity: two of family A at the top, a near-tie from B -> the third pick is B, not a third A
    fam = {"a1": "A", "a2": "A", "a3": "A", "b1": "B"}.get
    w3 = weigh([{"name": "a1", "score": 10}, {"name": "a2", "score": 9.9}, {"name": "a3", "score": 9.8},
                {"name": "b1", "score": 9.0}], {}, set())
    ok.append([c["name"] for c in select(w3, 3, fam)[0]] == ["a1", "a2", "b1"])
    # immune memory: wrong on "review the concept cards" blocks concept-card for a similar task, not a distant one
    mem = [({"review", "plan", "card", "risk"}, "concept-card", "wrong"), ({"review", "plan", "card"}, "gradable", "useful")]
    book, anti = recall(mem, {"review", "plan", "card", "riskiest"})
    ok.append("concept-card" in anti and "gradable" in book)
    ok.append(recall(mem, {"lint", "concept", "definition", "formal"}) == ({}, {}))
    # scope clauses and checker role
    ok.append(any("do not start" in s.lower() for s in stay_inside("Do not start the plan, just perfect it. Then stop.")))
    ok.append(is_checker("plant-the-bug", "") and not is_checker("trie-search", "prefix trie for autocomplete"))
    # 2026-10-25 deliverable reading (dial M51, scenario C2): a making verb names the output kind; the subject alone does not
    ok.append(deliverable_of("draw a chart of the equity curve") == "chart" and deliverable_of("make me a powerpoint deck") == "powerpoint"
              and deliverable_of("plot the equity curve") == "plot" and deliverable_of("compute the max drawdown of the equity curve") is None
              and deliverable_of("the chart looks wrong, why") is None and deliverable_of("") is None)
    dv = {"drawdown-stats": "Compute the risk numbers of an equity curve", "dataviz": "create any chart, graph or plot",
          "artifact-diagramming": "Diagramming know-how: when a picture earns its place", "hurst": "Hurst exponent of a series"}
    ok.append(deliverable_reading("draw a chart of the equity curve", ["drawdown-stats", "dataviz", "artifact-diagramming", "hurst"], dv)
              == ["dataviz"]                                              # keeps the fused order, drops the skills that draw nothing
              and deliverable_reading("compute the max drawdown", ["drawdown-stats", "dataviz"], dv) == [])
    # 2026-10-25 (artifact-diagramming): the diagram kinds vote too, as a family of stems, never by a skill's name
    ok.append(deliverable_of("draw a diagram of the data flow") == "diagram" and deliverable_of("make a flowchart of the landing ritual") == "flowchart"
              and deliverable_of("make a flow chart of the retry loop") == "flowchart" and deliverable_of("draw a schematic of the hook") == "schematic"
              and deliverable_of("the flowchart is wrong") is None and deliverable_of("draw a chart of the equity curve") == "chart")
    ok.append(deliverable_reading("make a flowchart of the landing ritual", ["drawdown-stats", "dataviz", "artifact-diagramming"], dv)
              == ["artifact-diagramming"]                                 # a flowchart is a diagram: "diagramming" starts with the kin stem
              and deliverable_reading("draw a picture of the mechanism", ["dataviz", "artifact-diagramming"], dv) == ["artifact-diagramming"]
              and deliverable_reading("draw a diagram of the data flow", ["dataviz", "hurst"], dv) == [])
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        good = DIALS.read_text(encoding="utf-8") if DIALS.is_file() else ""
        fp = Path(td) / "d.md"
        fp.write_text(re.sub(r"EXPECTED_DIALS: (\d+)", lambda m: f"EXPECTED_DIALS: {int(m.group(1)) - 1}", good),
                      encoding="utf-8")                       # a count one short of the rows must halt
        try:
            load_dials(fp)
            bad_count = False
        except DialError:
            bad_count = True
        fp.write_text(good.replace("| M01 | margin | 0.15 | yes |", "| M01 | margin | 0.5 | yes |"), encoding="utf-8")
        try:
            load_dials(fp)
            bad_lock = False
        except DialError:
            bad_lock = True
        ok.append(bad_count and bad_lock and load_dials()[0].get("margin") == "0.15")
    # v18 root fixes (run 6734e7c55e): a concept with a wrong or missing head word still reaches the concept reading
    # through tags inferred from its words; the sheet gives a runnable try on the named subject; a skill the judge
    # tried or judged counts as a pick for the baton even when the sheet never named it
    voc18 = load_vocab()
    inf = infer_tags("critique a protocol and find the weak spot of each rule", voc18, _plain_tokens)
    ok.append(bool(voc18) and bool(inf) and inf[0][0] == "red-team")
    pc = parse_concepts("op: critique a protocol; build the strongest case for the rule set", voc18, _plain_tokens)
    ok.append(pc[0]["inferred"] and "red-team" in pc[0]["tags"] and pc[0]["unknown"] == ["op"]
              and pc[1]["inferred"] and "steelman" in pc[1]["tags"])
    ok.append(parse_concepts("rank: order the picks", voc18, _plain_tokens)[0] == {
        "tags": ["rank"], "text": "order the picks", "analogy": False, "unknown": [], "inferred": False})
    ok.append(subject_cmd("python inner_critic.py <file|text> [--json]", "C:/x/subject.md") == "python inner_critic.py C:/x/subject.md [--json]"
              and subject_cmd("python t.py check x --repo <repo>", "s.md").endswith(" s.md")
              and subject_cmd("python zealot_eye.py memo.md", "s.md") == "python zealot_eye.py s.md")
    ok.append(is_metric_token("topic=4") and is_metric_token("fascinating=5") and not is_metric_token("H=0.61")
              and not is_metric_token("n=400") and not is_metric_token("topic=high"))
    bt = baton([{"kind": "SCORE", "run": "b1", "chosen": ["a"], "agenda": [], "questions": []},
                {"kind": "TRY", "run": "b1", "skill": "z"}, {"kind": "FIT", "run": "b1", "skill": "z", "verdict": "works"}], "b1")
    ok.append(any("ADDED BY THE JUDGE" in ln and "z" in ln for ln in bt) and any("6 VERDICT" in ln and "1/2" in ln for ln in bt))
    # v10 concept reading: an operation-tagged concept finds the skill that DOES it with no shared task word; a
    # word-only concept still matches by meaning lines; unknown tags are reported; NEEDED fires below the floor
    voc = {"overlay-config": "base plus overrides", "partition": "split into kinds", "rank": "order"}
    mk = {"gene-marks": {"does": "keeps a frozen base and switchable marks on top", "tags": ["overlay-config"],
                         "world": "bee larvae fed differently"},
          "splitter": {"does": "splits a whole into non overlapping kinds", "tags": ["partition"], "world": "sorting mail"},
          "ranker": {"does": "orders items by score", "tags": ["rank"], "world": "a league table"}}
    import string
    tok = lambda s: [w for w in s.lower().translate(str.maketrans("", "", string.punctuation)).split() if len(w) > 2]  # noqa: E731
    cs = parse_concepts("overlay-config: one profile per type over a shared self; world: bee larvae fed differently; "
                        "frobnicate: zzz", voc)
    ok.append(len(cs) == 3 and cs[0]["tags"] == ["overlay-config"] and cs[1]["analogy"] and cs[2]["unknown"] == ["frobnicate"])
    per = concept_scores(cs, mk, tok)
    ok.append(per[0][0][0] == "gene-marks" and per[1][0][0] == "gene-marks" and not per[2])
    ok.append(concept_rank([[("a", 1), ("b", .5)], [("c", 1), ("a", .4)]]) == ["a", "c", "b"])
    # v10c PONDER: quotes must come from real TRY output; the second think step names quorum and scouts
    pr = [{"kind": "SCORE", "run": "p1", "chosen": ["a", "b"], "pool_names": ["a", "b", "c", "d"], "spark": ["s"],
           "wonder": []},
          {"kind": "TRY", "run": "p1", "skill": "a", "out": "FOUND 3 gaps in section two\nok"},
          {"kind": "FIT", "run": "p1", "skill": "a", "verdict": "works", "why": "x", "evidenced": False}]
    ok.append(quote_in_tries(pr, "p1", "a", "found 3 gaps in  section two") and not quote_in_tries(pr, "p1", "a", "found 9 gaps")
              and not quote_in_tries(pr, "p1", "a", "gaps") and not quote_in_tries(pr, "p1", "b", "FOUND 3 gaps in section"))
    pl = "\n".join(ponder(pr, "p1", {"c": {"does": "x"}, "z": {"does": "y"}}, {}, [{"tags": ["red-team"], "text": "t",
                          "analogy": False, "unknown": []}], [[("a", .9), ("z", .8)]]))
    ok.append("QUORUM (named by both readings): a" in pl and "SCOUTS (only the failure reading found them): z" in pl
              and "UNEVIDENCED works verdicts: a" in pl and "NOT run yet" in pl and "c, d" in pl)
    # v10d: two ballots take turns, skip repeats, blocked skills and a third of one family; 'both' marks agreement
    fam2 = {"w1": "W", "w2": "W", "w3": "W", "m1": "M", "m2": "M", "x": "X"}.get
    tb = two_ballots(["w1", "x", "w2", "w3"], ["m1", "x", "m2"], 5, fam2, {"m2"})
    ok.append(tb == [("w1", "words"), ("m1", "meaning"), ("x", "both"), ("w2", "words")])   # m2 blocked, w3 = 3rd W
    ok.append(two_ballots([], ["m1", "m2"], 3, None, set()) == [("m1", "meaning"), ("m2", "meaning")])
    # v10e item 5: a pov-core lens on TEXT and a self-described word-counter are flagged; a pov lens on CODE is not
    with tempfile.TemporaryDirectory() as tdl:
        r5 = Path(tdl)
        for n, body in (("tally-lens", "import pov_core\n"), ("code-lens", "import pov_core\n"), ("deep", "x = 1\n")):
            (r5 / n).mkdir()
            (r5 / n / f"{n.replace('-', '_')}.py").write_text(body, encoding="utf-8")
        cl = {"tally-lens": {"input": {"kind": "TEXT"}}, "code-lens": {"input": {"kind": "CODE"}},
              "deep": {"input": {"kind": "TEXT"}}, "counter": {"input": {"kind": "TEXT"}, "output": "keyword tallies"}}
        lx = build_lexical(r5, cl, {}, {"tally-lens": "", "code-lens": "", "deep": "simulates a plan", "counter": ""})
    ok.append(set(lx) == {"tally-lens", "counter"} and lx["tally-lens"].startswith("pov"))
    # v10e item 9: named vs used counts READ/TRY/FIT, and lists the named-only picks
    ur = used_report([{"kind": "SCORE", "run": "u", "chosen": ["a", "b", "c"]},
                      {"kind": "READ", "run": "u", "skill": "a"}, {"kind": "TRY", "run": "u", "skill": "b"}], "u")
    ok.append("named 3, used 2 (ran on the subject: 1)" in ur[0] and "NAMED ONLY: c" in ur[0])
    # v10d item 6: a scout offered in a scan and then FIT works earns a record; a scout never used does not
    sr = scout_record([{"kind": "PONDER_SCAN", "run": "r", "scouts": ["good", "idle"]},
                       {"kind": "FIT", "run": "r", "skill": "good", "verdict": "works"},
                       {"kind": "PONDER_SCAN", "run": "q", "scouts": ["good"]}])
    ok.append(sr == {"good": (2, 1), "idle": (1, 0)})
    # v10d item 2: a sheet without concepts shows THINK FIRST + SPARK, never ranked picks
    sh = {"run": "t", "pool": 3, "readings": ["raw"], "chosen": [{"name": "kw1"}, {"name": "kw2"}], "families": ["F"],
          "library": {"NEW": [], "CHANGED": [], "REMOVED": []}, "notes": [], "concepts": [],
          "spark": [{"op": "analogize", "of": 1, "members": ["kingdom-sweep"], "new": []}]}
    rt = render(sh)
    ok.append(rt.startswith("THINK FIRST") and "KEYWORD PREVIEW" in rt and "NOT picks" in rt and "kingdom-sweep" in rt
              and "rank skill" not in rt and "FIRST MOVE" not in rt)
    ok.append(ponder_debt(pr) == [] and ponder_debt([{**pr[0], "concepts": "c"}] + pr[1:]) == ["p1"]
              and ponder_debt([{**pr[0], "concepts": "c"}, {"kind": "PONDER", "run": "p1"}]) == []
              and ponder_debt([{"kind": "SCORE", "run": "old", "chosen": ["a"]}]) == [])   # pre-v10c runs owe nothing
    b2, _ = recall([({"a", "b", "c"}, "shiny", "fascinating"), ({"a", "b", "c"}, "solid", "useful")], {"a", "b", "c"})
    ok.append("solid" in b2 and "shiny" not in b2)
    led = [{"kind": "RATE", "run": "r1", "skill": "a", "rating": "useful"},
           {"kind": "RATE", "run": "r1", "skill": "b", "rating": "useful"},
           {"kind": "RATE", "run": "r2", "skill": "c", "rating": "wrong", "why": "trap"},
           {"kind": "SCORE", "run": "r1", "chosen": ["a"], "pool_names": ["a", "w", "x"]},
           {"kind": "SCORE", "run": "r2", "chosen": ["c"], "pool_names": ["c", "w"]}]
    ok.append(learned_duets(led) == {"a": {"b"}, "b": {"a"}})
    rf = "\n".join(reflect(led))
    ok.append("w x2" in rf and "c (trap)" in rf and "a+b" in rf)
    ok.append(purpose(["first phase work can move: 3 Honest testing (x)", "plan card GT175 (phase 3): y"]).startswith(
        "PURPOSE: this serves phase 3") and "does not touch" in purpose(["first phase work can move: 3 Honest testing (x)"]))
    er = [{"kind": "SCORE", "run": "z", "chosen": ["u", "b"], "pool_names": ["u", "b", "shy"],
           "agenda": [["UNDERSTAND", "u"], ["BUILD", "b"]], "first_cmds": {"b": "python b.py go"}},
          {"kind": "READ", "run": "z", "skill": "u"}, {"kind": "RATE", "run": "z", "skill": "u", "rating": "useful"},
          {"kind": "FIT", "run": "z", "skill": "u", "verdict": "works", "why": "x"}]
    e1 = "\n".join(encore(er))
    er += [{"kind": "READ", "run": "z", "skill": "b"}, {"kind": "RATE", "run": "z", "skill": "b", "rating": "unused"}]
    ok.append("CLOSED" not in "\n".join(encore(er)))                     # v7: no FIT verdict yet, so not closed
    er += [{"kind": "FIT", "run": "z", "skill": "b", "verdict": "misfit", "why": "y"}]
    ok.append("NEXT: BUILD with b: run `python b.py go`" in e1 and "CURIOSITY" in e1 and "shy" in e1
              and "CLOSED" in "\n".join(encore(er)))
    sc, why = parse_metrics(["inner=4", "curiosity=5", "topic=3", "loved", "it"])
    ok.append(sc["curiosity"] == 5 and sc["fun"] == 4 and sc["task"] == 3 and why == ["loved", "it"])
    bad = 0
    for toks in (["fun=6"], ["vibes=3"], ["fun=x"], ["just", "words"]):
        try:
            parse_metrics(toks)
        except ValueError:
            bad += 1
    ok.append(bad == 4)
    wm = weigh([{"name": n, "score": s} for n, s in (("f1", 10), ("f2", 9.8), ("b1", 9.5), ("r1", 9.0), ("x1", 8))],
               {}, set())
    dm = {"f1": "build the thing", "f2": "build more", "b1": "write a draft", "r1": "read and map it", "x1": "audit it"}
    mn = menus(wm, [{"name": "f1"}, {"name": "f2"}], [{"kind": "SCORE", "run": "o", "chosen": ["b1"]}], dm,
               {"f1": "F", "f2": "F", "b1": "B", "r1": "R", "x1": "X"}.get)
    flat = [n for v in mn.values() for n in v]
    ok.append(mn["A"] == ["f1", "f2"] and "b1" not in mn["B"] and len(flat) == len(set(flat)))
    mr = [{"kind": "SCORE", "run": "q", "words": ["w"], "chosen": ["a"], "menus": {"A": ["a", "b"]}},
          {"kind": "METRIC", "run": "q", "target": "menu:A", "by": "max", "scores": {"task": 5.0, "research": 4.0}},
          {"kind": "METRIC", "run": "q", "target": "c", "by": "claude", "scores": {"task": 5.0}},
          {"kind": "METRIC", "run": "q", "target": "d", "by": "max", "scores": {"task": 0.0}}]
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td2:
        s2 = State(Path(td2))
        for r in mr:
            s2.append(r)
        mem = s2.memory()
    with _tf.TemporaryDirectory() as td3:
        s3 = State(Path(td3))
        for r in mr:
            s3.append(r)
        stt = s3.stats()
    ok.append(stt["a"].get("useful") == 1 and stt["b"].get("useful") == 1 and stt["d"].get("wrong") == 1
              and "c" not in stt)
    ok.append(({"w"}, "a", "useful") in mem and ({"w"}, "b", "useful") in mem and ({"w"}, "d", "wrong") in mem
              and not any(m[1] == "c" for m in mem))
    infl = [{"kind": "METRIC", "run": f"r{i}", "target": "s", "by": b, "scores": {"fun": v}}
            for i in range(3) for b, v in (("max", 2.0), ("claude", 5.0))]
    ok.append(any(x.startswith("SELF_INFLATION (inner)") for x in board(infl))
              and ("q", "b") in rated_pairs(mr))
    nl = Library.__new__(Library)
    nl._adj, nl.duets = {"x": {"y"}, "y": {"x"}}, {}
    ok.append(nl.network([("lone", 0.6), ("x", 0.4)])[0] == "lone")       # bench E07: an unlinked seed is not dropped
    fr = [{"kind": "SCORE", "run": "f", "words": ["plan", "card"], "chosen": ["log-reader", "lens"]},
          {"kind": "FIT", "run": "f", "skill": "log-reader", "verdict": "misfit", "why": "reads append-only logs"},
          {"kind": "FIT", "run": "f", "skill": "lens", "verdict": "works", "why": "x"}]
    with _tf.TemporaryDirectory() as td4:
        s4 = State(Path(td4))
        for r in fr:
            s4.append(r)
        fm, fs = s4.memory(), s4.stats()
    ok.append(({"plan", "card"}, "log-reader", "wrong") in fm and fs["log-reader"].get("wrong") == 1
              and fit_of(fr, "f", "lens") == "works" and fit_of(fr, "f", "nope") is None)
    ok.append(kind_mismatch("cross-cutting-check", "Apply the law of cross-cutting relationships to an ordered record "
                            "(DECISIONS.md, errata, numbered log)", "improve the trading research plan and its cards")
              is not None and kind_mismatch("negative-space", "Diffs a text against a domain checklist", "improve the plan")
              is None and kind_mismatch("hmm-regimes", "regimes in a price series", "speed up this python function")
              is not None)
    ok.append(taste_verdict({"HALF": 0.5, "SALAD": 0.95, "BLANKED": 0.97}) == "SIZE_ONLY"
              and taste_verdict({"HALF": 0.99, "SALAD": 0.2, "BLANKED": 0.3}, "FIND_GAPS") == "READS_IT"
              and taste_verdict({"HALF": 0.4, "SALAD": 0.2, "BLANKED": 0.95}, "FIND_GAPS") == "SATURATED"
              and echo_masked("PHANTOM alpha bet", "alpha betas") == "PHANTOM bet"
              and taste_verdict({"HALF": 1.0, "SALAD": 0.95, "BLANKED": 0.97}) == "CONSTANT"
              and taste_verdict({"HALF": 0.99, "SALAD": 0.5, "BLANKED": 0.4}) == "SATURATED"
              and taste_verdict({"HALF": 0.5, "SALAD": 0.93, "BLANKED": 0.2}) == "LEXICAL"
              and taste_verdict({"HALF": 0.4, "SALAD": 0.3, "BLANKED": 0.2}) == "READS_IT")
    cc = controls("alpha beta gamma\ndelta epsilon\nzeta eta theta iota\nkappa", seed=1)
    ok.append(sorted(cc["SALAD"].split()) == sorted("alpha beta gamma delta epsilon zeta eta theta iota kappa".split())
              and len(cc["BLANKED"].splitlines()) == 4 and "alpha" not in cc["BLANKED"]
              and len(cc["HALF"].splitlines()) == 2)
    cd = {"a": {"questions": ["FIND_GAPS"], "input": {"kind": "PLAN"}}, "b": {"questions": ["MEASURE"], "input": {"kind": "SERIES"}},
          "c": {"questions": ["FIND_GAPS", "ORDER"], "input": {"kind": "LOG"}}}
    ok.append(card_rank(["b", "x", "a", "c"], {"kind": "PLAN", "questions": ["FIND_GAPS"]}, cd) == ["a", "c", "b", "x"]
              and card_score({"kind": "PLAN", "questions": ["ORDER", "FIND_GAPS"]}, cd["c"]) == 4)
    qr = [{"kind": "SCORE", "run": "p", "chosen": ["x"], "questions": ["FIND_GAPS"]},
          {"kind": "SCORE", "run": "f", "chosen": ["y"], "questions": ["FORECAST"]},
          {"kind": "RATE", "run": "p", "skill": "x", "rating": "useful"},
          {"kind": "RATE", "run": "f", "skill": "x", "rating": "wrong"}]
    with _tf.TemporaryDirectory() as td5:
        s5 = State(Path(td5))
        for r in qr:
            s5.append(r)
        g, fq = s5.stats(), s5.stats(("FIND_GAPS",))
    ok.append(g["x"].get("useful") == 1 and g["x"].get("wrong") == 1 and fq["x"].get("useful") == 1
              and "wrong" not in fq["x"] and fq["y"].get("chosen") == 1)
    tp = thompson_pick(qr + [{"kind": "FIT", "run": "p", "skill": "bad", "verdict": "misfit", "why": "w"}] * 9,
                       {"run": "z", "questions": ["FIND_GAPS"], "pool_names": ["bad", "fresh"]})
    ok.append(tp is not None and tp[0] == "fresh")
    br = [{"kind": "SCORE", "run": "b", "chosen": ["k", "j"], "questions": ["ORDER"], "menus": {"A": ["k"]}},
          {"kind": "USE_PLAN", "run": "b", "skill": "k", "on": "plan.md", "expect": "keystones"}]
    b0 = "\n".join(baton(br, "b"))
    br += [{"kind": "READ", "run": "b", "skill": "k"}, {"kind": "TRY", "run": "b", "skill": "k"},
           {"kind": "FIT", "run": "b", "skill": "k", "verdict": "works", "why": "x"},
           {"kind": "RATE", "run": "b", "skill": "k", "rating": "useful"}]
    b1 = "\n".join(baton(br, "b"))
    ok.append("PAUSE 1 (before using): NOT clear" in b0 and "NEXT: 5 USE" in b0 and "PAUSE 1 (before using): clear" in b1
              and "PAUSE 2 (before reporting): clear" in b1 and "NEXT: report" in b1)
    ok.append(task_parts("Fix the plan. Then land it!") == ["Fix the plan.", "Then land it!"]
              and task_parts("one two three four five six") == ["one two", "three four", "five six"])
    fw = [{"kind": "SCORE", "run": "r1", "t": 1, "code": "c1", "finder_top": ["f", "g", "h"], "task": "x",
           "menus": {"A": ["a", "b", "c"], "B": ["d"]}},
          {"kind": "SCORE", "run": "r2", "t": 2, "code": "c1", "finder_top": ["a", "q", "r"], "task": "y",
           "menus": {"A": ["s", "t", "u"]}},
          {"kind": "SCORE", "run": "old", "t": 0, "menus": {"A": ["z"]}},
          {"kind": "METRIC", "run": "r1", "target": "b", "by": "max", "scores": {"task": 5.0}},
          {"kind": "METRIC", "run": "r1", "target": "c", "by": "claude", "scores": {"task": 5.0}},
          {"kind": "METRIC", "run": "r2", "target": "menu:A", "by": "max", "scores": {"task": 1.0}},
          {"kind": "METRIC", "run": "old", "target": "z", "by": "max", "scores": {"task": 4.0}}]
    fo = "\n".join(forward(fw))
    ok.append("2 rated run(s) with frozen picks, 1 LEGACY" in fo and "Maestro@1 0/2" in fo and "Maestro@3 1/2" in fo
              and "finder@3 0/2" in fo and "rejected in 1/2" in fo and "B 0/2" in fo)
    wf = water_fill({"a": 30, "b": 200, "c": 120}, 240)
    ok.append(wf == {"a": 30, "b": 105, "c": 105} and sum(wf.values()) == 240
              and water_fill({"a": 10, "b": 20}, 999) == {"a": 10, "b": 20})
    d = {"skill-finder": "Describe a need and find the best skills", "plant-the-bug": "Prove a test can fail by planting bugs",
         "land-a-change": "The exact landing ritual for a change", "skill-foundry": "Build a new skill through every gate"}
    ag = agenda([{"name": "plant-the-bug"}], [{"name": n} for n in d], d)
    ok.append([a[0] for a in ag] == list(PHASE_ORDER) and ag[2][1] == "plant-the-bug" and ag[3][1] == "land-a-change"
              and ag[0][2] == "from the pool")
    # v11 triage: a specified card is SKIP, a vague card is not, open wording is FULL, a one-line ask is QUICK
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "plans").mkdir()
        (Path(td) / "plans" / "PLAN.md").write_text(
            "### GT9: spelled out\n- files: `a.py`\n  - red: `test_x`\n\n### GT8: vague\n- an idea, no tests yet\n",
            encoding="utf-8")
        p = Path(td)
        ok.append(triage("build GT9 now please", p)[0] == "SKIP")
        ok.append(triage("build GT8 from the card, carefully and completely", p)[0] == "FULL")
        ok.append(triage("design a new way to build GT9", p)[0] == "FULL")          # open wording wins over the card
        ok.append(triage("is there a skill for counting words", p)[0] == "QUICK")
        ok.append(triage("build GT9 and GT8 together in one change today", p)[0] == "FULL")   # one vague card -> FULL
    # v11 brief sheet: bounded length, ends with the cost line, keeps the run id and each pick's command
    fake = {"run": "r0", "task": "do GT9", "pool": 40, "concepts": [{"text": "x", "analogy": False, "tags": [], "unknown": []}],
            "chosen": [{"name": f"s{i}", "when": "w" * 200, "first_cmd": f"python s{i}.py", "skill_md": "nope",
                        "grade": "S3", "ballot": "words"} for i in range(8)],
            "context": ["first phase work can move: 3", "plan card GT42 (phase 6): far", "plan card GT9 (phase 3): near"],
            "needed": [{"concept": "c" * 90, "best": "b", "score": 0.1}] * 5, "debt": ["a"], "ponder_debt": ["b"],
            "spark": [{"op": "analogize", "members": ["kingdom-sweep"]}], "stay_inside": ["only GT9"], "finder_top": ["s0", "zz"]}
    br = render_brief(fake)
    ok.append(len(br.splitlines()) <= 30 and br.splitlines()[-1].startswith("COST sheet ~") and "r0" in br
              and "python s7.py" in br and "GT42" not in br and "GT9 (phase 3)" in br and br.count("NEEDED:") == 3
              and "FINDER ALSO SAYS (judge these too): zz" in br)
    # v11 debt and cost: an unrated run is owed, a closed one is not; the cost report counts triage verdicts
    rows = [{"kind": "SCORE", "run": "u", "chosen": ["a"], "t": 0}, {"kind": "SCORE", "run": "c", "chosen": ["a"], "t": 0},
            {"kind": "CLOSE", "run": "c"}, {"kind": "TRIAGE", "verdict": "SKIP"}, {"kind": "TRIAGE", "verdict": "QUICK"},
            {"kind": "SHEET_COST", "run": "u", "sheet": 500, "read": 4000}]
    ok.append([r["run"] for r in debt_runs(rows)] == ["u"])
    cr = "\n".join(cost_report(rows))
    ok.append("1 skipped, 1 quick, 0 full" in cr and "~500 tokens shown" in cr and "0 of 2" in cr)
    ok.append(tokens_of("abcd" * 10) == 10 and SELF == "skill-maestro")
    # v14 fairness switches: each behaves as documented, whatever the default is
    global FAIR_ASKWORDS
    keep_a = FAIR_ASKWORDS
    FAIR_ASKWORDS = True
    ok.append(ranking_text("is there a Skill for tallying votes?") == "is there a for tallying votes?"
              and ranking_text("skills") == "skills")                          # nothing left: the task stays as typed
    FAIR_ASKWORDS = False
    ok.append(ranking_text("is there a skill for x") == "is there a skill for x")
    FAIR_ASKWORDS = keep_a
    mem = [({"plan", "card", "build"}, "far-famous", "useful")] * 50 + [({"vote", "tally", "count"}, "near", "useful")]
    cs = context_stats(mem, {"vote", "tally", "count", "ballot"})
    ok.append(cs == {"near": {"useful": 1}})                                   # fame on unrelated tasks counts for nothing
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "has-body").mkdir()
        (d / "has-body" / "SKILL.md").write_text("---\nname: has-body\ndescription: a widget tool\n---\nbody\n", encoding="utf-8")
        (d / "short-lab").mkdir()
        (d / "short-lab" / "SKILL.md").write_text("---\nname: short-lab\ndescription: Lab - X. It counts widgets per "
                                                  "batch and ranks batches by count.\n---\n", encoding="utf-8")
        L2 = Library(d, everything=False)
        am = {r["name"]: r for r in auto_mechanisms(L2, {"measure": "compute a statistic or count widgets",
                                                         "rank": "order items by a score"}, {"has-body"})}
        ok.append(set(am) == {"short-lab"} and am["short-lab"]["auto"] and "counts widgets" in am["short-lab"]["does"]
                  and am["short-lab"]["world"] == "")                    # hand lines are never overwritten
    nop = render_brief({"run": "r1", "task": "月次売上のグラフを作ってください", "pool": 0, "chosen": [], "context": [],
                        "concepts": [{"text": "x", "analogy": False, "tags": [], "unknown": []}]})
    ok.append("NO PICKS" in nop and "another language" in nop)
    import tempfile                                                         # v10: cloud sessions
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "skill-finder").mkdir()
        (t / "core-skill-pin").mkdir()
        (t / "skill-finder" / "find_skill.py").write_text("", encoding="utf-8")
        (t / "core-skill-pin" / "core_pin.py").write_text("", encoding="utf-8")
        ok.append(has_finder(t) and companion(t, "core_pin.py").parent.name == "core-skill-pin"
                  and companion(t, "find_skill.py").parent.name == "skill-finder")   # the repo layout finds both
        a, b = State(t / "pc"), t / "repo" / "ledger.jsonl"
        b.parent.mkdir()
        a.append({"kind": "RATE", "run": "r1", "t": 5})
        b.write_text(json.dumps({"kind": "SCORE", "run": "r1", "t": 3}, sort_keys=True) + "\n"
                     + json.dumps({"kind": "RATE", "run": "r1", "t": 5}, sort_keys=True) + "\n", encoding="utf-8")
        merged = State(t / "pc", also=(b,)).rows()
        ok.append([r["kind"] for r in merged] == ["SCORE", "RATE"])                # union, each row once, in time order
        cloud = State(t / "pc2", ledger=b)
        cloud.append({"kind": "CLOSE", "run": "r1", "t": 9})
        ok.append(len(b.read_text(encoding="utf-8").splitlines()) == 3 and not (t / "pc2" / "ledger.jsonl").exists())
        (t / "proj" / ".claude").mkdir(parents=True)
        (t / "proj" / ".claude" / "settings.json").write_text(json.dumps({"skillOverrides": {"x": "off", "y": "name-only"}}),
                                                               encoding="utf-8")
        (t / "proj" / ".claude" / "settings.local.json").write_text(json.dumps({"skillOverrides": {"y": "user-invocable-only"}}),
                                                                     encoding="utf-8")
        ov = skill_overrides(t / "proj")
        ok.append(ov.get("x") == "off" and ov.get("y") == "user-invocable-only")   # the local file wins
        h = t / "home"                                                       # v11: every skill, not only custom
        (h / "skills" / "synced" / "org" / "pdf").mkdir(parents=True)
        (h / "skills" / "synced" / "org" / "pdf" / "SKILL.md").write_text("---\nname: pdf\n---\n", encoding="utf-8")
        pl = h / "plugins" / "synced" / "org" / "abc123"
        (pl / ".claude-plugin").mkdir(parents=True)
        (pl / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "fin", "skills": ["./extra/dcf"]}),
                                                           encoding="utf-8")
        (pl / "skills" / "comps").mkdir(parents=True)
        (pl / "extra" / "dcf").mkdir(parents=True)
        (pl / "extra" / "dcf" / "SKILL.md").write_text("---\nname: dcf\n---\n", encoding="utf-8")   # a single-skill path
        roots = {(d.name, pre, src) for d, pre, src in other_skill_roots(h)}
        ok.append(roots == {("org", "anthropic-skills:", "synced"), ("skills", "fin:", "plugin fin"),
                            ("extra", "fin:", "plugin fin")})                # synced, default and manifest paths
        lib_dir = t / "lib"                                                  # v12: standalone, health, built-ins
        for n, body in (("alpha-tool", "print('PASS')\nimport sys; sys.exit(0)\n"), ("beta-broken", "import sys; sys.exit(1)\n")):
            (lib_dir / n).mkdir(parents=True)
            (lib_dir / n / "SKILL.md").write_text(f"---\nname: {n}\ndescription: {n.split('-')[0]} widget counting tool\n---\n",
                                                  encoding="utf-8")
            (lib_dir / n / "tool.py").write_text("# --selftest\n" + body, encoding="utf-8")
        L = Library(lib_dir, everything=False)
        ok.append(L.standalone and [r["name"] for r in L.search("alpha widget", 2)][:1] == ["alpha-tool"])
        S = State(t / "hs")
        ok.append(health_of(L, S, "alpha-tool") == "OK" and health_of(L, S, "beta-broken") == "FAIL"
                  and json.loads((S.d / "health.json").read_text()) and health_of(L, S, "beta-broken") == "FAIL")
        L2 = Library(lib_dir, everything=True)
        ok.append("simplify" in L2.desc and L2.source.get("simplify") == "built-in" and not L2.skill_md("simplify").is_file())
        cd = t / "survey_cards"                                              # v17 survey: the cards and the asks reading
        cd.mkdir()
        card = lambda n, v, asks: {"name": n, "does": f"{n} did it", "test": {"verdict": v, "result": "r"},  # noqa: E731
                                   "asks": asks, "not_asks": [], "overlaps": [], "side_effects": []}
        (cd / "alpha-tool.json").write_text(json.dumps(card("alpha-tool", "works", ["tally my gizmos per crate",
                                            "how many sprockets did we ship", "count the doohickeys"])), encoding="utf-8")
        (cd / "beta-broken.json").write_text(json.dumps(card("beta-broken", "broken", ["tally my gizmos per crate",
                                             "gizmos tally", "crate gizmos"])), encoding="utf-8")
        (cd / "thin.json").write_text(json.dumps(card("thin", "works", ["one ask"])), encoding="utf-8")
        tp = t / "tested.jsonl"
        n_ok, by, bad = survey_build(cd, tp)
        ok.append(n_ok == 2 and by == {"works": 1, "broken": 1} and len(bad) == 1 and bad[0].startswith("thin"))
        L.tested_path = tp
        ok.append(L.asks_reading("tally the gizmos in each crate", 5) == ["alpha-tool"]   # words the description never says
                  and L.asks_reading("weather in paris", 5) == [])                       # broken one left out; no match, no pick
        ok.append(load_tested(tp)["beta-broken"]["verdict"] == "broken" and load_tested(t / "none.jsonl") == {})
        ok.append(pc_only({"a": {}, "b": {}}, {"a": "x", "c": "y"}) == ["b"]            # this library's cards
                  and pc_only({"a": {}, "b": {}, "c": {}, "d": {}}, {"a": "x", "z": "y"}) == [])   # someone else's
        proj = t / "proj2"                                                   # v12: charter, limits, pick count
        proj.mkdir()
        (proj / "CLAUDE.md").write_text("# Demo\nA research project on fish prices.\n\n## The limits\n- No real orders "
                                        "until Sam signs.\n- No scripted pulls from Kraken or its API.\n\n## Where\n- look here\n",
                                        encoding="utf-8")
        chv = charter(proj)
        ok.append(chv["source"] == "CLAUDE.md" and chv["goals"][0].startswith("A research project on fish")
                  and len(chv["limits"]) == 2 and "Kraken" in chv["limits"][1])
        (proj / "MAESTRO_PROJECT.md").write_text("GOAL: ship it\nLIMIT: never post secrets\nnote\n", encoding="utf-8")
        chv = charter(proj)
        ok.append(chv == {"goals": ["ship it"], "limits": ["never post secrets"], "source": "MAESTRO_PROJECT.md"})
        tk = MiniFinder._tokens
        ok.append(limit_hits("No scripted pulls from Kraken or its API.", "kraken-feed", "pull bars from Kraken", tk) == ["kraken"]
                  and limit_hits("No real orders to a broker account until Sam signs.", "order-router",
                                 "place real orders at a broker account", tk) == ["account", "broker", "orders"]
                  and not limit_hits("No real orders to a broker account until Sam signs.", "hurst",
                                     "estimate the Hurst exponent of orders", tk))      # one shared word is not a trip
        w = [{"name": f"s{i}", "fit": 1.0 - i * 0.01} for i in range(30)]
        ok.append(pick_count("fix it", w)[0] == 1 and pick_count("one plain sentence about a task", w)[0] == 2
                  and pick_count(". ".join(["sentence"] * 15) + ".", w)[0] == PICKS_MAX
                  and pick_count("alpha one. beta two. gamma three.", w[:3])[0] == 3)   # 6 wanted, 3 within reach
        ok.append(_opt(["try", "r", "s", "--", "python", "x.py", "--state", "Q"], "--state") is None
                  and _positional(["try", "r", "s", "--state", "S", "--", "python", "x.py"]) == ["try", "r", "s"])
        ok.append(task_kinds("write a limerick about my trading bot, make it fun")[0][0] in ("CREATE", "WRITE", "PLAY")
                  and task_kinds("act as a hostile reviewer of this plan")[0][0] == "ROLEPLAY"
                  and task_kinds("measure the Sharpe honestly")[0][0] == "ANALYZE"
                  and task_kinds("zzz qqq")[0][0] == "ANALYZE")
        ok.append(KIND_PHASES["ROLEPLAY"] == ("CAST", "VOICE", "PLAY", "DEBRIEF")
                  and roles_of("devils-advocate", "writes a counter-argument for each claim", ("CRITIQUE", "DRAFT")) == ["CRITIQUE", "DRAFT"]
                  and side_effects("Post to the mailbox, then delete the scratch file and push") == ["delete", "post", "push"]
                  and side_effects("Estimate the Hurst exponent") == [])
        # v17: structured FIT, health verdicts, AST side effects, persona cards, subject STALE
        j, rest = parse_fit_judgments(["kind=yes", "question=no", "assumes=yes", "used=n", "it", "read", "the", "file"])
        ok.append(j == {"kind": True, "question": False, "assumes": True, "used": False} and rest == ["it", "read", "the", "file"]
                  and fit_verdict(j) == "misfit" and fit_verdict({"kind": True, "question": True, "assumes": True, "used": False}) == "works"
                  and parse_fit_judgments(["works", "why"]) == (None, ["works", "why"]))
        ok.append(health_verdict("Traceback\nModuleNotFoundError: No module named 'statsmodels.api'") == "NEEDS statsmodels"
                  and health_verdict("ImportError: cannot import name 'PSICQUIC' from 'bioservices'") == "DRIFT"
                  and health_verdict("AssertionError: 3 != 4") == "FAIL" and "NEEDS x" not in SWAP_HEALTH and "DRIFT" in SWAP_HEALTH)
        import tempfile as _tf
        with _tf.TemporaryDirectory() as _td:
            _p = Path(_td) / "t.py"
            _p.write_text("import os, subprocess, shutil\nos.remove('x')\nsubprocess.run(['git', 'push', 'origin'])\n"
                          "shutil.rmtree('d')\nprint(eval('1+1'))\n", encoding="utf-8")
            (Path(_td) / "clean.py").write_text("print('hi')\n", encoding="utf-8")
            ok.append(script_side_effects(Path(_td)) == ["delete", "exec", "push"])
            (Path(_td) / "SKILL.md").write_text("---\nname: t\nallowed-tools: Bash(python:*) Read\n---\n# t\n", encoding="utf-8")
            ok.append(frontmatter_field(Path(_td) / "SKILL.md", "allowed-tools") == "Bash(python:*) Read"
                      and frontmatter_field(Path(_td) / "SKILL.md", "argument-hint") is None)
            _subj = Path(_td) / "subject.txt"
            _subj.write_text("v1", encoding="utf-8")
            _rows = [{"kind": "TRY", "run": "r", "skill": "s", "subject": str(_subj), "subject_sha": file_sha(_subj)}]
            ok.append(subject_state(_rows, "r", "s")["stale"] is False)
            _subj.write_text("v2", encoding="utf-8")
            ok.append(subject_state(_rows, "r", "s")["stale"] is True and stale_line(subject_state(_rows, "r", "s"), "verdict").startswith("STALE")
                      and subject_state(_rows, "other", "s") is None)
        pc = persona_card("statistician", "Think like a Statistician. Reasons from estimands, generative-model assumptions, and a "
                          "budgeted Type I/II error tradeoff through analysis plans (SAP), mixed models, and Benjamini-Hochberg FDR "
                          "while treating naive post-selection SEs, unadjusted multiplicity, and sequential peeking as first-class "
                          "failure modes.", None)
        ok.append(pc is not None and pc["persona"] is True and len(pc["assumes"]) == 3 and "sequential peeking" in pc["not_for"]
                  and "mixed models" in pc["probe"] and persona_card("x", "Estimate the Hurst exponent.", None) is None)
        global TOOL_BONUS
        TOOL_BONUS = False
        wt = weigh([{"name": "doc", "score": 10.0, "tool": False}, {"name": "tool", "score": 10.0, "tool": True}], {}, set())
        TOOL_BONUS = True
        wt2 = weigh([{"name": "doc", "score": 10.0, "tool": False}, {"name": "tool", "score": 10.0, "tool": True}], {}, set())
        ok.append(wt[0]["use"] == wt[1]["use"] and wt2[0]["name"] == "tool" and wt2[0]["use"] > wt2[1]["use"])
        ps = {"fin": (False, "fin@synced")}
        ok.append(switch_on("fin:dcf", "plugin fin", {}, ps).count('"fin@synced": true') == 1
                  and "name-only" in switch_on("x", "", {"x": "off"}, {})
                  and switch_on("y", "", {"y": "name-only"}, {}) is None
                  and switch_on("fin:dcf", "plugin fin", {}, {"fin": (True, "fin@synced")}) is None)
        ok.append(eval_null([{"m": ["a"], "good": ["a"]}, {"m": ["b"], "good": ["b"]}, {"m": ["c"], "good": ["z"]}], 50)["real"] == 2
                  and eval_null([{"m": ["a"], "good": ["a"]}, {"m": ["a"], "good": ["a"]}], 20)["p"] == 1.0   # ties count: p is 1, not 0
                  and eval_ci([1, 0, 1, 1])["hits"] == 3 and mcnemar([1, 0, 0], [1, 1, 1])["b_only"] == 2
                  and mcnemar([1], [1, 0])["ok"] is False and mcnemar([1, 1], [1, 1])["verdict"] == "IDENTICAL")
    for mod in ("hindsight", "conduct", "introspect", "inverse", "index", "concert", "rerank", "community", "meaning", "personal", "modes", "phase", "scrub"):   # v15/v16 + 2026-10-24/25: the modules beside this file
        if _module_path(mod) is None and mod in EXTRA_MODULES:     # v20: an extra that is not installed is not a failure
            print(f"  {mod}: not installed ({EXTRAS_PKG}); its selftest is skipped")
            continue
        try:
            ok.append(bool(_load(HERE / f"{mod}.py", mod)._selftest()))
        except Exception as exc:  # noqa: BLE001
            print(f"  {mod} selftest crashed: {type(exc).__name__}: {exc}")
            ok.append(False)
    print(f"SELFTEST {'PASS' if all(ok) else 'FAIL'} {sum(ok)}/{len(ok)}"
          + ("" if all(ok) else f"  failed check(s) {[i + 1 for i, x in enumerate(ok) if not x]}"))
    return all(ok)


VALUED = ("--root", "--state", "--top", "--probes", "--project", "--budget", "--by", "--subject", "--question",
          "--questions", "--on", "--write", "--concepts", "--concepts2", "--quote", "--note", "--close-older-than",
          "--like", "--null", "--before", "--days", "--split", "--keys", "--grid", "--passes", "--workers", "--timeout",
          "--only", "--kind", "--paths", "--out", "--limit", "--since", "--min", "--k", "--context", "--epochs", "--l2", "--mode")
FLAGS = ("--graph", "--pool", "--json", "--plain", "--quick", "--keywords-only", "--full", "--custom-only", "--auto", "--no-ledger", "--misses", "--no-infer",
         "--no-kinds", "--brief", "--plain-words", "--ci", "--armed", "--compare", "--dry", "--hook", "--stdin", "--switches",
         "--power", "--write", "--personas", "--stamp", "--observed-only", "--discriminative")
PLAIN_WORDS = ("PLAIN WORDS: pick = a skill it chose. [words] = chosen because your words match its description; "
               "[meaning] = chosen because the task's operations match what it does; [both] = both, the strongest. "
               "S1/S2/S3 = how much evidence backs it (S1 best). FIT = run it on your real file and say works or misfit. "
               "NEEDED = an operation no skill does well. SPARK = a wild card to invent with. ODDS = how often the Maestro "
               "helped on tasks like this before. COST = tokens this sheet and its reading cost.")
BRIEF_KEEP = ("MAESTRO run", "PROJECT", "  GOAL", "  LIMIT", "TASK vs LIMIT", "SPECTRUM", "PICKS", "rank skill", "HOW TO USE",
              "  - ", "CONDUCTOR PROMPT", "SELECT ", "AUDIT DEBT")   # --brief: the lines a working session needs, nothing else


def brief(text: str) -> str:
    """The sheet cut to what the work needs (the user: "do not spend excessive tokens unless actually helpful"): the
    picks table rows, each pick's how-to line, the conductor prompt, the project's limits and the swaps."""
    out = []
    for ln in text.splitlines():
        if ln.startswith(BRIEF_KEEP) or re.match(r"^ {2,4}\d+ \S", ln):
            out.append(ln)
    return "\n".join(out)


def _own(argv: list[str]) -> list[str]:
    """The Maestro's own part of the line: everything before `--` (what follows `--` is the command for try/taste,
    verbatim; v12's command tour found a `--state` after `--` swallowed into the command)."""
    return argv[:argv.index("--")] if "--" in argv else argv


def _opt(argv: list[str], flag: str, default=None):
    argv = _own(argv)
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def _positional(argv: list[str]) -> list[str]:
    """The words that are not options or option values, in order; options may appear anywhere before `--`."""
    out, skip = [], False
    for a in _own(argv):
        if skip:
            skip = False
        elif a in VALUED:
            skip = True
        elif a not in FLAGS:
            out.append(a)
    return out


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):                 # a sheet can hold any character (α, →); a cp1252 console
        try:                                                # crashed mid-sheet on 2026-10-21
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if "--selftest" in _own(argv):            # a `--selftest` after `--` belongs to the tried command, not to us
        return 0 if _selftest() else 1
    global DIAL_SHA
    try:
        dials, DIAL_SHA = load_dials()
        apply_dials(dials)
    except DialError as exc:
        print(f"HALT {exc}  ({DIALS})")
        return 4
    root = Path(_opt(argv, "--root", ROOT))
    if not root.is_dir():
        print(f"NO_LIBRARY: {root} is not a folder; pass --root <a folder of skill folders>")
        return 5
    if _positional(argv)[:1] == ["whisper"] and "--hook" not in argv:     # O4/O7: no Library, the index file alone
        C = _load(HERE / "concert.py", "concert")
        raw = sys.stdin.read() if "--stdin" in argv else " ".join(_positional(argv)[1:])
        if "--stdin" in argv:                                   # 2026-10-24 (scenario test A): with no index yet the
            import io                                           # full path below reads stdin again; give it the prompt
            sys.stdin = io.StringIO(raw)
        try:
            hook_in = json.loads(raw) if raw.strip().startswith("{") else {}
            prompt = hook_in.get("prompt", raw) if isinstance(hook_in, dict) else raw
            HOOK["transcript"] = hook_in.get("transcript_path") if isinstance(hook_in, dict) else None   # 2026-10-25: the phase reading's session
        except ValueError:
            prompt = raw
        t0 = time.time()
        fast = C.whisper_fast(prompt, Path(_opt(argv, "--state", STATE)), root)
        if fast is not None:
            print(C.render_whisper(prompt, fast, time.time() - t0))
            return 0
    if not has_finder(root):
        print(f"STANDALONE: {root} has no skill-finder/core-skill-pin; using the Maestro's own mini finder (no core pins)")
    top, probes_opt = (int(_opt(argv, "--top")) if _opt(argv, "--top") else None), _opt(argv, "--probes")   # None: 1-22 by the task
    flags = {a for a in _own(argv) if a in FLAGS}
    pos = _positional(argv)
    cmd = pos[0] if pos else ""
    extra = [Path(_opt(argv, '--project'))] if _opt(argv, '--project') else []
    if not extra and (Path.cwd() / '.claude' / 'skills').is_dir():
        extra = [Path.cwd() / '.claude' / 'skills']     # the project library of the folder you work in
    project = (extra[0].parent.parent if extra and extra[0].name == "skills"
               else extra[0] if extra and (extra[0] / ".claude").is_dir() else None)
    shared = project / SHARED_LEDGER if project else None
    if _opt(argv, "--state"):
        st = State(Path(_opt(argv, "--state")))                      # an explicit state folder stands alone
    elif CLOUD and shared is not None:
        st = State(STATE, ledger=shared)                             # cloud: ratings go to the repo
    else:
        community = _load(HERE / "community.py", "maestro_community").community_files(STATE) if (HERE / "community.py").is_file() else ()
        st = State(STATE, also=((shared,) if shared else ()) + community)   # PC: also read cloud sessions and other people's bundles (2026-10-24)
    st.shared = CLOUD and shared is not None and not _opt(argv, "--state")
    if "--no-ledger" in flags or __import__("os").environ.get("MAESTRO_NO_LEDGER") == "1":   # v14: privacy
        st.append = lambda row: None                   # nothing is written; history already there is still read
    lib = Library(root, tuple(extra), everything="--custom-only" not in flags)
    lib.overrides, lib.plugins = skill_overrides(project), plugin_states(project)
    lib.project = project
    lib.cache_dir = st.d
    lib.state_dir = st.d                               # the meaning vectors, self-pick record and personal reading live here
    lib.personal_rows = st.rows                        # your own Maestro learns from this person's own rows only
    lib.duets = learned_duets(st.rows())
    lib.quick = "--quick" in flags
    if len(pos) > 1 and pos[1] == "last" and cmd in ("read", "try", "fit", "taste", "close", "plan", "baton", "rate",
                                                      "encore", "ponder", "breed"):
        runs = [r["run"] for r in st.rows() if r.get("kind") == "SCORE"]
        if not runs:
            print("RUN_UNKNOWN: no score run yet")
            return 3
        pos[1] = runs[-1]
        print(f"(last = run {pos[1]})")
    if cmd in ("read", "try", "fit", "taste", "close", "plan", "baton", "ponder", "breed") and len(pos) > 1 and not any(
            r.get("kind") == "SCORE" and r.get("run") == pos[1] for r in st.rows()):
        print(f"RUN_UNKNOWN: no score run {pos[1]!r} in the ledger; use the run id the score sheet printed")
        return 3
    if cmd == "used":
        print("\n".join(used_report(st.rows(), pos[1] if len(pos) > 1 else None)))
    elif cmd == "score" and len(pos) > 1:
        task = " ".join(pos[1:])
        forced = flags & {"--full", "--keywords-only", "--quick", "--json", "--pool"} or _opt(argv, "--concepts")
        if TRIAGE_ON and not forced:                        # v11: is a sheet worth its cost?
            verdict, why = triage(task, Path(_opt(argv, "--project")) if _opt(argv, "--project") else Path.cwd())
            if verdict != "FULL":
                print(triage_note(lib, st, task, verdict, why))
                return 0
        qs = tuple(q.strip().upper() for q in (_opt(argv, "--questions") or "").split(",") if q.strip())
        concepts_in = _opt(argv, "--concepts") or ""
        if _opt(argv, "--like") and not concepts_in:          # v15 item 7: reuse a past run's concepts
            like = _opt(argv, "--like")
            prev = [r for r in st.rows() if r.get("kind") == "SCORE" and r.get("concepts")]
            row = prev[-1] if like == "last" and prev else next((r for r in prev if r.get("run") == like), None)
            if row is None:
                print(f"RUN_UNKNOWN: no score run {like!r} with concepts (`maestro.py used` lists runs)")
                return 3
            concepts_in = row["concepts"]
            print(f"(concepts reused from run {row['run']}: {concepts_in[:120]})")
        k_ctx = int(_opt(argv, "--context")) if _opt(argv, "--context") else CONTEXT_PROMPTS   # v16 M41
        prev = []
        if k_ctx > 0:
            try:
                prev = _load(HERE / "hindsight.py", "hindsight").recent_prompts(k_ctx, exclude=task)
            except Exception:  # noqa: BLE001
                prev = []
        if WEIGHTS.get("phase"):                                # 2026-10-25 (M52): the skills this session just used
            try:
                lib.phase_context = _load(HERE / "phase.py", "phase").live_context(st.d, HOOK.get("transcript"))
            except Exception:  # noqa: BLE001
                lib.phase_context = None
        sheet = score(lib, st, task, top, "--graph" in flags, qs, concepts_in, session_ctx=" ".join(prev),
                      subject=_opt(argv, "--subject"), mode=_opt(argv, "--mode"))        # v18: name the subject at score time
        sheet["session_ctx"] = (f"CONTEXT: ranked with the last {len(prev)} prompt(s) of this session (dial M41; `--context 0` to rank the task alone)"
                                if prev else None)
        try:                                                # v15: odds and hindsight lines (never a ranking input)
            w15 = set(lib.fs._tokens(lib.variants(task)["_plain"]))
            sheet["odds"] = (_load(HERE / "introspect.py", "introspect").odds_line(st.rows(), w15)
                             if ODDS_SHOWN and _module_path("introspect") else None)      # v20: introspect is an extra
            sheet["hindsight"] = _load(HERE / "hindsight.py", "hindsight").hindsight_line(st.d, w15) if HINDSIGHT_SHOWN else None
        except Exception as exc:  # noqa: BLE001
            sheet["odds"] = f"ODDS: unavailable ({type(exc).__name__}: {exc})"
        sheet["show_pool"] = "--pool" in flags
        sheet["keywords_only"] = "--keywords-only" in flags or "--quick" in flags
        if _opt(argv, "--budget"):
            sheet["budget"] = int(_opt(argv, "--budget"))
            sheet["reading"] = water_fill({c["name"]: c.get("lines", 0) for c in sheet["chosen"]}, sheet["budget"])
        full = "--full" in flags or "--pool" in flags or not BRIEF
        if "--json" in flags:
            text = json.dumps(sheet, indent=1, default=list)
        elif "--brief" in flags:                          # the cloud line's filter of the full sheet (v12)
            text = brief(render(sheet))
        else:
            text = render(sheet) if full else render_brief(sheet)
        if "--plain-words" in flags and "--json" not in flags:   # v15 item 33: the glossary footnote
            text += "\n" + PLAIN_WORDS
        print(text)
        st.append({"kind": "SHEET_COST", "run": sheet["run"], "sheet": tokens_of(text), "read": read_cost(sheet["chosen"]),
                   "full": full, "t": int(time.time())})
        if "--json" not in flags and code_type_line():
            print(code_type_line())
    elif cmd == "newskill" and len(pos) > 2:             # v14: when no skill fits and there is no skill-foundry
        slug = re.sub(r"[^a-z0-9-]+", "-", pos[1].lower()).strip("-") or "new-skill"
        dest = root / slug / "SKILL.md"
        if dest.exists():
            print(f"EXISTS {dest}: not overwritten")
            return 3
        job = " ".join(pos[2:])
        dest.parent.mkdir(parents=True)
        dest.write_text(f"---\nname: {slug}\ndescription: {job[0].upper() + job[1:] if job else 'Describe the job'}. "
                        "Use this when <the situations, in the words people actually type>.\n---\n\n"
                        f"# {slug}\n\n## What it does\n{job}\n\n## Steps\n1. \n2. \n3. \n\n## How to tell it worked\n- \n",
                        encoding="utf-8")
        print(f"NEWSKILL {dest}: a template. Fill in the steps and the 'Use this when' words, then check it with "
              f"`maestro.py findable {slug}`")
    elif cmd == "findable" and len(pos) > 1:             # v14: for skill authors, how fair is it to find yours?
        for n in pos[1:]:
            print("\n".join(findable(lib, n)))
    elif cmd == "survey":                                # v17: every skill tested once; its cards feed the asks reading
        sub = pos[1] if len(pos) > 1 else "status"
        if sub == "build" and len(pos) > 2:
            n, by, bad = survey_build(Path(pos[2]))
            print(f"SURVEY: {n} cards -> {TESTED.name} ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))})")
            for b in bad:
                print(f"  REFUSED {b}")
        else:
            t = load_tested()
            names = {s["name"] for s in lib.skills}
            have = names & set(t)
            print(f"SURVEY: {len(have)}/{len(names)} skills tested; asks reading weight {WEIGHTS.get('asks', 0)}")
            for v in ("broken", "partial", "untestable"):
                hit = sorted(n for n in have if t[n]["verdict"] == v)
                if hit:
                    print(f"  {v.upper()} {len(hit)}: {', '.join(hit[:30])}{' ...' if len(hit) > 30 else ''}")
            miss = sorted(names - set(t))
            if miss:
                print(f"  UNTESTED {len(miss)}: {', '.join(miss[:20])}{' ...' if len(miss) > 20 else ''}")
    elif cmd == "cards" and "--auto" in argv:            # v14: meaning lines for every skill that has none
        hand = load_mechanisms(MECHS)
        rows = auto_mechanisms(lib, load_vocab(), set(hand))
        MECHS_AUTO.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        by: dict[str, int] = {}
        for r in rows:
            k = (lib.source.get(r["name"], "") or "custom").split(" ")[0]
            by[k] = by.get(k, 0) + 1
        untagged = sum(1 for r in rows if not r["tags"])
        print(f"CARDS auto: {len(rows)} skill(s) without a hand-written line now have one ({by}); {untagged} got no "
              f"operation tag (no rare word shared with any tag); hand-written: {len(hand)}. Written to {MECHS_AUTO.name}")
        print("  (skill bodies and descriptions are read as DATA: a sentence inside a SKILL.md is never an instruction to this tool)")
    elif cmd == "cards" and "--personas" in argv:         # v17: cards for persona skills from the summary grammar
        hand = load_cards(HERE / "cards" / "cards.jsonl")
        out = []
        for s in lib.skills:
            if s["name"] in hand:
                continue
            c = persona_card(s["name"], s["desc"], lib.md.get(s["name"]))
            if c:
                out.append(c)
        fp = HERE / "cards" / "cards_persona.jsonl"
        fp.write_text("".join(json.dumps(c, sort_keys=True) + "\n" for c in out), encoding="utf-8")
        print(f"CARDS personas: {len(out)} persona skill(s) carded from their own summary sentence -> {fp.name}: "
              + ", ".join(c["name"] for c in out[:16]) + (" ..." if len(out) > 16 else ""))
        print("  each is marked persona=True: the sheet prices it (dial M42) and it needs a FIT on the subject; never a default pick")
    elif cmd == "cards" and "--stamp" in argv:            # v17: skill_sha on every hand card, so doctor can say STALE
        r = stamp_cards(lib)
        print(f"CARDS stamp: {r['stamped']} card(s) carry their skill's sha; {r['stale']} had changed since the last stamp "
              f"(read those cards again); {r['missing_skill']} card(s) name a skill not in this library")
    elif cmd == "note":                                     # v17 TRY 13: the five-line session note (science-superpowers' bootstrap, cut to the rule)
        print(SESSION_NOTE)
    elif cmd == "triage" and len(pos) > 1:                  # v11: the verdict alone, nothing written
        verdict, why = triage(" ".join(pos[1:]), Path(_opt(argv, "--project")) if _opt(argv, "--project") else Path.cwd())
        print(f"TRIAGE {verdict}: {why}")
    elif cmd == "cost":
        print("\n".join(cost_report(st.rows())))
    elif cmd == "debt":                                     # v11: one place to see and clear the feedback debt
        rows = st.rows()
        owed = debt_runs(rows)
        days = _opt(argv, "--close-older-than")
        if days is not None:
            cut = time.time() - float(days) * 86400
            stale = [r for r in owed if r.get("t", 0) < cut]
            for r in stale:
                st.append({"kind": "CLOSE", "run": r["run"], "why": f"stale: no rating or ponder after {days} day(s) "
                           "(closed by `debt --close-older-than`; counts as unused, never as useful)", "t": int(time.time())})
            print(f"CLOSED {len(stale)} stale run(s); {len(owed) - len(stale)} still owed")
        else:
            for r in owed[-15:]:
                age = (time.time() - r.get("t", time.time())) / 86400
                print(f"  {r['run']}  {age:4.1f} d  {', '.join(r['chosen'][:4])}  | {r.get('task', '')[:60]}")
            print(f"DEBT {len(owed)} run(s): rate a pick (`rate RUN SKILL unused|useful|wrong`), ponder, `close RUN \"why\"`, "
                  "or `debt --close-older-than 3`")
    elif cmd == "ponder" and len(pos) > 1:
        rows = st.rows()
        if _opt(argv, "--note"):
            st.append({"kind": "PONDER", "run": pos[1], "note": _opt(argv, "--note")[:1500], "t": int(time.time())})
            print(f"PONDER recorded for {pos[1]}")
            return 0
        c2 = parse_concepts(_opt(argv, "--concepts2") or "", load_vocab(), lib.fs._tokens) if _opt(argv, "--concepts2") else None
        mechs = load_mechanisms()
        per2 = concept_scores(c2, {n: m for n, m in mechs.items() if n in lib.desc}, lib.fs._tokens) if c2 else None
        lines = ponder(rows, pos[1], mechs, load_cards(), c2, per2)
        rec = scout_record(rows)
        if per2:                                             # item 6: log the scan so scouts can earn a record
            sc = next(r for r in rows if r.get("kind") == "SCORE" and r.get("run") == pos[1])
            first = set(sc.get("chosen", [])) | set(sc.get("wonder", [])) | set(sc.get("spark", []))
            second = []
            for row in per2:
                second += [n for n, _ in row[:3] if n not in second]
            st.append({"kind": "PONDER_SCAN", "run": pos[1], "concepts2": _opt(argv, "--concepts2")[:600],
                       "quorum": [n for n in second if n in first], "scouts": [n for n in second if n not in first],
                       "t": int(time.time())})
            proven = [f"{n} ({rec[n][1]}/{rec[n][0]})" for n in second if n not in first and rec.get(n, (0, 0))[1]]
            if proven:
                at = next((i for i, x in enumerate(lines) if x.startswith("   SCOUTS")), len(lines) - 1) + 1
                lines.insert(at, "   PROVEN SCOUTS (worked when offered before): " + ", ".join(proven))
        print("\n".join(lines))
    elif cmd == "breed" and len(pos) > 1:                   # item 10: a proposed new skill from two strong picks
        rows = st.rows()
        if not any(r.get("kind") == "SCORE" and r.get("run") == pos[1] for r in rows):
            print(f"RUN_UNKNOWN: no score run {pos[1]!r}")
            return 3
        b = breed(rows, pos[1], load_mechanisms(), lib.family, lib.root)
        if b.get("error"):
            print("BREED_REFUSED: " + b["error"])
            return 3
        st.append({"kind": "BREED", "run": pos[1], "parents": b["parents"], "name": b["name"], "operator": b["operator"],
                   "passed": b["passed"], "stopped_at": b["stopped_at"], "t": int(time.time())})
        print(f"BREED {b['parents'][0]} x {b['parents'][1]} by {b['operator']} -> '{b['name']}' "
              f"(other names: {', '.join(b['name_options'][1:]) or 'none'})")
        print(f"  mechanism: {b['mechanism'][:200]}")
        for g in b["gates"]:
            print(f"  {'PASS' if g['pass'] else 'FAIL'} {g['gate']:<14} {g['detail'][:110]}")
        print("  VERDICT: " + ("passes every gate (dry run - nothing created); build it with skill-foundry --create if "
                               "you want it" if b["passed"] else f"stopped at {b['stopped_at']} - the library already "
                               "covers it or the idea needs work; a finding, not a failure"))
    elif cmd == "lexical":                                  # item 5: (re)build the word-reader list
        lex = build_lexical(lib.root, load_cards(), load_mechanisms(), lib.desc)
        LEXICAL_FILE.write_text(json.dumps(lex, indent=0, sort_keys=True), encoding="utf-8")
        why: dict[str, int] = {}
        for r in lex.values():
            k = r if r.startswith("pov") else "says so in its own text"
            why[k] = why.get(k, 0) + 1
        print(f"{len(lex)} word-reading skill(s) of {len(lib.desc)} written to {LEXICAL_FILE.name}: {why}")
        for n in pos[1:]:
            print(f"  {n}: {lex.get(n, 'reads meaning (not flagged)')}")
    elif cmd == "vocab":
        mechs = load_mechanisms()
        counts: dict[str, int] = {}
        for m in mechs.values():
            for t in m.get("tags", []):
                counts[t] = counts.get(t, 0) + 1
        for t, meaning in load_vocab().items():
            print(f"{t:<20} {counts.get(t, 0):>4} skills  {meaning}")
        print(f"({len(mechs)} skills indexed in {MECHS.name}; write concepts as 'tag[,tag]: text; world: analogy')")
    elif cmd == "read" and len(pos) > 2:
        print("\n".join(read_receipt(lib, st, pos[1], pos[2:])))
    elif cmd == "rate" and len(pos) > 3 and any(is_metric_token(a) for a in pos[3:]):   # v18: 'H=0.61' in a why is prose
        by = {"user": "max", "owner": "max"}.get(_opt(argv, "--by"), _opt(argv, "--by"))   # the library's owner is "max" in the ledger
        if by not in ("max", "claude"):
            print("RATE_REFUSED: say who rates: --by user (the library's owner; `max` is the same) or --by claude "
                  "(a metric is never attributed silently)")
            return 2
        try:
            scores, why = parse_metrics(pos[3:])
        except ValueError as exc:
            print(f"RATE_REFUSED {exc}")
            return 2
        rows = st.rows()
        run_row = next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == pos[1]), None)
        if run_row is None:
            print(f"RATE_REFUSED: no run {pos[1]}")
            return 3
        target = pos[2]
        if target.lower().startswith("menu:"):
            target = "menu:" + target[5:].upper()
            members = run_row.get("menus", {}).get(target[5:])
            if not members:
                print(f"RATE_REFUSED: run {pos[1]} has no {target} (menus are recorded from v6 on)")
                return 3
        else:
            members = [target]
        if by == "claude" and not all(fit_of(rows, pos[1], m) == "works" for m in members) and (
                group_mean(scores, METRICS_TOPIC) or 0) > 1:
            print(f"RATE_REFUSED: Claude rates a pick above 1 only after it WORKED on the task's subject in run "
                  f"{pos[1]}: `maestro.py try {pos[1]} <skill> -- <command>` then `fit ... works`")
            return 3
        if by == "claude" and not any(r.get("kind") == "READ" and r.get("run") == pos[1] and r.get("skill") in members
                                      for r in rows):
            print(f"RATE_REFUSED: Claude rates only what it read in run {pos[1]}; `maestro.py read {pos[1]} "
                  f"{' '.join(members)}` first")
            return 3
        st.append({"kind": "METRIC", "run": pos[1], "target": target, "by": by, "scores": scores,
                   "why": " ".join(why)[:300], "t": int(time.time())})
        im, tm = group_mean(scores, METRICS_INNER), group_mean(scores, METRICS_TOPIC)
        print(f"METRIC {target} by {by}: inner {im if im is not None else '-'} topic {tm if tm is not None else '-'}"
              + ("  (self-report, S3: never evidence for the ranking)" if by == "claude" else
                 f"  ({OWNER}'s topic score feeds the opening book at >= 4, an antibody at <= 1)"))
    elif cmd == "try" and len(pos) > 2 and "--" in argv:
        import subprocess
        run_cmd = argv[argv.index("--") + 1:]
        if not run_cmd:
            print("TRY_REFUSED: give the command after --")
            return 2
        exe = [sys.executable if run_cmd[0] in ("python", "py") else run_cmd[0], *run_cmd[1:]]
        import shutil
        if not (shutil.which(exe[0]) or Path(exe[0]).is_file()):
            print(f"TRY_REFUSED: {exe[0]!r} is not a program on this machine (a typo is not a try)")
            return 2
        try:
            r = subprocess.run(exe, capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
                               env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            out, code = (r.stdout + r.stderr), r.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            out, code = f"{type(exc).__name__}: {exc}", -1
        lines = out.splitlines()
        subj = _opt(argv, "--subject") or next((a for a in run_cmd[1:] if Path(a).is_file() and not a.endswith(".py")), None)
        st.append({"kind": "TRY", "run": pos[1], "skill": pos[2], "cmd": run_cmd, "exit": code, "lines": len(lines),
                   "head": out[:600], "out": out[:8000], "subject": subj, "subject_sha": file_sha(subj),
                   "t": int(time.time())})   # out: what a FIT quote must come from; subject_sha: v17 STALE check
        print("\n".join(lines[:40]) + (f"\n... ({len(lines) - 40} more lines)" if len(lines) > 40 else ""))
        print(f"TRY {pos[2]} exit {code}, {len(lines)} lines" + (f", subject {subj} (sha {file_sha(subj)[:8]})" if file_sha(subj) else "")
              + f". Now judge it on the TASK, not the exit code, one judgment at a time: `maestro.py fit {pos[1]} "
              f"{pos[2]} kind=yes|no question=yes|no assumes=yes|no used=yes|no \"why\"` (works|misfit still accepted)")
    elif cmd == "taste" and len(pos) > 2 and "--" in argv and _opt(argv, "--subject"):
        subject = Path(_opt(argv, "--subject"))
        run_cmd = argv[argv.index("--") + 1:]
        if not subject.is_file() or not any("{subject}" in a for a in run_cmd):
            print("TASTE_REFUSED: --subject must be a file and the command must contain {subject}")
            return 2
        res = taste(run_cmd, subject, st.d / "taste" / pos[1] / pos[2], question=_opt(argv, "--question"))
        st.append({"kind": "TRY", "run": pos[1], "skill": pos[2], "cmd": run_cmd, "exit": 0, "lines": res["real_lines"],
                   "head": res["real_out"], "taste": res["sims"], "verdict": res["verdict"], "subject": str(subject),
                   "t": int(time.time())})
        print(res["real_out"].rstrip()[:600])
        meaning = {"CONSTANT": "its output ignores the subject: drop it",
                   "SATURATED": "it gives the same answer without the subject's substance: aim it narrower, or drop it",
                   "SIZE_ONLY": "it responds to how much there is, not to what it says",
                   "LEXICAL": "it reads the subject's words, not its structure: fine for word questions only",
                   "STRUCTURAL": "it reads the subject's layout, not its words",
                   "READS_IT": "its output depends on this subject's words and structure"}[res["verdict"]]
        print(f"TASTE {pos[2]}: {res['verdict']}{'' if res['calibrated'] else ' [UNCALIBRATED: bench E28 not passed]'} (similarity to HALF {res['sims']['HALF']}, SALAD {res['sims']['SALAD']}, "
              f"BLANKED {res['sims']['BLANKED']}; same at >= {SAME_AT}) - {meaning}. Then `maestro.py fit {pos[1]} "
              f"{pos[2]} works|misfit \"why\"`")
    elif cmd == "fit" and len(pos) > 3 and (pos[3] in ("works", "misfit") or "=" in pos[3]):
        rows = st.rows()
        judg, why_words = parse_fit_judgments(pos[3:])    # v17: the structured form, or the old works|misfit word
        if judg is not None:
            missing = [q for q in ("kind", "question", "assumes") if q not in judg]
            if missing:
                print(f"FIT_REFUSED: judge every question: {', '.join(q + '=yes|no' for q in missing)} "
                      f"({'; '.join(q + ': ' + FIT_MEANING[q] for q in missing)})")
                return 2
            verdict = fit_verdict(judg)
        else:
            verdict, why_words = pos[3], pos[4:]
        if verdict == "works" and not any(r.get("kind") == "TRY" and r.get("run") == pos[1] and r.get("skill") == pos[2]
                                          for r in rows):
            print(f"FIT_REFUSED: 'works' needs a TRY of {pos[2]} on the subject in run {pos[1]} "
                  f"(`maestro.py try {pos[1]} {pos[2]} -- <command>`)")
            return 3
        if not why_words:
            print("FIT_REFUSED: say why in words (what it found on the subject, or why the subject is the wrong kind)")
            return 2
        quote = _opt(argv, "--quote")
        if quote is not None and not quote_in_tries(rows, pos[1], pos[2], quote):
            print(f"FIT_REFUSED: the quote is not in any TRY output of {pos[2]} in run {pos[1]}; quote a line the skill "
                  "really printed (v10c: a verdict travels with its evidence, not with Claude's word)")
            return 3
        sstate = subject_state(rows, pos[1], pos[2])
        st.append({"kind": "FIT", "run": pos[1], "skill": pos[2], "verdict": verdict, "why": " ".join(why_words)[:300],
                   "quote": quote, "evidenced": quote is not None, "judgments": judg,
                   "stale": bool(sstate and sstate["stale"]), "t": int(time.time())})
        if judg is not None:
            print("  " + "  ".join(f"{q}={'yes' if judg.get(q) else 'no' if q in judg else '-'}" for q in FIT_QUESTIONS)
                  + "  -> " + verdict + "  (works needs kind, question and assumes; `used` is recorded, never decides)")
        print(f"FIT {pos[2]} {verdict}" + ("  (an antibody: similar tasks will not get it again)" if verdict == "misfit" else ""))
        if stale_line(sstate, "verdict"):
            print(stale_line(sstate, "verdict"))
    elif cmd == "plan" and len(pos) > 3 and _opt(argv, "--on"):
        on = _opt(argv, "--on")
        st.append({"kind": "USE_PLAN", "run": pos[1], "skill": pos[2], "on": on, "subject_sha": file_sha(on),
                   "expect": " ".join(pos[3:])[:300], "t": int(time.time())})
        print(f"USE_PLAN {pos[2]} on {on}: {' '.join(pos[3:])[:120]}" + (f"  (sha {file_sha(on)[:8]})" if file_sha(on) else ""))
    elif cmd == "forward":
        out = "\n".join(forward(st.rows()))
        print(out)
        if _opt(argv, "--write"):
            Path(_opt(argv, "--write")).write_text(out + "\n", encoding="utf-8")
    elif cmd == "baton" and len(pos) > 1:
        print("\n".join(baton(st.rows(), pos[1])))
    elif cmd == "close" and len(pos) > 2:
        st.append({"kind": "CLOSE", "run": pos[1], "why": " ".join(pos[2:])[:300], "t": int(time.time())})
        print(f"CLOSED {pos[1]} without ratings: {' '.join(pos[2:])[:120]}")
    elif cmd == "metrics":
        print("\n".join(board(st.rows())))
    elif cmd == "rate" and len(pos) > 3 and pos[3] in RATINGS:
        read = any(r.get("kind") == "READ" and r.get("run") == pos[1] and r.get("skill") == pos[2] for r in st.rows())
        if pos[3] in ("useful", "fascinating", "favourite") and fit_of(st.rows(), pos[1], pos[2]) != "works":
            print(f"RATE_REFUSED: {pos[2]} has no FIT works in run {pos[1]}; run it on the task's subject first "
                  f"(`maestro.py try {pos[1]} {pos[2]} -- <command>`, then `maestro.py fit {pos[1]} {pos[2]} works \"why\"`)")
            return 3
        if pos[3] in ("useful", "fascinating", "favourite") and not read:
            print(f"RATE_REFUSED: {pos[2]} has no READ receipt in run {pos[1]}; read it (`maestro.py read {pos[1]} {pos[2]}`) "
                  "before calling it useful")
            return 3
        sstate = subject_state(st.rows(), pos[1], pos[2])
        st.append({"kind": "RATE", "run": pos[1], "skill": pos[2], "rating": pos[3], "t": int(time.time()),
                   "why": " ".join(pos[4:])[:300], "stale": bool(sstate and sstate["stale"])})
        print(f"RATED {pos[2]} {pos[3]}" + (f" ({' '.join(pos[4:])})" if pos[4:] else ""))
        if stale_line(sstate, "rating"):
            print(stale_line(sstate, "rating"))
    elif cmd == "builtins":
        # v12: refresh builtins.json from the running claude's own /context listing (names only; descriptions kept)
        import subprocess
        f = HERE / "builtins.json"
        try:
            cur = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        except ValueError:
            cur = {}
        if "--refresh" not in argv:
            names = sorted(k for k in cur if not k.startswith("_"))
            print(f"{len(names)} built-in skills in {f}; `maestro.py builtins --refresh` "
                  "asks the claude CLI for the current list")
            print("  " + ", ".join(names))
            return 0
        try:
            r = subprocess.run(["claude", "-p", "/context"], capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
            out = r.stdout + r.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"BUILTINS_REFUSED: could not run `claude -p /context` ({type(exc).__name__}); edit builtins.json by hand")
            return 2
        names = re.findall(r"^\|\s*([a-z0-9][a-z0-9:_-]*)\s*\|\s*Built-in\s*\|", out, re.M)
        if not names:
            print("BUILTINS_REFUSED: /context listed no Built-in rows (is this a Claude Code session?); builtins.json unchanged")
            return 2
        new = {k: v for k, v in cur.items() if k.startswith("_")}
        new["_note"] = (f"Claude Code's built-in skills, refreshed from `claude -p /context` on {time.strftime('%Y-%m-%d')}; "
                        "descriptions are kept from the last edit, a new name gets a placeholder: fill it in from the session listing.")
        added, dropped = [], [k for k in cur if not k.startswith("_") and k not in names]
        for n in names:
            if n in cur:
                new[n] = cur[n]
            else:
                new[n] = "built into Claude Code (description not readable from disk; run /" + n + " to see it)"
                added.append(n)
        f.write_text(json.dumps(new, indent=1) + "\n", encoding="utf-8")
        print(f"BUILTINS {len(names)} listed; added {added or 'none'}; dropped {dropped or 'none'}; written {f}")
    elif cmd == "new":
        snap = lib.snapshot()
        old = json.loads(st.registry.read_text(encoding="utf-8")) if st.registry.is_file() else {}
        d = diff_registry(old, snap)
        print("FIRST_SNAPSHOT" if not old else "", {k: v[:20] for k, v in d.items()}, f"total {len(snap)}")
        st.registry.write_text(json.dumps(snap, indent=0, sort_keys=True), encoding="utf-8")
    elif cmd == "eval":
        global KINDS_ON
        KINDS_ON = "--no-kinds" not in flags
        probes = Path(probes_opt) if probes_opt else companion(root, "probes_heldout.tsv")
        if _opt(argv, "--before"):                          # v15: walk-forward memory cut (item 29)
            cut = time.mktime(time.strptime(_opt(argv, "--before"), "%Y-%m-%d"))
            base_rows = st.rows()
            st.rows = lambda: [r for r in base_rows if r.get("t", 0) < cut]
            lib.personal_rows, lib.personal_before = st.rows, cut   # the personal reading learns only from before the cut
            lib.phase_before = cut                              # 2026-10-25: the phase table too (M52)
        if "--armed" in flags:                              # v15: the tripwire first (item 42)
            arm = eval_armed(lib, st)
            print("ARMED " + json.dumps(arm))
        res = evaluate(lib, st, probes, fused="--plain" not in flags, infer="--no-infer" not in flags)   # v19
        detail = res.pop("_detail")
        code = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
        extra = {}
        if _opt(argv, "--null"):                            # v15: label-permutation null (item 6)
            extra["null"] = eval_null(detail, int(_opt(argv, "--null")))
        if "--ci" in flags:                                 # v15: bootstrap interval (item 14)
            extra["ci"] = eval_ci(res["vec"])
        if "--power" in flags:                              # v16 O3: the significance budget of this probe set
            from math import comb
            b = next(k for k in range(1, 60) if 2 * sum(comb(k, i) for i in range(0, 1)) / 2 ** k < 0.05)
            extra["power"] = {"n": res["n"], "min_clean_gain": b,
                              "note": f"on {res['n']} probes a change is DIFFERENT (McNemar p<0.05) only with >= {b} probes "
                                      f"won and none lost, or more when some are lost; a +1..+{b - 1} move is noise"}
        if _opt(argv, "--before"):
            extra["before"] = _opt(argv, "--before")
        extra["probes_sha"] = file_sha(probes)             # v17 (ruflo harness-frozen-eval): the answer key is pinned
        st.append({"kind": "EVAL", "t": int(time.time()), "code": code, "fused": "--plain" not in flags, **res, **extra})
        print(json.dumps({**{k: v for k, v in res.items() if k != "vec"}, **extra, "code": code}))
        if "--misses" in flags:                             # v18 (O9): name every probe the pool missed, and the top-3 misses
            for d in detail:
                g = set(d["good"])
                tag = "POOL_MISS" if not (g & set(d["pool"])) else ("TOP3_MISS" if not (g & set(d["m"])) else None)
                if tag:
                    print(f"  {tag:<9} {d['prompt'][:88]!r} | key {','.join(d['good'])} | top-3 {','.join(d['m'])}")
    elif cmd == "encore":
        print("\n".join(encore(st.rows(), pos[1] if len(pos) > 1 else None)))
    elif cmd == "reflect":
        print("\n".join(reflect(st.rows())))
    elif cmd == "selfcheck":
        sc = HERE / "selfcheck"
        comp = root / "skill-compose" / "skill_compose.py"
        import subprocess
        mods = json.loads((sc / "modules.json").read_text(encoding="utf-8"))
        pipe = json.loads((sc / "pipeline.json").read_text(encoding="utf-8"))
        pipe["inputs"] = {"skills": str(root), "maestro": str(HERE / "maestro.py"), "project": str(Path.cwd()),
                          "state": str(st.d), "maestro_dir": str(HERE)}
        work = st.d / "selfcheck"
        work.mkdir(exist_ok=True)
        (work / "modules.json").write_text(json.dumps(mods), encoding="utf-8")
        (work / "pipeline.json").write_text(json.dumps(pipe), encoding="utf-8")
        r = subprocess.run([sys.executable, str(comp), "run", str(work / "modules.json"), str(work / "pipeline.json"),
                            "--receipt", str(work / "receipt.json")], cwd=str(work))
        return r.returncode
    elif cmd == "trend":
        evs = [r for r in st.rows() if r.get("kind") == "EVAL"]
        for r in evs:
            print(time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["t"])), r["code"], r["probes"],
                  "fused" if r.get("fused") else "plain",
                  {k: v for k, v in r.items() if "@" in k},
                  *([f"null p={r['null'].get('p')} {r['null'].get('verdict')}"] if r.get("null") else []),
                  *([f"ci {r['ci'].get('lo')}-{r['ci'].get('hi')}"] if r.get("ci") else []))
        for r in st.rows():                                 # v15 item 13: ABLATE and NULL rows beside the evals
            if r.get("kind") == "ABLATE":
                print(time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["t"])), r.get("code"), r.get("probes"), "ABLATE",
                      {x["part"]: x["verdict"] for x in r.get("rows", [])})
        if "--compare" in flags:                            # v15 item 15: paired comparison of the last two with vectors
            withv = [r for r in evs if r.get("vec")]
            same = [r for r in withv if withv and r.get("probes") == withv[-1].get("probes") and r.get("fused") == withv[-1].get("fused")]
            if len(same) < 2:
                print("COMPARE: fewer than two evals with per-probe vectors on the same probes (run `eval` twice)")
            elif same[-2].get("probes_sha") and same[-1].get("probes_sha") and same[-2]["probes_sha"] != same[-1]["probes_sha"]:
                print(f"COMPARE_REFUSED: the probe file changed between the two evals (sha {same[-2]['probes_sha'][:8]} -> "
                      f"{same[-1]['probes_sha'][:8]}); a paired test needs the same answer key (v17 pinned eval set)")
            else:
                a, b = same[-2], same[-1]
                mc = mcnemar(a["vec"], b["vec"])
                print(f"COMPARE {a['code']} ({a.get('maestro@3')}) vs {b['code']} ({b.get('maestro@3')}): "
                      + (f"only-first {mc['a_only']}, only-second {mc['b_only']}, McNemar p {mc['p']}: {mc['verdict']}"
                         if mc.get("ok") else mc.get("why", "")))
    elif cmd == "modes":                                     # 2026-10-24: the modes the Maestro applies to itself
        print(_load(HERE / "modes.py", "modes").list_modes())
    elif cmd == "private":                                   # 2026-10-24: share nothing (the default) or allow `share`
        P = _load(HERE / "personal.py", "personal")
        arg = pos[1] if len(pos) > 1 else "status"
        if arg in ("on", "off"):
            P.set_private(st.d, arg == "on")
        print("PRIVATE: " + ("on. `share` writes nothing; your ratings stay on this machine and still teach your own Maestro."
                             if P.is_private(st.d) else "off. `share` may write a ratings file for you to send; nothing is sent by itself."))
    elif cmd == "personal":                                  # 2026-10-24: your own Maestro, learned from your ratings and use
        P = _load(HERE / "personal.py", "personal")
        if not meaning_ok():
            print("PERSONAL needs the meaning model (fastembed). Run this with the maestro-meaning venv python; see SHARING.md.")
            return 2
        rows = st.rows()
        if len(pos) > 1 and pos[1] == "eval":
            cut_s = _opt(argv, "--before") or "2026-10-16"
            cut = time.mktime(time.strptime(cut_s, "%Y-%m-%d"))
            probes = Path(probes_opt) if probes_opt else HERE / "evals" / "probes_walkforward_2026-10-16.tsv"
            M = _MEANING["mod"]
            res = P.eval_walkforward(M, M._word_ranker(), st.d, rows, M.read_probes(probes), cut, WEIGHTS.get("personal", 1.0))
            print(json.dumps({"before": cut_s, "probes": probes.name, **res}))
        else:
            print(P.report(_MEANING["mod"], st.d, rows))
    elif cmd == "share" and _load(HERE / "personal.py", "personal").is_private(st.d) and "--help" not in flags:
        print("PRIVATE: nothing written. Your Maestro is in private mode (the default), so `share` makes no file. "
              "`maestro.py private off` allows it; nothing is ever sent by itself.")
        return 0
    elif cmd in ("share", "intake", "community"):           # 2026-10-24 (the user): ratings from everyone who uses the skill
        return _load(HERE / "community.py", "maestro_community").run(argv[argv.index(cmd):], st, STATE, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12])
    elif cmd == "index":                                     # v15: the prepared index's state, or a forced rebuild
        return _load(HERE / "index.py", "maestro_index").cli_index(argv, lib, st, root, sys.modules[__name__])
    elif cmd in ("hindsight", "chain", "rehearse", "ablate", "why", "odds", "inverse", "repertoire", "anti", "tune",
                 "play", "whisper", "doctor", "welcome", "digest", "grade", "matrix", "suggest", "brief", "rerank", "thumbs"):   # v15/v16 modules
        mod = {"hindsight": "hindsight", "chain": "conduct", "rehearse": "conduct", "inverse": "inverse", "rerank": "rerank",
               "repertoire": "inverse", "anti": "inverse", "play": "concert", "whisper": "concert", "doctor": "concert", "thumbs": "concert",
               "welcome": "concert", "digest": "concert", "grade": "concert", "matrix": "concert", "suggest": "concert",
               "brief": "concert"}.get(cmd, "introspect")
        try:
            return _load(HERE / f"{mod}.py", mod).cli(argv[argv.index(cmd):], lib, st, root)
        except ImportError as exc:                            # v20: the research commands ship in skill-maestro-extras
            if type(exc).__name__ != "ExtraMissing":         # concert.py imports maestro as a second module: match by name
                raise
            print(f"{cmd}: {exc}")
            return 2
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
