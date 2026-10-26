"""seed_bank - the skills that did not survive, kept searchable (backs the skill-finder skill).

Every merge or cull leaves ideas behind in archive snapshots. This indexes each skill folder found in one or
more archive roots that is NOT in the live library, labels its fate ("merged into Y" when a live SKILL.md says
"(merged from X)" or X's files now live in Y - detection reused from wave-yield; otherwise "killed"), and
searches the dead by need with skill-finder's ranking. Revive = it prints the folder to copy from. It never
copies anything itself.

    python seed_bank.py "rate limit cooldown"            # search all of ~/.claude/skills_archive/*
    python seed_bank.py --list                           # every banked seed and its fate
    python seed_bank.py --salvage                        # working functions of the dead that no live tool has
    python seed_bank.py QUERY --archive ROOT [--archive ROOT2] [--live ROOT] [--top 8]
    python seed_bank.py --selftest

Pure stdlib + sibling imports (skill-finder, wave-yield), no network. A seed present in several archives is
listed once, from the newest archive (archives are sorted by folder name, dated names sort by date).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
SK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SK / "skill-finder"))
sys.path.insert(0, str(SK / "wave-yield"))
from find_skill import load, search  # noqa: E402
from wave_yield import merge_targets, snapshot  # noqa: E402


def default_archives() -> list:
    base = Path.home() / ".claude" / "skills_archive"
    return sorted(d for d in base.iterdir() if d.is_dir()) if base.is_dir() else []


def bank(archive_roots, live_root: Path) -> list:
    """[{name, archive, path, fate, into}] for every archived skill folder absent from the live library."""
    live = snapshot(live_root)
    seeds = {}
    for root in sorted(Path(r) for r in archive_roots):
        arch = snapshot(root)
        dead = sorted(set(arch) - set(live))
        targets = merge_targets(dead, arch, live)
        for x in dead:                                   # later (newer) archives overwrite earlier ones
            into = targets.get(x, (None, None))[0]
            seeds[x] = {"name": x, "archive": root, "path": arch[x], "into": into,
                        "fate": f"merged into {into}" if into else "killed"}
    return [seeds[k] for k in sorted(seeds)]


def find_seeds(seeds: list, query: str, top: int = 8) -> list:
    """Rank banked seeds against a need. Ranks within each archive's own corpus (so IDF reflects that
    library), keeps only banked names, then merges by score."""
    by_root = {}
    for s in seeds:
        by_root.setdefault(s["archive"], {})[s["path"].name] = s
    hits = []
    for root, names in by_root.items():
        corpus = load(root)
        for h in search(corpus, query, top=len(corpus)):
            folder = next((n for n in names if n == h["name"]), None)
            if folder is None:                               # frontmatter name may differ from folder name
                folder = next((n for n in names if names[n]["path"].name == h["name"]), None)
            if folder:
                hits.append({**names[folder], "score": h["score"], "when": h["when"], "tool": h["tool"]})
    hits.sort(key=lambda r: (-r["score"], r["name"]))
    return hits[:top]


# ---- salvage (merged from nucleosynthesis) -------------------------------------------------------------------

def _run_selftest(py: Path, timeout: int) -> str:
    """'works' / 'broken' / 'timeout' / 'untested' for one archived tool, run from a throwaway cwd with -B (the
    archive stays read-only: no __pycache__ is written into it)."""
    import os
    import subprocess
    src = py.read_text(encoding="utf-8", errors="replace")
    if "--selftest" not in src or "_selftest" not in src:
        return "untested"
    cwd = tempfile.mkdtemp(prefix="salvage_")
    try:
        r = subprocess.run([sys.executable, "-B", str(py), "--selftest"], cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return "works" if r.returncode == 0 else "broken"
    except subprocess.TimeoutExpired:
        return "timeout"
    finally:
        shutil.rmtree(cwd, ignore_errors=True)


def salvage(seeds: list, live_root: Path, timeout: int = 60) -> dict:
    """Nucleosynthesis - each generation of stars dies and forges heavier elements for the next. For the banked
    seeds, index their public functions (exaptation-finder's index), drop every function whose normalised body
    already exists anywhere in the live library (convergence-detector's fingerprint), run each remaining tool's
    --selftest, and return the raw material: {"material": [{function, seed, fate, file, status, doc}],
    "already_live": n, "tools": {file: status}}. Reads and runs only; never copies into the live library."""
    sys.path.insert(0, str(SK / "exaptation-finder"))
    sys.path.insert(0, str(SK / "convergence-detector"))
    from convergence import fingerprint  # noqa: E402
    from exaptation import index_functions  # noqa: E402
    live_hashes = {fingerprint(r["node"])[0]
                   for r in index_functions(live_root, include_private=True, keep_ast=True)}
    by_archive = {}
    for s in seeds:
        by_archive.setdefault(s["archive"], {})[s["path"].name] = s
    material, already, tools = [], 0, {}
    for root, names in by_archive.items():
        for r in index_functions(root, keep_ast=True):
            seed = names.get(r["skill"])
            if seed is None or r["name"] == "main":
                continue
            if fingerprint(r["node"])[0] in live_hashes:
                already += 1
                continue
            py = Path(root) / r["file"]
            if str(py) not in tools:
                tools[str(py)] = _run_selftest(py, timeout)
            material.append({"function": f"{r['module']}.{r['name']}", "seed": seed["name"], "fate": seed["fate"],
                             "file": str(py), "status": tools[str(py)], "doc": r["doc"]})
    order = {"works": 0, "untested": 1, "timeout": 2, "broken": 3}
    material.sort(key=lambda m: (order[m["status"]], m["seed"], m["function"]))
    return {"material": material, "already_live": already, "tools": tools}


def _selftest() -> bool:
    ok = {}
    tmp = Path(tempfile.mkdtemp(prefix="seedbank_"))
    try:
        def mk(root, name, desc, body="", files=None):
            d = root / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n{body}\n",
                                        encoding="utf-8")
            for fn, txt in (files or {}).items():
                (d / fn).write_text(txt, encoding="utf-8")
        arch, live = tmp / "archive" / "2026-01-01", tmp / "live"
        mk(arch, "token-bucket", "Throttle alerts with a token bucket and burst budget.")
        mk(arch, "refractory", "Enforce a cooldown after each alert so a rate limit is respected.")
        mk(arch, "dead-idea", "Throttle alerts by a cooldown window on rate.", files={"t.py": "x = 'orphan'\n"})
        mk(arch, "hurst", "Classify a time series as trending or mean reverting.")
        mk(live, "token-bucket", "Throttle alerts with a token bucket and burst budget.",
           body="## Cooldown (merged from refractory)")
        mk(live, "hurst", "Classify a time series as trending or mean reverting.")
        seeds = bank([arch], live)
        names = [s["name"] for s in seeds]
        ok["only archived skills absent from the live library are banked"] = names == ["dead-idea", "refractory"]
        fate = {s["name"]: s["fate"] for s in seeds}
        ok["a merged seed says where its content went"] = fate["refractory"] == "merged into token-bucket"
        ok["a seed with no trace in the live library is 'killed'"] = fate["dead-idea"] == "killed"
        hits = find_seeds(seeds, "rate limit cooldown")
        ok["a need finds the banked seeds and never a live skill"] = (
            {h["name"] for h in hits} == {"refractory", "dead-idea"})
        ok["revive points at the archive folder (a path to copy from)"] = (
            hits and all(h["path"].parent == arch and h["path"].is_dir() for h in hits))
        ok["an unrelated need returns nothing"] = find_seeds(seeds, "bake sourdough bread") == []
        try:
            bank([tmp / "missing_archive"], live)
            ok["planted bad input: a missing archive root raises"] = False
        except FileNotFoundError:
            ok["planted bad input: a missing archive root raises"] = True
        before = sorted(p.name for p in live.iterdir())
        find_seeds(bank([arch], live), "cooldown")
        ok["nothing is copied into the live library"] = sorted(p.name for p in live.iterdir()) == before
        arch2 = tmp / "archive" / "2026-02-01"
        sel = ("import sys\n{body}\ndef _selftest():\n    return {verdict}\n"
               "def main(a):\n    return 0 if _selftest() else 1\n"
               "if __name__ == '__main__':\n    sys.exit(main(sys.argv[1:]))  # --selftest\n")
        mk(live, "stats", "x", files={"st.py": "def mean(xs):\n    return sum(xs) / len(xs)\n"})
        mk(arch2, "old-stats", "x", files={"old.py": sel.format(
            body="def avg(v):\n    '''old copy'''\n    return sum(v) / len(v)\ndef geo_mean(v):\n"
                 "    p = 1.0\n    for x in v:\n        p *= x\n    return p ** (1 / len(v))", verdict="True")})
        mk(arch2, "rotten", "x", files={"rot.py": sel.format(body="def rot(v):\n    return v[::-1]",
                                                             verdict="False")})
        before = sorted(p.name for p in live.iterdir())
        sv = salvage(bank([arch2], live), live, timeout=30)
        got = {m["function"]: m["status"] for m in sv["material"]}
        ok["salvage: a body already live is dropped, working and broken raw material are told apart"] = (
            got == {"old.geo_mean": "works", "rot.rot": "broken"} and sv["already_live"] == 1
            and sorted(p.name for p in live.iterdir()) == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    archives, live, top, rest = [], Path.home() / ".claude" / "skills", 8, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--archive", "--live", "--top") and i + 1 < len(argv):
            v = argv[i + 1]
            if a == "--archive":
                archives.append(Path(v))
            elif a == "--live":
                live = Path(v)
            else:
                top = int(v)
            i += 2
        else:
            rest.append(a)
            i += 1
    archives = archives or default_archives()
    if not archives:
        print("no archive roots found (pass --archive ROOT)")
        return 1
    seeds = bank(archives, live)
    if rest == ["--salvage"]:
        sv = salvage(seeds, live)
        st = {}
        for m in sv["material"]:
            st[m["status"]] = st.get(m["status"], 0) + 1
        print(f"{len(sv['material'])} archived functions no live tool provides "
              f"({sv['already_live']} dropped as already live); by status: {st}")
        for m in sv["material"]:
            print(f"  {m['status']:8s} {m['seed']}:{m['function']:34s} [{m['fate']}]  {m['doc'][:70]}")
        return 0
    if rest == ["--list"]:
        for s in seeds:
            print(f"{s['name']:28s} {s['fate']:34s} {s['path']}")
        print(f"\n{len(seeds)} seeds in {len(archives)} archive(s)")
        return 0
    hits = find_seeds(seeds, " ".join(rest), top)
    if not hits:
        print(f"no banked seed matches ({len(seeds)} seeds searched)")
        return 0
    for h in hits:
        print(f"{h['score']:6.2f}  {h['name']:26s} [{'T' if h['tool'] else 'D'}] {h['fate']}")
        print(f"        {h['when']}")
        print(f"        revive from: {h['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
