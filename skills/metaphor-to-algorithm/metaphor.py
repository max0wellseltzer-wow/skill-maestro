"""metaphor - reduce a metaphor-named skill idea to its algorithm, then check the library (backs metaphor-to-algorithm).

Biology/physics names ("refractory", "percolation", "catalyst") hide ordinary algorithms (cooldown,
union-find threshold, memoization) - and the 2026-10-15 merges showed most of them already existed. Before
building one: reduce(name, description) looks the name up in metaphor_table.json, reads algorithm cue words
from the description, searches the library with skill-finder for that algorithm, and says
BUILD (nothing close) or FOLD INTO <skill> (a known fold target, or a skill whose coverage of the algorithm
query is >= threshold).

    from metaphor import reduce
    reduce("chemotaxis", "move toward the strongest signal gradient")
    python metaphor.py "chemotaxis" "move toward the strongest signal gradient"
    python metaphor.py --selftest
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SK = HERE.parent
sys.path.insert(0, str(SK / "skill-finder"))
from find_skill import _tokens, load, search  # noqa: E402

TABLE = HERE / "metaphor_table.json"


def load_table(path=None) -> dict:
    return json.loads(Path(path or TABLE).read_text(encoding="utf-8"))


def _stem(w):
    t = _tokens(w)
    return t[0] if t else w


def candidates(name: str, description: str = "", table=None) -> list:
    """[(algorithm, why, folded_into)] - table hits on the name first, then description cue words."""
    tab = table or load_table()
    out, seen = [], set()
    key = name.strip().lower()
    parts = [key] + re.split(r"[-_\s]+", key)
    for p in parts:
        m = tab["metaphors"].get(p)
        if m and m["algorithm"] not in seen:
            seen.add(m["algorithm"])
            out.append((m["algorithm"], f"table: '{p}'", m.get("folded_into")))
    cues = {_stem(k): v for k, v in tab["cues"].items()}
    for w in re.findall(r"[a-z]+", (description or "").lower()):
        alg = cues.get(_stem(w)) or cues.get(w)
        if alg and alg not in seen:
            seen.add(alg)
            out.append((alg, f"cue: '{w}'", None))
    return out


def coverage(skill: dict, query: str, skills: list) -> float:
    """Share of the query's IDF weight that the skill's name+description contains (0..1)."""
    q = set(_tokens(query))
    if not q:
        return 0.0
    n = len(skills)
    df = {}
    for s in skills:
        for t in set(s["toks"]):
            df[t] = df.get(t, 0) + 1
    w = {t: math.log((n + 1) / (df.get(t, 0) + 0.5)) for t in q}
    tot = sum(w.values())
    return sum(w[t] for t in q & set(skill["toks"])) / tot if tot else 0.0


def reduce(name: str, description: str = "", skills=None, root=None, top: int = 3,
           threshold: float = 0.5, table=None) -> dict:
    skills = skills if skills is not None else load(Path(root) if root else SK)
    skills = [s for s in skills if s["name"] != name]          # never fold a skill into itself
    by_name = {s["name"]: s for s in skills}
    cands = candidates(name, description, table)
    query = " ".join(a for a, _, _ in cands) + " " + description
    hits = search(skills, query, top) if query.strip() else []
    algs = [a for a, _, _ in cands] or [description]
    for h in hits:                              # best coverage of any ONE candidate algorithm (no dilution)
        h["coverage"] = round(max(coverage(by_name[h["name"]], a, skills) for a in algs), 3)
    fold = next((f for _, _, f in cands if f and f in by_name), None)
    if fold:
        verdict, why = f"FOLD INTO {fold}", "the table records this metaphor was already merged there"
    elif hits and max(h["coverage"] for h in hits) >= threshold:
        best = max(hits, key=lambda h: h["coverage"])
        verdict, why = f"FOLD INTO {best['name']}", f"covers {best['coverage']:.0%} of the algorithm query"
    else:
        verdict, why = "BUILD", f"no skill covers >= {threshold:.0%} of the algorithm query"
    return {"name": name, "algorithms": cands, "query": query.strip(), "skills": hits,
            "verdict": verdict, "why": why}


def render(r: dict) -> str:
    lines = [f"{r['name']}:"]
    for alg, why, fold in r["algorithms"] or [("(no algorithm found - describe what it computes)", "", None)]:
        lines.append(f"  algorithm  {alg}  [{why}]" + (f" -> folded into {fold}" if fold else ""))
    for h in r["skills"]:
        lines.append(f"  library    {h['name']:22s} coverage {h['coverage']:.2f}  {h['when'][:70]}")
    lines.append(f"  VERDICT    {r['verdict']} ({r['why']})")
    return "\n".join(lines)


def stress(analogy: dict) -> dict:
    """Stress-test an analogy before relying on it (merged from analogy-stress-test).
    analogy = {"source": "tides", "target": "market reversals", "maps": {"moon": "news cycle", ...},
               "breaks": ["tides are periodic, markets are not"], "prediction": "a testable claim"}
    Every analogy breaks somewhere: one that lists no break hasn't been tested. It must also make a testable
    prediction, and the prediction may only use mapped elements (an unmapped one is the metaphor doing the work)."""
    issues = []
    maps = analogy.get("maps") or {}
    if not maps:
        issues.append("no element mapping: say which part of the source is which part of the target")
    if not analogy.get("breaks"):
        issues.append("no breaking point listed - every analogy breaks somewhere; find it before using this one")
    pred = (analogy.get("prediction") or "").lower()
    if not pred:
        issues.append("no testable prediction - an analogy that predicts nothing is decoration")
    else:
        mentioned = {s for s in re.findall(r"[a-z]{4,}", pred)}
        src_terms = set(re.findall(r"[a-z]{4,}", " ".join(maps).lower()))
        tgt_terms = set(re.findall(r"[a-z]{4,}", " ".join(maps.values()).lower()))
        smuggled = sorted((mentioned & set(re.findall(r"[a-z]{4,}", analogy.get("source", "").lower()))) - tgt_terms - src_terms)
        if smuggled:
            issues.append(f"prediction leans on unmapped source words {smuggled}: the metaphor is doing the work")
    return {"issues": issues, "ok": not issues}


def _selftest() -> bool:
    import shutil
    import tempfile
    ok = {}
    root = Path(tempfile.mkdtemp(prefix="metaphor_"))
    try:
        def mk(n, d):
            (root / n).mkdir()
            (root / n / "SKILL.md").write_text(f"---\nname: {n}\ndescription: {d}\n---\n", encoding="utf-8")
        mk("token-bucket", "Rate limit with a token bucket, a hard cooldown and a leaky bucket burst buffer.")
        mk("lru-cache", "Memoization: cache a pure function's results with least-recently-used eviction.")
        mk("union-find", "Union-find connectivity: merge items into connected clusters.")
        mk("convex-hull", "Minimal convex boundary of 2-D points.")
        sk = load(root)
        tab = load_table()
        ok["table seeds all 14 merged metaphors with a fold target"] = (
            len(tab["metaphors"]) >= 14 and all(m["folded_into"] for m in tab["metaphors"].values()))
        r1 = reduce("refractory", "", skills=sk)
        ok["refractory -> cooldown/token bucket, FOLD INTO token-bucket"] = (
            "token bucket" in r1["algorithms"][0][0] and r1["verdict"] == "FOLD INTO token-bucket")
        r2 = reduce("enzyme", "speed up repeated calls by caching each pure result (memoize)", skills=sk)
        ok["an unknown metaphor found by cue words folds into the covering skill"] = (
            any("memoization" in a for a, _, _ in r2["algorithms"]) and r2["verdict"] == "FOLD INTO lru-cache")
        r3 = reduce("aurora", "paint the sky with colours at night", skills=sk)
        ok["a metaphor with no algorithm and no close skill is BUILD"] = r3["verdict"] == "BUILD"
        r4 = reduce("percolation", "", skills=[s for s in sk if s["name"] != "union-find"])
        ok["a fold target missing from the library falls back to coverage, not a dangling FOLD"] = (
            "union-find" not in r4["verdict"])
        r5 = reduce("token-bucket", "rate limit with a token bucket", skills=sk)
        ok["a skill is never folded into itself"] = r5["verdict"] != "FOLD INTO token-bucket"
        ok["compound names split: 'buffer-pool' still hits the buffer row"] = any(
            "leaky bucket" in a for a, _, _ in candidates("buffer-pool", "", tab))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    good = {"source": "a neuron's refractory period", "target": "alert cooldown",
            "maps": {"firing": "sending an alert", "recovery time": "cooldown seconds"},
            "breaks": ["neurons recover gradually; a cooldown is all-or-nothing"],
            "prediction": "alerts within the cooldown seconds are suppressed and counted"}
    ok["stress: a mapped analogy with a breaking point and a prediction passes"] = stress(good)["ok"]
    lazy = {"source": "tides pulled by the moon", "target": "market reversals", "maps": {"water": "price"},
            "breaks": [], "prediction": "reversals follow the moon"}
    r_l = stress(lazy)
    ok["stress: planted lazy analogy (no break, unmapped 'moon' in the prediction) is caught"] = (
        len(r_l["issues"]) == 2 and any("unmapped" in i for i in r_l["issues"]))
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    name, desc = argv[0], " ".join(argv[1:])
    if ":" in name and not desc:
        name, desc = (x.strip() for x in name.split(":", 1))
    print(render(reduce(name, desc)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
