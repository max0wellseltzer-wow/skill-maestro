"""Command tour of maestro.py: every subcommand and flag, against a library, in a throwaway state folder.
One line per invocation; exit 1 when any exit code differs from the expected one, an expected phrase is missing,
or a traceback appears.

    python tour.py <maestro.py> <skills root> [--project DIR]      # stdlib, Windows and Linux
    python tour.py --selftest                                       # every command in maestro.py --help is toured
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "evals"))
from scenarios import stop_helpers                  # v20.0.4: the tour stops the meaning helpers it spawned


def build_tours(maestro: Path, tmp: Path, lib: Path, st: Path) -> list[tuple]:
    """(label, expected exit, argv after maestro.py[, a phrase the output must contain[, extra environment]])."""
    S = ["--state", str(st)]
    NOX = {"MAESTRO_EXTRAS": str(tmp / "no-extras")}   # v20: a core install, whatever is beside this copy
    return [
        ("help", 0, []),
        ("index --build", 0, ["index", "--build", *S], "INDEX"),   # v20.0.4: first, so every score below reads the prepared index
        ("--selftest", 0, ["--selftest"]),
        ("score plain", 0, ["score", "check whether a forward test result is real", *S]),
        ("score --pool --top 4", 0, ["score", "land a branch safely with tests", "--pool", "--top", "4", *S]),
        ("score --quick", 0, ["score", "is there a skill for cron expressions", "--quick", *S]),
        ("score --json", 0, ["score", "size a position from a return history", "--json", *S]),
        ("score --budget", 0, ["score", "size a position from a return history", "--budget", "200", *S]),
        ("score --questions", 0, ["score", "find gaps in this plan", "--questions", "FIND_GAPS,ORDER", *S]),
        ("score --custom-only", 0, ["score", "make a slide deck", "--custom-only", *S]),
        ("score 3 words -> 1 pick", 0, ["score", "parse cron", *S]),
        ("score empty task", 2, ["score", *S]),
        ("read last", 0, ["read", "last", "position-sizer", "kelly-sizing", *S]),
        ("read bad run", 3, ["read", "nosuchrun", "position-sizer", *S]),
        ("rate useful w/o fit (refused)", 3, ["rate", "last", "position-sizer", "useful", *S]),
        ("rate unused", 0, ["rate", "last", "kelly-sizing", "unused", *S]),
        ("rate metrics no --by (refused)", 2, ["rate", "last", "position-sizer", "topic=4", *S]),
        ("rate metrics --by user", 0, ["rate", "last", "menu:A", "--by", "user", "topic=4", "inner=3", "good", *S]),
        ("plan", 0, ["plan", "last", "position-sizer", "--on", "returns.csv", "a size that respects drawdown", *S]),
        ("baton", 0, ["baton", "last", *S]),
        ("try (options before --)", 0, ["try", "last", "position-sizer", *S, "--", "python", str(maestro), "--selftest"]),
        ("try missing program (refused)", 2, ["try", "last", "position-sizer", *S, "--", "no-such-program-xyz", "a"]),
        ("fit works", 0, ["fit", "last", "position-sizer", "works", "selftest ran on the subject", *S]),
        ("fit works w/o try (refused)", 3, ["fit", "last", "drawdown-stats", "works", "no try", *S]),
        ("fit misfit", 0, ["fit", "last", "drawdown-stats", "misfit", "wrong kind", *S]),
        ("rate useful after fit", 0, ["rate", "last", "position-sizer", "useful", *S]),
        ("thumbs last up", 0, ["thumbs", "last", "up", "position-sizer", *S], "THUMBS UP"),
        ("taste bad subject (refused)", 2, ["taste", "last", "doc-truth", "--subject", "/nonexistent", *S, "--", "python", "x", "{subject}"]),
        ("metrics", 0, ["metrics", *S]),
        ("forward", 0, ["forward", *S]),
        ("close", 0, ["close", "last", "tour run", *S]),
        ("encore", 0, ["encore", *S]),
        ("reflect", 0, ["reflect", *S]),
        ("new", 0, ["new", *S]),
        ("trend", 0, ["trend", *S]),
        # v11-v14: triage, cost, debt, findable, newskill, privacy, vocab, used
        ("triage QUICK", 0, ["triage", "is there a skill for cron expressions", *S], "TRIAGE QUICK"),
        ("triage FULL", 0, ["triage", "design a fair way to share findings between sessions", *S], "TRIAGE FULL"),
        ("score triaged QUICK", 0, ["score", "is there a skill for cron expressions", *S], "TRIAGE QUICK"),
        ("score --full", 0, ["score", "design a fair way to share findings", "--full", *S], "MAESTRO run"),
        ("score --concepts brief", 0, ["score", "design a fair way to share findings", "--concepts",
                                       "rank: order skills by fit; world: a blind audition", *S], "COST sheet"),
        ("ponder last (concept run)", 0, ["ponder", "last", *S], "PONDER"),
        ("breed last", None, ["breed", "last", *S]),               # passes or refuses by design: no traceback
        ("builtins", 0, ["builtins", *S], "simplify"),
        ("eval (creative probes)", 0, ["eval", "--probes", str(maestro.parent / "probes_creative.tsv"), *S], "maestro@1"),
        ("score --no-ledger", 0, ["score", "is there a skill for cron", "--no-ledger", *S], "TRIAGE"),
        ("cost", 0, ["cost", *S], "TRIAGE:"),
        ("debt", 0, ["debt", *S], "DEBT"),
        ("findable", 0, ["findable", "position-sizer", *S], "FINDABLE position-sizer"),
        ("findable unknown", 0, ["findable", "no-such-skill-xyz", *S], "NO_SKILL"),
        ("newskill (foreign library)", 0, ["newskill", "tour-demo", "count demo widgets", "--root", str(lib),
                                          "--state", str(tmp / "state3")], "NEWSKILL"),
        ("newskill again (refused)", 3, ["newskill", "tour-demo", "again", "--root", str(lib),
                                        "--state", str(tmp / "state3")], "EXISTS"),
        ("vocab", 0, ["vocab", *S], "skills"),
        ("used", 0, ["used", *S]),
        # v20: the one-folder commands that had no tour before
        ("whisper", 0, ["whisper", "size a position from a return history", *S], "WHISPER"),
        ("doctor", None, ["doctor", *S], "DOCTOR:"),            # a STALE card or a missing venv is a finding, never a traceback
        ("digest", 0, ["digest", "position-sizer", *S], "NAME position-sizer"),
        ("grade", 0, ["grade", *S], "REPORT CARD"),
        ("hindsight status", 0, ["hindsight", "status", *S], "HINDSIGHT"),
        ("index", 0, ["index", *S], "INDEX VERIFIED"),
        # v20: the research commands live in skill-maestro-extras; a core install says so in one line
        *[(f"{c} without extras", 2, [c, *a, *S], "is part of skill-maestro-extras", NOX)
          for c, a in (("chain", ["last"]), ("rehearse", ["last"]), ("play", ["last"]), ("brief", ["last"]),
                       ("inverse", ["position-sizer"]), ("rerank", []), ("tune", []), ("ablate", []),
                       ("why", ["last", "position-sizer"]), ("odds", []))],
        ("debt --close-older-than", 0, ["debt", "--close-older-than", "0", *S], "CLOSED"),
        ("unknown command", 2, ["dance", *S]),
        ("bad --root", 5, ["score", "x", "--root", str(tmp / "nowhere"), *S]),
        ("STANDALONE foreign library", 0, ["score", "count alpha widgets", "--root", str(lib), "--custom-only",
                                           "--keywords-only", "--state", str(tmp / "state2")]),
    ]


def help_commands(maestro: Path) -> set[str]:
    """Every subcommand maestro.py's own help lists (`python maestro.py <cmd>`)."""
    text = maestro.read_text(encoding="utf-8")
    doc = text.split('"""', 2)[1]
    return set(re.findall(r"python maestro\.py ([a-z][a-z-]*)", doc)) - {"score"} | {"score"}


def _selftest() -> bool:
    maestro = HERE.parent / "maestro.py"
    t = Path(tempfile.gettempdir())
    tours = build_tours(maestro, t, t / "lib", t / "st")
    toured = {args[0] for _, _, args, *_ in tours if args}
    # not toured on purpose: these rewrite real files in the skill folder (cards/lexical.json, cards/mechanisms_auto.jsonl)
    # or run every reviewer skill (selfcheck); a throwaway tour must not change the library it tours
    exempt = ("cards", "lexical", "selfcheck")
    missing = sorted(c for c in help_commands(maestro) if c not in toured and c not in exempt)
    labels = [x[0] for x in tours]
    ok = not missing and len(labels) == len(set(labels))
    print(f"TOUR SELFTEST {'PASS' if ok else 'FAIL'}: {len(tours)} tours, {len(help_commands(maestro))} documented commands"
          + (f"; never toured: {missing}" if missing else "") + ("" if len(labels) == len(set(labels)) else "; duplicate labels"))
    return ok


def main(argv: list[str]) -> int:
    if argv[:1] == ["--selftest"]:
        return 0 if _selftest() else 1
    if len(argv) < 2:
        print(__doc__)
        return 2
    maestro = Path(argv[0]).resolve()
    project = Path(argv[argv.index("--project") + 1]).resolve() if "--project" in argv else None
    tmp = Path(tempfile.mkdtemp(prefix="maestro_tour_"))
    st = tmp / "state"
    lib = tmp / "lib"                      # a two-skill foreign library: the standalone run
    for n, desc, body in (("alpha-tool", "alpha widget counting tool", "print('PASS')\nimport sys; sys.exit(0)\n"),
                          ("beta-broken", "beta gadget tool", "import sys; sys.exit(1)\n")):
        (lib / n).mkdir(parents=True)
        (lib / n / "SKILL.md").write_text(f"---\nname: {n}\ndescription: {desc}\n---\n# {n}\n\n```\npython tool.py --selftest\n```\n",
                                          encoding="utf-8")
        (lib / n / "tool.py").write_text("# --selftest\n" + body, encoding="utf-8")
    M = [sys.executable, "-B", str(maestro)]
    cwd = str(project) if project else str(tmp)
    tours = build_tours(maestro, tmp, lib, st)
    bad, t_all = 0, time.time()
    for label, want, args, *expect in tours:
        env_extra = expect[1] if len(expect) > 1 else {}
        t0 = time.time()
        try:
            r = subprocess.run([*M, *args], cwd=str(tmp) if label.startswith("STANDALONE") else cwd,   # no project library
                               capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8", **env_extra})
            out, rc = r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired:
            out, rc = "TIMEOUT", -1
        tb = "Traceback" in out
        phrase_ok = not expect or expect[0] is None or expect[0] in out
        ok = (want is None or rc == want) and not tb and phrase_ok   # None: any exit, but never a traceback
        bad += not ok
        first = next((ln for ln in out.splitlines() if ln.strip() and not ln.startswith(("(last", "STANDALONE"))), "")[:70]
        if tb:                                            # v20.0.4: the exception line, not the "Traceback" header
            first = next((ln for ln in reversed(out.splitlines()) if ln.strip()), first)[:70]
        print(f"{'ok  ' if ok else 'BAD '} {label:<34} {time.time() - t0:5.1f}s exit={rc}{'' if rc == want else f' (want {want})'}"
              f"{' TRACEBACK' if tb else ''}{'' if phrase_ok else f' (missing {expect[0]!r})'} | {first}")
        if label == "STANDALONE foreign library" and ok:
            if "STANDALONE" not in out or "alpha-tool" not in out or "ON THE PC" in out:
                bad += 1
                print("BAD  standalone output: expected STANDALONE + alpha-tool, no ON THE PC line")
    for sd in (st, tmp / "state2", tmp / "state3"):     # v20.0.4: the helpers the tours spawned, then the folder itself
        if sd.is_dir():
            stop_helpers(sd)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"TOUR {'PASS' if not bad else 'FAIL'}: {len(tours) - bad}/{len(tours)} invocations as expected, "
          f"{time.time() - t_all:.0f} s, temp folder {'removed' if not tmp.exists() else 'left: ' + str(tmp)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
