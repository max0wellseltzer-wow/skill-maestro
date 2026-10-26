"""find_skill - describe a need in plain words, get the best-matching skills ranked (backs the skill-finder skill).

With 150+ skills, "which one do I use?" is a real search problem. This indexes every SKILL.md's name and
description, then ranks skills against a plain-English query by TF-IDF-weighted word overlap (rare, specific
words count more than common ones), with a boost when a query word appears in the skill's NAME. It returns the
top matches with a one-line "use when", and marks which ship a tool. Pure stdlib, no network.

    python find_skill.py "is my series trending or mean reverting"
    python find_skill.py "rate limit alerts" --top 5
    python find_skill.py --selftest
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

STOP = set("a an the and or of to in on for with is are be it this that my our your i we you do does how what "
           "which when where why can should would could from by as at into about than then them they there "
           "use using want need help get make find one".split())


def _tokens(text: str):
    words = re.findall(r"[a-z0-9]+", text.lower().replace("-", " "))
    out = []
    for w in words:
        if w in STOP or len(w) < 3:
            continue
        if w.endswith(("eed", "ss", "us", "is")):              # 2026-10-16: 'speed' -> 'spe' never met 'speeding'
            out.append(w)
            continue
        for suf in ("ing", "ers", "ies", "es", "ed", "s"):      # crude stem so 'trends'/'trending' meet
            if len(w) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def load(root: Path) -> list:
    skills = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
        name, desc = d.name, ""
        text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            for line in text.splitlines()[1:60]:
                if line.strip() == "---":
                    break
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("'\"")
                elif line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip("'\"")
        tool = any(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
        skills.append({"name": name, "desc": desc, "tool": tool,
                       "name_toks": set(_tokens(name)), "toks": _tokens(name + " " + desc)})
    return skills


def search(skills: list, query: str, top: int = 5) -> list:
    q = set(_tokens(query))
    if not q or not skills:
        return []
    n = len(skills)
    df = {}
    for s in skills:
        for t in set(s["toks"]):
            df[t] = df.get(t, 0) + 1
    scored = []
    for s in skills:
        toks = set(s["toks"])
        score = 0.0
        for t in q & toks:
            idf = math.log((n + 1) / (df[t] + 0.5))
            score += idf * (2.0 if t in s["name_toks"] else 1.0)
        if score > 0:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [{"name": s["name"], "score": round(sc, 3), "tool": s["tool"],
             "when": s["desc"].split(". ")[0][:160]} for sc, s in scored[:top]]


def _selftest() -> bool:
    import tempfile
    ok = {}
    root = Path(tempfile.mkdtemp())

    def mk(name, desc, tool=False):
        d = root / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n", encoding="utf-8")
        if tool:
            (d / "t.py").write_text("x=1\n", encoding="utf-8")
    mk("hurst", "Classify a time series as trending, mean-reverting or a random walk via the Hurst exponent.", True)
    mk("token-bucket", "Throttle events: token bucket, hard cooldown and burst buffer to rate-limit alerts and retries.",
       True)
    mk("convex-hull", "Compute the minimal convex boundary of 2-D points.")
    mk("backoff-retry", "Retry failed calls with exponential backoff and jitter when a rate limit is hit.", True)
    sk = load(root)
    r1 = search(sk, "is my series trending or mean reverting")
    ok["a trend question finds hurst first"] = (r1 and r1[0]["name"] == "hurst")
    r2 = search(sk, "rate limit my alerts")
    ok["a rate-limit-alerts question finds token-bucket first"] = (r2 and r2[0]["name"] == "token-bucket")
    ok["related skills also surface (backoff-retry for rate limiting)"] = ("backoff-retry" in [x["name"] for x in r2])
    ok["an unrelated query returns nothing rather than noise"] = (search(sk, "bake sourdough bread") == [])
    ok["a query of only stopwords returns nothing"] = (search(sk, "how do I do it") == [])
    ok["a name match outranks a description-only match"] = (search(sk, "convex boundary")[0]["name"] == "convex-hull")
    ok["tool markers come through"] = (r1[0]["tool"] is True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    top = 5
    if "--top" in argv:
        i = argv.index("--top")
        top = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    query = " ".join(argv)
    res = search(load(Path.home() / ".claude" / "skills"), query, top)
    if not res:
        print("no matching skills - try different words, or browse skills-index/INDEX.md")
        return 0
    for r in res:
        print(f"{r['score']:6.2f}  {r['name']:24s} [{'T' if r['tool'] else 'D'}]  {r['when']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
