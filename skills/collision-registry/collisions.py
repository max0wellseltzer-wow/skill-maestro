"""collisions - an append-only registry that says "this idea already exists" the moment it is registered
(backs the collision-registry skill).

Every idea/skill is registered as (name, text). It is scored against EVERY earlier entry with word-shingle
Jaccard (content words, shingles of 1..k words, default k=2); each earlier entry scoring >= threshold is a
collision and is written to the registry as its own line with both ids and the score. The file is JSONL and
only ever appended to. Re-registering the same name with the same text is idempotent: no new lines, the
original verdict is returned. Same name with changed text is a new revision (and will usually collide with
its own earlier version - that is the point).

    python collisions.py register NAME "text..." [--registry FILE] [--threshold 0.4]
    python collisions.py check NAME "text..."          # dry run: score, write nothing
    python collisions.py seed-skills [SKILLS_DIR]      # register every SKILL.md description, in folder order
    python collisions.py list                          # entries and their collisions
    python collisions.py --selftest
Default registry: ~/.claude/collision-registry.jsonl
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STOP = set("a an the and or of to in on for with is are be it this that my our your i we you do does how what which "
           "when where why can should would could from by as at into about than then them they there use using "
           "whenever max pairs".split())
THRESHOLD = 0.4


def default_registry() -> Path:
    return Path.home() / ".claude" / "collision-registry.jsonl"


def words(text: str) -> list:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 3:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if len(w) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def shingles(text: str, k: int = 2) -> frozenset:
    w = words(text)
    return frozenset(" ".join(w[i:i + n]) for n in range(1, k + 1) for i in range(len(w) - n + 1))


def similarity(a: str, b: str, k: int = 2) -> float:
    sa, sb = shingles(a, k), shingles(b, k)
    return round(len(sa & sb) / len(sa | sb), 4) if sa and sb else 0.0


def _digest(name: str, text: str) -> str:
    return hashlib.sha1(f"{name}\0{text}".encode("utf-8")).hexdigest()[:16]


def read(registry) -> tuple:
    """(entries, collisions, bad_line_count). Unreadable lines are counted and skipped, never fatal."""
    entries, colls, bad = [], [], 0
    p = Path(registry)
    if not p.exists():
        return entries, colls, bad
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            kind = r["kind"]
        except (ValueError, KeyError, TypeError):
            bad += 1
            continue
        (entries if kind == "entry" else colls if kind == "collision" else []).append(r)
    return entries, colls, bad


def score(name: str, text: str, entries, threshold: float = THRESHOLD, k: int = 2) -> list:
    me = shingles(f"{name} {text}", k)
    out = []
    for e in entries:
        other = shingles(f"{e['name']} {e['text']}", k)
        s = round(len(me & other) / len(me | other), 4) if me and other else 0.0
        if s >= threshold:
            out.append({"id": e["id"], "name": e["name"], "score": s})
    return sorted(out, key=lambda c: -c["score"])


def register(name: str, text: str, registry=None, threshold: float = THRESHOLD, k: int = 2,
             dry_run: bool = False) -> dict:
    """-> {"status": "new"|"collision"|"exists", "id", "collisions": [{"id","name","score"}...]}"""
    if not isinstance(name, str) or not name.strip() or not isinstance(text, str):
        raise ValueError("register needs a non-empty name and a text string")
    registry = Path(registry) if registry else default_registry()
    entries, colls, _ = read(registry)
    h = _digest(name, text)
    for e in entries:
        if e.get("hash") == h:
            mine = [{"id": c["with"], "name": c["with_name"], "score": c["score"]} for c in colls if c["id"] == e["id"]]
            return {"status": "exists", "id": e["id"], "collisions": mine}
    hits = score(name, text, entries, threshold, k)
    new_id = max((e["id"] for e in entries), default=0) + 1
    if not dry_run:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [{"kind": "entry", "id": new_id, "name": name, "text": text, "hash": h, "ts": now}]
        lines += [{"kind": "collision", "id": new_id, "name": name, "with": c["id"], "with_name": c["name"],
                   "score": c["score"], "threshold": threshold, "ts": now} for c in hits]
        registry.parent.mkdir(parents=True, exist_ok=True)
        with registry.open("a", encoding="utf-8") as fh:               # one write: entry + its collisions together
            fh.write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines))
    return {"status": "collision" if hits else "new", "id": new_id, "collisions": hits}


def skill_texts(root: Path) -> list:
    out = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
        desc = ""
        for line in (d / "SKILL.md").read_text(encoding="utf-8", errors="replace").splitlines()[1:60]:
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip("'\"")
                break
        out.append((d.name, desc))
    return out


def _fmt(name: str, r: dict) -> str:
    s = f"{r['status']:9s} #{r['id']} {name}"
    if r["collisions"]:
        s += "  <-> " + ", ".join(f"#{c['id']} {c['name']} ({c['score']:.2f})" for c in r["collisions"][:4])
    return s


def _selftest() -> bool:
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="collisions_selftest_"))
    reg = tmp / "reg.jsonl"
    checks = {}
    try:
        a = register("token-bucket", "throttle alerts with a token bucket and burst buffer to rate limit", reg)
        b = register("hurst", "classify a time series as trending or mean reverting with the hurst exponent", reg)
        c = register("alert-throttle", "rate limit alerts with a token bucket and a burst buffer", reg)
        checks["unrelated ideas register as new with ids 1, 2"] = (a["status"], b["status"], a["id"], b["id"]) == (
            "new", "new", 1, 2)
        checks["a reworded duplicate collides with the right earlier entry, score >= threshold"] = (
            c["status"] == "collision" and c["collisions"][0]["id"] == 1 and c["collisions"][0]["score"] >= THRESHOLD
            and all(x["id"] != 2 for x in c["collisions"]))
        size = reg.stat().st_size
        again = register("alert-throttle", "rate limit alerts with a token bucket and a burst buffer", reg)
        checks["re-register is idempotent: same verdict, file unchanged"] = (
            again["status"] == "exists" and again["id"] == 3 and again["collisions"][0]["id"] == 1
            and reg.stat().st_size == size)
        entries, colls, bad = read(reg)
        checks["collision recorded append-only with both ids and the score"] = (
            len(entries) == 3 and len(colls) == 1 and colls[0]["id"] == 3 and colls[0]["with"] == 1
            and colls[0]["score"] == c["collisions"][0]["score"])
        dry = register("hurst-2", "trending or mean reverting series hurst exponent classify", reg, dry_run=True)
        checks["check (dry run) scores but writes nothing"] = dry["status"] == "collision" and reg.stat().st_size == size
        with reg.open("a", encoding="utf-8") as fh:
            fh.write("{ planted broken line\n[1,2]\n")
        d = register("kelly", "size a bet by the kelly criterion fraction", reg)
        checks["planted corrupt registry lines are skipped and counted; registry keeps working"] = (
            read(reg)[2] == 2 and d["status"] == "new" and d["id"] == 4)
        bad_in = False
        try:
            register("", "x", reg)
        except ValueError:
            bad_in = True
        checks["empty name is refused"] = bad_in
        checks["similarity: identical 1.0, disjoint 0.0, empty 0.0"] = (
            similarity("rate limit alerts", "alerts rate limit!", k=1) == 1.0 and similarity("apple pie", "zebra run") == 0
            and similarity("", "x y z") == 0.0)
    except Exception as e:
        checks[f"selftest crashed: {type(e).__name__}: {e}"] = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for k_, v in checks.items():
        print(("PASS " if v else "FAIL ") + k_)
    return all(checks.values())


def main(argv) -> int:
    argv = list(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")       # Windows cp1252 console vs non-ASCII names
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    reg, thr = default_registry(), THRESHOLD
    if "--registry" in argv:
        i = argv.index("--registry")
        reg = Path(argv[i + 1])
        del argv[i:i + 2]
    if "--threshold" in argv:
        i = argv.index("--threshold")
        thr = float(argv[i + 1])
        del argv[i:i + 2]
    cmd, rest = argv[0], argv[1:]
    if cmd in ("register", "check") and len(rest) >= 2:
        r = register(rest[0], " ".join(rest[1:]), reg, thr, dry_run=cmd == "check")
        print(_fmt(rest[0], r))
        return 0
    if cmd == "seed-skills":
        root = Path(rest[0]) if rest else Path.home() / ".claude" / "skills"
        n = 0
        for name, desc in skill_texts(root):
            r = register(name, desc, reg, thr)
            n += r["status"] == "collision"
            if r["status"] == "collision":
                print(_fmt(name, r))
        print(f"{n} collision(s) at threshold {thr} -> {reg}")
        return 0
    if cmd == "list":
        entries, colls, bad = read(reg)
        for e in entries:
            cs = [c for c in colls if c["id"] == e["id"]]
            print(f"#{e['id']} {e['name']}" + ("  <-> " + ", ".join(f"#{c['with']} {c['with_name']} ({c['score']:.2f})"
                                                                for c in cs) if cs else ""))
        print(f"{len(entries)} entries, {len(colls)} collisions" + (f", {bad} unreadable line(s)" if bad else ""))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
