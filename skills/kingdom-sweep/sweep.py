"""sweep - the user's "all the kingdoms besides and in between" method as a grid with a coverage map (backs kingdom-sweep).

the user, 2026-10-13: "Model these skills from both the flora and the fauna and all the kingdoms besides and inbetween ...
stretch the definitions of reproduce ... software, hardware, stars ... the continued homeostasis of a planet ...
real, or imagined." That is two axes: WHERE to look (domains) and HOW FAR to stretch the concept (levels).
grid() lays out every domain x level cell as a concrete question; the ledger records what each mined cell yielded
(built / folded / killed / empty), so the coverage map shows which kingdoms are exhausted and which were never
visited - and the yield per domain shows where inspiration actually turned into skills that survived.

    from sweep import grid, record, coverage
    cells = grid("reproduction")                         # 17 domains x 6 levels = 102 questions
    record(ledger, "reproduction", "Fungi", "functional", "built", name="skill-finder")
    coverage(ledger, "reproduction")                     # map, unmined cells, yield per domain
    python sweep.py --selftest
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

DOMAINS = ["Animalia", "Plantae", "Fungi", "Protista", "Bacteria", "Archaea", "Viruses",          # life
           "Stellar", "Planetary", "Atmosphere-Ocean", "Chemistry", "Physics",                      # non-life
           "Social-Economic", "Software", "Hardware", "Mathematics", "Imagined"]
LEVELS = {
    "literal": "Where does {c} literally happen in {d}?",
    "functional": "What in {d} does the job of {c}, in a different form?",
    "structural": "What in {d} has the shape or structure of {c}?",
    "abstract": "Strip {c} to a rule: where does that rule run in {d}?",
    "inverted": "What in {d} is the opposite of {c}, and what does that protect against?",
    "imaginary": "Invent a {d}-like world where {c} works differently: what changes?",
}
OUTCOMES = {"built", "folded", "killed", "empty"}


def grid(concept: str, domains=None, levels=None) -> list:
    if not concept or not concept.strip():
        raise ValueError("need a concept to sweep")
    domains = domains or DOMAINS
    levels = levels or list(LEVELS)
    bad = [x for x in levels if x not in LEVELS]
    if bad:
        raise ValueError(f"unknown stretch level(s): {bad}")
    return [{"domain": d, "level": lv, "question": LEVELS[lv].format(c=concept, d=d)} for d in domains for lv in levels]


def record(ledger: Path, concept: str, domain: str, level: str, outcome: str, name: str = "", note: str = ""):
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(OUTCOMES)}")
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}")
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"concept": concept, "domain": domain, "level": level, "outcome": outcome,
                             "name": name, "note": note}) + "\n")


def coverage(ledger: Path, concept: str, domains=None) -> dict:
    domains = domains or DOMAINS
    recs = [json.loads(ln) for ln in Path(ledger).read_text(encoding="utf-8").splitlines() if ln.strip()] \
        if Path(ledger).exists() else []
    recs = [r for r in recs if r["concept"] == concept]
    cell = {(r["domain"], r["level"]): r["outcome"] for r in recs}       # latest outcome per cell wins
    unmined = [(d, lv) for d in domains for lv in LEVELS if (d, lv) not in cell]
    yield_by = {}
    for d in domains:
        outs = [o for (dd, _), o in cell.items() if dd == d]
        if outs:
            yield_by[d] = {"mined": len(outs), "built": outs.count("built"), "folded": outs.count("folded"),
                           "killed": outs.count("killed")}
    return {"mined": len(cell), "total": len(domains) * len(LEVELS), "unmined": unmined, "yield": yield_by,
            "built": sorted(r["name"] for r in recs if r["outcome"] == "built" and r["name"])}


def _selftest() -> bool:
    ok = {}
    g = grid("reproduction")
    ok["the full grid is every domain x every stretch level"] = len(g) == len(DOMAINS) * len(LEVELS) == 102
    ok["each cell is a concrete question naming concept and domain"] = all(
        "reproduction" in c["question"] and c["domain"] in c["question"] for c in g)
    d = Path(tempfile.mkdtemp(prefix="sweep_"))
    try:
        L = d / "sweep.jsonl"
        record(L, "reproduction", "Viruses", "literal", "built", name="viral-spread")
        record(L, "reproduction", "Viruses", "functional", "folded", name="viral-spread", note="into safe-bulk-edit")
        record(L, "reproduction", "Stellar", "abstract", "killed", note="no mechanism")
        cv = coverage(L, "reproduction")
        ok["coverage counts mined cells and lists the rest as unmined"] = cv["mined"] == 3 and len(cv["unmined"]) == 99
        ok["yield per domain separates built, folded and killed"] = cv["yield"]["Viruses"] == {
            "mined": 2, "built": 1, "folded": 1, "killed": 0} and cv["yield"]["Stellar"]["killed"] == 1
        ok["another concept's ledger rows do not leak in"] = (record(L, "homeostasis", "Planetary", "literal", "built")
                                                              or coverage(L, "reproduction")["mined"] == 3)
        try:
            record(L, "reproduction", "Fungi", "literal", "maybe")
            ok["planted bad outcome is rejected"] = False
        except ValueError:
            ok["planted bad outcome is rejected"] = True
        try:
            grid("x", levels=["sideways"])
            ok["planted unknown stretch level is rejected"] = False
        except ValueError:
            ok["planted unknown stretch level is rejected"] = True
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    for c in grid(argv[0]):
        print(f"[{c['domain']} / {c['level']}] {c['question']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
