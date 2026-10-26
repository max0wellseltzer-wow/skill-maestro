"""Ratings from everyone who uses the Maestro (the user, 2026-10-24: "the ratings will come from everyone who uses the skill
and then the ratings will be sent to you or your git hub ... hopefully we can integrate their picks asap").

    maestro.py share [--out FILE] [--with-tasks]   write this copy's picks, FIT verdicts and ratings as one bundle
    maestro.py share --preview                     print the bundle it would write; writes nothing (allowed in private mode)
    maestro.py share --issue                       write the bundle and print a prefilled GitHub issue link to attach it to
    maestro.py intake FILE|DIR ...                 fold other people's bundles into state/community/ (read as DATA)
    maestro.py community                           who sent what, and how many of their ratings the sheet now reads
    maestro.py contribute                          every way to help the Maestro, by the time it takes (30 s / 5 min / 1 h)

Nothing is sent by itself, ever: `share` writes a file this person reads and attaches; `--issue` only prints a link
whose query holds the summary counts (never a row). DO_NOT_TRACK=1 makes `share` write nothing and prints why.

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
import os
import platform
import re
import time
import urllib.parse
from pathlib import Path

FORMAT = "maestro-ratings/1"
REPO = "https://github.com/max0wellseltzer-wow/skill-maestro"       # the only destination; a fork changes this one line
ISSUE_TEMPLATE = "ratings-bundle.yml"                                # .github/ISSUE_TEMPLATE on that repository
URL_LIMIT = 7500                                                     # browsers and GitHub truncate longer prefilled links
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


def counts(rows: list[dict]) -> dict:
    n = {}
    for r in rows:
        n[r.get("kind")] = n.get(r.get("kind"), 0) + 1
    return n


def _counts_line(n: dict) -> str:
    return ", ".join(f"{v} {k}" for k, v in sorted(n.items())) or "0 rows"


def do_not_track() -> bool:
    """The console DO_NOT_TRACK convention (any value but empty or 0): share writes nothing, doctor drops the pointer."""
    return os.environ.get("DO_NOT_TRACK", "") not in ("", "0")


def issue_url(bundle: dict, out: Path | None, with_tasks: bool = False) -> str:
    """A prefilled GitHub issue link. Only the summary travels in the URL (counts, sender, code, file name); the rows go
    in the attached file. Under URL_LIMIT by construction; asserted anyway because the link lands in browser history."""
    n = counts(bundle["rows"])
    summary = (f"Maestro ratings bundle from sender {bundle['from']} (code {bundle.get('code') or '?'}): "
               f"{_counts_line(n)}; task text {'included' if with_tasks else 'left out (sha + words only)'}; "
               f"file {out.name if out else '(attach the share file)'}. "
               f"I read the file before attaching it.")
    q = {"template": ISSUE_TEMPLATE, "title": f"ratings bundle {bundle['from']}", "summary": summary}
    url = f"{REPO}/issues/new?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
    assert len(url) < URL_LIMIT, len(url)
    return url


def contribute_text(rows: list[dict], private: bool | None) -> str:
    """Every way to help, by the time it takes. Printed on request only (`maestro.py contribute`); nothing runs."""
    mine = [r for r in rows if not r.get("community_from")]
    n = counts(mine)
    owner_rates = sum(1 for r in mine if r.get("kind") == "RATE" and r.get("by") not in (None, "claude"))
    priv = "unknown" if private is None else ("ON (share writes nothing until `maestro.py private off`)" if private else "OFF")
    L = ["CONTRIBUTE: ways to help the Maestro, by the time they take. Nothing here runs or sends by itself.",
         f"  You so far: {n.get('SCORE', 0)} runs scored, {n.get('FIT', 0)} FIT verdicts, {owner_rates} ratings by you "
         f"({n.get('RATE', 0) - owner_rates} by Claude). Private mode: {priv}.",
         "",
         "  30 seconds",
         "    python maestro.py thumbs last up        or `down`: rate the last run. A wrong pick is the most useful signal there is.",
         "    python maestro.py doctor                any line that starts with `--` is worth an issue (copy the line).",
         "",
         "  5 minutes",
         "    python maestro.py share --preview       read exactly what a bundle holds (paths, e-mails and keys already masked). Writes nothing.",
         "    python maestro.py private off           then `python maestro.py share --issue`: writes the file, prints a prefilled issue link;",
         "                                            attach the file to the issue. Only you send it. `private on` afterwards if you like.",
         "    python maestro.py fit RUN SKILL kind=no question=no assumes=no used=no \"why\"   when a pick was wrong for the task, say so.",
         "",
         "  1 hour",
         "    python maestro.py eval                  held-out accuracy on YOUR library; paste the numbers in an issue (no prompts needed).",
         "    python maestro.py findable <skill>      fix one skill description so the Maestro finds it; send the diff as a pull request.",
         "    one real prompt + the skill you ended up using, as a line for evals/probes_walkforward_*.tsv (the honest yardstick).",
         "",
         f"  Not helping costs nothing. DO_NOT_TRACK=1 makes `share` write nothing. Where it goes: {REPO}/issues",
         "  What leaves your machine, and the off switches: SHARING.md, section \"What leaves your machine\"."]
    return "\n".join(L)


def run(argv: list[str], st, state_dir: Path, code: str = "", private: bool | None = None) -> int:
    cmd = argv[0]
    if cmd == "contribute":
        print(contribute_text(st.rows(), private))
        return 0
    if cmd == "share":
        with_tasks = "--with-tasks" in argv
        b = make_bundle(st.rows(), with_tasks=with_tasks, code=code)
        n = counts(b["rows"])
        if "--preview" in argv:
            print(json.dumps(b, indent=1, ensure_ascii=False))
            print(f"PREVIEW: {_counts_line(n)}; sender {b['from']}; task text "
                  f"{'INCLUDED' if with_tasks else 'left out (sha + words only)'}. Nothing written, nothing sent.")
            return 0
        if do_not_track():
            print("DO_NOT_TRACK is set: `share` writes nothing. Unset it (or use `share --preview`, which only prints).")
            return 0
        out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else state_dir / f"maestro_ratings_{sender_id()}_{time.strftime('%Y-%m-%d')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(b, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"SHARE: {out}  ({_counts_line(n)}; sender {b['from']}; "
              f"task text {'INCLUDED' if with_tasks else 'left out (sha + words only)'})")
        if "--issue" in argv:
            print("ISSUE: open this link, attach the file above, read the form, send:")
            print("  " + issue_url(b, out, with_tasks))
        else:
            print(f"Read it before sending. Send it as an issue or pull request on {REPO} (SHARING.md); "
                  "`share --issue` prints a prefilled link.")
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
        # v20.0.13: `share` writes the bundle into the state folder, never into the current folder
        class _St:
            def rows(self):
                return rows
        saved_dnt, cwd_before = os.environ.pop("DO_NOT_TRACK", None), set(Path.cwd().glob("maestro_ratings_*.json"))
        try:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                run(["share"], _St(), t / "state", code="c0de", private=False)
        finally:
            if saved_dnt is not None:
                os.environ["DO_NOT_TRACK"] = saved_dnt
        ok["share: the bundle lands in the state folder, not the current folder"] = (
            len(list((t / "state").glob("maestro_ratings_*.json"))) == 1
            and set(Path.cwd().glob("maestro_ratings_*.json")) == cwd_before)
    url = issue_url(b, Path("maestro_ratings_x.json"), False)
    ok["issue_url: summary counts only, under the limit, no row text in the link"] = (
        url.startswith(REPO + "/issues/new?template=") and len(url) < URL_LIMIT and "a%40example" not in url
        and "<path>" not in urllib.parse.unquote(url) and "1%20SCORE" in url)
    text = contribute_text(rows + [{"kind": "RATE", "run": "z:r9", "skill": "q", "rating": "useful", "by": "user", "community_from": "z"}], True)
    ok["contribute: three tiers, own counts only, private status, nothing runs"] = (
        "30 seconds" in text and "5 minutes" in text and "1 hour" in text and "1 runs scored" in text
        and "1 ratings by you" in text and "Private mode: ON" in text and "costs nothing" in text)
    saved = os.environ.get("DO_NOT_TRACK")
    try:
        os.environ["DO_NOT_TRACK"] = "1"
        ok["DO_NOT_TRACK=1 is honoured"] = do_not_track()
        os.environ["DO_NOT_TRACK"] = "0"
        ok["DO_NOT_TRACK=0 is not tracking-off"] = not do_not_track()
    finally:
        if saved is None:
            os.environ.pop("DO_NOT_TRACK", None)
        else:
            os.environ["DO_NOT_TRACK"] = saved
    bad = [k for k, v in ok.items() if not v]
    print(f"community selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
