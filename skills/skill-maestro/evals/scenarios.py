"""Scenario test (the user, 2026-10-24: "test skill maestro on indexed skills and non indexed skills ... usable when skills
are indexed and when none are indexed OR loaded").

Builds a throwaway library in a temp folder: 30 skills copied from this PC's library plus one NEW skill that no
index, no vector file and no session listing has ever seen. Then runs the Maestro on it eight ways:

  A  nothing indexed, the meaning model available (the venv python, or the resident helper)
  B  the same library again, now indexed by A's run (the cached path)
  C  meaning switched off (MAESTRO_NO_MEANING=1): words alone must still pick something (C2: the same prompt with
     meaning on must pick the right skill; words alone are allowed to miss it, which is why meaning exists)
  D  a prompt for one of Anthropic's own skills (builtins.json): reachable with no file on disk
  E  skills never loaded into any session: the library root is a temp folder no session lists
  F, G  a diagram and a schematic (2026-10-25): the diagramming skill, not the chart skill (C2 keeps dataviz)

Each case passes when the right skill is among the picks. Exit 0 when all pass.
    python evals/scenarios.py            (system python: meaning through the resident helper)
    <venv python> evals/scenarios.py     (meaning in process)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
COPY = ["skill-finder", "core-skill-pin", "pen-run", "doc-truth", "dataviz", "scheduled-run-forensics", "bootstrap-ci",
        "kalman-filter", "hurst", "drawdown-stats", "plain-terms", "beginner-steps", "decision-menu", "transcript-grep",
        "windows-gotchas", "escape-proof", "land-a-change", "tree-status", "code-cage", "speed-proof", "kelly-sizing",
        "walk-forward-split", "monte-carlo-paths", "skill-health", "skills-index", "staged-secret-scan", "statsmodels",
        "polars", "redaction", "receipt-report"]
NEW = ("tide-table-reader", ("Reads a harbour's published tide table and tells you the next high and low water, the "
        "range, and whether a boat with a given draught can leave the berth. Use when someone asks when the tide turns, "
        "whether there is enough water to sail, or plans a trip around the tides."))
CASES = [
    ("A", "when is high water tomorrow, can my boat with 1.4 m draught get out of the marina", {"tide-table-reader"}, {}),
    ("B", "is there enough water under the keel to leave the harbour at noon", {"tide-table-reader"}, {}),
    ("C", "draw a chart of the equity curve", None, {"MAESTRO_NO_MEANING": "1"}),   # words alone: must still pick
    ("C2", "draw a chart of the equity curve", {"dataviz"}, {}),                     # the same prompt with meaning on
    ("D", "make me a powerpoint deck about our results", {"anthropic-skills:pptx"}, {}),
    ("E", "the nightly scheduled task did not run, find out why", {"scheduled-run-forensics"}, {}),
    ("F", "draw a diagram of the data flow", {"artifact-diagramming"}, {}),              # 2026-10-25: a diagram, not a chart
    ("G", "draw a schematic of how the whisper hook talks to the meaning helper", {"artifact-diagramming"}, {}),   # a diagram kin
]


def build(td: Path) -> Path:
    lib = td / "skills"
    for name in COPY:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, lib / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "state", ".git"))
    shutil.copytree(HERE, lib / "skill-maestro", ignore=shutil.ignore_patterns("__pycache__", "state", "*.pyc"))
    (lib / NEW[0]).mkdir(parents=True)
    (lib / NEW[0] / "SKILL.md").write_text(f"---\nname: {NEW[0]}\ndescription: {NEW[1]}\n---\n\n# {NEW[0]}\n\n{NEW[1]}\n",
                                           encoding="utf-8")
    return lib


def whisper(lib: Path, state: Path, prompt: str, env_extra: dict) -> tuple[list[str], float, str]:
    env = dict(os.environ, MAESTRO_STATE=str(state), **env_extra)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(lib / "skill-maestro" / "maestro.py"), "whisper", "--stdin", "--no-ledger",
                        "--root", str(lib), "--state", str(state)], input=json.dumps({"prompt": prompt}),
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=600, check=False)
    line = next((x for x in r.stdout.splitlines() if x.startswith("WHISPER (")), "")   # 2026-10-28: was the last line,
    names = re.findall(r"/([a-z0-9][a-z0-9_.:-]*)", line.split("): ", 1)[-1].split("   (")[0]) if "): " in line else []
    return names, time.time() - t0, (r.stdout + r.stderr)[-400:]       # which is NEXT STEP since v20.0.7 (no picks)


def stop_helpers(state: Path, wait: float = 120.0) -> str:
    """v20: the whispers may have started the resident meaning helper (`meaning.py serve`) and a background build in the
    throwaway state folder; both keep files open there (the fastembed cache lock), so they are stopped before the folder
    is removed. Only the processes recorded in THIS state folder are touched."""
    stopped = []
    info, t0 = state / "meaning_server.json", time.time()
    if (state / "meaning_server.lock").is_file():       # a helper was spawned; it announces itself only once its model is loaded
        while time.time() - t0 < wait and not info.is_file():
            time.sleep(0.5)
    try:
        pid = int(json.loads(info.read_text(encoding="utf-8"))["pid"])
        os.kill(pid, signal.SIGTERM)                      # on Windows this is TerminateProcess; the venv launcher exits with it
        stopped.append(pid)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    t0 = time.time()
    while time.time() - t0 < wait and any(state.glob("meaning_build_*.lock")):   # `build --release-lock` removes its lock when done
        time.sleep(0.5)
    time.sleep(0.5)                                       # a terminated process lets go of its files a moment later
    return f"helpers stopped: {stopped or 'none'}; build locks left: {len(list(state.glob('meaning_build_*.lock')))}"


def main() -> int:
    ok_all = True
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tdn:
        td = Path(tdn)
        lib, state = build(td), td / "state"
        state.mkdir()
        print(f"temp library: {sum(1 for p in lib.iterdir() if (p / 'SKILL.md').is_file())} skills, none indexed, "
              f"state folder empty; python {sys.executable}")
        for case, prompt, want, env in CASES:
            names, secs, tail = whisper(lib, state, prompt, env)
            ok = bool(names) if want is None else bool(want & set(names))
            ok_all &= ok
            print(f"  {case} {'PASS' if ok else 'FAIL'} {secs:5.1f}s  want {sorted(want) if want else 'any picks'}  got {names[:6]}")
            if not names:
                print("     output: " + tail.replace("\n", " | "))
        print("  cleanup: " + stop_helpers(state))
    if td.exists():
        print(f"  cleanup: {td} could not be removed in full (a helper still held a file); not a Maestro check")
    print("SCENARIOS " + ("PASS" if ok_all else "FAIL"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
