"""source_labels - tag every idea or claim by where it came from, so an analogy never passes as a fact
(backs the source-labels skill).

Tags (inline, at the end of the claim's line):
    [REAL: <source>]     observed or read: a file, commit, paper, command output - the source is required
    [IMAGINED]           a design, guess or extrapolation - plausible, unverified
    [FABRICATED]         invented on purpose for inspiration (an analogy, a made-up scenario) - never evidence
the user (2026-10-13): "Use all forms of production for your inspiration be they real, or imagined, or whole sale
fabricated" - fine for generating ideas, as long as the three never get mixed up later.

check(text) flags: claim lines with no tag, REAL with no source, and a FABRICATED claim reused as a premise
(a later line saying "because/since/as shown" and quoting its words).

    python source_labels.py notes.md
    python source_labels.py --selftest
"""
from __future__ import annotations

import re
import sys

TAG = re.compile(r"\[(REAL|IMAGINED|FABRICATED)(?::\s*([^\]]*))?\]\s*$")
CLAIM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$")                 # list items are the claims
PREMISE = re.compile(r"\b(because|since|as shown|therefore|which proves)\b", re.I)


def check(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    claims, issues, fabricated = [], [], []
    for n, line in enumerate(text.splitlines(), start=1):
        m = CLAIM.match(line)
        if not m:
            continue
        body = m.group(1).strip()
        t = TAG.search(body)
        if not t:
            issues.append(f"line {n}: claim has no source label: {body[:60]!r}")
            continue
        kind, src = t.group(1), (t.group(2) or "").strip()
        claim = TAG.sub("", body).strip()
        claims.append({"line": n, "kind": kind, "source": src or None, "claim": claim})
        if kind == "REAL" and not src:
            issues.append(f"line {n}: REAL needs a source (file, commit, paper, output)")
        if kind == "FABRICATED":
            fabricated.append((n, set(re.findall(r"[a-z]{5,}", claim.lower()))))
        if PREMISE.search(claim):
            words = set(re.findall(r"[a-z]{5,}", claim.lower()))
            for fn, fw in fabricated:
                if fn < n and len(words & fw) >= 3:
                    issues.append(f"line {n}: uses the FABRICATED idea from line {fn} as a premise")
    counts = {k: sum(c["kind"] == k for c in claims) for k in ("REAL", "IMAGINED", "FABRICATED")}
    return {"claims": claims, "counts": counts, "issues": issues, "ok": not issues}


def _selftest() -> bool:
    ok = {}
    good = ("- The 22 merged skills include 15 from the nature waves [REAL: wave-yield over the 10-15 archive]\n"
            "- A metaphor gate would have prevented most of them [IMAGINED]\n"
            "- Picture markets as tides pulled by a hidden moon [FABRICATED]\n")
    r = check(good)
    ok["a fully labelled list passes"] = r["ok"] and r["counts"] == {"REAL": 1, "IMAGINED": 1, "FABRICATED": 1}
    ok["planted unlabelled claim is flagged"] = not check("- Trend following works on crypto\n")["ok"]
    ok["planted REAL without a source is flagged"] = any("needs a source" in i for i in
                                                         check("- The ledger is quadratic [REAL]\n")["issues"])
    laund = good + "- Markets reverse on schedule because a hidden moon pulls the tides\n"
    laund = laund.replace("pulls the tides\n", "pulls the tides [IMAGINED]\n")
    ok["planted fabricated analogy used as a premise is caught"] = any("as a premise" in i for i in check(laund)["issues"])
    ok["prose outside list items is not treated as a claim"] = check("Intro paragraph with no tag.\n")["ok"]
    try:
        check(None)
        ok["planted bad input (not text) is rejected"] = False
    except TypeError:
        ok["planted bad input (not text) is rejected"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    r = check(open(argv[0], encoding="utf-8").read())
    print(r["counts"])
    for i in r["issues"]:
        print(" ", i)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
