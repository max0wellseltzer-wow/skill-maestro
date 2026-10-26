"""Fairness audit for the SKILL Maestro: does a skill's chance of being picked depend on anything but fit?

the user, 2026-10-21: "make sure skill maestro does not favor skills because they are used more often or because there is
more information known about some skills more so then others ... or adjacent to that or parallel to that or opposite
to that or around that". Every check is a counterfactual or a parity measurement on the selection core (fused
readings -> weigh -> select), so it is fast and judges nothing by eye:

    python fairness.py popularity      # F1 blind audition: the same tasks picked with the real history (use record,
                                       #    opening book, antibodies, learned duets) and with none; picks that change
                                       #    were moved by history, not by fit
    python fairness.py information     # F2 every custom skill searched by its own synthetic query; hit rate by
                                       #    quartile of how much is written about it (body, description, links),
                                       #    with and without a mechanism line, tool vs document; fair = flat
    python fairness.py sources         # F3 pool share by source (custom / plugin / built-in / synced) against
                                       #    library share, on the probes and on the odd tasks; family Gini of picks
    python fairness.py wording         # F4 asking-words: how much of the pool is taken by skills whose description
                                       #    talks about itself as a "skill" when the task says "skill" vs when not
    python fairness.py all [--out FILE]
    python fairness.py --selftest

Writes nothing to the Maestro's ledger.
"""
from __future__ import annotations

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


sys.path.insert(0, str(_core_dir()))
import maestro as M  # noqa: E402

PROBES = [M.HERE.parent / "skill-finder" / n for n in ("probes_heldout.tsv", "probes_real.tsv")] + [M.HERE / "probes_creative.tsv"]
ODD = [M.HERE / "probes_odd.tsv"]   # written 2026-10-21 before any fairness change (sha256 4be96c11536c0009)


def tasks_from(files: list[Path]) -> list[str]:
    out = []
    for f in files:
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#"):
                    out.append(line.split("\t")[0])
    return out


def library(everything: bool = True) -> "M.Library":
    lib = M.Library(M.ROOT, (), everything=everything)
    lib.cache_dir = Path(M.STATE)
    return lib


def src_of(lib: "M.Library", name: str) -> str:
    return (lib.source.get(name, "") or "custom").split(" ")[0]


def gini(xs: list[float]) -> float:
    xs = sorted(x for x in xs if x >= 0)
    n, s = len(xs), sum(xs)
    if n == 0 or s == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * s) - (n + 1) / n, 4)


def spearman(a: list[float], b: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(cov / (va * vb), 4) if va and vb else 0.0


def pick(lib: "M.Library", task: str, stats: dict, favs: set, memory: list, duets: dict, top: int = 6) -> list[str]:
    """The selection core of score(): fused readings (with these duets), opening book and antibodies (from this
    memory), weigh with these stats and favourites, select under the fit-first rule."""
    lib.duets = duets
    ranked = lib.fused(task)
    words = set(lib.fs._tokens(lib.variants(task)["_plain"]))
    book, anti = M.recall(memory, words)
    pool = [r for r in ranked[:M.POOL] if r["name"] != M.SELF and r["name"] not in anti]
    names = {r["name"] for r in pool}
    allr = {r["name"]: r for r in ranked}
    for n in book:
        if n not in names and n in allr:
            pool.append({**allr[n], "score": max(allr[n]["score"], min(r["score"] for r in pool) if pool else 0.0)})
    chosen, _ = M.select(M.weigh(pool, stats, favs), top, lib.family)
    return [c["name"] for c in chosen]


# ---- F1 popularity -------------------------------------------------------------------------------------------------
def popularity(lib: "M.Library", tasks: list[str]) -> dict:
    st = M.State(Path(M.STATE))
    stats, favs, mem, duets = st.stats(), st.favourites(), st.memory(), M.learned_duets(st.rows())
    changed, first, moved_in, moved_out, ex = 0, 0, {}, {}, []
    for t in tasks:
        a = pick(lib, t, stats, favs, mem, duets)
        b = pick(lib, t, {}, set(), [], {})
        if set(a) != set(b):
            changed += 1
            for n in set(a) - set(b):
                moved_in[n] = moved_in.get(n, 0) + 1
            for n in set(b) - set(a):
                moved_out[n] = moved_out.get(n, 0) + 1
            if len(ex) < 6:
                ex.append({"task": t[:70], "history_added": sorted(set(a) - set(b)), "history_removed": sorted(set(b) - set(a))})
        first += a[:1] != b[:1]
    rated = sum(1 for v in stats.values() if any(v.values()))
    return {"tasks": len(tasks), "skills_with_any_history": rated, "picks_changed_by_history": changed,
            "first_pick_changed_by_history": first,
            "history_lifted_most": sorted(moved_in.items(), key=lambda x: -x[1])[:8],
            "history_pushed_out_most": sorted(moved_out.items(), key=lambda x: -x[1])[:8], "examples": ex}


# ---- F2 information ------------------------------------------------------------------------------------------------
def information(lib_custom: "M.Library") -> dict:
    lib = lib_custom
    lib.duets = {}
    f = HERE / "intents" / "intents.json"            # v20: the file left the package; F2 then measures an empty set
    queries = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    names = sorted(x for x in queries if x in lib.desc and queries[x] and x != M.SELF)
    mechs, graph = M.load_mechanisms(), lib.graph()
    byname = {s["name"]: s for s in lib.skills}
    feats, hit6, hitp = {}, {}, {}
    for n in names:
        md = lib.skill_md(n)
        feats[n] = {"body": len(md.read_text(encoding="utf-8", errors="replace")) if md.is_file() else 0,
                    "desc": len(lib.desc[n]), "links": len(graph.get(n, ())), "mech": int(n in mechs),
                    "tool": int(bool(byname[n].get("tool")))}
        ranked = [r["name"] for r in lib.fused(queries[n][-1])]   # the last query: never shown on a sheet
        hit6[n], hitp[n] = int(n in ranked[:6]), int(n in ranked[:M.POOL])
    out = {"skills": len(names), "hit@6": round(sum(hit6.values()) / len(names), 3),
           "hit@pool": round(sum(hitp.values()) / len(names), 3)}
    for key in ("body", "desc", "links"):
        vals = sorted(feats[x][key] for x in names)
        cuts = [vals[int(len(vals) * q)] for q in (0.25, 0.5, 0.75)]
        rates = {}
        for qn in range(4):
            mem = [x for x in names if sum(feats[x][key] > c for c in cuts) == qn]
            rates[f"Q{qn + 1}"] = [round(sum(hit6[x] for x in mem) / max(1, len(mem)), 3), len(mem)]
        out[key] = {"hit@6 by quartile [rate, n]": rates,
                    "spearman(amount, hit@6)": spearman([feats[x][key] for x in names], [hit6[x] for x in names])}
    for flag in ("mech", "tool"):
        g1, g0 = [x for x in names if feats[x][flag]], [x for x in names if not feats[x][flag]]
        out[flag] = {"with": [round(sum(hit6[x] for x in g1) / max(1, len(g1)), 3), len(g1)],
                     "without": [round(sum(hit6[x] for x in g0) / max(1, len(g0)), 3), len(g0)]}
    return out


# ---- F3 sources and families ---------------------------------------------------------------------------------------
def sources(lib: "M.Library", tasks: list[str], label: str) -> dict:
    lib.duets = {}
    lib_share: dict[str, int] = {}
    for s in lib.skills:
        lib_share[src_of(lib, s["name"])] = lib_share.get(src_of(lib, s["name"]), 0) + 1
    pool_share: dict[str, int] = {}
    top6_share: dict[str, int] = {}
    fams: dict[str, int] = {}
    for t in tasks:
        ranked = [r for r in lib.fused(t) if r["name"] != M.SELF]
        for r in ranked[:M.POOL]:
            pool_share[src_of(lib, r["name"])] = pool_share.get(src_of(lib, r["name"]), 0) + 1
        for r in ranked[:6]:
            top6_share[src_of(lib, r["name"])] = top6_share.get(src_of(lib, r["name"]), 0) + 1
            fams[lib.family(r["name"])] = fams.get(lib.family(r["name"]), 0) + 1
    tl, tp, t6 = sum(lib_share.values()), max(1, sum(pool_share.values())), max(1, sum(top6_share.values()))
    return {"tasks": f"{len(tasks)} ({label})",
            "share [library, pool@40, top6]": {k: [round(lib_share[k] / tl, 3), round(pool_share.get(k, 0) / tp, 3),
                                                   round(top6_share.get(k, 0) / t6, 3)] for k in sorted(lib_share)},
            "family_gini_top6": gini(list(fams.values())), "families_in_top6": len(fams)}


# ---- F4 asking-words -----------------------------------------------------------------------------------------------
def wording(lib: "M.Library", tasks: list[str]) -> dict:
    lib.duets = {}
    selfref = {s["name"] for s in lib.skills if " skill" in (" " + s["desc"].lower())}
    with_word, without = [], []
    for t in tasks:
        names = [r["name"] for r in lib.fused(t)[:M.POOL] if r["name"] != M.SELF]
        share = sum(n in selfref for n in names) / max(1, len(names))
        (with_word if " skill" in (" " + t.lower()) else without).append(share)
    base = len(selfref) / len(lib.skills)
    avg = lambda v: round(sum(v) / max(1, len(v)), 3)  # noqa: E731
    return {"self-describing skills (library share)": round(base, 3),
            "their pool share when the task says 'skill'": [avg(with_word), len(with_word)],
            "their pool share otherwise": [avg(without), len(without)]}


def _selftest() -> bool:
    ok = [gini([1, 1, 1, 1]) == 0.0, gini([0, 0, 0, 10]) > 0.7,
          spearman([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0, spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0,
          spearman([1, 2, 3, 4], [1, 1, 1, 1]) == 0.0, len(tasks_from(ODD)) == 20]
    print(f"FAIRNESS SELFTEST {'PASS' if all(ok) else 'FAIL'} {sum(ok)}/{len(ok)}")
    return all(ok)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return 0 if _selftest() else 1
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    M.apply_dials(M.load_dials()[0])
    t0 = time.time()
    tasks, odd = tasks_from(PROBES), tasks_from(ODD)
    lib = library()
    res: dict = {"t": int(t0), "code": M.hashlib.sha256((M.HERE / "maestro.py").read_bytes()).hexdigest()[:12],
                 "weights": dict(M.WEIGHTS), "tool_bonus": M.TOOL_BONUS}
    cmd = argv[0]
    if cmd in ("popularity", "all"):
        res["F1_popularity"] = popularity(lib, tasks + odd)
    if cmd in ("information", "all"):
        res["F2_information"] = information(library(everything=False))
    if cmd in ("sources", "all"):
        res["F3_sources_probes"] = sources(lib, tasks, "probes")
        res["F3_sources_odd"] = sources(lib, odd, "odd tasks")
    if cmd in ("wording", "all"):
        res["F4_wording"] = wording(lib, tasks + odd)
    res["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(res, indent=1))
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
