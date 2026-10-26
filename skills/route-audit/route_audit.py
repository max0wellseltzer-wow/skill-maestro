"""route_audit - does the skill router send a need to the right skill? (backs the route-audit skill;
self-attacking-referee applied to skill-finder).

skill-finder indexes each skill's NAME and frontmatter DESCRIPTION. This audit asks it about text it has never
indexed: the first paragraph of each skill's BODY (its plain-English pitch), with the skill's own name words
removed so the answer can't be read off the name. A good library routes each pitch back to its own skill.
Wrong answers are the interesting output: a confusion A -> B means A's need is described in B's words (an overlap,
or a description too vague to route), so either merge them or sharpen A's description.

    python route_audit.py [skills_root] [--top 3]
    python route_audit.py --selftest
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
SK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SK / "skill-finder"))
from find_skill import load, search  # noqa: E402


def pitch(skill_md: Path, name: str) -> str | None:
    """First prose paragraph of the body (after frontmatter and the title), with the name's words removed."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        parts = text.split("---", 2)
        text = parts[2] if len(parts) == 3 else ""
    for para in re.split(r"\n\s*\n", text):
        p = para.strip()
        if p and not p.startswith(("#", "```", "|", "-", "*", ">")) and len(p.split()) >= 8:
            for w in re.split(r"[-_]", name):
                if len(w) > 2:
                    p = re.sub(rf"\b{re.escape(w)}\w*", " ", p, flags=re.I)
            return p
    return None


def route_audit(root: Path, top: int = 3) -> dict:
    root = Path(root)
    skills = load(root)
    rows, skipped = [], []
    for s in skills:
        q = pitch(root / s["name"] / "SKILL.md", s["name"])
        if not q:
            skipped.append(s["name"])
            continue
        hits = [h["name"] for h in search(skills, q, top=top)]
        rows.append({"skill": s["name"], "top1": hits[0] if hits else None, "hits": hits,
                     "rank": hits.index(s["name"]) + 1 if s["name"] in hits else None})
    n = len(rows)
    confusions = sorted((r["skill"], r["top1"]) for r in rows if r["top1"] != r["skill"])
    return {"n": n, "top1": sum(r["rank"] == 1 for r in rows) / n if n else None,
            f"top{top}": sum(r["rank"] is not None for r in rows) / n if n else None,
            "missed": sorted(r["skill"] for r in rows if r["rank"] is None), "confusions": confusions,
            "skipped_no_pitch": skipped}


def _selftest() -> bool:
    ok = {}
    root = Path(tempfile.mkdtemp(prefix="route_audit_"))

    def mk(name, desc, body):
        d = root / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n\n{body}\n",
                                    encoding="utf-8")
    try:
        mk("tide-clock", "Predict ocean tides from lunar phase and harbour geometry for sailing plans.",
           "Sailors need to know when the water in the harbour rises and falls, using the moon's phase and the "
           "shape of the bay to forecast high and low water.")
        mk("bread-proof", "Time sourdough fermentation from flour, starter strength and kitchen temperature.",
           "Bakers want the dough to rise exactly enough: starter strength, flour type and how warm the kitchen "
           "is decide how long fermentation should take.")
        mk("dough-timer", "Schedule sourdough fermentation from starter strength, flour and kitchen warmth.",
           "Bakers want the dough to rise exactly enough: starter strength, flour type and how warm the kitchen "
           "is decide how long fermentation should take.")
        mk("orbit-calc", "Compute satellite orbital period and altitude from Kepler's third law.",
           "Mission planners need how long a satellite takes to circle the planet at a given height, from "
           "Kepler's third law and the planet's mass.")
        mk("no-body", "A skill with only a heading and a list.", "- item one\n- item two")
        rep = route_audit(root, top=3)
        conf = set(rep["confusions"])
        ok["distinct skills route to themselves"] = ("tide-clock", "tide-clock") not in conf and not any(
            a in ("tide-clock", "orbit-calc") for a, _ in conf)
        ok["planted near-duplicates are caught as a confusion"] = any(
            {a, b} == {"bread-proof", "dough-timer"} for a, b in conf)
        ok["a skill with no prose pitch is skipped, not guessed"] = rep["skipped_no_pitch"] == ["no-body"]
        ok["the query never contains the skill's own name words"] = "tide" not in (
            pitch(root / "tide-clock" / "SKILL.md", "tide-clock") or "").lower()
        ok["top-k includes the right skill even when top-1 is its twin"] = "bread-proof" not in rep["missed"]
        ok["rates are fractions of the audited skills"] = rep["n"] == 4 and 0 <= rep["top1"] <= 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if argv and argv[0] == "--selftest":
        return 0 if _selftest() else 1
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 3
    args = [a for i, a in enumerate(argv) if a != "--top" and (i == 0 or argv[i - 1] != "--top")]
    root = Path(args[0]) if args else SK
    rep = route_audit(root, top)
    print(f"{rep['n']} skills audited: top-1 {rep['top1']:.0%}, top-{top} {rep[f'top{top}']:.0%}; "
          f"{len(rep['skipped_no_pitch'])} had no prose pitch")
    print(f"never in top-{top} ({len(rep['missed'])}): {', '.join(rep['missed'])}")
    print("confusions (asked for A, router said B):")
    for a, b in rep["confusions"]:
        print(f"  {a} -> {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
