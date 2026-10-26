"""core_pin - make the router find the CORE ritual skills (backs the skill-finder skill).

skill-finder ranks by TF-IDF over name + description. Ritual skills (land-a-change, guard-respect, receipt-report...)
are asked for in short situational words ("status?", "PreToolUse hook error", "ready to commit") that their
descriptions share with dozens of other skills, so they sink. This adds a TRIGGER TABLE (core_triggers.json:
skill -> phrases) on top of skill-finder's scores: a phrase fires when all of its content words are in the query
(one-word phrases only fire on short queries), and each firing phrase adds one maximum-IDF word's worth of score.
It does not edit any SKILL.md and does not change skill-finder's own ranking of non-core skills except by the boost.

    python core_pin.py find "status?" [--root SKILLS] [--top 5] [--triggers core_triggers.json]
    python core_pin.py audit [SKILLS] [--top 5]          # route-audit before/after, split core vs library
    python core_pin.py probe PROBES.tsv [--root SKILLS]  # real phrasings: query<TAB>ok1,ok2 -> hit@k before/after
    python core_pin.py check [--root SKILLS]             # trigger table: dangling skills, empty/collapsed phrases
    python core_pin.py table                             # the table as markdown for CLAUDE.md / memory
    python core_pin.py --selftest
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SHORT_QUERY = 8      # a one-word trigger ("status") fires only when the query has this many content words or fewer
MAX_HITS = 2         # at most this many phrases count per skill per query
PIN_WEIGHT = 2.0     # one firing phrase = the rarest word in the library matched in a skill's NAME


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod


def finder(root: Path):
    return _load_module(Path(root) / "skill-finder" / "find_skill.py", "find_skill")


def load_triggers(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: list(v) for k, v in data.items() if not k.startswith("_")}


def fired(fs, triggers: dict, query: str) -> dict:
    """skill -> list of trigger phrases whose content words are all in the query."""
    q = set(fs._tokens(query))
    short = len(q) <= SHORT_QUERY
    out = {}
    for skill, phrases in triggers.items():
        hits = []
        for ph in phrases:
            toks = set(fs._tokens(ph))
            if not toks or (len(toks) == 1 and not short):
                continue
            if toks <= q:
                hits.append(ph)
        if hits:
            out[skill] = hits
    return out


def pinned_search(fs, skills: list, query: str, triggers: dict, top: int = 5) -> list:
    base = fs.search(skills, query, top=len(skills))
    by = {r["name"]: dict(r) for r in base}
    names = {s["name"]: s for s in skills}
    boost = PIN_WEIGHT * math.log((len(skills) + 1) / 0.5)   # largest IDF any word can have, name-weighted
    for skill, hits in fired(fs, triggers, query).items():
        if skill not in names:
            continue
        r = by.setdefault(skill, {"name": skill, "score": 0.0, "tool": names[skill]["tool"],
                                  "when": names[skill]["desc"].split(". ")[0][:160]})
        r["score"] = round(r["score"] + boost * min(len(hits), MAX_HITS), 3)
        r["pin"] = hits[:MAX_HITS]
    ranked = sorted(by.values(), key=lambda r: (-r["score"], r["name"]))
    return ranked[:top]


def audit(root: Path, triggers: dict, top: int = 5) -> dict:
    root = Path(root)
    fs = finder(root)
    ra = _load_module(root / "route-audit" / "route_audit.py", "route_audit")
    skills = fs.load(root)
    core = set(triggers)
    res = {"before": {}, "after": {}}
    for s in skills:
        q = ra.pitch(root / s["name"] / "SKILL.md", s["name"])
        if not q:
            continue
        b = [h["name"] for h in fs.search(skills, q, top=top)]
        a = [h["name"] for h in pinned_search(fs, skills, q, triggers, top=top)]
        res["before"][s["name"]] = b
        res["after"][s["name"]] = a

    def summ(tab):
        out = {}
        for grp, keep in (("core", lambda n: n in core), ("library", lambda n: n not in core), ("all", lambda n: True)):
            rows = {k: v for k, v in tab.items() if keep(k)}
            n = len(rows)
            out[grp] = {"n": n,
                        "top1": sum(1 for k, v in rows.items() if v and v[0] == k),
                        f"top{top}": sum(1 for k, v in rows.items() if k in v),
                        "missed": sorted(k for k, v in rows.items() if k not in v)}
        out["confusions"] = sorted((k, v[0] if v else None) for k, v in tab.items() if not v or v[0] != k)
        return out
    rep = {"top": top, "before": summ(res["before"]), "after": summ(res["after"])}
    lost = sorted(k for k in res["before"] if k in res["before"][k] and k not in res["after"][k])
    rep["lost"] = lost                                    # skills that fell OUT of top-k because of the pins
    new_conf = set(rep["after"]["confusions"]) - set(rep["before"]["confusions"])
    rep["new_confusions"] = sorted(new_conf)
    return rep


def probe(root: Path, triggers: dict, rows: list, top: int = 5) -> dict:
    fs = finder(root)
    skills = fs.load(root)
    out = []
    for q, ok in rows:
        b = [h["name"] for h in fs.search(skills, q, top=top)]
        a = [h["name"] for h in pinned_search(fs, skills, q, triggers, top=top)]
        out.append({"q": q, "ok": ok, "before": bool(set(b) & ok), "after": bool(set(a) & ok),
                    "b": b, "a": a})
    return {"n": len(out), "before": sum(r["before"] for r in out), "after": sum(r["after"] for r in out),
            "rows": out}


def check(root: Path, triggers: dict) -> list:
    fs = finder(root)
    present = {s["name"] for s in fs.load(root)}
    probs = []
    for skill, phrases in triggers.items():
        if skill not in present:
            probs.append(f"DANGLING {skill}: not a skill under {root}")
        for ph in phrases:
            toks = fs._tokens(ph)
            if not toks:
                probs.append(f"EMPTY {skill}: '{ph}' has no content words (all stopwords)")
            elif len(set(toks)) == 1 and len(ph.split()) > 1:
                probs.append(f"COLLAPSED {skill}: '{ph}' is only '{toks[0]}' after stopwords - it fires on any "
                             f"short query with that word")
    return probs


def render_table(triggers: dict) -> str:
    """Compact markdown for CLAUDE.md / memory: the harness skill listing often drops descriptions, so the
    words a ritual is asked in must be visible somewhere Claude reads every session."""
    lines = ["| when the ask or tool output says | load |", "|---|---|"]
    for skill in sorted(triggers):
        lines.append(f"| {'; '.join(triggers[skill])} | {skill} |")
    return "\n".join(lines)


def read_probes(path: Path) -> list:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        q, ok = line.split("\t", 1)
        rows.append((q, {x.strip() for x in ok.split(",") if x.strip()}))
    return rows


def _selftest() -> bool:
    import shutil
    import tempfile
    ok = {}
    root = Path(tempfile.mkdtemp(prefix="core_pin_"))
    try:
        src_finder = HERE.parent / "skill-finder" / "find_skill.py"
        if not src_finder.exists():
            src_finder = Path.home() / ".claude" / "skills" / "skill-finder" / "find_skill.py"
        src_ra = Path(src_finder).parents[1] / "route-audit" / "route_audit.py"
        for sub, src in (("skill-finder", src_finder), ("route-audit", src_ra)):
            (root / sub).mkdir()
            (root / sub / Path(src).name).write_text(Path(src).read_text(encoding="utf-8"), encoding="utf-8")
            (root / sub / "SKILL.md").write_text(f"---\nname: {sub}\ndescription: router tool ranking skill "
                                                 f"descriptions.\n---\n\n# {sub}\n", encoding="utf-8")

        def mk(name, desc, body):
            d = root / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n\n{body}\n",
                                        encoding="utf-8")
        mk("report-out", "Write the end of session report with receipts for every number.",
           "Files are ground truth, never memory: the final message must tie each number to a command output.")
        mk("status-board", "Show a status board of trains, delays and platforms at a station.",
           "Travellers want to see each train's status, delay and platform on one board at the station.")
        mk("guard-yield", "What to do when the guard hook blocks a command.",
           "When the PreToolUse hook error says blocked, find the honest allowed equivalent instead.")
        mk("delete-files", "Delete files and folders safely with a recursive forced delete and a dry run.",
           "Removing a directory tree needs a dry run first, then the recursive forced delete of every folder.")
        trig = {"report-out": ["status", "are you done"], "guard-yield": ["pretooluse hook error", "hook blocked"],
                "ghost-skill": ["anything"]}
        fs = finder(root)
        sk = fs.load(root)
        b = [r["name"] for r in fs.search(sk, "status?", top=5)]
        a = [r["name"] for r in pinned_search(fs, sk, "status?", trig, top=5)]
        ok["baseline sends 'status?' to the train board, not the report skill"] = b[:1] == ["status-board"]
        ok["pinned search puts the report skill first for 'status?'"] = a[:1] == ["report-out"]
        long_q = ("travellers want to know the status of each delayed train and platform at the station board "
                  "before the evening rush and the next departure")
        a2 = [r["name"] for r in pinned_search(fs, sk, long_q, trig, top=5)]
        ok["a one-word trigger does not fire on a long query (train question stays with the board)"] = (
            a2[:1] == ["status-board"] and "report-out" not in a2)
        err = "PreToolUse:Bash hook error: blocked: destructive command (recursive or forced delete)"
        b3 = [r["name"] for r in fs.search(sk, err, top=5)]
        a3 = pinned_search(fs, sk, err, trig, top=5)
        ok["the real hook-error text routes to the guard skill only with the pin"] = (
            b3[:1] == ["delete-files"] and a3[0]["name"] == "guard-yield" and a3[0].get("pin"))
        ok["no trigger fired -> ranking identical to skill-finder"] = (
            [r["name"] for r in pinned_search(fs, sk, "train platform delay", trig)]
            == [r["name"] for r in fs.search(sk, "train platform delay")])
        probs = check(root, trig)
        ok["check reports a trigger for a skill that does not exist"] = any("DANGLING ghost-skill" in p for p in probs)
        ok["check flags a multi-word phrase that collapses to one word ('are you done' -> 'done')"] = any(
            "COLLAPSED report-out" in p for p in probs)
        rep = audit(root, {k: v for k, v in trig.items() if k != "ghost-skill"}, top=1)
        ok["a phrase fires only when ALL its words are in the query ('hook' alone does not fire 'hook blocked')"] = (
            fired(fs, {"guard-yield": ["hook blocked"]}, "the git hook ran fine") == {})
        tb = render_table({"report-out": ["status"]})
        ok["table renders one markdown row per core skill"] = tb.splitlines()[-1] == "| status | report-out |"
        ok["audit splits core vs library and counts both"] = (rep["after"]["core"]["n"] == 2
                                                             and rep["after"]["library"]["n"] >= 2)
        rows = [("status?", {"report-out"}), (err, {"guard-yield"}), ("train platform delay", {"status-board"})]
        pr = probe(root, trig, rows, top=1)
        ok["probe counts hit@k before/after (1 -> 3)"] = (pr["before"], pr["after"]) == (1, 3)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def _opt(argv, flag, default):
    if flag in argv:
        i = argv.index(flag)
        val = argv[i + 1]
        del argv[i:i + 2]
        return val
    return default


def main(argv) -> int:
    argv = list(argv)
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    cmd = argv.pop(0)
    top = int(_opt(argv, "--top", "5"))
    trig = load_triggers(Path(_opt(argv, "--triggers", str(HERE / "core_triggers.json"))))
    root = Path(_opt(argv, "--root", str(Path.home() / ".claude" / "skills")))
    if cmd == "find":
        for r in pinned_search(finder(root), finder(root).load(root), " ".join(argv), trig, top):
            pin = f"  [pin: {', '.join(r['pin'])}]" if r.get("pin") else ""
            print(f"{r['score']:6.2f}  {r['name']:24s} [{'T' if r['tool'] else 'D'}]  {r['when'][:90]}{pin}")
        return 0
    if cmd == "audit":
        rep = audit(Path(argv[0]) if argv else root, trig, top)
        for when in ("before", "after"):
            s = rep[when]
            print(f"{when:6s}: " + "; ".join(
                f"{g} {s[g]['n']}: top-1 {s[g]['top1']}/{s[g]['n']}, top-{top} {s[g][f'top{top}']}/{s[g]['n']}"
                for g in ("core", "library", "all")))
        print(f"core never in top-{top} before ({len(rep['before']['core']['missed'])}): "
              f"{', '.join(rep['before']['core']['missed'])}")
        print(f"core never in top-{top} after  ({len(rep['after']['core']['missed'])}): "
              f"{', '.join(rep['after']['core']['missed'])}")
        print(f"skills that LOST their top-{top} place because of the pins ({len(rep['lost'])}): "
              f"{', '.join(rep['lost'])}")
        print(f"new confusions A -> B ({len(rep['new_confusions'])}):")
        for a, b in rep["new_confusions"]:
            print(f"  {a} -> {b}")
        return 0
    if cmd == "probe":
        pr = probe(root, trig, read_probes(Path(argv[0])), top)
        for r in pr["rows"]:
            mark = {(False, True): "FIXED", (True, False): "BROKE", (True, True): "ok", (False, False): "MISS"}
            print(f"{mark[(r['before'], r['after'])]:5s}  {r['q'][:70]:70s} -> {', '.join(r['a'][:3])}")
        print(f"hit@{top}: before {pr['before']}/{pr['n']}, after {pr['after']}/{pr['n']}")
        return 0
    if cmd == "table":
        print(render_table(trig))
        return 0
    if cmd == "check":
        probs = check(root, trig)
        print("\n".join(probs) if probs else f"trigger table OK: {len(trig)} core skills, all present")
        return 1 if any(p.startswith("DANGLING") for p in probs) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
