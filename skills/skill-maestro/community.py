"""Ratings from everyone who uses the Maestro (Max, 2026-10-24: "the ratings will come from everyone who uses the skill
and then the ratings will be sent to you or your git hub ... hopefully we can integrate their picks asap").

    maestro.py share [--out FILE] [--with-tasks]   write this copy's picks, FIT verdicts and ratings as one bundle
    maestro.py intake FILE|DIR ...                 fold other people's bundles into state/community/ (read as DATA)
    maestro.py community                           who sent what, and how many of their ratings the sheet now reads

A bundle is JSON: {"format": "maestro-ratings/1", "from": <anonymous id>, "created", "code", "rows": [...]}.
Rows are SCORE (the picks and the pool), FIT (the structured verdict), RATE and READ. Task text is left out unless
--with-tasks: a task is replaced by its sha and its content words, so a similar task still finds it. Paths, e-mail
addresses and key-shaped strings are masked either way. Send the file as an issue or pull request on the Maestro's
GitHub repository (SHARING.md names it); `intake` on that copy folds it in. Intake never runs anything from a bundle
and never lets a row claim to be the local owner: every row is stamped with its sender and its run is prefixed.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import time
from pathlib import Path

FORMAT = "maestro-ratings/1"
KINDS = ("SCORE", "FIT", "RATE", "READ")
SCORE_KEYS = ("run", "chosen", "pool_names", "finder_top", "concepts", "questions", "words", "task_sha", "code", "t")
MASKS = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"),
         (re.compile(r"\b(?:sk|pk|ghp|gho|xox[bap])[-_][A-Za-z0-9_-]{12,}\b"), "<key>"),
         (re.compile(r"\b[A-Za-z0-9]{32,}\b"), "<long-token>"),
         (re.compile(r"[A-Za-z]:[\\/][^\s'\"]+"), "<path>"),
         (re.compile(r"(?:/home|/Users)/[^\s'\"]+"), "<path>")]


def mask(s: str) -> str:
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s


def sender_id() -> str:
    """Anonymous and stable per machine and user: a hash, never the name."""
    raw = f"{platform.node()}|{Path.home().name}|maestro"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _clean(v):
    if isinstance(v, str):
        return mask(v)
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    return v


def make_bundle(rows: list[dict], with_tasks: bool = False, code: str = "") -> dict:
    out = []
    for r in rows:
        k = r.get("kind")
        if k not in KINDS or r.get("community_from"):          # never re-share what came from someone else
            continue
        if k == "SCORE":
            row = {x: r.get(x) for x in SCORE_KEYS if x in r}
            row["kind"] = "SCORE"
            if with_tasks and r.get("task"):
                row["task"] = r["task"][:500]
        else:
            row = {x: v for x, v in r.items() if x not in ("quote",)}
        out.append(_clean(row))
    return {"format": FORMAT, "from": sender_id(), "created": int(time.time()), "code": code, "rows": out}


def read_bundle(p: Path) -> dict:
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("format") != FORMAT or not isinstance(d.get("rows"), list):
        raise ValueError(f"{p}: not a {FORMAT} bundle")
    src = re.sub(r"[^0-9a-f]", "", str(d.get("from", "")))[:12] or "unknown"
    return {"from": src, "rows": d["rows"], "created": d.get("created")}


def intake(paths: list[Path], community_dir: Path, me: str | None = None) -> dict:
    """Fold bundles into community_dir/<sender>.jsonl. Rows are data: only known kinds and plain values are kept,
    each is stamped community_from=<sender>, its run is prefixed with the sender, and a row seen before is skipped."""
    me = me or sender_id()
    community_dir.mkdir(parents=True, exist_ok=True)
    report = {"bundles": 0, "added": 0, "skipped_dupe": 0, "skipped_bad": 0, "own": 0, "senders": {}}
    files = []
    for p in paths:
        p = Path(p)
        files += sorted(p.glob("*.json")) if p.is_dir() else [p]
    for f in files:
        try:
            b = read_bundle(f)
        except (ValueError, OSError) as e:
            report["skipped_bad"] += 1
            report.setdefault("errors", []).append(str(e)[:120])
            continue
        if b["from"] == me:
            report["own"] += 1
            continue
        report["bundles"] += 1
        out = community_dir / f"{b['from']}.jsonl"
        seen = set(out.read_text(encoding="utf-8").splitlines()) if out.is_file() else set()
        new = []
        for r in b["rows"]:
            if not isinstance(r, dict) or r.get("kind") not in KINDS or not isinstance(r.get("run", ""), str):
                report["skipped_bad"] += 1
                continue
            r = {k: v for k, v in r.items() if isinstance(k, str) and isinstance(v, (str, int, float, bool, list, dict, type(None)))}
            r["run"] = f"{b['from'][:6]}:{r.get('run', '')}"
            r["community_from"] = b["from"]
            if r.get("kind") == "RATE" and r.get("by") in (None, "claude"):
                r["by"] = r.get("by") or "claude"                   # a sender's Claude self-report stays one
            line = json.dumps(r, sort_keys=True, ensure_ascii=False)
            if line in seen:
                report["skipped_dupe"] += 1
                continue
            seen.add(line)
            new.append(line)
        if new:
            with out.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(new) + "\n")
        report["added"] += len(new)
        report["senders"][b["from"]] = report["senders"].get(b["from"], 0) + len(new)
    return report


def community_files(state_dir: Path) -> tuple[Path, ...]:
    d = Path(state_dir) / "community"
    return tuple(sorted(d.glob("*.jsonl"))) if d.is_dir() else ()


def summary(state_dir: Path) -> str:
    fs = community_files(state_dir)
    if not fs:
        return "COMMUNITY: no bundles folded in yet. Others run `maestro.py share` and send the file; you run `maestro.py intake FILE`."
    L = ["COMMUNITY (other people's picks and ratings the Maestro now reads as memory):"]
    for f in fs:
        rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        k = {}
        for r in rows:
            k[r.get("kind")] = k.get(r.get("kind"), 0) + 1
        L.append(f"  {f.stem}: " + ", ".join(f"{n} {kind}" for kind, n in sorted(k.items())))
    return "\n".join(L)


def run(argv: list[str], st, state_dir: Path, code: str = "") -> int:
    cmd = argv[0]
    if cmd == "share":
        out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path.cwd() / f"maestro_ratings_{sender_id()}_{time.strftime('%Y-%m-%d')}.json"
        b = make_bundle(st.rows(), with_tasks="--with-tasks" in argv, code=code)
        out.write_text(json.dumps(b, indent=1, ensure_ascii=False), encoding="utf-8")
        n = {}
        for r in b["rows"]:
            n[r["kind"]] = n.get(r["kind"], 0) + 1
        print(f"SHARE: {out}  ({', '.join(f'{v} {k}' for k, v in sorted(n.items()))}; sender {b['from']}; "
              f"task text {'INCLUDED' if '--with-tasks' in argv else 'left out (sha + words only)'})")
        print("Read it before sending. Send it as an issue or pull request on the Maestro's GitHub repository (SHARING.md).")
        return 0
    if cmd == "intake":
        paths = [Path(a) for a in argv[1:] if not a.startswith("--")]
        if not paths:
            print("INTAKE needs a bundle file or a folder of them")
            return 2
        rep = intake(paths, Path(state_dir) / "community")
        print("INTAKE: " + json.dumps(rep))
        return 0 if not rep["skipped_bad"] else 1
    if cmd == "community":
        print(summary(Path(state_dir)))
        return 0
    return 2


def _selftest() -> bool:
    import tempfile
    ok = {}
    rows = [{"kind": "SCORE", "run": "r1", "task": "email me at a@example.com about C:\\Users\\x\\f.txt", "chosen": ["x"],
             "pool_names": ["x", "y"], "task_sha": "abc", "t": 1},
            {"kind": "FIT", "run": "r1", "skill": "x", "verdict": "works", "why": "ran on C:\\Users\\x\\f.txt", "t": 2},
            {"kind": "RATE", "run": "r1", "skill": "x", "rating": "useful", "by": "user", "t": 3},
            {"kind": "TRY", "run": "r1", "skill": "x", "cmd": "rm -rf /"}]
    b = make_bundle(rows)
    ok["share: task text left out by default, TRY rows never leave"] = (
        "task" not in b["rows"][0] and all(r["kind"] != "TRY" for r in b["rows"]) and len(b["rows"]) == 3)
    ok["share: paths and e-mails are masked"] = "<path>" in b["rows"][1]["why"] and "a@example.com" not in json.dumps(make_bundle(rows, True))
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        b["from"] = "aaaaaaaaaaaa"
        (t / "b.json").write_text(json.dumps(b), encoding="utf-8")
        (t / "bad.json").write_text('{"format": "nope"}', encoding="utf-8")
        r1 = intake([t / "b.json", t / "bad.json"], t / "community", me="ffffffffffff")
        r2 = intake([t / "b.json"], t / "community", me="ffffffffffff")
        got = [json.loads(x) for x in (t / "community" / "aaaaaaaaaaaa.jsonl").read_text(encoding="utf-8").splitlines()]
        ok["intake: rows stamped with the sender, runs prefixed, a bad bundle refused"] = (
            r1["added"] == 3 and r1["skipped_bad"] == 1 and all(g["community_from"] == "aaaaaaaaaaaa" and g["run"].startswith("aaaaaa:") for g in got))
        ok["intake: the same bundle twice adds nothing"] = r2["added"] == 0 and r2["skipped_dupe"] == 3
        r3 = intake([t / "b.json"], t / "c2", me="aaaaaaaaaaaa")
        ok["intake: your own bundle is not folded back in"] = r3["own"] == 1 and r3["added"] == 0
        ok["community_files lists the folded senders"] = len(community_files(t)) == 1
    bad = [k for k, v in ok.items() if not v]
    print(f"community selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
