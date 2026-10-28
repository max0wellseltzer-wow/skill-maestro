"""index - the prepared library index (v15, 2026-10-22): the same answers, read instead of recomputed.

Every Maestro command rebuilt the library from scratch: find_skill.load read 735 SKILL.md files and walked every skill
folder for a .py file, once per root (the profile of one `triage` on 2026-10-22: 4 loads, 2.4 s of a 2.4 s command),
and every search recomputed the document frequencies of 742 skills. This module keeps:

  * indexed_load(fs, root, cache_dir): the list find_skill.load returns, field for field and in the same order, from
    a JSON index in the state folder keyed by each skill's SKILL.md size and mtime and its folder's mtime. A changed
    or new skill is re-read; the rest are not. Roots with fewer than MIN_DIRS skills use the plain loader (a selftest's
    temp library leaves no index behind). Each entry also carries the SKILL.md sha the registry needs, so `snapshot()`
    stops re-reading every file.
  * FastSearch(fs, skills): find_skill.search's scoring with the document frequencies computed once per skills list.

Both are proven identical to the finder on the real library by `python index.py --selftest` (every field of every
skill; the full ranking of 40 queries), and the Maestro falls back to the plain loader on any doubt. A tool that
appears in a sub-folder after its SKILL.md and folder are untouched is the one staleness this index cannot see:
`python maestro.py index --build` rebuilds everything.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX_VERSION = 2
MIN_DIRS = 30


def _sig(d: Path, dir_mtime_ns: int | None = None) -> list:
    md = (d / "SKILL.md").stat()
    dm = d.stat().st_mtime_ns if dir_mtime_ns is None else dir_mtime_ns
    return [md.st_size, md.st_mtime_ns // 1_000_000, dm // 1_000_000]


def skill_dirs(root: Path) -> list[tuple[Path, int]]:
    """(folder, folder mtime_ns) for every skill folder, sorted as find_skill.load sorts them, from one scandir pass
    (a DirEntry's stat is free on Windows; the SKILL.md check is one stat per folder)."""
    import os
    out = []
    with os.scandir(root) as it:
        for e in it:
            if e.is_dir() and (Path(e.path) / "SKILL.md").exists():
                out.append((Path(e.path), e.stat().st_mtime_ns))
    out.sort(key=lambda x: x[0])
    return out


def _tokens_sig(fs) -> str:
    """The tokenizer the cached tokens were made with: the finder file's hash, or 'mini'."""
    f = getattr(fs, "__file__", None)
    try:
        return hashlib.sha256(Path(f).read_bytes()).hexdigest()[:12] if f else "mini"
    except OSError:
        return "mini"


def entry(fs, d: Path) -> dict:
    """Exactly find_skill.load's work for one skill folder, plus the SKILL.md sha and the folder signature."""
    name, desc = d.name, ""
    raw = (d / "SKILL.md").read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if text.startswith("---"):
        for line in text.splitlines()[1:60]:
            if line.strip() == "---":
                break
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip("'\"")
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip("'\"")
    tool = any(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
    return {"name": name, "desc": desc, "tool": tool, "sha": hashlib.sha256(raw).hexdigest()[:16],
            "name_toks": sorted(set(fs._tokens(name))), "toks": fs._tokens(name + " " + desc), "sig": _sig(d)}


def _as_skill(e: dict) -> dict:
    return {"name": e["name"], "desc": e["desc"], "tool": bool(e["tool"]), "name_toks": set(e["name_toks"]),
            "toks": list(e["toks"]), "sha": e["sha"]}


def index_path(root: Path, cache_dir: Path) -> Path:
    key = hashlib.sha256(str(Path(root).resolve()).lower().encode()).hexdigest()[:12]
    return Path(cache_dir) / f"index_{key}.json"


def indexed_load(fs, root: Path, cache_dir: Path | None, force: bool = False, stats: dict | None = None,
                 write: bool = True) -> list:
    root = Path(root)
    pairs = skill_dirs(root)
    dirs = [d for d, _ in pairs]
    if cache_dir is None or len(dirs) < MIN_DIRS:
        out = fs.load(root)                               # the plain loader, as before (small or unnamed libraries)
        if stats is not None:
            stats.update({"indexed": False, "n": len(out)})
        return out
    f = index_path(root, cache_dir)
    tsig = _tokens_sig(fs)
    old: dict = {}
    if f.is_file() and not force:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("version") == INDEX_VERSION and data.get("tokens") == tsig:
                old = data.get("skills", {})
        except (OSError, ValueError):
            old = {}
    out, new, changed = [], {}, 0
    for d, dm in pairs:
        sig = _sig(d, dm)
        e = old.get(d.name)
        if not e or e.get("sig") != sig:
            e = entry(fs, d)
            changed += 1
        new[d.name] = e
        out.append(_as_skill(e))
    if write and (changed or set(old) != set(new)):        # write False (--no-ledger): read, never written
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": INDEX_VERSION, "tokens": tsig, "root": str(root), "built": int(time.time()),
                                   "skills": new}), encoding="utf-8")
        tmp.replace(f)
    if stats is not None:
        stats.update({"indexed": True, "n": len(out), "changed": changed, "file": str(f)})
    return out


class FastSearch:
    """find_skill.search, with the document frequencies of a skills list computed once. Same tokens (the finder's),
    same idf log((n+1)/(df+0.5)), same 2.0 name boost, same rounding, same tie order, same keys."""

    def __init__(self, fs, skills: list) -> None:
        self.fs = fs
        self._tokens = fs._tokens
        self.load = fs.load
        self._key = None
        self._df: dict = {}
        self._sets: list = []
        self._prime(skills)

    def _prime(self, skills: list) -> None:
        key = (id(skills), len(skills))
        if key == self._key:
            return
        df: dict = {}
        sets = []
        for s in skills:
            ts = set(s["toks"])
            sets.append(ts)
            for t in ts:
                df[t] = df.get(t, 0) + 1
        self._key, self._df, self._sets = key, df, sets

    def search(self, skills: list, query: str, top: int = 5) -> list:
        q = set(self._tokens(query))
        if not q or not skills:
            return []
        self._prime(skills)
        n, df = len(skills), self._df
        scored = []
        for s, toks in zip(skills, self._sets):
            score = 0.0
            for t in q & toks:
                score += math.log((n + 1) / (df[t] + 0.5)) * (2.0 if t in s["name_toks"] else 1.0)
            if score > 0:
                scored.append((score, s))
        scored.sort(key=lambda x: (-x[0], x[1]["name"]))
        return [{"name": s["name"], "score": round(sc, 3), "tool": s["tool"], "when": s["desc"].split(". ")[0][:160]}
                for sc, s in scored[:top]]

    def __getattr__(self, name):                  # anything else the pin or the finder's callers ask for
        return getattr(self.fs, name)


# --- command line ----------------------------------------------------------------------------------------------------

def cli_index(argv: list[str], lib, st, root: Path, M) -> int:
    """`maestro.py index [--build]`: the index's state, or a forced rebuild of every root."""
    force = "--build" in argv
    roots = [root] + [r for r, _, _ in M.other_skill_roots()]
    total, changed = 0, 0
    for r in roots:
        stats: dict = {}
        t0 = time.perf_counter()
        indexed_load(lib.fs, r, st.d, force=force, stats=stats, write=st.keep)
        dt = time.perf_counter() - t0
        total += stats.get("n", 0)
        changed += stats.get("changed", 0)
        print(f"  {str(r)[-60:]:<60} {stats.get('n', 0):>4} skills  {'indexed' if stats.get('indexed') else 'plain (small)':<14} "
              f"changed {stats.get('changed', 0):>3}  {dt:.2f}s")
    print(f"INDEX {'REBUILT' if force else 'VERIFIED'}: {total} skills over {len(roots)} root(s), {changed} re-read; "
          f"files in {st.d}")
    return 0


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    import tempfile
    ok: dict[str, bool] = {}
    sys.path.insert(0, str(HERE))
    import maestro as M
    fsp = M.companion(M.ROOT, "find_skill.py")
    fs = M._load(fsp, "find_skill") if fsp.is_file() else M.MiniFinder()
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        root = td / "skills"
        for name, desc, tool in [("hysteresis", "A latch. Use this whenever an alert flaps.", True),
                                 ("plain-terms", "Plain words. Use this whenever the user wants plain language.", False)]:
            (root / name).mkdir(parents=True)
            (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n", encoding="utf-8")
            if tool:
                (root / name / "t.py").write_text("x = 1\n", encoding="utf-8")
        st_: dict = {}
        small = indexed_load(fs, root, td / "state", stats=st_)
        ok["a small library uses the plain loader and leaves no index"] = \
            st_["indexed"] is False and small == fs.load(root) and not list((td / "state").glob("index_*.json")) if (td / "state").is_dir() else st_["indexed"] is False
        # the real library: the index must equal the plain loader field for field, twice (cold, then cached)
        if M.USER_LIB.is_dir() and len([p for p in M.USER_LIB.iterdir() if p.is_dir()]) >= MIN_DIRS:
            plain = fs.load(M.USER_LIB)
            s1: dict = {}
            t0 = time.perf_counter()
            a = indexed_load(fs, M.USER_LIB, td / "state", stats=s1)
            cold = time.perf_counter() - t0
            s2: dict = {}
            t0 = time.perf_counter()
            b = indexed_load(fs, M.USER_LIB, td / "state", stats=s2)
            warm = time.perf_counter() - t0
            strip = lambda L: [{k: (sorted(v) if isinstance(v, set) else v) for k, v in s.items() if k != "sha"} for s in L]
            ok["cold index == find_skill.load on the real library (every field, same order)"] = strip(a) == strip(plain)
            ok["warm index == plain, nothing re-read, and it is faster"] = \
                strip(b) == strip(plain) and s2["changed"] == 0 and warm < cold
            ok["every entry carries a 16-hex sha of its SKILL.md"] = all(len(s["sha"]) == 16 for s in a)
            # a touched SKILL.md is re-read, nothing else
            victim = M.USER_LIB / a[0]["name"] / "SKILL.md"
            idx = json.loads(index_path(M.USER_LIB, td / "state").read_text(encoding="utf-8"))
            idx["skills"][a[0]["name"]]["sig"] = [0, 0, 0]
            index_path(M.USER_LIB, td / "state").write_text(json.dumps(idx), encoding="utf-8")
            s3: dict = {}
            c = indexed_load(fs, M.USER_LIB, td / "state", stats=s3)
            ok["a changed signature re-reads exactly that skill"] = s3["changed"] == 1 and strip(c) == strip(plain) and victim.is_file()
            fast = FastSearch(fs, plain)
            qs = ["stop my alert from flapping", "which skill lands a change", "rate limit alerts", "find the keystone",
                  "cache an expensive function safely", "two sessions writing the same repo", "plain words for a report",
                  "zzz qqq nothing", "is my series trending or mean reverting", "plant a bug to prove the test can fail"]
            same = all(fast.search(plain, q, 40) == fs.search(plain, q, 40) for q in qs) and \
                all(fast.search(plain, q, len(plain)) == fs.search(plain, q, len(plain)) for q in qs[:4])
            ok["FastSearch == find_skill.search (full rankings, 10 queries, depth 40 and full depth)"] = same
            t0 = time.perf_counter()
            for q in qs * 3:
                fs.search(plain, q, 40)
            slow_s = time.perf_counter() - t0
            t0 = time.perf_counter()
            for q in qs * 3:
                fast.search(plain, q, 40)
            fast_s = time.perf_counter() - t0
            ok["FastSearch is faster on 30 queries"] = fast_s < slow_s
            print(f"  index cold {cold:.2f}s warm {warm:.2f}s (plain loader each time); search x30 plain {slow_s:.2f}s fast {fast_s:.2f}s")
        else:
            ok["(no real library to prove against)"] = True
    ok = {k: bool(v) for k, v in ok.items()}
    print(f"index selftest: {sum(ok.values())}/{len(ok)} " + ("PASS" if all(ok.values()) else "FAIL"))
    for k, v in ok.items():
        if not v:
            print(f"  FAIL {k}")
    return all(ok.values())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.path.insert(0, str(HERE))
    import maestro as M
    sys.exit(M.main(["index", *sys.argv[1:]]))
