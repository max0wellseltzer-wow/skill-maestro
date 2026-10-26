"""introspect - the Maestro audits its own parts and forecasts its own usefulness (v15, 2026-10-22).

    python maestro.py ablate [--probes FILE] [--only word,word]
        Each reading or rule switched off (or, for the parts kept off, switched on) in turn; the held-out numbers
        re-run; every part labelled EARNS (the numbers fall without it), FREE (nothing changes: rent unpaid) or HURTS
        (the numbers rise without it); for parts switched on: GAINS / FREE / COSTS. The module's globals are restored
        after every variant (the selftest proves it). One ABLATE row goes to the ledger so `trend` can show it.
    python maestro.py why "<task>" <skill> [--concepts "..."] [--json]
        One skill's whole account on one task: its rank in every reading and the fusion score each earned it, the
        task words it shares with the skill's description and body, the task words its text never says (what it
        would take to be found by words), pins, memory (book / antibody, with the similar past tasks), the record
        from similar tasks, the bonuses, its weighed place and any select note about it.
    python maestro.py odds "<task>" | RUN
        The Maestro's forecast of its own usefulness on this task: the most similar past runs and whether a pick there
        worked (FIT works, or the owner's useful rating), a Wilson interval, and the plain advice. Similar tasks only,
        never the global record (dial M32's rule applied to the Maestro itself). The ODDS line of every sheet.
    python introspect.py --selftest
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
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

VARIANTS = [   # (part, kind, changes): kind "remove" switches a live part off, "add" switches a kept-off part on
    ("raw words", "remove", {"WEIGHTS": {"raw": 0.0}}),
    ("body (BM25 over SKILL.md)", "remove", {"WEIGHTS": {"body": 0.0}}),
    ("network (pairs-with walk)", "remove", {"WEIGHTS": {"network": 0.0}}),
    ("core pins", "remove", {"PINS": False}),
    ("memory (ratings, book, antibodies)", "remove", {"MEMORY": False}),
    ("tool bonus", "remove", {"FAIR_NO_TOOL": True}),
    ("family diversity", "remove", {"FAMILY_CAP": 99}),
    ("fit-first margin (bonuses rule)", "remove", {"MARGIN": 1.0}),
    ("bonuses (pure fit)", "remove", {"W_USE": 0.0, "W_FASC": 0.0, "W_FAV": 0.0}),
    ("fair askwords", "remove", {"FAIR_ASKWORDS": False}),
    ("fair context (global fame instead)", "remove", {"FAIR_CONTEXT": False}),
    ("stabilize (leave-one-part-out)", "add", {"STABILIZE": True}),
    ("family reading (capability tree)", "add", {"WEIGHTS": {"family": 1.0}}),
    ("ncd reading (compression distance)", "add", {"WEIGHTS": {"ncd": 1.0}}),
    ("owner lexicon reading", "add", {"WEIGHTS": {"owner": 1.0}}),
    ("meaning reading (purpose embeddings, M46)", "remove", {"WEIGHTS": {"meaning": 0.0}}),      # v19: the 2026-10-24 readings
    ("concept reading (inferred operations, M19)", "remove", {"WEIGHTS": {"concept": 0.0}}),
    ("personal reading (your own history, M48)", "remove", {"WEIGHTS": {"personal": 0.0}}),
    ("mode reading (the mode's lean words, M49)", "add", {"WEIGHTS": {"mode": 1.0}}),
    ("phase reading (session transitions, M52)", "remove", {"WEIGHTS": {"phase": 0.0}}),   # 2026-10-25: phase.py, landed at 1.0
]   # v16 O10: lexicon, feedback, intents (1.0 and 0.5) and the eligible rescale were removed from the code after this ablation marked all four COSTS
TUNE_KEYS = ("raw", "body", "network", "concept", "meaning", "personal", "family", "ncd", "owner", "phase")
TUNE_GRID = (0.0, 0.25, 0.5, 1.0, 2.0)


def tune(lib, st, train: Path, tests: dict, keys=TUNE_KEYS, grid=TUNE_GRID, passes: int = 2, log=None) -> dict:
    """Learning to rank from the owner's own record, in its smallest honest form: coordinate descent over the fusion
    weights on TRAIN (real prompts before a date), judged only on the sets it never saw (real prompts after the date;
    the hand-labelled held-out file). Objective: top-3 hits plus top-1 hits. Nothing is applied: the result is a
    suggested dial panel, and the dials stay as they are until a person changes them."""
    keys = [k for k in keys if k in M.WEIGHTS]

    def hits(path: Path) -> dict:
        return _counts(M.evaluate(lib, st, path))

    def obj(r: dict) -> int:
        return r["maestro@3"] + r["maestro@1"]

    start = dict(M.WEIGHTS)
    best = dict(start)
    base_train = hits(train)
    cur = obj(base_train)
    base_tests = {name: hits(p) for name, p in tests.items()}
    steps = []
    for ps in range(passes):
        moved = False
        for k in keys:
            for v in grid:
                if abs(v - best.get(k, 0.0)) < 1e-9:
                    continue
                trial = dict(best)
                trial[k] = v
                with altered(lib, st, {"WEIGHTS": trial}):
                    r = hits(train)
                if obj(r) > cur:
                    if log:
                        log(f"  pass {ps + 1}: {k} {best.get(k)} -> {v}: train {cur} -> {obj(r)}")
                    steps.append({"pass": ps + 1, "key": k, "from": best.get(k), "to": v, "train_from": cur, "train_to": obj(r)})
                    cur, best = obj(r), trial
                    moved = True
        if not moved:
            break
    with altered(lib, st, {"WEIGHTS": best}):
        final_train = hits(train)
        final_tests = {name: hits(p) for name, p in tests.items()}
    return {"start": start, "best": best, "steps": steps, "train": {"before": base_train, "after": final_train},
            "tests": {name: {"before": base_tests[name], "after": final_tests[name]} for name in tests}, "keys": keys, "grid": list(grid)}


def render_tune(res: dict) -> str:
    pk = f"pool@{M.POOL}"

    def line(r):
        return f"@1 {r['maestro@1']:>3}  @3 {r['maestro@3']:>3}  {pk} {r[pk]:>3}  (n {r['n']})"

    L = ["TUNE (coordinate descent on TRAIN; judged on sets it never saw):"]
    L.append(f"  weights start {json.dumps({k: res['start'][k] for k in res['keys']})}")
    L.append(f"  weights best  {json.dumps({k: res['best'][k] for k in res['keys']})}")
    for s in res["steps"]:
        L.append(f"  step pass {s['pass']}: {s['key']} {s['from']} -> {s['to']}  train objective {s['train_from']} -> {s['train_to']}")
    L.append(f"  TRAIN   before {line(res['train']['before'])}\n          after  {line(res['train']['after'])}")
    for name, t in res["tests"].items():
        L.append(f"  {name.upper():<7} before {line(t['before'])}\n          after  {line(t['after'])}")
    changed = {k: v for k, v in res["best"].items() if abs(v - res["start"].get(k, 0.0)) > 1e-9}
    if changed:
        L.append("  TO APPLY (by hand, maestro_dials.md): " + ", ".join(f"weight_{k} = {v}" for k, v in changed.items())
                 + "  - only if every unseen set is at least level")
    else:
        L.append("  the starting weights were already the best on TRAIN: nothing to apply")
    return "\n".join(L)
WATCHED = ("MARGIN", "FAMILY_CAP", "W_USE", "W_FASC", "W_FAV", "FAIR_NO_TOOL", "FAIR_ASKWORDS", "FAIR_CONTEXT",
           "STABILIZE", "TOOL_BONUS")


def snapshot() -> dict:
    return {**{k: getattr(M, k) for k in WATCHED}, "WEIGHTS": dict(M.WEIGHTS)}


@contextlib.contextmanager
def altered(lib, st, changes: dict):
    """Apply a variant's changes to the running maestro, the library's pins and the state's memory; restore all of
    them afterwards, whatever happened."""
    saved = snapshot()
    saved_trig = lib.triggers
    had = {a: st.__dict__.get(a) for a in ("memory", "stats")}
    try:
        for k, v in changes.items():
            if k == "WEIGHTS":
                M.WEIGHTS.update(v)
            elif k == "PINS":
                lib.triggers = {}
            elif k == "MEMORY":
                st.memory = lambda: []
                st.stats = lambda questions=(): {}
            else:
                setattr(M, k, v)
        yield
    finally:
        M.WEIGHTS.clear()
        M.WEIGHTS.update(saved["WEIGHTS"])
        for k in WATCHED:
            setattr(M, k, saved[k])
        lib.triggers = saved_trig
        for a, old in had.items():
            if old is None:
                st.__dict__.pop(a, None)
            else:
                st.__dict__[a] = old


def _counts(res: dict) -> dict:
    out = {k: int(str(v).split("/")[0]) for k, v in res.items() if "@" in k}
    out["n"] = int(res.get("n", 0))
    return out


def judge(kind: str, delta: dict) -> str:
    down, up = any(v < 0 for v in delta.values()), any(v > 0 for v in delta.values())
    if kind == "remove":
        return "EARNS" if down else "HURTS" if up else "FREE"
    return "COSTS" if down else "GAINS" if up else "FREE"


def ablate(lib, st, probes: Path, only: list[str] | None = None, log=None) -> dict:
    keys = ("maestro@1", "maestro@3", f"pool@{M.POOL}")
    base = _counts(M.evaluate(lib, st, probes))
    rows = []
    for part, kind, changes in VARIANTS:
        if only and not any(o.lower() in part.lower() for o in only):
            continue
        if log:
            log(f"  ... {kind} {part}")
        with altered(lib, st, changes):
            res = _counts(M.evaluate(lib, st, probes))
        delta = {k: res.get(k, 0) - base.get(k, 0) for k in keys}
        rows.append({"part": part, "kind": kind, **{k: res.get(k, 0) for k in keys}, "delta": delta, "verdict": judge(kind, delta)})
    return {"n": base["n"], "probes": Path(probes).name, "base": {k: base.get(k, 0) for k in keys}, "rows": rows}


def render_ablate(res: dict) -> str:
    b = res["base"]
    pk = f"pool@{M.POOL}"
    L = [f"ABLATION on {res['probes']} ({res['n']} prompts): baseline maestro@1 {b['maestro@1']}  @3 {b['maestro@3']}  "
         f"{pk} {b[pk]}",
         f"  {'part':<36} {'switch':<7} {'@1':>3} {'@3':>3} {'pool':>4}   {'d@1':>4} {'d@3':>4} {'dpool':>5}  verdict"]
    for r in res["rows"]:
        d = r["delta"]
        L.append(f"  {r['part']:<36} {('- off' if r['kind'] == 'remove' else '+ on'):<7} {r['maestro@1']:>3} {r['maestro@3']:>3} "
                 f"{r[pk]:>4}   {d['maestro@1']:>+4} {d['maestro@3']:>+4} {d[pk]:>+5}  {r['verdict']}")
    L.append("READ IT AS: EARNS = the numbers fall without the part (it pays rent); FREE = no change on these probes "
             "(a candidate for module-rent, not for deletion: other probes may need it); HURTS = the numbers rise "
             "without it. GAINS / COSTS are the same for parts kept off. The concept reading here is the INFERRED one "
             "every sheet runs since think_first = no (v19: eval infers it the same way; `eval --no-infer` is the paired check).")
    return "\n".join(L)


# --- why: one skill's account ----------------------------------------------------------------------------------------

def account(lib, st, task: str, skill: str, concepts: str = "") -> dict:
    toks = lib.fs._tokens
    task_r = M.ranking_text(task)
    words = set(toks(lib.variants(task)["_plain"]))
    readings, partial = {}, {}

    def reading(vname: str, names: list[str]) -> None:
        w = M.WEIGHTS.get(vname, 1.0)
        for rank, n in enumerate(names, 1):
            partial[n] = partial.get(n, 0.0) + w / (M.RRF_K + rank)
        rank = names.index(skill) + 1 if skill in names else None
        readings[vname] = {"weight": w, "rank": rank, "of": len(names), "rrf": round(w / (M.RRF_K + rank), 5) if rank else 0.0}

    for vname, q in lib.variants(task_r).items():
        if vname.startswith("_") or not M.WEIGHTS.get(vname, 1.0):
            continue
        reading(vname, [r["name"] for r in lib.search(q, 120)])
    if M.WEIGHTS.get("body"):
        reading("body", lib.body(task_r, 120))
    for extra in ("family", "ncd", "owner"):
        if M.WEIGHTS.get(extra) and hasattr(lib, extra + "_reading"):
            reading(extra, getattr(lib, extra + "_reading")(task_r, 120))
    if M.WEIGHTS.get("network") and partial:
        seeds = sorted(partial.items(), key=lambda x: (-x[1], x[0]))[:M.NET_SEEDS]
        reading("network", lib.network(seeds)[:120])
    per = []
    if concepts:
        mechs = M.load_mechanisms()
        cons = M.parse_concepts(concepts, M.load_vocab())
        per = M.concept_scores(cons, {n: m for n, m in mechs.items() if n in lib.desc}, toks)
        reading("concept", M.concept_rank(per, 120))
    lib.concept_per = per
    ranked = lib.fused(task)
    lib.concept_per = []
    names = [r["name"] for r in ranked]
    frank = names.index(skill) + 1 if skill in names else None
    top = ranked[0]["score"] if ranked else 0.0
    fit = round(ranked[frank - 1]["score"] / top, 3) if frank and top else 0.0
    desc = lib.desc.get(skill, "")
    md = lib.skill_md(skill)
    body_text = md.read_text(encoding="utf-8", errors="replace")[:20000] if md.is_file() else ""
    shared_desc = sorted(words & set(toks(skill + " " + desc)))
    shared_body = sorted((words & set(toks(body_text))) - set(shared_desc))
    never = sorted(words - set(toks(skill + " " + desc + " " + body_text)))
    pin = next((r.get("pin") for r in lib.search(task, 120) if r["name"] == skill and r.get("pin")), None)
    mem = st.memory()
    book, anti = M.recall(mem, words)
    past = sorted(((round(M.jaccard(w, words), 2), rating) for w, s, rating in mem
                   if s == skill and M.jaccard(w, words) >= M.MEMORY_SIM), reverse=True)[:5]
    stats = M.context_stats(mem, words) if M.FAIR_CONTEXT else st.stats()
    pool = ranked[:M.POOL]
    in_pool = skill in {r["name"] for r in pool}
    weighed = M.weigh(pool, stats, st.favourites()) if pool else []
    wrow = next((w for w in weighed if w["name"] == skill), None)
    wpos = (weighed.index(wrow) + 1) if wrow else None
    chosen, notes = M.select(weighed, min(6, len(weighed)), lib.family) if weighed else ([], [])
    return {"task": task, "skill": skill, "known": skill in lib.desc, "readings": readings, "fused_rank": frank,
            "of": len(names), "fit": fit, "leader": names[0] if names else None,
            "leader_score": ranked[0]["score"] if ranked else 0.0, "score": ranked[frank - 1]["score"] if frank else 0.0,
            "shared_desc": shared_desc, "shared_body": shared_body, "never": never, "pin": pin,
            "book": round(book.get(skill, 0.0), 2), "antibody": round(anti.get(skill, 0.0), 2), "past": past,
            "record": stats.get(skill, {}), "in_pool": in_pool, "weighed": wrow, "weighed_pos": wpos,
            "picked": skill in {c["name"] for c in chosen},
            "notes": [n for n in notes if skill in (n.get("demoted"), n.get("for"))]}


def render_why_plain(a: dict) -> str:
    """v15 item 34: the same account in plain words, for a reader who has not met the Maestro's terms."""
    if not a["known"]:
        return f"{a['skill']} is not one of your skills. Check the spelling."
    L = [f"Why {a['skill']} for \"{a['task'][:70]}\":"]
    if a["fused_rank"]:
        L.append(f"  Of {a['of']} skills, it came {a['fused_rank']}th when the task's words were matched against every "
                 f"skill's description. The best match was {a['leader']}.")
    else:
        L.append(f"  None of the task's words appear in its description, so it was not ranked at all. {a['leader']} matched best.")
    L.append("  It " + ("was" if a["in_pool"] else "was not") + f" among the {M.POOL} skills the judge looked at"
             + (", and it " + ("was" if a["picked"] else "was not") + " one of the final picks." if a["in_pool"] else "."))
    if a["shared_desc"]:
        L.append("  Words the task and its description share: " + ", ".join(a["shared_desc"][:10]) + ".")
    if a["never"]:
        L.append("  Words from the task it never mentions anywhere: " + ", ".join(a["never"][:10]) + ".")
    if a.get("weighed"):
        w = a["weighed"]
        L.append(f"  After the bonuses (past usefulness {w['use']}, interest {w['fasc']}, your favourites {w['fav']}) its score was {w['total']}.")
    L.append("  To make it findable for tasks like this, add those missing words to its description (`maestro.py findable " + a["skill"] + "`).")
    return "\n".join(L)


def render_why(a: dict) -> str:
    if not a["known"]:
        return f"WHY: {a['skill']} is not a skill in this library (spelling? `maestro.py new` lists what changed)"
    L = [f"WHY {a['skill']} on \"{a['task'][:70]}{'...' if len(a['task']) > 70 else ''}\""]
    L.append(f"  fused rank {a['fused_rank'] or 'absent'} of {a['of']} (fit {a['fit']}); leader {a['leader']}; "
             f"in the pool of {M.POOL}: {'yes' if a['in_pool'] else 'no'}; weighed {a['weighed_pos'] or '-'}"
             + (f" (use {a['weighed']['use']}, fasc {a['weighed']['fasc']}, fav {a['weighed']['fav']} -> total "
                f"{a['weighed']['total']})" if a["weighed"] else "") + f"; picked in the top 6: {'yes' if a['picked'] else 'no'}")
    rd = " | ".join(f"{k} rank {v['rank'] or '-'}/{v['of']} (+{v['rrf']})" for k, v in a["readings"].items())
    L.append("  readings: " + rd)
    L.append("  shares with its description: " + (", ".join(a["shared_desc"]) or "nothing")
             + ("; with its body only: " + ", ".join(a["shared_body"][:12]) if a["shared_body"] else ""))
    L.append("  never says (task words absent from its whole text): " + (", ".join(a["never"][:14]) or "none")
             + ("  <- the words that would have to enter its description for the words reading to find it" if a["never"] else ""))
    mem = []
    if a["pin"]:
        mem.append(f"pin {a['pin']}")
    if a["book"]:
        mem.append(f"opening book sim {a['book']}")
    if a["antibody"]:
        mem.append(f"ANTIBODY sim {a['antibody']}")
    if a["past"]:
        mem.append("past similar tasks: " + ", ".join(f"{s} {r}" for s, r in a["past"]))
    rec = ", ".join(f"{k} {v}" for k, v in a["record"].items()) or "none"
    L.append("  memory: " + ("; ".join(mem) or "none") + f"; record from similar tasks: {rec}")
    for n in a["notes"]:
        L.append(f"  select: {n.get('demoted')} demoted for {n.get('for')} ({n.get('why')}, fit gap {n.get('fit_gap')})")
    if a["fused_rank"] and a["fused_rank"] > 1:
        L.append(f"  TO LEAD: it needs +{round(a['leader_score'] - a['score'], 4)} fused score; a first place in one more "
                 f"reading is worth about +{round(1000 / (M.RRF_K + 1), 2)}; the 'never says' words are where that reading is lost")
    return "\n".join(L)


# --- odds: the Maestro's forecast of itself -------------------------------------------------------------------------

OWNER_BY = {None, "", "max", "user", "owner", "the owner"}


def odds(rows: list[dict], words: set, k: int = 8, floor: float | None = None) -> dict:
    floor = (M.MEMORY_SIM / 2) if floor is None else floor
    scored = [r for r in rows if r.get("kind") == "SCORE" and r.get("words")]
    sims = sorted(((M.jaccard(set(r["words"]), words), r) for r in scored), key=lambda x: (-x[0], x[1].get("t", 0)))
    sims = [(s, r) for s, r in sims if s >= floor][:k]
    fits: dict[str, set] = {}
    for r in rows:
        if r.get("kind") == "FIT":
            fits.setdefault(r["run"], set()).add(r.get("verdict"))
    useful = {r["run"] for r in rows if r.get("kind") == "RATE" and r.get("rating") == "useful"
              and str(r.get("by") or "").lower() in OWNER_BY}
    closed = {r["run"] for r in rows if r.get("kind") == "CLOSE"}
    out = []
    for s, r in sims:
        run, v = r["run"], fits.get(r["run"], set())
        o = ("WORKED" if "works" in v or run in useful else "MISFIT" if "misfit" in v
             else "CLOSED" if run in closed else "UNTRIED")
        out.append({"run": run, "sim": round(s, 2), "outcome": o, "task": (r.get("task") or " ".join(r["words"]))[:70]})
    worked = sum(o["outcome"] == "WORKED" for o in out)
    judged = worked + sum(o["outcome"] == "MISFIT" for o in out)
    return {"similar": out, "worked": worked, "judged": judged, "untried": len(out) - judged}


def odds_line(rows: list[dict], words: set) -> str:
    o = odds(rows, words)
    n = len(o["similar"])
    if not n:
        return "ODDS: no similar past run in the ledger; the Maestro's help on this kind of task is untested"
    if not o["judged"]:
        return (f"ODDS: {n} similar past run(s), none tried on its subject: untested; try the picks this time "
                "(`rehearse`) or skip the Maestro")
    p = o["worked"] / o["judged"]
    ci = M.wilson_ci(o["worked"], o["judged"])
    advice = ("it rarely helped on tasks like this: consider QUICK or doing it directly" if o["judged"] >= 4 and p < 0.25
              else "it usually helped here" if p >= 0.5 and o["judged"] >= 2 else "too few judged runs to say")
    return (f"ODDS: a pick worked on {o['worked']} of {o['judged']} judged similar run(s) ({p:.0%}, 95% {ci}); "
            f"{o['untried']} untried; {advice}")


def render_odds(o: dict, line: str) -> str:
    L = [line]
    for s in o["similar"]:
        L.append(f"  {s['run']}  sim {s['sim']:.2f}  {s['outcome']:<8} {s['task']}")
    if not o["similar"]:
        L.append("  (similarity is word Jaccard with the past runs' task words; the bar is half the memory bar)")
    return "\n".join(L)


# --- command line ----------------------------------------------------------------------------------------------------

def _val(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def cli(argv: list[str], lib, st, root: Path) -> int:
    """argv starts with 'ablate', 'why' or 'odds'."""
    sub = argv[0]
    if sub == "ablate":
        probes = Path(_val(argv, "--probes") or M.companion(root, "probes_heldout.tsv"))
        if not probes.is_file():
            print(f"NO_PROBES: {probes} is not a file (pass --probes FILE; `hindsight probes` writes one from real prompts)")
            return 2
        only = [x for x in (_val(argv, "--only") or "").split(",") if x]
        res = ablate(lib, st, probes, only or None, log=print)
        print(json.dumps(res, indent=1) if "--json" in argv else render_ablate(res))
        st.append({"kind": "ABLATE", "t": int(time.time()), "probes": probes.name, "n": res["n"], "base": res["base"],
                   "rows": [{"part": r["part"], "kind": r["kind"], "delta": r["delta"], "verdict": r["verdict"]} for r in res["rows"]],
                   "code": __import__("hashlib").sha256(Path(M.__file__).read_bytes()).hexdigest()[:12]})
        return 0
    if sub == "tune":
        H = M._load(M.HERE / "hindsight.py", "hindsight")
        rows = H.rows_of(Path(st.d))
        split = _val(argv, "--split")
        lab = H.labels(rows)
        if not lab or not split:
            print("TUNE needs the hindsight cache and --split YYYY-MM-DD (train = labelled prompts before it, test = after)")
            return 2
        work = Path(st.d) / "tune"
        work.mkdir(exist_ok=True)
        tr, te = work / "train.tsv", work / "test.tsv"
        for f, part in ((tr, [r for r in lab if r["ts"][:10] < split]), (te, [r for r in lab if r["ts"][:10] >= split])):
            f.write_text("".join(r["text"].replace("\t", " ") + "\t" + ",".join(r["used"]) + "\n" for r in part), encoding="utf-8")
        tests = {"test": te}
        held = M.companion(root, "probes_heldout.tsv")
        if held.is_file():
            tests["heldout"] = held
        keys = tuple(x for x in (_val(argv, "--keys") or "").split(",") if x) or TUNE_KEYS
        grid = tuple(float(x) for x in (_val(argv, "--grid") or "").split(",") if x) or TUNE_GRID
        print(f"  train {sum(1 for _ in tr.open(encoding='utf-8'))} prompts before {split}, test {sum(1 for _ in te.open(encoding='utf-8'))} after; keys {list(keys)}; grid {list(grid)}")
        res = tune(lib, st, tr, tests, keys=keys, grid=grid, passes=int(_val(argv, "--passes", 2)), log=print)
        print(json.dumps(res, indent=1) if "--json" in argv else render_tune(res))
        st.append({"kind": "TUNE", "t": int(time.time()), "split": split, "start": res["start"], "best": res["best"],
                   "train": res["train"], "tests": res["tests"], "code": __import__("hashlib").sha256(Path(M.__file__).read_bytes()).hexdigest()[:12]})
        return 0
    if sub == "why":
        pos = [a for a in argv[1:] if not a.startswith("--")]
        pos = [p for i, p in enumerate(pos) if i == 0 or argv[argv.index(p) - 1] not in ("--concepts", "--state", "--root", "--project")]
        if len(pos) < 2:
            print("WHY needs a task and a skill: maestro.py why \"<task>\" <skill> [--concepts \"...\"]")
            return 2
        skill = pos[-1]
        task = " ".join(pos[:-1])
        a = account(lib, st, task, skill, _val(argv, "--concepts") or "")
        print(json.dumps(a, indent=1, default=list) if "--json" in argv else
              render_why_plain(a) if "--plain" in argv else render_why(a))
        return 0
    if sub == "odds":
        target = " ".join(a for a in argv[1:] if not a.startswith("--"))
        rows = st.rows()
        run = next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == target), None)
        if target == "last":
            run = next((r for r in reversed(rows) if r.get("kind") == "SCORE"), None)
        words = set(run["words"]) if run and run.get("words") else set(lib.fs._tokens(lib.variants(target)["_plain"]))
        o = odds(rows, words)
        print(render_odds(o, odds_line(rows, words)))
        return 0
    print(__doc__)
    return 2


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    import tempfile
    ok: dict[str, bool] = {}
    rows = [{"kind": "SCORE", "run": "r1", "t": 1, "words": ["plan", "cards", "audit", "gaps"], "task": "audit the plan cards for gaps"},
            {"kind": "FIT", "run": "r1", "skill": "x", "verdict": "works"},
            {"kind": "SCORE", "run": "r2", "t": 2, "words": ["plan", "cards", "order", "gaps"], "task": "order the plan cards"},
            {"kind": "FIT", "run": "r2", "skill": "y", "verdict": "misfit"},
            {"kind": "SCORE", "run": "r3", "t": 3, "words": ["plan", "audit", "gaps", "rules"], "task": "audit the plan rules"},
            {"kind": "SCORE", "run": "r4", "t": 4, "words": ["limerick", "cat", "funny"], "task": "a limerick"},
            {"kind": "SCORE", "run": "r5", "t": 5, "words": ["plan", "cards", "gaps"], "task": "plan gaps"},
            {"kind": "RATE", "run": "r5", "skill": "z", "rating": "useful", "by": "claude"},
            {"kind": "SCORE", "run": "r6", "t": 6, "words": ["plan", "cards", "gaps", "audit"], "task": "plan gaps audit"},
            {"kind": "RATE", "run": "r6", "skill": "z", "rating": "useful", "by": "max"}]
    o = odds(rows, {"plan", "cards", "gaps", "audit"})
    runs = {s["run"]: s["outcome"] for s in o["similar"]}
    ok["odds: similar runs only (the limerick is out), outcomes from FIT and the owner's rating"] = \
        "r4" not in runs and runs.get("r1") == "WORKED" and runs.get("r2") == "MISFIT" and runs.get("r3") == "UNTRIED" \
        and runs.get("r6") == "WORKED"
    ok["odds: Claude's own useful rating is a self-report, not WORKED"] = runs.get("r5") == "UNTRIED"
    ok["odds: counts"] = o["worked"] == 2 and o["judged"] == 3 and o["untried"] == 2
    line = odds_line(rows, {"plan", "cards", "gaps", "audit"})
    ok["odds line carries the fraction and an interval"] = "2 of 3" in line and "95%" in line
    ok["odds line with no similar run says untested"] = "untested" in odds_line(rows, {"zzz", "qqq"})
    ok["judge: remove/add verdicts"] = judge("remove", {"a": -1}) == "EARNS" and judge("remove", {"a": 0}) == "FREE" and \
        judge("remove", {"a": 1}) == "HURTS" and judge("add", {"a": 1}) == "GAINS" and judge("add", {"a": -1}) == "COSTS"
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        root = td / "skills"
        for name, desc in [("hysteresis", "Two-threshold latch that stops a flapping alert from chattering. Use this whenever an alert flaps on and off."),
                           ("plain-terms", "Rewrite a report in plain words for a reader. Use this whenever the user wants plain language."),
                           ("lindy", "How long a thing has lasted predicts how long it will last. Use this whenever the user asks about age.")]:
            (root / name).mkdir(parents=True)
            (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\nIt debounces a noisy sensor.\n",
                                                   encoding="utf-8")
        lib = M.Library(root, everything=False)
        st = M.State(td / "state")
        a = account(lib, st, "stop my sensor alert from flapping on and off", "hysteresis")
        ok["why: the matching skill leads the raw reading and the fusion"] = \
            a["readings"].get("raw", {}).get("rank") == 1 and a["fused_rank"] == 1 and a["fit"] == 1.0
        ok["why: shared words with the description, body-only words, and the words it never says"] = \
            "alert" in a["shared_desc"] and "sensor" in a["shared_body"] and "stop" in a["never"]
        ok["why: an unknown skill is reported, not crashed"] = account(lib, st, "x", "nosuch")["known"] is False
        txt = render_why(a)
        ok["why renders the readings and the never-says line"] = "readings:" in txt and "never says" in txt
        probes = td / "p.tsv"
        probes.write_text("stop my alert from flapping\thysteresis\nsay it in plain words\tplain-terms\n", encoding="utf-8")
        before = snapshot()
        res = ablate(lib, st, probes, only=["raw words", "pure fit", "stabilize"])   # v16 O10: Rocchio row removed
        ok["ablate: one row per chosen variant, the baseline finds both"] = \
            len(res["rows"]) == 3 and res["base"]["maestro@1"] == 2 and res["n"] == 2
        ok["ablate: every global is restored after the ladder"] = snapshot() == before
        with altered(lib, st, {"WEIGHTS": {"raw": 0.0, "body": 0.0, "network": 0.0, "meaning": 0.0, "concept": 0.0}}):   # v19: eval infers concepts
            dark = _counts(M.evaluate(lib, st, probes))
        ok["altered really switches the readings off (no reading, no hit) and restores"] = \
            dark["maestro@1"] == 0 and snapshot() == before and M.WEIGHTS["raw"] == before["WEIGHTS"]["raw"]
        with altered(lib, st, {"MEMORY": False, "PINS": False}):
            memo = st.memory()
            pins = lib.triggers
        ok["altered: memory and pins are emptied inside, back outside"] = memo == [] and pins == {} and "memory" not in st.__dict__
        txt2 = render_ablate(res)
        ok["ablate renders a verdict per part"] = txt2.count("\n") >= 4 and ("FREE" in txt2 or "EARNS" in txt2)
    ok = {k: bool(v) for k, v in ok.items()}
    print(f"introspect selftest: {sum(ok.values())}/{len(ok)} " + ("PASS" if all(ok.values()) else "FAIL"))
    for k, v in ok.items():
        if not v:
            print(f"  FAIL {k}")
    return all(ok.values())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(M.main(sys.argv[1:]))
