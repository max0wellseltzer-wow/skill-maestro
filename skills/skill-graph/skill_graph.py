"""skill_graph - the skill library as a graph: who leans on whom (backs the skill-graph skill).

Nodes are skill folders. An undirected edge A - B exists when
  text    A's SKILL.md names B: a hyphenated name anywhere in the text, a one-word name only inside a
          "Pairs with ..." clause or in `backticks` (one-word names like 'bud' or 'lindy' are ordinary words);
  import  a .py in A imports a module that lives in B's folder, or builds a path to it (SK / "B").
Roles per node:
  HUB     degree >= max(4, mean + 2 sd)              - many skills point here; a break hurts widely
  BRIDGE  betweenness >= max(0.02, mean + 2 sd), or an articulation point that cuts off >= 2 skills
          - remove it and parts of the library stop reaching each other
  LEAF    degree 1                                    - hangs off a single neighbour
  ORPHAN  degree 0                                    - nothing names it and it names nothing
Dangling references: a single hyphenated name in a "Pairs with" list that has no folder (renamed, merged or
never built); one-word items there are usually prose and are skipped.
One-way pairs (merged from dangling-pairs): (A, B) where A's "Pairs with" names B but B's SKILL.md never names A -
reported as a list in build()["one_way"], never as an error.

    python skill_graph.py live [--node NAME]        # 'live' = ~/.claude/skills
    python skill_graph.py ROOT [--node NAME]        # any other library root
    python skill_graph.py --selftest

Pure stdlib (regex scan + BFS, Brandes betweenness), no network. ~220 nodes runs in a few seconds.
"""
from __future__ import annotations

import re
import shutil
import statistics
import sys
import tempfile
from collections import deque
from pathlib import Path

sys.dont_write_bytecode = True
IGNORE = {"synced", "__pycache__"}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PAIRS = re.compile(r"pairs? with (.+?)(?:\.(?:\s|$)|\n\n|$)", re.I | re.S)
SK_PATH = re.compile(r"""SK\s*/\s*["']([a-z0-9][a-z0-9-]*)["']""")
IMPORT_LINE = re.compile(r"^[ \t]*(?:from[ \t]+([A-Za-z_]\w*)[\w.]*[ \t]+import\b|import[ \t]+([\w., \t]+))", re.M)


def pairs_items(text: str) -> list:
    """Every item named in a 'Pairs with ...' clause, parentheticals removed."""
    out = []
    for m in PAIRS.finditer(text):
        clause = re.sub(r"\([^)]*\)", " ", m.group(1))
        for item in re.split(r",|;|\band\b|\bor\b|\n", clause):
            item = item.strip().strip("`*'\" ").lower()
            if item:
                out.append(item)
    return out


def text_refs(text: str, names: set, self_name: str) -> tuple:
    """(set of skill names referenced, list of dangling single-slug pairs-with names)."""
    refs, dangling = set(), []
    for item in pairs_items(text):
        if SLUG.match(item):
            if item in names:
                refs.add(item)
            elif "-" in item and item != self_name:      # one-word items are usually prose ("pairs with different")
                dangling.append(item)
        else:
            refs |= {w for w in re.findall(r"[a-z0-9][a-z0-9-]*", item) if w in names}
    refs |= {w for w in re.findall(r"`([a-z0-9][a-z0-9-]*)`", text) if w in names}
    refs |= {w for w in re.findall(r"(?<![\w-])[a-z0-9]+(?:-[a-z0-9]+)+(?![\w-])", text.lower()) if w in names}
    refs.discard(self_name)
    return refs, sorted(set(dangling))


def import_refs(skill_dir: Path, stem_owner: dict, names: set) -> set:
    refs = set()
    for py in skill_dir.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        src = py.read_text(encoding="utf-8", errors="replace")
        refs |= {m for m in SK_PATH.findall(src) if m in names}
        mods = set()
        for frm, imp in IMPORT_LINE.findall(src):
            if frm:
                mods.add(frm)
            else:
                mods |= {a.strip().split(" ")[0].split(".")[0] for a in imp.split(",")}
        for m in mods:
            refs |= stem_owner.get(m, set())
    refs.discard(skill_dir.name)
    return refs


def build(root: Path) -> dict:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"not a library root: {root}")
    dirs = {d.name: d for d in sorted(root.iterdir())
            if d.is_dir() and d.name not in IGNORE and (d / "SKILL.md").is_file()}
    names = set(dirs)
    stem_owner = {}
    for n, d in dirs.items():
        for py in d.rglob("*.py"):
            if "__pycache__" not in py.parts:
                stem_owner.setdefault(py.stem, set()).add(n)
    adj = {n: set() for n in names}
    kinds, dangling, names_of, pairs_of = {}, {}, {}, {}
    for n, d in dirs.items():
        text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        t_refs, dang = text_refs(text, names, n)
        names_of[n], pairs_of[n] = t_refs, pair_targets(text, names, n)
        i_refs = import_refs(d, stem_owner, names)
        if dang:
            dangling[n] = dang
        for m, kind in [(m, "text") for m in t_refs] + [(m, "import") for m in i_refs]:
            adj[n].add(m)
            adj[m].add(n)
            kinds.setdefault(frozenset((n, m)), set()).add(kind)
    one_way = sorted((a, b) for a, bs in pairs_of.items() for b in bs if a not in names_of[b])
    return {"adj": adj, "kinds": kinds, "dangling": dangling, "one_way": one_way}


def pair_targets(text: str, names: set, self_name: str) -> set:
    """Skills named inside this SKILL.md's 'Pairs with ...' clauses (the directed half of the graph)."""
    out = set()
    for item in pairs_items(text):
        if SLUG.match(item):
            out |= {item} & names
        else:
            out |= {w for w in re.findall(r"[a-z0-9][a-z0-9-]*", item) if w in names}
    out.discard(self_name)
    return out


def _components(adj: dict, removed=None) -> list:
    seen, comps = {removed}, []
    for s in adj:
        if s in seen:
            continue
        comp, q = [], deque([s])
        seen.add(s)
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        comps.append(comp)
    return comps


def betweenness(adj: dict) -> dict:
    """Brandes (2001), unweighted undirected, normalized to [0, 1]."""
    bc = dict.fromkeys(adj, 0.0)
    for s in adj:
        stack, pred = [], {v: [] for v in adj}
        sigma, dist = dict.fromkeys(adj, 0), dict.fromkeys(adj, -1)
        sigma[s], dist[s] = 1, 0
        q = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = dict.fromkeys(adj, 0.0)
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += sigma[v] / sigma[w] * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]
    n = len(adj)
    norm = (n - 1) * (n - 2) if n > 2 else 1          # undirected: each pair counted twice, so /2 * 2/(n-1)(n-2)
    return {v: b / norm for v, b in bc.items()}


def cut_size(adj: dict, node: str) -> int:
    """Skills cut off from the largest remaining piece when `node` is removed (0 = not an articulation point)."""
    own = next(c for c in _components(adj) if node in c)
    sub = {u: adj[u] & set(own) for u in own}
    pieces = sorted((len(c) for c in _components(sub, removed=node)), reverse=True)
    return sum(pieces[1:])


def roles(graph: dict) -> dict:
    adj = graph["adj"]
    deg = {n: len(v) for n, v in adj.items()}
    bc = betweenness(adj)
    dv, bv = list(deg.values()), list(bc.values())
    hub_t = max(4, statistics.mean(dv) + 2 * statistics.pstdev(dv)) if dv else 4
    br_t = max(0.02, statistics.mean(bv) + 2 * statistics.pstdev(bv)) if bv else 1
    rows = []
    for n in sorted(adj):
        r, cut = [], (cut_size(adj, n) if deg[n] >= 2 else 0)
        if deg[n] == 0:
            r.append("ORPHAN")
        elif deg[n] == 1:
            r.append("LEAF")
        if deg[n] >= hub_t:
            r.append("HUB")
        if bc[n] >= br_t or cut >= 2:
            r.append("BRIDGE")
        rows.append({"skill": n, "degree": deg[n], "betweenness": round(bc[n], 4), "cuts_off": cut, "roles": r})
    edges = len(graph["kinds"])
    return {"rows": rows, "nodes": len(adj), "edges": edges,
            "import_edges": sum("import" in k for k in graph["kinds"].values()),
            "components": len(_components(adj)), "hub_threshold": round(hub_t, 2),
            "bridge_threshold": round(br_t, 4), "dangling": graph["dangling"], "one_way": graph.get("one_way", [])}


def _print(rep: dict, node=None) -> None:
    rows = rep["rows"]
    by = lambda role: [r for r in rows if role in r["roles"]]   # noqa: E731
    if node:
        r = next((x for x in rows if x["skill"] == node), None)
        print(r if r else f"no skill named {node}")
        return
    print(f"nodes {rep['nodes']}  edges {rep['edges']} ({rep['import_edges']} with imports)  "
          f"components {rep['components']}  hub>=deg {rep['hub_threshold']}  bridge>=btw {rep['bridge_threshold']}")
    hubs = sorted(by("HUB"), key=lambda r: -r["degree"])
    print(f"HUB    {len(hubs)}: " + ", ".join(f"{r['skill']}({r['degree']})" for r in hubs))
    br = sorted(by("BRIDGE"), key=lambda r: -r["betweenness"])
    print(f"BRIDGE {len(br)}: " + ", ".join(f"{r['skill']}({r['betweenness']:.3f}"
                                             + (f",cuts {r['cuts_off']}" if r["cuts_off"] >= 2 else "") + ")"
                                             for r in br))
    print(f"LEAF   {len(by('LEAF'))}")
    print(f"ORPHAN {len(by('ORPHAN'))}: " + ", ".join(r["skill"] for r in by("ORPHAN")))
    d = rep["dangling"]
    print(f"DANGLING refs {sum(map(len, d.values()))}: "
          + ("; ".join(f"{k} -> {', '.join(v)}" for k, v in sorted(d.items())) or "-"))
    ow = rep.get("one_way", [])                      # a list to read, not an error: the exit code stays 0
    print(f"ONE-WAY pairs {len(ow)} (A pairs with B, B never names A): "
          + ("; ".join(f"{a} -> {b}" for a, b in ow) or "-"))


def _selftest() -> bool:
    ok = {}
    tmp = Path(tempfile.mkdtemp(prefix="skillgraph_"))
    try:
        def mk(name, body, py=None):
            d = tmp / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n{body}\n", encoding="utf-8")
            if py:
                (d / py[0]).write_text(py[1], encoding="utf-8")
        mk("core-hub", "The centre.", py=("core_tool.py", "x = 1\n"))
        for s in ("a-one", "a-two", "a-three"):
            mk(s, "Pairs with core-hub.")
        mk("joiner", "Uses `core-hub`.", py=("j.py", "from far_tool import y\n"))
        mk("far-side", "Pairs with far-leaf and ghost-skill (renamed).", py=("far_tool.py", "y = 2\n"))
        mk("far-leaf", "Stands at the end.")
        mk("lonely", "Mentions nothing. A bud is just a word here.")
        mk("bud", "One-word name.")
        (tmp / "synced").mkdir()
        rep = roles(build(tmp))
        R = {r["skill"]: r for r in rep["rows"]}
        ok["synced/ is ignored and every skill folder is a node"] = rep["nodes"] == 9 and "synced" not in R
        ok["the most-named skill is a HUB"] = "HUB" in R["core-hub"]["roles"]
        ok["a python import of a sibling module makes an edge"] = "far-side" in build(tmp)["adj"]["joiner"]
        ok["the skill joining two clusters is a BRIDGE (articulation point)"] = (
            "BRIDGE" in R["joiner"]["roles"] and R["joiner"]["cuts_off"] >= 2)
        ok["degree-1 skills are LEAFs"] = all("LEAF" in R[s]["roles"] for s in ("a-one", "far-leaf"))
        ok["a one-word name used as an ordinary word is not an edge (lonely, bud stay ORPHAN)"] = (
            R["lonely"]["roles"] == ["ORPHAN"] and R["bud"]["roles"] == ["ORPHAN"])
        ok["planted bad input: a Pairs-with name with no folder is reported dangling"] = (
            rep["dangling"] == {"far-side": ["ghost-skill"]})
        bc = betweenness({"x": {"y"}, "y": {"x", "z"}, "z": {"y"}})
        ok["betweenness of a 3-path's middle is 1.0, ends 0"] = bc == {"x": 0.0, "y": 1.0, "z": 0.0}
        lib2 = tmp / "synced" / "oneway"                 # planted: mutual pair, one-way pair, prose mention
        for nm, body in (("ping-a", "Pairs with ping-b."), ("ping-b", "Pairs with ping-a."),
                         ("solo-c", "Pairs with ping-a and ghost-x."), ("talk-d", "Mentions solo-c in prose.")):
            (lib2 / nm).mkdir(parents=True)
            (lib2 / nm / "SKILL.md").write_text(f"---\nname: {nm}\ndescription: x\n---\n{body}\n", encoding="utf-8")
        ok["planted one-way pair: solo-c -> ping-a flagged; mutual and prose-only mentions are not"] = (
            build(lib2)["one_way"] == [("solo-c", "ping-a")] and build(tmp)["one_way"][:1] == [("a-one", "core-hub")])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    node = None
    if "--node" in argv:
        i = argv.index("--node")
        node = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    root = Path(argv[0]) if argv and argv[0] != "live" else Path.home() / ".claude" / "skills"
    _print(roles(build(root)), node)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
