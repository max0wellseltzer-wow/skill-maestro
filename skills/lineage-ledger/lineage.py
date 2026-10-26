"""lineage - every skill's family tree: parents, operator, the prompt that caused it, and who chose it
(backs the lineage-ledger skill).

Append-only JSONL, one record per birth:
    {"skill", "parents": [...], "operator", "prompt": "the user's words", "prompt_date", "chooser": "max"|"claude", "date"}
"chooser" keeps the lesson of the 2026-10-14 waves: once the user said "skills that simply fascinate you", the choices
were mine, not his - and that is where most of the later duplicates came from. Record it.

    from lineage import record, ancestors, descendants, unrecorded
    record(ledger, "token-thrift", parents=["literal-execution"], operator="essentials-filter",
           prompt="stop wasting tokens dude", prompt_date="2026-10-15", chooser="max")
    ancestors(ledger, "finish-everything"); unrecorded(ledger, skills_root)
    python lineage.py --selftest
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

CHOOSERS = {"max", "claude"}


def _load(ledger: Path):
    if not Path(ledger).exists():
        return []
    return [json.loads(ln) for ln in Path(ledger).read_text(encoding="utf-8").splitlines() if ln.strip()]


def record(ledger: Path, skill: str, parents=(), operator: str = "", prompt: str = "", prompt_date: str = "",
           chooser: str = "max", when: str | None = None) -> dict:
    if not skill or chooser not in CHOOSERS:
        raise ValueError(f"need a skill name and chooser in {sorted(CHOOSERS)}")
    if skill in parents:
        raise ValueError("a skill cannot be its own parent")
    if any(r["skill"] == skill for r in _load(ledger)):
        raise ValueError(f"{skill} already has a birth record (append-only: add a note, don't rewrite)")
    rec = {"skill": skill, "parents": list(parents), "operator": operator, "prompt": prompt,
           "prompt_date": prompt_date, "chooser": chooser, "date": when or date.today().isoformat()}
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def ancestors(ledger: Path, skill: str) -> list:
    by = {r["skill"]: r for r in _load(ledger)}
    out, todo, seen = [], list(by.get(skill, {}).get("parents", [])), set()
    while todo:
        p = todo.pop(0)
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
        todo += by.get(p, {}).get("parents", [])
    return out


def descendants(ledger: Path, skill: str) -> list:
    recs = _load(ledger)
    out, frontier = [], {skill}
    while frontier:
        kids = {r["skill"] for r in recs if frontier & set(r["parents"]) and r["skill"] not in out}
        out += sorted(kids)
        frontier = kids
    return out


def unrecorded(ledger: Path, skills_root: Path) -> list:
    have = {r["skill"] for r in _load(ledger)}
    return sorted(d.name for d in Path(skills_root).iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists() and d.name not in have)


def chooser_share(ledger: Path) -> dict:
    recs = _load(ledger)
    return {c: sum(r["chooser"] == c for r in recs) for c in sorted(CHOOSERS)}


def shift(ledger: Path, at: str, field: str = "chooser") -> dict:
    """Prompt attribution, the honest offline version: how the mix of `field` (chooser, operator, ...) among births
    changed before vs on/after the date of a prompt. Correlational - it shows WHAT changed after a prompt, not that
    the prompt alone caused it (that would need re-running with the phrase removed)."""
    recs = _load(ledger)
    if not recs:
        raise ValueError("empty ledger")
    mix = lambda rs: {k: sum(r.get(field) == k for r in rs) for k in sorted({r.get(field) for r in recs})}
    before = [r for r in recs if (r.get("prompt_date") or r["date"]) < at]
    after = [r for r in recs if (r.get("prompt_date") or r["date"]) >= at]
    return {"field": field, "at": at, "before": mix(before), "after": mix(after)}


def _selftest() -> bool:
    ok = {}
    d = Path(tempfile.mkdtemp(prefix="lineage_"))
    try:
        L = d / "lineage.jsonl"
        record(L, "literal-execution", operator="essentials-filter", prompt="take me literally", chooser="max")
        record(L, "token-thrift", operator="essentials-filter", prompt="stop wasting tokens", chooser="max")
        record(L, "finish-everything", parents=["literal-execution", "token-thrift"], operator="composite",
               chooser="claude")
        record(L, "super-finisher", parents=["finish-everything"], operator="graft", chooser="claude")
        ok["ancestors walk the whole tree"] = set(ancestors(L, "super-finisher")) == {
            "finish-everything", "literal-execution", "token-thrift"}
        ok["descendants walk down the tree"] = descendants(L, "literal-execution") == ["finish-everything", "super-finisher"]
        ok["who chose is counted (the user vs Claude)"] = chooser_share(L) == {"claude": 2, "max": 2}
        record(L, "early-max", chooser="max", prompt_date="2026-10-13")
        record(L, "late-claude", chooser="claude", prompt_date="2026-10-14T01:00")
        s = shift(L, "2026-10-14T00:55")
        ok["shift shows the chooser mix before vs after a prompt (attribution recipe)"] = (
            s["before"]["max"] == 1 and s["after"]["claude"] >= 1)
        root = d / "skills"
        for n in ("literal-execution", "token-thrift", "orphan-skill"):
            (root / n).mkdir(parents=True)
            (root / n / "SKILL.md").write_text("x", encoding="utf-8")
        ok["skills with no birth record are listed"] = unrecorded(L, root) == ["orphan-skill"]
        try:
            record(L, "token-thrift", chooser="max")
            ok["planted rewrite of an existing birth is refused (append-only)"] = False
        except ValueError:
            ok["planted rewrite of an existing birth is refused (append-only)"] = True
        try:
            record(L, "x", parents=["x"], chooser="max")
            ok["planted self-parent is refused"] = False
        except ValueError:
            ok["planted self-parent is refused"] = True
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    ledger = Path(argv[0])
    if len(argv) > 1:
        print("ancestors:", ancestors(ledger, argv[1]))
        print("descendants:", descendants(ledger, argv[1]))
    print("chooser share:", chooser_share(ledger))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
