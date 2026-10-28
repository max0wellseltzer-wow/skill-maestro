"""MODES and ASK FIRST (the user, 2026-10-24: "Skill maestro also probably needs dozens and dozens of diffrent modes it can
apply to itself for diffrent prompts" and "needs to ask clarifying questions before it does its job so it knows more
about what is needed for the job").

A mode is how the Maestro conducts one kind of prompt. Each mode says:
  when       what prompts it is for (matched by MEANING against the prompt, like a skill)
  picks      the least and most skills it chooses (inside 1 to 22)
  lean       a few words of purpose added to the meaning search, so the pool leans toward the mode's kind of skill
  direct     how the picks should be used (the order and the way, printed on the sheet)
  ask        the questions that matter most for this kind of job (asked only when the prompt does not answer them)
The best-matching mode is chosen automatically and printed with its closeness; `--mode NAME` forces one;
`maestro.py modes` lists them all. A prompt can wear a second mode when two match closely (shown, not applied).

ASK FIRST: before the picks run, the sheet lists up to four questions the prompt leaves open (the subject, what done
looks like, which part first, who reads it, what must not change, plus the mode's own), each with the default the
Maestro will use if nobody answers. Claude asks them in one AskUserQuestion call, then conducts.

YOUR OWN MODES (v20.0.10, prompt 10 of 2026-10-25: "can people customize it"): `modes.json` in the state folder (or the
file `MAESTRO_MODES` names) holds a list of modes in the same five-field shape (`ask` optional). They are embedded and
chosen by meaning exactly like the built-ins; a user mode with a built-in's name replaces it. `maestro.py modes add NAME
"when" [--picks lo-hi] [--lean "..."] [--direct "..."] [--ask "question=default"]` writes one, `modes remove NAME` drops
it, `modes template` prints the file shape. A bad entry is skipped and named on `maestro.py modes`; it never breaks a score.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

MODES: list[dict] = [
    {"name": "quick-answer", "when": "a short factual question, is there a skill or tool for X, a one-line lookup", "picks": [1, 2],
     "lean": "look up, find, answer", "direct": "Run the one pick, answer in a sentence, stop.", "ask": []},
    {"name": "choose-skills", "when": "which skills should I use, pick the best skills or tools for this job, skill selection", "picks": [3, 22],
     "lean": "skill finder, skill index, route, choose tools", "direct": "Name the job's purpose first, then the skills per phase; prove each on the subject before trusting it.",
     "ask": [("What job are the skills for?", "the task in this prompt")]},
    {"name": "build-feature", "when": "build, add or implement a new feature, command, script or tool in code", "picks": [3, 8],
     "lean": "build code, implement, tests, land", "direct": "Understand the code first, write tests that fail, build, verify, then land with the project's checks.",
     "ask": [("Which repository or folder?", "the current working project"), ("What must not change?", "public commands and saved data formats")]},
    {"name": "fix-bug", "when": "fix a bug, something is broken, wrong output, an error message, a failing test", "picks": [2, 6],
     "lean": "reproduce, debug, root cause, regression test", "direct": "Reproduce first, find the root cause, fix it, add the test that would have caught it.",
     "ask": [("What is the exact error or wrong output?", "the one in this prompt or the latest log")]},
    {"name": "debug-crash", "when": "a crash, a hang, a timeout, a process that died, a scheduled job that did not run", "picks": [2, 6],
     "lean": "forensics, logs, timeline, process, scheduler", "direct": "Collect the evidence (logs, exit codes, times) before guessing; name the cause with its evidence.",
     "ask": [("When did it last work?", "the last successful run in the logs")]},
    {"name": "code-review", "when": "review code, a diff, a pull request, check my changes for problems", "picks": [2, 6],
     "lean": "review, correctness, simplify, security", "direct": "Read the diff whole, then one lens at a time; report findings ranked by harm, with the line.",
     "ask": [("Which diff, branch or files?", "the uncommitted changes")]},
    {"name": "refactor", "when": "clean up, simplify, restructure or rename code without changing what it does", "picks": [2, 5],
     "lean": "simplify, refactor, same behaviour, tests", "direct": "Pin behaviour with tests first, change in small steps, keep the tests green.",
     "ask": []},
    {"name": "test-writing", "when": "write tests, improve test coverage, check that tests can fail", "picks": [2, 5],
     "lean": "tests, mutation, plant a fault, coverage", "direct": "Write the test, then plant a fault to prove it can fail.", "ask": []},
    {"name": "red-team", "when": "grill, attack, criticise, poke holes in, break or stress this plan, rule, protocol or claim", "picks": [3, 8],
     "lean": "red team, adversary, falsify, steelman, failure", "direct": "Steelman it first, then attack from several angles; every hole names how to see it.",
     "ask": [("What exactly should be attacked?", "the plan or claim named in the prompt")]},
    {"name": "decide", "when": "choose between options, should we do X or Y, make a decision, weigh tradeoffs", "picks": [3, 7],
     "lean": "decision, options, regret, tradeoff, counterfactual", "direct": "List the options, the cost of being wrong for each, then recommend one.",
     "ask": [("What are the options?", "the ones in the prompt plus doing nothing")]},
    {"name": "plan", "when": "make a plan, roadmap, next steps, how should we approach this big job", "picks": [3, 8],
     "lean": "plan, steps, dependencies, order, milestones", "direct": "Goal first, then steps in dependency order, each with how you will know it is done.",
     "ask": [("What does done look like?", "the outcome named in the prompt")]},
    {"name": "prioritize", "when": "what should I do first, rank these tasks, triage a backlog or open list", "picks": [2, 5],
     "lean": "triage, rank, prioritize, queue", "direct": "Rank by value over cost; say what to drop.", "ask": []},
    {"name": "explain", "when": "explain how or why something works, teach me, I do not understand this concept", "picks": [1, 4],
     "lean": "explain, teach, learn, plain words, analogy", "direct": "Plain words first, one example, then the detail; check understanding.",
     "ask": [("How much do you already know about it?", "a smart beginner")]},
    {"name": "how-to", "when": "how do I do an everyday computer task, step by step, click by click", "picks": [1, 3],
     "lean": "beginner steps, how to, click by click", "direct": "Numbered steps someone who never did it can follow, plus what to do if a step fails.", "ask": []},
    {"name": "write-doc", "when": "write a document, guide, README, policy, letter or notes for people to read", "picks": [2, 6],
     "lean": "document, write, plain terms, audience, docs", "direct": "Audience and purpose first, outline, draft, then a cold-reader pass.",
     "ask": [("Who will read it?", "the owner"), ("What format: doc, Markdown, Word, PDF?", "a Markdown file in the project")]},
    {"name": "report", "when": "status report, summary of what was done, receipts, catch me up, what happened", "picks": [2, 5],
     "lean": "receipt, report, status honesty, numbers check", "direct": "Lead with the outcome; every number from a file; say what is not done.", "ask": []},
    {"name": "slides", "when": "make a slide deck, presentation, PowerPoint", "picks": [1, 4],
     "lean": "slides, deck, pptx, presentation", "direct": "One idea per slide; build from the real numbers.",
     "ask": [("Who is the audience and how long is the talk?", "the owner, ten slides")]},
    {"name": "spreadsheet", "when": "spreadsheet, Excel, CSV, clean messy tabular data, formulas", "picks": [1, 4],
     "lean": "xlsx, csv, table, clean data", "direct": "Keep the source untouched; write a new file and show the changes.", "ask": []},
    {"name": "pdf-office", "when": "PDF, Word document, fill a form, merge or split files, office files", "picks": [1, 3],
     "lean": "pdf, docx, form, office file", "direct": "Work on a copy; show the result file.", "ask": [("Which file?", "the one named in the prompt")]},
    {"name": "data-analysis", "when": "analyse data, statistics, is this significant, find patterns, regression, distributions", "picks": [3, 8],
     "lean": "statistics, significance, bootstrap, regression, data hygiene", "direct": "Check the data first, state the question, pick the test, report the effect with its uncertainty.",
     "ask": [("Which data file or table?", "the data named in the prompt")]},
    {"name": "trading-research", "when": "trading strategy, backtest, edge, market signal, returns, drawdown, portfolio", "picks": [3, 10],
     "lean": "backtest, overfitting, walk forward, drawdown, deflated sharpe", "direct": "Pre-register the test, guard against overfitting, judge out of sample, report costs.",
     "ask": [("Which market, timeframe and data?", "the lane in the prompt with its usual data"), ("Paper or live?", "paper")]},
    {"name": "risk-safety", "when": "is this safe, live money, irreversible action, limits, guardrails before acting", "picks": [2, 6],
     "lean": "preflight, limits, blast radius, rollback, guard", "direct": "Name what could go wrong and the rollback before anything runs; ask before the irreversible step.",
     "ask": [("What must never happen?", "no real money moves and nothing is deleted")]},
    {"name": "forecast", "when": "predict, forecast, what will happen, probability of an event, odds", "picks": [2, 6],
     "lean": "forecast, base rate, calibration, odds", "direct": "Base rate first, then adjust; give a probability and how it will be checked.", "ask": []},
    {"name": "invent", "when": "invent something new, be creative, surprising idea, combine ideas, make a new skill", "picks": [4, 12],
     "lean": "invent, combine, analogy, creative, generate variants", "direct": "Go wide first (several unlike skills), then pick and build the best idea; mark fascination as not evidence.",
     "ask": []},
    {"name": "brainstorm", "when": "brainstorm, many ideas, options, what could we try", "picks": [4, 12],
     "lean": "brainstorm, divergent, lenses, perspectives", "direct": "Many ideas from different lenses, then cluster and rank.", "ask": []},
    {"name": "new-skill", "when": "create a new skill, write a SKILL.md, turn this workflow into a skill", "picks": [2, 6],
     "lean": "skill creator, skill foundry, findable, evals", "direct": "Check no skill already does it, write it, test it on a real subject, make it findable.", "ask": []},
    {"name": "skill-library", "when": "maintain the skill library, skill health, duplicates, broken skills, listing", "picks": [2, 8],
     "lean": "skill health, skills index, skill sync, retire", "direct": "Measure the library first; fix by evidence, never retire unasked.", "ask": []},
    {"name": "land-change", "when": "commit, push, merge, land a change, git branches, submodules", "picks": [2, 5],
     "lean": "land a change, git, pen, precommit, checks", "direct": "Run the project's checks, commit by name, push, verify the remote.",
     "ask": [("Which repository?", "the one with the change")]},
    {"name": "ops", "when": "scheduled tasks, services, machine health, disk, memory, processes, hooks", "picks": [2, 6],
     "lean": "scheduler, health, processes, hooks, windows", "direct": "Look at the machine's real state before changing it; one change at a time.", "ask": []},
    {"name": "security", "when": "security, secrets, keys, permissions, vulnerability, leak", "picks": [2, 6],
     "lean": "security, secret scan, permissions, audit", "direct": "Find and contain first; never print a secret.", "ask": []},
    {"name": "speed-cost", "when": "make it faster, cheaper, fewer tokens, performance, too slow, usage", "picks": [2, 5],
     "lean": "speed, measure first, token thrift, cost", "direct": "Measure before and after; report both numbers.", "ask": []},
    {"name": "read-the-person", "when": "angry or frustrated message, the person repeats an order, what does the person really want", "picks": [1, 4],
     "lean": "read as human, literal execution, take literally, frustration", "direct": "Take the order literally, do it fully, answer plainly; no excuses.", "ask": []},
    {"name": "finish-everything", "when": "continue, keep going, finish all the tasks, what is left, are we done", "picks": [2, 5],
     "lean": "open steps, finish everything, promise ledger, receipts", "direct": "List every open ask with evidence; keep working until each is done.", "ask": []},
    {"name": "web-browser", "when": "do something on a website, browse, click in the browser, read a web page", "picks": [1, 3],
     "lean": "browser, chrome, web page", "direct": "New tab, one action at a time, stop on dialogs.", "ask": [("Which site?", "the one named")]},
    {"name": "desktop-app", "when": "use a desktop program, look at my screen, click in an app", "picks": [1, 3],
     "lean": "computer use, desktop, screen", "direct": "Screenshot first; confirm before anything financial or irreversible.", "ask": []},
    {"name": "math", "when": "prove, derive, a math problem, a proof, a formula", "picks": [2, 6],
     "lean": "proof, derive, check, mathematics", "direct": "State what is to be shown, prove it, then check with a small case.", "ask": []},
    {"name": "research-web", "when": "research a topic across sources, compare options, literature, a market or industry", "picks": [2, 6],
     "lean": "deep research, sources, compare, synthesize", "direct": "Sources first, each claim cited, disagreements shown.",
     "ask": [("What decision will the research feed?", "the one in the prompt")]},
    {"name": "memory-notes", "when": "remember this, save a note, what did we decide before, past sessions", "picks": [1, 4],
     "lean": "memory, notes, transcripts, ledger", "direct": "Find the earlier record first; write one fact per note.", "ask": []},
]

REQUIRED = ("name", "when", "picks", "lean", "direct")
NAME_RX = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
TEMPLATE = [
    {"name": "mark-essays", "when": "mark or grade student essays, give feedback on a piece of writing against a rubric",
     "picks": [2, 5], "lean": "rubric, feedback, writing, plain words",
     "direct": "Read the rubric first, then each essay once whole; feedback names the sentence, not the student.",
     "ask": [["Which rubric?", "the one in the prompt or the course default"]]},
]


def user_path(state: Path | str | None) -> Path:
    env = os.environ.get("MAESTRO_MODES", "").strip()
    return Path(env) if env else Path(state or ".") / "modes.json"


def validate(m) -> list[str]:
    """The problems with one mode entry, empty when it is usable."""
    if not isinstance(m, dict):
        return ["not an object"]
    bad = [f"missing {k}" for k in REQUIRED if k not in m]
    if "name" in m and not (isinstance(m["name"], str) and NAME_RX.match(m["name"])):
        bad.append("name: lowercase letters, digits and dashes, 1-40 characters")
    for k in ("when", "lean", "direct"):
        if k in m and not (isinstance(m[k], str) and 3 <= len(m[k].strip()) <= 400):
            bad.append(f"{k}: a sentence of 3 to 400 characters")
    p = m.get("picks")
    if "picks" in m and not (isinstance(p, list) and len(p) == 2 and all(isinstance(x, int) for x in p) and 1 <= p[0] <= p[1] <= 22):
        bad.append("picks: [low, high] with 1 <= low <= high <= 22")
    a = m.get("ask", [])
    if not (isinstance(a, list) and len(a) <= 4 and all(isinstance(q, (list, tuple)) and len(q) == 2 and all(isinstance(s, str) and s.strip() for s in q) for q in a)):
        bad.append("ask: up to four [question, default] pairs of text")
    return bad


def load_user(state: Path | str | None) -> tuple[list[dict], list[str]]:
    """(usable user modes marked user=True, problems as 'file: ...' or 'entry N: ...' lines). A missing file is no problem."""
    p = user_path(state)
    if not p.is_file():
        return [], []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [], [f"{p}: unreadable ({e.__class__.__name__}); no user modes applied"]
    if isinstance(data, dict):
        data = data.get("modes", [])
    if not isinstance(data, list):
        return [], [f"{p}: expected a list of modes"]
    good, probs, seen = [], [], set()
    for i, m in enumerate(data, 1):
        bad = validate(m)
        if not bad and m["name"] in seen:
            bad = ["name used twice in the file"]
        if bad:
            probs.append(f"entry {i} ({m.get('name', '?') if isinstance(m, dict) else '?'}): " + "; ".join(bad))
            continue
        seen.add(m["name"])
        good.append({"name": m["name"], "when": m["when"].strip(), "picks": list(m["picks"]), "lean": m["lean"].strip(),
                     "direct": m["direct"].strip(), "ask": [(q, d) for q, d in m.get("ask", [])], "user": True})
    return good, probs


def all_modes(state: Path | str | None) -> list[dict]:
    """Built-ins, then the user's; a user mode with a built-in's name takes its place."""
    user, _ = load_user(state)
    byname = {m["name"]: m for m in user}
    out = [byname.pop(m["name"], m) for m in MODES]
    return out + [byname[n] for n in sorted(byname)]


def _write_user(state, modes: list[dict]) -> Path:
    p = user_path(state)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [{k: (v if k != "ask" else [list(q) for q in v]) for k, v in m.items() if k != "user"} for m in modes]
    p.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def add(state, name: str, when: str, picks=None, lean: str | None = None, direct: str | None = None, ask=None) -> Path:
    """Write or replace one user mode. Defaults: picks 2-6, lean = the first words of `when`, direct = a plain line."""
    m = {"name": name, "when": when, "picks": list(picks) if picks else [2, 6],
         "lean": lean or " ".join(re.findall(r"[a-z]+", when.lower())[:6]),
         "direct": direct or "Run the picks in order on the real subject; judge each before trusting it.",
         "ask": [tuple(q) for q in (ask or [])]}
    bad = validate({**m, "ask": [list(q) for q in m["ask"]]})
    if bad:
        raise ValueError("; ".join(bad))
    cur, _ = load_user(state)
    return _write_user(state, [x for x in cur if x["name"] != name] + [m])


def remove(state, name: str) -> bool:
    cur, _ = load_user(state)
    keep = [x for x in cur if x["name"] != name]
    if len(keep) == len(cur):
        return False
    _write_user(state, keep)
    return True


def template() -> str:
    return json.dumps(TEMPLATE, indent=1)


GENERIC = {
    "subject": ("What exactly should the skills work on: which file, folder, data or page?", "the files this session is working on"),
    "done": ("What does done look like?", "the outcome the prompt names, fully finished"),
    "order": ("Which part first, or all of it in order?", "all of it, in the order written"),
    "limits": ("Is there anything that must not change or be touched?", "nothing outside the named work"),
}
NO_SUBJECT = {"quick-answer", "read-the-person", "finish-everything", "explain", "how-to", "brainstorm", "invent",
              "memory-notes", "forecast", "math", "research-web", "choose-skills"}   # the subject is the conversation or the idea
NO_DONE = {"quick-answer", "explain", "how-to", "read-the-person", "finish-everything", "brainstorm", "memory-notes"}
SUBJECT_RX = re.compile(r"([A-Za-z]:[\\/]|\.(py|md|json|jsonl|csv|tsv|toml|txt|xlsx|pdf|docx|pptx|html)\b|https?://|\b[\w-]+/[\w./-]+|`[^`]+`|\bGT\d+\b)")
DONE_RX = re.compile(r"\b(so that|until|done when|should (?:be|show|print|pass)|must|goal|target|pass(?:es)?|by \w+day)\b", re.IGNORECASE)
RISKY_RX = re.compile(r"\b(delete|remove|push|merge|live|real money|deploy|overwrite|rename|migrate|drop|reset)\b", re.IGNORECASE)


def _texts_key(modes: list[dict]) -> str:
    return hashlib.sha256(json.dumps([[m["name"], m["when"]] for m in modes]).encode()).hexdigest()[:12]


def select(meaning, prompt: str, state: Path, force: str | None = None) -> dict | None:
    """{mode, sim, second, second_sim}: the mode whose `when` means most what the prompt means (or the forced one)."""
    modes = all_modes(state)                              # v20.0.10: built-ins plus the person's own (modes.json)
    byname = {m["name"]: m for m in modes}
    if force:
        if force not in byname:
            raise KeyError(f"no mode {force!r}; `maestro.py modes` lists them")
        return {"mode": byname[force], "sim": 1.0, "second": None, "second_sim": 0.0, "forced": True}
    try:
        import numpy as np
    except ImportError:                                   # v20: no numpy means no meaning model here: no mode (the caller's None)
        return None
    p = Path(state) / f"modes_{_texts_key(modes)}.npy"   # the key covers names and `when` texts: a new user mode re-embeds
    if p.is_file():
        mv = np.load(p)
    else:
        mv = meaning.embed_docs([m["name"].replace("-", " ") + ": " + m["when"] for m in modes])
        if os.environ.get("MAESTRO_NO_LEDGER") != "1":   # v20.1.6: --no-ledger writes nothing, this file included
            p.parent.mkdir(parents=True, exist_ok=True)
            np.save(p, mv)
    q = meaning.embed_queries([prompt[:2000]])[0]
    sims = mv @ q
    order = list(np.argsort(-sims))
    a, b = order[0], order[1]
    return {"mode": modes[a], "sim": round(float(sims[a]), 3), "second": modes[b] if sims[a] - sims[b] < 0.02 else None,
            "second_sim": round(float(sims[b]), 3), "forced": False}


def clamp(n: int, mode: dict) -> int:
    lo, hi = mode.get("picks", [1, 22])
    return max(1, min(22, max(lo, min(hi, n))))


def ask_first(prompt: str, mode: dict | None, subject: str | None = None, k: int = 4) -> list[dict]:
    """The questions the prompt leaves open, most important first, each with the default used if nobody answers."""
    qs: list[tuple[str, str, str]] = []
    if not subject and not SUBJECT_RX.search(prompt) and not (mode and mode["name"] in NO_SUBJECT):
        qs.append(("subject", *GENERIC["subject"]))
    if mode:
        for q, d in mode.get("ask", []):
            if q.lower().startswith(("which file", "which data", "which repository", "which diff")) and (subject or SUBJECT_RX.search(prompt)):
                continue
            qs.append(("mode", q, d))
    sents = [s for s in re.split(r"(?<=[.?!;])\s+|\n+", prompt.strip()) if len(s.split()) >= 3]
    if len(sents) >= 3:
        qs.append(("order", *GENERIC["order"]))
    if not DONE_RX.search(prompt) and (not mode or mode["name"] not in NO_DONE):
        qs.append(("done", *GENERIC["done"]))
    if RISKY_RX.search(prompt):
        qs.append(("limits", *GENERIC["limits"]))
    seen, out = set(), []
    for kind, q, d in qs:
        if q not in seen:
            seen.add(q)
            out.append({"kind": kind, "question": q, "default": d})
    return out[:k]


def render(sel: dict, qs: list[dict]) -> list[str]:
    m = sel["mode"]
    how = "forced" if sel.get("forced") else f"closeness {sel['sim']:.2f}"
    L = [f"MODE {m['name']} ({how}): {m['when']}"
         + (f"  | also close: {sel['second']['name']}" if sel.get("second") else ""),
         f"  HOW TO USE THE PICKS: {m['direct']}"]
    if qs:
        L.append("ASK FIRST (one AskUserQuestion call; if nobody can answer, go on with the defaults and say so):")
        L += [f"  Q{i}. {q['question']}   default: {q['default']}" for i, q in enumerate(qs, 1)]
    return L


def list_modes(state: Path | str | None = None) -> str:
    modes = all_modes(state) if state is not None else list(MODES)
    _, probs = load_user(state) if state is not None else ([], [])
    L = [f"{'*' if m.get('user') else ' '} {m['name']:<18} picks {m['picks'][0]}-{m['picks'][1]:<3} {m['when']}" for m in modes]
    n_user = sum(1 for m in modes if m.get("user"))
    L.append(f"{len(modes)} modes ({n_user} yours, marked *). Chosen by meaning per prompt; `score ... --mode NAME` forces one.")
    if state is not None:
        L.append(f"Yours live in {user_path(state)}: `modes add NAME \"when\" [--picks lo-hi] [--lean ...] [--direct ...] "
                 f"[--ask \"question=default\"]`, `modes remove NAME`, `modes template`.")
    L += [f"  SKIPPED {p}" for p in probs]
    return "\n".join(L)


def _selftest() -> bool:
    ok = {}
    names = [m["name"] for m in MODES]
    ok["modes: dozens, unique names, picks inside 1-22"] = (
        len(MODES) >= 30 and len(set(names)) == len(names) and all(1 <= m["picks"][0] <= m["picks"][1] <= 22 for m in MODES))
    ok["clamp keeps a mode's range"] = clamp(20, {"picks": [1, 2]}) == 2 and clamp(1, {"picks": [3, 8]}) == 3
    q1 = ask_first("fix it", MODES[names.index("fix-bug")])
    ok["ask: a prompt with no subject asks for one first"] = q1 and q1[0]["kind"] == "subject"
    q2 = ask_first("fix the failing test in tv-core/tests/test_x.py so that it passes", MODES[names.index("fix-bug")])
    ok["ask: a named file and a done-line are not asked again"] = all(q["kind"] not in ("subject", "done") for q in q2)
    q3 = ask_first("delete the old branches", None)
    ok["ask: a risky verb asks what must not change"] = any(q["kind"] == "limits" for q in q3)
    ok["ask: at most four questions, each with a default"] = all(len(ask_first(p, m)) <= 4 and all(q["default"] for q in ask_first(p, m))
                                                                for p in ("a. b c d. e f g. h i j.", "x") for m in MODES)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        st = Path(td)
        ok["user modes: no file means built-ins only, no problems"] = all_modes(st) == MODES and load_user(st) == ([], [])
        add(st, "mark-essays", "mark or grade student essays against a rubric", picks=[2, 5], ask=[("Which rubric?", "the course default")])
        add(st, "fix-bug", "fix a bug my way", direct="Reproduce, then fix.")
        am = all_modes(st)
        byname = {m["name"]: m for m in am}
        ok["user modes: added one appends, same-named one replaces the built-in in place"] = (
            len(am) == len(MODES) + 1 and am[-1]["name"] == "mark-essays" and am[-1]["user"] and byname["fix-bug"]["direct"] == "Reproduce, then fix."
            and [m["name"] for m in am[:len(MODES)]] == [m["name"] for m in MODES])
        ok["user modes: the embedding cache key changes with them"] = _texts_key(am) != _texts_key(MODES)
        ok["user modes: forced select finds a user mode and ask_first reads its questions"] = (
            select(None, "x", st, force="mark-essays")["mode"]["user"] and any(q["question"] == "Which rubric?" for q in ask_first("mark these", byname["mark-essays"])))
        ok["user modes: listing marks them * and names the file"] = "* mark-essays" in list_modes(st) and "modes.json" in list_modes(st)
        p = user_path(st)
        rows = json.loads(p.read_text(encoding="utf-8")) + [{"name": "Bad Name", "when": "x"}, {"name": "ok-mode", "when": "fine words here", "picks": [5, 1], "lean": "a b c", "direct": "do it"}]
        p.write_text(json.dumps(rows), encoding="utf-8")
        good, probs = load_user(st)
        ok["user modes: a bad entry is skipped and named, the good ones still load"] = len(good) == 2 and len(probs) == 2 and "picks" in probs[1] and "SKIPPED" in list_modes(st)
        p.write_text("{not json", encoding="utf-8")
        ok["user modes: an unreadable file is reported, never raised"] = load_user(st)[0] == [] and "unreadable" in load_user(st)[1][0] and all_modes(st) == MODES
        p.write_text(template(), encoding="utf-8")
        ok["user modes: the template loads clean; remove drops by name"] = load_user(st)[1] == [] and remove(st, "mark-essays") and not remove(st, "mark-essays") and all_modes(st) == MODES
        try:
            add(st, "no spaces here", "when text")
            ok["user modes: add refuses a bad name"] = False
        except ValueError:
            ok["user modes: add refuses a bad name"] = True
    bad = [k for k, v in ok.items() if not v]
    print(f"modes selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
