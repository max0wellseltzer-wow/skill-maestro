"""skill_compose - type-checked pipelines of skill modules (backs skill-compose).

A modules file (JSON) declares what each module consumes and produces:
    {"modules": {"census":  {"consumes": ["scratch_dirs"], "produces": ["unlanded_list"],
                             "run": ["python", "scratch_landing_audit.py", "audit", "{scratch_dirs}", "--repo", "{repo}"],
                             "out": "unlanded.tsv"},
                 "triage":  {"consumes": ["unlanded_list"], "produces": ["keep_list"], "run": "MANUAL"}}}
A pipeline file names the steps in order, the types (with values) it starts from, and limits:
    {"inputs": {"scratch_dirs": "C:/tmp/scratch", "repo": "C:/repo"}, "steps": ["census", "triage"], "max_depth": 3}

check  every consumed type is produced by an EARLIER step or given as an input (TYPE_GAP names the step and type);
       no step uses a type only a later step makes (ORDER); no module is listed twice (REPEAT); the producer chain is no
       deeper than max_depth (DEPTH); unknown module names are UNKNOWN; types produced but never consumed and not
       the final step's are listed as UNUSED (info).
plan   --have t1,t2 --want T: the shortest step list (breadth-first over modules) that turns the given types into T,
       or NO_PLAN.
run    check first (refuses on any error), then run each script step (argv list, {type} placeholders filled from
       inputs and from earlier steps' "out" paths, no shell), record exit code, artefact path and sha256 in a receipt
       JSON; MANUAL steps take their text from --manual FILE (JSON {step: text}); with --landing an empty MANUAL line
       is an error.

    python skill_compose.py check  MODULES.json PIPELINE.json
    python skill_compose.py plan   MODULES.json --have scratch_dirs,repo --want keep_list
    python skill_compose.py run    MODULES.json PIPELINE.json --receipt receipt.json [--manual notes.json] [--landing]
    python skill_compose.py --selftest
Exit 0 ok, 1 type errors / NO_PLAN / a failed step, 2 bad arguments.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path


def load(p) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def check(mods: dict, pipe: dict) -> dict:
    errors, info = [], []
    have = {t: ("input", 0) for t in pipe.get("inputs", {})}
    steps = pipe.get("steps", [])
    max_depth = int(pipe.get("max_depth", 3))
    later = {}
    for i, s in enumerate(steps):
        for t in mods.get(s, {}).get("produces", []):
            later.setdefault(t, i)
    seen, consumed = set(), set()
    for i, s in enumerate(steps):
        if s not in mods:
            errors.append(("UNKNOWN", s, "no such module"))
            continue
        if s in seen:
            errors.append(("REPEAT", s, "listed twice"))
        seen.add(s)
        m = mods[s]
        depth = 0
        for t in m.get("consumes", []):
            consumed.add(t)
            if t in have:
                depth = max(depth, have[t][1])
            elif t in later and later[t] >= i:
                errors.append(("ORDER", s, f"{t} is only made by step {steps[later[t]]} at or after this one"))
            else:
                errors.append(("TYPE_GAP", s, f"consumes {t}, which no earlier step or input provides"))
        d = depth + 1
        if d > max_depth:
            errors.append(("DEPTH", s, f"producer chain depth {d} > max_depth {max_depth}"))
        for t in m.get("produces", []):
            have[t] = (s, d)
    final = set(mods.get(steps[-1], {}).get("produces", [])) if steps and steps[-1] in mods else set()
    for t, (src, _) in have.items():
        if src != "input" and t not in consumed and t not in final:
            info.append(("UNUSED", src, f"produces {t}, never consumed"))
    return {"ok": not errors, "errors": errors, "info": info}


def plan(mods: dict, have: set, want: str):
    """Shortest list of modules (BFS over sets of available types) that makes `want`."""
    start = frozenset(have)
    if want in start:
        return []
    q, seen = deque([(start, [])]), {start}
    while q:
        types, path = q.popleft()
        for name in sorted(mods):
            m = mods[name]
            if name in path or not set(m.get("consumes", [])) <= types:
                continue
            new = types | set(m.get("produces", []))
            if new == types:
                continue
            if want in new:
                return path + [name]
            if new not in seen and len(path) < 8:
                seen.add(new)
                q.append((new, path + [name]))
    return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(mods, pipe, receipt, manual=None, landing=False, cwd=None) -> dict:
    c = check(mods, pipe)
    if not c["ok"]:
        return {"ok": False, "refused": c["errors"], "steps": []}
    values = {k: str(v) for k, v in pipe.get("inputs", {}).items()}
    manual = manual or {}
    rows, ok = [], True
    for s in pipe["steps"]:
        m = mods[s]
        if m.get("run") == "MANUAL":
            text = (manual.get(s) or "").strip()
            row = {"step": s, "kind": "MANUAL", "text": text, "status": "OK" if text else "EMPTY"}
            if not text and landing:
                row["status"] = "EMPTY_AT_LANDING"
                ok = False
            rows.append(row)
            for t in m.get("produces", []):
                values.setdefault(t, f"MANUAL:{s}")
            continue
        argv = [a.format(**values) if "{" in a else a for a in m["run"]]
        argv = [sys.executable if a == "python" else a for a in argv]
        limit = int(m.get("timeout", 600))
        out = Path(cwd or ".") / m["out"] if m.get("out") else None
        try:
            r = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, timeout=limit)
        except subprocess.TimeoutExpired as e:        # 2026-10-25: a step past its `timeout` is a TIMEOUT row and the
            if out is not None and m.get("capture"):   # receipt is still written (skill-maestro's selfcheck tour hit this)
                part = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
                out.write_text(part + f"\nTIMEOUT after {limit} s\n", encoding="utf-8")
            rows.append({"step": s, "kind": "SCRIPT", "argv": argv, "exit": None, "out": str(out) if out else None,
                         "sha256": None, "status": "TIMEOUT", "timeout": limit})
            ok = False
            break
        if out is not None and m.get("capture"):            # tools that print their artefact: save stdout as it
            out.write_text(r.stdout, encoding="utf-8")
        row = {"step": s, "kind": "SCRIPT", "argv": argv, "exit": r.returncode,
               "out": str(out) if out else None, "sha256": sha256(out) if out and out.is_file() else None}
        allowed = set(m.get("ok_exits", [0]))
        row["status"] = "OK" if r.returncode in allowed and (out is None or row["sha256"]) else "FAILED"
        rows.append(row)
        if row["status"] != "OK":
            ok = False
            break
        for t in m.get("produces", []):
            values[t] = str(out) if out else ""
    rec = {"ok": ok, "steps": rows}
    Path(receipt).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main(argv) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if argv[:1] == ["--selftest"]:
        return 0 if _selftest() else 1
    if not argv or argv[0] not in ("check", "plan", "run"):
        print(__doc__)
        return 2
    args, o = argv[1:], {}
    try:
        for f in ("--have", "--want", "--receipt", "--manual"):
            if f in args:
                i = args.index(f)
                o[f] = args[i + 1]
                del args[i:i + 2]
    except IndexError:
        print("REFUSED: a flag is missing its value", file=sys.stderr)
        return 2
    landing = "--landing" in args
    args = [a for a in args if a != "--landing"]
    try:
        if argv[0] == "plan":
            if len(args) != 1 or "--want" not in o:
                raise ValueError("plan needs MODULES.json and --want")
            mods = load(args[0])["modules"]
            p = plan(mods, set(filter(None, o.get("--have", "").split(","))), o["--want"])
            print("NO_PLAN" if p is None else "PLAN " + " -> ".join(p) if p else "PLAN (already have it)")
            return 1 if p is None else 0
        if len(args) != 2:
            raise ValueError("need MODULES.json PIPELINE.json")
        mods, pipe = load(args[0])["modules"], load(args[1])
    except (ValueError, OSError, KeyError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    if argv[0] == "check":
        c = check(mods, pipe)
        for k, s, d in c["errors"] + c["info"]:
            print(f"{k:<9} {s:<16} {d}")
        print("TYPECHECK OK" if c["ok"] else f"TYPECHECK FAILED ({len(c['errors'])} error(s))")
        return 0 if c["ok"] else 1
    if "--receipt" not in o:
        print("REFUSED: run needs --receipt", file=sys.stderr)
        return 2
    r = run(mods, pipe, o["--receipt"], load(o["--manual"]) if "--manual" in o else None, landing)
    if r.get("refused"):
        for k, s, d in r["refused"]:
            print(f"REFUSED {k} {s}: {d}")
        return 1
    for row in r["steps"]:
        print(f"{row['status']:<17} {row['step']:<16} {row.get('sha256') or row.get('text', '')[:40]}")
    print(f"receipt {o['--receipt']}: {'OK' if r['ok'] else 'FAILED'}")
    return 0 if r["ok"] else 1


def _selftest() -> bool:
    ok = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "mk.py").write_text("import sys\nopen(sys.argv[2], 'w').write(open(sys.argv[1]).read().upper())\n",
                                  encoding="utf-8")
        (td / "src.txt").write_text("hello\n", encoding="utf-8")
        mods = {
            "upper": {"consumes": ["text"], "produces": ["shout"], "run": ["python", "mk.py", "{text}", "up.txt"],
                      "out": "up.txt"},
            "review": {"consumes": ["shout"], "produces": ["verdict"], "run": "MANUAL"},
            "side": {"consumes": ["text"], "produces": ["junk"], "run": "MANUAL"},
            "loop": {"consumes": ["verdict"], "produces": ["text2"], "run": "MANUAL"},
            "fail": {"consumes": ["text"], "produces": ["x"], "run": ["python", "-c", "import sys; sys.exit(3)"]},
            "slow": {"consumes": ["text"], "produces": ["y"], "run": ["python", "-c", "import time; time.sleep(20)"],
                     "timeout": 1, "capture": True, "out": "slow.txt"},
        }
        good = {"inputs": {"text": str(td / "src.txt")}, "steps": ["upper", "review"], "max_depth": 3}
        c = check(mods, good)
        ok["a pipeline whose types line up passes"] = c["ok"] and c["info"] == []
        cg = check(mods, {"inputs": {}, "steps": ["upper"]})
        ok["a consumed type nobody provides is TYPE_GAP"] = any(k == "TYPE_GAP" for k, _, _ in cg["errors"])
        co = check(mods, {"inputs": {"text": "x"}, "steps": ["review", "upper"]})
        ok["using a type only a later step makes is ORDER"] = any(k == "ORDER" for k, _, _ in co["errors"])
        cd = check(mods, {"inputs": {"text": "x"}, "steps": ["upper", "review", "loop"], "max_depth": 2})
        ok["a producer chain deeper than max_depth is DEPTH"] = any(k == "DEPTH" and s == "loop" for k, s, _ in cd["errors"])
        cr = check(mods, {"inputs": {"text": "x"}, "steps": ["upper", "upper", "nosuch"]})
        ok["repeated and unknown modules are errors"] = {k for k, _, _ in cr["errors"]} >= {"REPEAT", "UNKNOWN"}
        cu = check(mods, {"inputs": {"text": "x"}, "steps": ["side", "upper", "review"]})
        ok["an output nobody consumes is UNUSED info, not an error"] = cu["ok"] and any(k == "UNUSED" for k, _, _ in cu["info"])
        ok["plan finds the shortest chain to a wanted type"] = plan(mods, {"text"}, "verdict") == ["upper", "review"]
        two = {"a1": {"consumes": ["x"], "produces": ["r"]}, "a2": {"consumes": ["r"], "produces": ["goal"]},
               "b1": {"consumes": ["x"], "produces": ["p"]}, "b2": {"consumes": ["p"], "produces": ["q"]},
               "b3": {"consumes": ["q"], "produces": ["goal"]}}
        ok["plan prefers the 2-step route over the 3-step one"] = plan(two, {"x"}, "goal") == ["a1", "a2"]
        ok["plan says None when the type cannot be made"] = plan(mods, {"shout"}, "nothing") is None
        r = run(mods, good, td / "receipt.json", manual={"review": "looks right to the user"}, cwd=td)
        want = hashlib.sha256(b"HELLO\n").hexdigest()
        ok["run fills placeholders, records the artefact sha256 and the MANUAL text"] = (
            r["ok"] and r["steps"][0]["sha256"] in (want, hashlib.sha256(b"HELLO\r\n").hexdigest())
            and r["steps"][1]["text"] == "looks right to the user" and (td / "receipt.json").is_file())
        rl = run(mods, good, td / "r2.json", manual={}, landing=True, cwd=td)
        ok["an empty MANUAL line at landing fails the run"] = not rl["ok"] and rl["steps"][1]["status"] == "EMPTY_AT_LANDING"
        rf = run(mods, {"inputs": {"text": "x"}, "steps": ["fail", "upper"]}, td / "r3.json", cwd=td)
        ok["a failing step stops the run"] = not rf["ok"] and len(rf["steps"]) == 1 and rf["steps"][0]["exit"] == 3
        rt = run(mods, {"inputs": {"text": "x"}, "steps": ["slow", "upper"]}, td / "r5.json", cwd=td)
        ok["a step past its timeout is TIMEOUT, stops the run, and the receipt is still written"] = (
            not rt["ok"] and len(rt["steps"]) == 1 and rt["steps"][0]["status"] == "TIMEOUT"
            and (td / "r5.json").is_file() and "TIMEOUT after 1 s" in (td / "slow.txt").read_text(encoding="utf-8"))
        rr = run(mods, {"inputs": {}, "steps": ["upper"]}, td / "r4.json", cwd=td)
        ok["run refuses a pipeline that does not typecheck (nothing runs)"] = rr.get("refused") and not (td / "r4.json").exists()
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
