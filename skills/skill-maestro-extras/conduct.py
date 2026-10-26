"""conduct - the conductor writes the score and holds the rehearsal (v15, 2026-10-22).

The Maestro named the players; it never wrote the score. `chain` orders a run's picks into a pipeline from what each
card says the skill takes and gives (input kind -> output kinds), inside the work's phases (UNDERSTAND -> BUILD ->
VERIFY -> LAND), and prints every handoff and every gap; --write emits skill-compose files so the chain is
type-checked and runs with a sha256 receipt per step. `rehearse` runs every pick's own probe on the real subject at
once and writes the same TRY rows `try` writes, so step 3 of the protocol (prove each pick on the subject) costs one
command instead of one hand-typed command per pick: on 2026-10-22 only 2 of the last 20 score runs had any pick
tried at all.

    python maestro.py chain RUN [--subject FILE] [--write DIR]
    python maestro.py rehearse RUN --subject FILE [--workers N] [--timeout S] [--only a,b]
    python conduct.py --selftest

A step's input kind comes from its card (cards/cards.jsonl: input.kind), else from the words of its description;
its output kinds are read from the card's output line by the OUT_KINDS table (a heuristic: the chain prints what it
read, and the judge decides). A handoff is a step that takes a kind an earlier step gives and the subject is not of
that kind; a GAP is a step that takes a kind nobody gives. Workers default to dial M36 (2 on a 3.9 GB PC).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _core_dir() -> Path:
    """v20: this module ships in skill-maestro-extras; maestro.py is beside it, at MAESTRO_HOME, or in the sibling skill-maestro."""
    env = os.environ.get("MAESTRO_HOME")
    for d in (HERE, Path(env).expanduser() if env else None, HERE.parent / "skill-maestro"):
        if d is not None and (d / "maestro.py").is_file():
            return d
    return HERE

sys.path.insert(0, str(HERE))


def _maestro():
    main = sys.modules.get("__main__")
    if main is not None and Path(getattr(main, "__file__", "") or "").name == "maestro.py":
        return main
    if str(_core_dir()) not in sys.path:
        sys.path.insert(0, str(_core_dir()))
    import maestro
    return maestro


M = _maestro()

PHASE_IDX = {p: i for i, p in enumerate(M.PHASE_ORDER)}
NO_PHASE = 1.5                                   # a pick with no phase word sits between BUILD and VERIFY
OUT_KINDS = [   # what a card's output line says the skill gives; every matching kind is kept, TEXT when none
    ("TABLE", re.compile(r"\b(table|rows?|per (?:pair|step|skill|item|row|file)|tsv|csv|matrix|columns?)\b", re.I)),
    ("LOG", re.compile(r"\b(jsonl|ledger|receipt|append-only|log)\b", re.I)),
    ("GRAPH", re.compile(r"\b(graph|network|nodes?|edges?|waves?|topolog\w*|dependenc\w*)\b", re.I)),
    ("PLAN", re.compile(r"\b(plan|cards?)\b", re.I)),
    ("CODE", re.compile(r"\b(patch|diff|scaffold\w*|module|test file|\.py)\b", re.I)),
    ("SERIES", re.compile(r"\b(series|curve|signal|returns)\b", re.I)),
    ("CLAIM", re.compile(r"\b(verdict|pass(?:es|ed)?|fail(?:s|ed)?|match|mismatch|warn\w*|refused|reject\w*)\b", re.I)),
]
DEFAULT_OUT = "TEXT"
NO_INPUT = ("NONE", None, "")


def guess_kind(desc: str) -> str:
    for k, rx in M.KINDS.items():
        if rx.search(desc or ""):
            return k
    return "TEXT"


def out_kinds(text: str) -> list[str]:
    return [k for k, rx in OUT_KINDS if rx.search(text or "")] or [DEFAULT_OUT]


def step_of(name: str, lib, cards: dict) -> dict:
    card = cards.get(name) or {}
    desc = lib.desc.get(name, "")
    md = lib.skill_md(name)
    roles = M.roles_of(name, desc)
    phase = next((r for r in M.PHASE_ORDER if r in roles), None)
    takes = (card.get("input") or {}).get("kind") or guess_kind(desc)
    return {"name": name, "phase": phase, "takes": takes, "gives": out_kinds(card.get("output", "")),
            "probe_t": card.get("probe") or None, "skill_dir": str(md.parent), "carded": bool(card),
            "first_cmd": M.first_command(md) if md.is_file() else None}


def fill(probe_t: str, skill_dir: str, subject) -> list[str]:
    """Split the template first (it holds no Windows path yet), then fill the placeholders token by token: a
    backslash path never meets shlex."""
    toks = shlex.split(probe_t)
    return [t.replace("{skill_dir}", skill_dir).replace("{subject}", str(subject) if subject else "{subject}") for t in toks]


def order_steps(steps: list[dict], subject_kind: str) -> dict:
    """Pure. Handoff edges A->B when B takes a kind A gives and that kind is not the subject's own (a step that reads
    the subject needs nobody before it). Kahn's order, ties by phase then by the sheet's rank; a cycle is cut at its
    earliest step and the dropped edges are reported; a GAP is a step that takes a kind nobody gives."""
    idx = {s["name"]: i for i, s in enumerate(steps)}
    edges = [(a["name"], b["name"], b["takes"]) for b in steps if b["takes"] not in NO_INPUT and b["takes"] != subject_kind
             for a in steps if a is not b and b["takes"] in a["gives"]]
    indeg = {s["name"]: 0 for s in steps}
    outs: dict[str, list] = {s["name"]: [] for s in steps}
    for a, b, k in edges:
        indeg[b] += 1
        outs[a].append((b, k))

    def key(name: str):
        s = steps[idx[name]]
        return (PHASE_IDX.get(s["phase"], NO_PHASE), idx[name])

    left, order, dropped = set(indeg), [], []
    while left:
        ready = [x for x in left if indeg[x] == 0]
        if not ready:
            x = min(left, key=key)
            dropped += [(a, b, k) for a, b, k in edges if b == x and a in left]
            indeg[x] = 0
            ready = [x]
        x = min(ready, key=key)
        left.remove(x)
        order.append(x)
        for b, _ in outs[x]:
            if b in left:
                indeg[b] -= 1
    pos = {n: i for i, n in enumerate(order)}
    handoffs = [(a, b, k) for a, b, k in edges if (a, b, k) not in dropped and pos[a] < pos[b]]
    fed = {b for _, b, _ in handoffs}
    gaps = [s["name"] for s in steps if s["takes"] not in NO_INPUT and s["takes"] != subject_kind and s["name"] not in fed]
    return {"order": order, "handoffs": handoffs, "gaps": gaps, "dropped": dropped}


def render_chain(run: str, steps: list[dict], res: dict, subject_kind: str, subject) -> str:
    by = {s["name"]: s for s in steps}
    L = [f"SCORE for run {run}: {len(steps)} step(s), subject {subject or '(none named)'} read as {subject_kind}"]
    for i, n in enumerate(res["order"], 1):
        s = by[n]
        cmd = (" ".join(fill(s["probe_t"], s["skill_dir"], subject)) if s["probe_t"] else s["first_cmd"]
               or f"invoke /{n} (no script; it has no card probe)")
        L.append(f"  {i}. {n:<28} [{s['phase'] or '-':<10}] takes {s['takes']:<7} -> gives {','.join(s['gives'])}")
        L.append(f"       run: {cmd[:120]}")
    for a, b, k in res["handoffs"]:
        L.append(f"HANDOFF {a} -> {b} ({k}): {b} reads what {a} printed")
    for g in res["gaps"]:
        L.append(f"GAP: {g} takes {by[g]['takes']}; no earlier step gives one and the subject is a {subject_kind}: give "
                 f"it a {by[g]['takes']} by hand, or drop it")
    for a, b, k in res["dropped"]:
        L.append(f"CYCLE CUT: {a} -> {b} ({k}) dropped so the order is finite")
    L.append(f"NEXT: `maestro.py rehearse {run} --subject FILE` runs every probe at once; `chain {run} --write DIR` "
             "makes it a skill-compose pipeline (type-checked, a sha256 receipt per step)")
    return "\n".join(L)


def write_compose(steps: list[dict], res: dict, subject_kind: str, subject, out_dir: Path) -> tuple[Path, Path]:
    """skill-compose's files: a module per step (its probe as argv with {KIND} placeholders, captured to NAME.txt;
    MANUAL when it has no probe), the subject as the one input, the chain as the steps."""
    by = {s["name"]: s for s in steps}
    fed = {b: k for _, b, k in res["handoffs"]}
    mods = {}
    for n in res["order"]:
        s = by[n]
        takes = s["takes"] if s["takes"] not in NO_INPUT else subject_kind
        consumes = [fed.get(n, takes)]
        if s["probe_t"]:
            argv = [t.replace("{skill_dir}", s["skill_dir"]).replace("{subject}", "{" + consumes[0] + "}")
                    for t in shlex.split(s["probe_t"])]
            mods[n] = {"consumes": consumes, "produces": list(s["gives"]), "run": argv, "capture": True,
                       "out": f"{n}.txt", "ok_exits": [0, 1, 2]}
        else:
            mods[n] = {"consumes": consumes, "produces": list(s["gives"]), "run": "MANUAL"}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mp, pp = out_dir / "modules.json", out_dir / "pipeline.json"
    mp.write_text(json.dumps({"modules": mods}, indent=1), encoding="utf-8")
    pp.write_text(json.dumps({"inputs": {subject_kind: str(subject or "")}, "steps": list(res["order"]),
                              "max_depth": max(3, len(res["order"]))}, indent=1), encoding="utf-8")
    return mp, pp


def echoes(out: str, subject_text: str, skill_text: str) -> int:
    """How many of the subject's own words (5+ letters, not in the skill's SKILL.md) the output repeats: 0 means
    the output holds nothing of the subject, weak evidence it never read it."""
    words = lambda t: set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", t or ""))  # noqa: E731
    subj = words(subject_text) - words(skill_text)
    return len(subj & words(out))


def rehearse(run_row: dict, lib, cards: dict, subject: Path, st, workers: int = 2, timeout: int = 120,
             only: set | None = None) -> tuple[list[dict], list[str]]:
    steps = [step_of(n, lib, cards) for n in run_row.get("chosen", []) if not only or n in only]
    noprobe = [s["name"] for s in steps if not s["probe_t"]]
    jobs = []
    for s in steps:                                   # v16: a probe with an unfilled <placeholder> cannot run honestly
        if not s["probe_t"]:
            continue
        hole = next((t for t in fill(s["probe_t"], s["skill_dir"], subject) if t.startswith("<") and t.endswith(">")), None)
        if hole:
            noprobe.append(f"{s['name']} (probe needs {hole}: run it by hand with `maestro.py try`)")
        else:
            jobs.append(s)
    text = Path(subject).read_text(encoding="utf-8", errors="replace") if Path(subject).is_file() else ""

    def run(s: dict):
        argv = fill(s["probe_t"], s["skill_dir"], subject)
        exe = [sys.executable if argv[0] in ("python", "py", "python3") else argv[0], *argv[1:]]
        t0 = time.time()
        try:
            r = subprocess.run(exe, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            out, code = r.stdout + r.stderr, r.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            out, code = f"{type(exc).__name__}: {exc}", -1
        return s, argv, out, code, round(time.time() - t0, 1)

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        results = list(ex.map(run, jobs))
    rows = []
    for s, argv, out, code, secs in results:
        lines = out.splitlines()
        md = Path(s["skill_dir"]) / "SKILL.md"
        echo = echoes(out, text, md.read_text(encoding="utf-8", errors="replace") if md.is_file() else "")
        st.append({"kind": "TRY", "run": run_row["run"], "skill": s["name"], "cmd": argv, "exit": code, "lines": len(lines),
                   "head": out[:600], "out": out[:8000], "t": int(time.time()), "via": "rehearse", "secs": secs})
        first = next((ln.strip() for ln in lines if ln.strip()), "")
        rows.append({"skill": s["name"], "exit": code, "secs": secs, "lines": len(lines), "echo": echo, "first": first})
    return rows, noprobe


def render_rehearsal(run: str, subject, rows: list[dict], noprobe: list[str], workers: int) -> str:
    L = [f"REHEARSAL run {run} on {subject}: {len(rows)} probe(s), {workers} at a time",
         f"  {'skill':<28} {'exit':>4} {'secs':>6} {'lines':>5} {'echo':>4}  first line"]
    for r in sorted(rows, key=lambda r: r["skill"]):
        L.append(f"  {r['skill']:<28} {r['exit']:>4} {r['secs']:>6} {r['lines']:>5} {r['echo']:>4}  {r['first'][:70]}")
    if noprobe:
        L.append("NO_PROBE: " + ", ".join(noprobe) + "  (no card probe: run by hand with `try`, or invoke the skill)")
    L.append(f"NEXT: judge each on the TASK, not the exit code: `maestro.py fit {run} <skill> works|misfit \"why\"`. "
             "echo 0 = the output repeats none of the subject's own words (it may not have read it).")
    return "\n".join(L)


# --- command line ----------------------------------------------------------------------------------------------------

def _val(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def _run_row(st, run: str) -> dict | None:
    rows = [r for r in st.rows() if r.get("kind") == "SCORE"]
    if run == "last":
        return rows[-1] if rows else None
    return next((r for r in rows if r.get("run") == run), None)


def cli(argv: list[str], lib, st, root: Path) -> int:
    """argv starts with 'chain' or 'rehearse'."""
    sub = argv[0]
    run = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "last"
    row = _run_row(st, run)
    if row is None:
        print(f"RUN_UNKNOWN: no score run {run!r} in the ledger; use the run id the score sheet printed, or `last`")
        return 3
    cards = M.load_cards()
    subject = _val(argv, "--subject")
    steps = [step_of(n, lib, cards) for n in row.get("chosen", [])]
    if sub == "chain":
        sk = (_val(argv, "--kind") or "").upper() or guess_kind(row.get("task", "")) or "TEXT"
        res = order_steps(steps, sk)
        print(render_chain(row["run"], steps, res, sk, subject))
        if _val(argv, "--write"):
            mp, pp = write_compose(steps, res, sk, subject, Path(_val(argv, "--write")))
            comp = root / "skill-compose" / "skill_compose.py"
            print(f"WROTE {mp} and {pp}" + (f"\n  check: python \"{comp}\" check \"{mp}\" \"{pp}\"" if comp.is_file() else ""))
        return 0
    if sub == "rehearse":
        if not subject or not Path(subject).is_file():
            print("REHEARSE_REFUSED: --subject FILE must name the real thing the task is about (a file that exists)")
            return 2
        workers = int(_val(argv, "--workers", getattr(M, "REHEARSE_WORKERS", 2)))
        only = set(_val(argv, "--only", "").split(",")) - {""} or None
        if "--dry" in argv:                                 # v15 item 16: print the commands, run nothing, write nothing
            print(f"REHEARSE --dry for run {row['run']} on {subject}: nothing runs, nothing is written")
            for s in steps:
                if only and s["name"] not in only:
                    continue
                print(f"  {s['name']:<28} " + (" ".join(fill(s["probe_t"], s["skill_dir"], subject)) if s.get("probe_t")
                                               else "(no probe: nothing would run)"))
            return 0
        rows, noprobe = rehearse(row, lib, cards, Path(subject), st, workers=workers,
                                 timeout=int(_val(argv, "--timeout", 120)), only=only)
        print(render_rehearsal(row["run"], subject, rows, noprobe, workers))
        return 0
    print(__doc__)
    return 2


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    import tempfile
    ok: dict[str, bool] = {}
    # 1. the pure ordering
    steps = [{"name": "checker", "phase": "VERIFY", "takes": "PLAN", "gives": ["CLAIM"]},
             {"name": "stats", "phase": None, "takes": "TABLE", "gives": ["CLAIM"]},
             {"name": "lens", "phase": "UNDERSTAND", "takes": "PLAN", "gives": ["TABLE"]},
             {"name": "grapher", "phase": "BUILD", "takes": "GRAPH", "gives": ["TEXT"]}]
    res = order_steps(steps, "PLAN")
    ok["phases order the subject readers: UNDERSTAND before VERIFY"] = res["order"].index("lens") < res["order"].index("checker")
    ok["a handoff puts the giver before the taker (lens TABLE -> stats)"] = \
        ("lens", "stats", "TABLE") in res["handoffs"] and res["order"].index("lens") < res["order"].index("stats")
    ok["a step that takes a kind nobody gives is a GAP"] = res["gaps"] == ["grapher"]
    cyc = order_steps([{"name": "a", "phase": None, "takes": "Y", "gives": ["X"]},
                       {"name": "b", "phase": None, "takes": "X", "gives": ["Y"]}], "PLAN")
    ok["a cycle is cut, both steps stay, the cut is reported"] = len(cyc["order"]) == 2 and cyc["dropped"]
    ok["output kinds are read from the card's output line"] = \
        out_kinds("per pair x attribute: a table of rows with a VERDICT") == ["TABLE", "CLAIM"] and out_kinds("") == ["TEXT"]
    ok["fill keeps a Windows path whole"] = fill("python {skill_dir}/t.py {subject}", "C:\\u\\s", "C:\\p\\plan.md") == \
        ["python", "C:\\u\\s/t.py", "C:\\p\\plan.md"]
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        root = td / "skills"
        for name, desc in [("lens", "Read a plan and list its steps as a table. Use this whenever the user wants a map."),
                           ("stats", "Measure a table and test it. Use this whenever the user wants a check."),
                           ("checker", "Verify a plan against rules. Use this whenever the user asks for an audit.")]:
            (root / name).mkdir(parents=True)
            (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n", encoding="utf-8")
        (root / "lens" / "echo.py").write_text(
            "import sys\nprint('first line:', open(sys.argv[1], encoding='utf-8').readline().strip())\n", encoding="utf-8")
        (root / "stats" / "boom.py").write_text("import sys\nprint('stats cannot read this')\nsys.exit(3)\n", encoding="utf-8")
        cards = {"lens": {"input": {"kind": "PLAN"}, "output": "a table of rows per step", "probe": "python {skill_dir}/echo.py {subject}"},
                 "stats": {"input": {"kind": "TABLE"}, "output": "PASS or FAIL verdict", "probe": "python {skill_dir}/boom.py {subject}"}}
        lib = M.Library(root, everything=False)
        st = M.State(td / "state")
        subject = td / "plan.md"
        subject.write_text("zebrafish plan step one\nstep two\n", encoding="utf-8")
        row = {"run": "r1", "chosen": ["checker", "stats", "lens"], "task": "audit the plan"}
        steps2 = [step_of(n, lib, cards) for n in row["chosen"]]
        res2 = order_steps(steps2, "PLAN")
        ok["steps from cards and descriptions: kinds, phases and probes"] = \
            res2["order"][0] == "lens" and ("lens", "stats", "TABLE") in res2["handoffs"] and \
            next(s for s in steps2 if s["name"] == "checker")["phase"] == "VERIFY"
        mp, pp = write_compose(steps2, res2, "PLAN", subject, td / "compose")
        mods = json.loads(mp.read_text(encoding="utf-8"))["modules"]
        ok["compose files: the taker's placeholder is the giver's type, no probe = MANUAL"] = \
            "{TABLE}" in mods["stats"]["run"] and mods["checker"]["run"] == "MANUAL" and "{PLAN}" in mods["lens"]["run"]
        comp = HERE.parent / "skill-compose" / "skill_compose.py"
        if comp.is_file():
            sc = M._load(comp, "skill_compose")
            chk = sc.check(mods, json.loads(pp.read_text(encoding="utf-8")))
            ok["skill-compose type-checks the written chain with no error"] = not chk.get("errors")
        rows, noprobe = rehearse(row, lib, cards, subject, st, workers=2, timeout=60)
        by = {r["skill"]: r for r in rows}
        ok["rehearse runs every probe at once: exits recorded"] = by["lens"]["exit"] == 0 and by["stats"]["exit"] == 3
        ok["echo counts the subject's own words in the output (lens 1+, stats 0)"] = by["lens"]["echo"] >= 1 and by["stats"]["echo"] == 0
        ok["a pick without a probe is NO_PROBE"] = noprobe == ["checker"]
        tries = [r for r in st.rows() if r.get("kind") == "TRY"]
        ok["one TRY row per probe, in try's shape (fit accepts it)"] = \
            len(tries) == 2 and all(set(r) >= {"run", "skill", "cmd", "exit", "lines", "head", "out", "t"} for r in tries)
        text = render_rehearsal("r1", subject, rows, noprobe, 2)
        ok["the table names the next move: fit"] = "fit r1" in text and "NO_PROBE: checker" in text
        ok["an unfilled <placeholder> in a probe is detected before anything runs"] = \
            next((t for t in fill("python {skill_dir}/a.py --test <test_file.py> {subject}", "D", "S")
                  if t.startswith("<") and t.endswith(">")), None) == "<test_file.py>" \
            and next((t for t in fill("python {skill_dir}/a.py {subject}", "D", "S") if t.startswith("<")), None) is None
        text2 = render_chain("r1", steps2, res2, "PLAN", subject)
        ok["the score prints steps, handoffs and the next move"] = "HANDOFF lens -> stats" in text2 and "rehearse r1" in text2
    ok = {k: bool(v) for k, v in ok.items()}
    print(f"conduct selftest: {sum(ok.values())}/{len(ok)} " + ("PASS" if all(ok.values()) else "FAIL"))
    for k, v in ok.items():
        if not v:
            print(f"  FAIL {k}")
    return all(ok.values())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(M.main(sys.argv[1:]))
