"""route_rank - WARN for skills the router never finds (patch for skill-health: "healthy" should mean retrievable).

skill-health checks that a skill is well formed. It can report FAIL 0 / WARN 0 while 26 skills never reach the
router's top 5 for their own pitch (2026-10-15). This runs route-audit once per library STATE and caches the result
by a hash of every SKILL.md, so a repeat health check costs nothing until a skill changes. It prints one WARN line per
unreachable skill.

    python route_rank.py <skills root> [--top 5] [--cache DIR]      # default cache: the system temp dir
    python route_rank.py --selftest
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


def library_hash(root: Path) -> str:
    h = hashlib.sha256()
    for d in sorted(p for p in Path(root).iterdir() if (p / "SKILL.md").is_file()):
        h.update(d.name.encode("utf-8") + b"\0")
        h.update((d / "SKILL.md").read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def _route_audit(root: Path):
    path = Path(root) / "route-audit" / "route_audit.py"
    spec = importlib.util.spec_from_file_location("route_audit", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def route_rank(root: Path, top: int = 5, cache: Path | None = None, runner=None) -> dict:
    """{'hash', 'missed': [...], 'top1': {skill: router's pick}, 'cached': bool}."""
    root = Path(root)
    cache = Path(cache) if cache else Path(tempfile.gettempdir())
    key = library_hash(root)
    f = cache / f"route_rank_{key[:16]}_top{top}.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        data["cached"] = True
        return data
    rep = (runner or (lambda r, t: _route_audit(r).route_audit(r, t)))(root, top)
    data = {"hash": key, "missed": rep["missed"], "top1": {a: b for a, b in rep["confusions"]}}
    cache.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=1), encoding="utf-8")
    data["cached"] = False
    return data


def warn_lines(data: dict, top: int) -> list:
    return [f"WARN {s}: never in top-{top} for its own pitch (router said {data['top1'].get(s)})"
            for s in data["missed"]]


def _selftest() -> bool:
    import shutil
    ok = {}
    root = Path(tempfile.mkdtemp(prefix="route_rank_"))
    cache = root / "_cache"
    calls = []

    def fake(r, t):
        calls.append(t)
        return {"missed": ["ghost"], "confusions": [("ghost", "loud"), ("twin", "twin2")]}
    try:
        for n in ("ghost", "loud"):
            (root / n).mkdir()
            (root / n / "SKILL.md").write_text(f"---\nname: {n}\ndescription: d\n---\n", encoding="utf-8")
        d1 = route_rank(root, 5, cache, fake)
        ok["first run computes and lists the unreachable skill"] = (not d1["cached"]) and d1["missed"] == ["ghost"]
        d2 = route_rank(root, 5, cache, fake)
        ok["second run on the same library is a cache hit (audit not rerun)"] = d2["cached"] and len(calls) == 1
        h1 = library_hash(root)
        (root / "loud" / "SKILL.md").write_text("---\nname: loud\ndescription: changed\n---\n", encoding="utf-8")
        ok["editing any SKILL.md changes the library hash"] = library_hash(root) != h1
        route_rank(root, 5, cache, fake)
        ok["a changed library reruns the audit"] = len(calls) == 2
        (root / "loud" / "SKILL.md").write_bytes(b"---\nname: loud\ndescription: changed\n---\n")
        h_lf = library_hash(root)
        (root / "loud" / "SKILL.md").write_bytes(b"---\r\nname: loud\r\ndescription: changed\r\n---\r\n")
        ok["CRLF vs LF of the same text is the same library"] = library_hash(root) == h_lf
        lines = warn_lines(d1, 5)
        ok["one WARN line per missed skill, naming the router's pick"] = lines == [
            "WARN ghost: never in top-5 for its own pitch (router said loud)"]
        route_rank(root, 3, cache, fake)
        ok["a different --top is cached separately"] = calls[-1] == 3
    finally:
        shutil.rmtree(root, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 5
    cache = Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    data = route_rank(Path(argv[0]), top, cache)
    for line in warn_lines(data, top):
        print(line)
    print(f"route-rank: {len(data['missed'])} WARN ({'cached' if data['cached'] else 'computed'}, "
          f"library {data['hash'][:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
