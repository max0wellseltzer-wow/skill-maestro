"""skill_health - one command that verifies the whole skill library (backs the skill-health skill).

Walks a skills root (default: ~/.claude/skills), and for every skill folder with a SKILL.md checks:
  * frontmatter `name:` matches the folder name (a mismatch breaks discovery);
  * every bundled tool that offers `--selftest` passes it, run from a NEUTRAL working directory (so a tool
    that secretly depends on the current directory is caught);
  * tools import only the standard library (or sibling tools in the library) - i.e. they are portable;
  * WARN: absolute user/repo paths written into a tool (usually a portability smell).
It also counts doc-only skills (no bundled script). Exit code is 1 if anything FAILS, so it can gate a CI step.

    python skill_health.py                    # check ~/.claude/skills
    python skill_health.py <skills_root>      # check another library
    python skill_health.py --only a,b,c       # check just these skills
    python skill_health.py --selftest         # proves the checker catches each failure kind
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
# Built from pieces so this file's own source does not match its own pattern.
_DRIVE = r"[A-Za-z]:[\\/]+"
PATH_SMELL = re.compile("(" + "|".join([_DRIVE + "Use" + r"rs[\\/]", "/c/" + "Users/",
                                        _DRIVE + "Auto" + "trade", "/c/" + "Auto" + "trade"]) + ")")
_OPTIONAL_CATCH = {"ImportError", "ModuleNotFoundError", "Exception"}


def _description_problems(skill_md: Path) -> list:
    """An UNQUOTED YAML description breaks silently on two traps (found 2026-10-16): ' #' starts a comment (the rest
    of the description vanishes - writer-pen lost everything after 'issue #41'), and ': ' is a mapping indicator
    (the whole frontmatter fails and the skill shows only its name). Quote the value or avoid both."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines()[1:40]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            v = line[len("description:"):].strip()
            if not v:
                return ["empty description"]
            if v[0] in "\"'":
                return []
            out = []
            if re.search(r"\s#", v):
                out.append("unquoted description contains ' #' (YAML comment: the rest is dropped)")
            if ": " in v or v.endswith(":"):
                out.append("unquoted description contains ': ' (YAML error: the description is lost)")
            return out
    return ["no description in frontmatter"]


def _frontmatter_name(skill_md: Path):
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    for line in text.splitlines()[1:40]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def _tools(skill_dir: Path):
    out = []
    for p in sorted(skill_dir.rglob("*.py")):
        if "__pycache__" in p.parts or p.name.startswith("test_"):
            continue
        if "evals" in p.relative_to(skill_dir).parts:      # eval fixtures/graders run by the harness, not shipped tools
            continue
        out.append(p)
    return out


def _third_party_imports(py: Path, local_modules: set) -> list:
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as e:
        return [f"SYNTAX ERROR: {e.msg} (line {e.lineno})"]
    # Imports inside `try: ... except ImportError/Exception:` are OPTIONAL (the tool has a fallback), so they
    # don't break portability and are not counted.
    guarded = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            def _catches(h):
                if h.type is None:
                    return True
                if isinstance(h.type, ast.Name):
                    return h.type.id in _OPTIONAL_CATCH
                if isinstance(h.type, ast.Tuple):
                    return any(isinstance(e, ast.Name) and e.id in _OPTIONAL_CATCH for e in h.type.elts)
                return False
            if any(_catches(h) for h in node.handlers):
                for stmt in node.body:
                    for sub in ast.walk(stmt):
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            guarded.add(id(sub))
    bad = set()
    for node in ast.walk(tree):
        if id(node) in guarded:
            continue
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        for n in names:
            if n not in STDLIB and n not in local_modules:
                bad.add(n)
    return sorted(bad)


def _offers_selftest(py: Path) -> bool:
    t = py.read_text(encoding="utf-8", errors="replace")
    # 2026-10-22 (L5461): tour.py had `def selftest()` and was reported "no --selftest"; accept both spellings.
    return "--selftest" in t and ("_selftest" in t or re.search(r"\bdef\s+selftest\s*\(", t) is not None)


def check_library(root: Path, only=None, timeout: int = 90) -> dict:
    root = Path(root).resolve()          # selftests run from a neutral cwd, so a relative root must be made absolute
    root = Path(root)
    skills = sorted(d for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    if only:
        skills = [d for d in skills if d.name in only]
    local_modules = {p.stem for p in root.rglob("*.py")}
    neutral = tempfile.mkdtemp(prefix="skillhealth_")
    rows, fails, warns, doc_only = [], 0, 0, []
    for d in skills:
        name_fm = _frontmatter_name(d / "SKILL.md")
        problems, notes = [], []
        if name_fm != d.name:
            problems.append(f"frontmatter name '{name_fm}' != folder '{d.name}'")
        problems += _description_problems(d / "SKILL.md")
        tools = _tools(d)
        if not tools:
            doc_only.append(d.name)
        for py in tools:
            tp = _third_party_imports(py, local_modules)
            if tp:
                problems.append(f"{py.name}: non-stdlib import(s) {tp}")
            if PATH_SMELL.search(py.read_text(encoding="utf-8", errors="replace")):
                notes.append(f"{py.name}: absolute user/repo path in source")
            if _offers_selftest(py):
                try:
                    r = subprocess.run([sys.executable, "-B", str(py), "--selftest"], cwd=neutral,
                                       capture_output=True, text=True, timeout=timeout,
                                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})   # leave no __pycache__ in skills
                    if r.returncode != 0:
                        fl = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")][:3]
                        problems.append(f"{py.name}: selftest exit {r.returncode} {fl}")
                except subprocess.TimeoutExpired:
                    problems.append(f"{py.name}: selftest timed out (>{timeout}s)")
            else:
                notes.append(f"{py.name}: no --selftest")
        status = "FAIL" if problems else ("WARN" if notes else "OK")
        fails += status == "FAIL"
        warns += status == "WARN"
        rows.append({"skill": d.name, "status": status, "tools": len(tools),
                     "problems": problems, "notes": notes})
    shutil.rmtree(neutral, ignore_errors=True)
    return {"rows": rows, "skills": len(rows), "fails": fails, "warns": warns,
            "doc_only": doc_only, "tool_backed": len(rows) - len(doc_only)}


def _print(report: dict) -> None:
    for r in report["rows"]:
        if r["status"] != "OK":
            print(f"{r['status']:4s} {r['skill']}")
            for p in r["problems"]:
                print(f"       ! {p}")
            for n in r["notes"]:
                print(f"       - {n}")
    print(f"\nskills: {report['skills']}   tool-backed: {report['tool_backed']}   "
          f"doc-only: {len(report['doc_only'])}   FAIL: {report['fails']}   WARN: {report['warns']}")
    if report["doc_only"]:
        print("doc-only:", ", ".join(report["doc_only"]))


def _selftest() -> bool:
    ok = {}
    root = Path(tempfile.mkdtemp(prefix="sh_selftest_"))

    def skill(name, fm_name, tool_src=None, tool_name="t.py"):
        d = root / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {fm_name}\ndescription: x\n---\nbody\n", encoding="utf-8")
        if tool_src is not None:
            (d / tool_name).write_text(tool_src, encoding="utf-8")

    good = ("import sys\ndef _selftest():\n    print('PASS ok'); return True\n"
            "def main(a):\n    return 0 if _selftest() else 1\n"
            "if __name__=='__main__': sys.exit(main(sys.argv[1:]))  # --selftest\n")
    failing = good.replace("return True", "return False")
    third = "import numpy\n" + good
    cwd_dep = ("import sys, os\ndef _selftest():\n    return os.path.exists('only_in_skill_dir.txt')\n"
               "def main(a):\n    return 0 if _selftest() else 1\n"
               "if __name__=='__main__': sys.exit(main(sys.argv[1:]))  # --selftest\n")
    skill("good", "good", good)
    skill("misnamed", "wrong-name", good)
    skill("failing", "failing", failing)
    skill("thirdparty", "thirdparty", third)
    skill("cwddep", "cwddep", cwd_dep)
    (root / "cwddep" / "only_in_skill_dir.txt").write_text("x", encoding="utf-8")
    skill("doconly", "doconly", None)
    optional = "try:\n    import numpy\nexcept ImportError:\n    numpy = None\n" + good
    skill("optional", "optional", optional)
    bare = "import sys\nprint('no selftest here')\n"
    skill("nosel", "nosel", bare)
    skill("withevals", "withevals", good)
    (root / "withevals" / "evals" / "files").mkdir(parents=True)
    (root / "withevals" / "evals" / "files" / "check_e1.py").write_text(bare, encoding="utf-8")
    skill("imports", "imports", "import helper\n" + good)       # importing a sibling is what writes __pycache__
    (root / "imports" / "helper.py").write_text(good, encoding="utf-8")
    skill("plainself", "plainself", good.replace("_selftest", "selftest"))
    rep = check_library(root)
    st = {r["skill"]: r for r in rep["rows"]}
    ok["a healthy skill reads OK"] = st["good"]["status"] == "OK"
    ok["a frontmatter/folder name mismatch FAILS"] = st["misnamed"]["status"] == "FAIL"
    ok["a failing selftest FAILS"] = st["failing"]["status"] == "FAIL"
    ok["a non-stdlib import FAILS"] = st["thirdparty"]["status"] == "FAIL"
    ok["a tool that only works from its own folder FAILS (neutral cwd)"] = st["cwddep"]["status"] == "FAIL"
    ok["a doc-only skill is counted, not failed"] = ("doconly" in rep["doc_only"] and st["doconly"]["status"] == "OK")
    ok["an OPTIONAL import (try/except ImportError) is not a failure"] = st["optional"]["status"] == "OK"
    ok["the checker does not flag its own source"] = not PATH_SMELL.search(Path(__file__).read_text(encoding="utf-8"))
    ok["a shipped tool without --selftest still WARNs"] = st["nosel"]["status"] == "WARN"
    ok["eval fixtures under evals/ are not treated as shipped tools"] = st["withevals"]["status"] == "OK"
    ok["a tool importing its sibling module still passes"] = st["imports"]["status"] == "OK"
    ok["a tool with `def selftest()` (no underscore) counts as offering --selftest"] = st["plainself"]["status"] == "OK"
    ok["totals add up"] = (rep["skills"] == 11 and rep["fails"] == 4 and rep["tool_backed"] == 10)
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):                # 2026-10-21 (L4976): `--help` crashed with a traceback
        codes = (main(["--help"]), main([str(root / "no_such_dir")]), main(["--bogus"]), main(["--only"]))
    ok["--help, a missing root, an unknown flag and a bare --only print usage and exit 2, no traceback"] = (
        codes == (0, 2, 2, 2) and "usage" in buf.getvalue().lower())
    here = os.getcwd()                                   # 2026-10-16: three builders saw every tool FAIL with "."
    try:
        os.chdir(root.parent)
        rel = check_library(Path(root.name), only={"good"})
        ok["a RELATIVE root gives the same verdict as the absolute one"] = (
            rel["fails"] == 0 and {r["skill"]: r["status"] for r in rel["rows"]}.get("good") == "OK")
    finally:
        os.chdir(here)
    trap = root / "trap.md"
    trap.write_text("---\nname: t\ndescription: ask on issue #41 first: then land\n---\n", encoding="utf-8")
    quoted = root / "quoted.md"
    quoted.write_text('---\nname: q\ndescription: "ask on issue #41 first: then land"\n---\n', encoding="utf-8")
    ok["planted YAML traps in a description (' #', ': ') are caught; a quoted one passes"] = (
        len(_description_problems(trap)) == 2 and _description_problems(quoted) == [])
    ok["running selftests leaves no __pycache__ in skill folders"] = not any(root.rglob("__pycache__"))
    shutil.rmtree(root, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if argv and argv[0] == "--selftest":
        return 0 if _selftest() else 1
    usage = "usage: python skill_health.py [skills_root] [--only a,b,c] | --selftest"
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        print(usage)
        return 0
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
            print("--only needs a comma-separated list of skill names\n" + usage)
            return 2
        only = set(argv[i + 1].split(","))
        argv = argv[:i] + argv[i + 2:]
    if argv and argv[0].startswith("-"):
        print(f"unknown option {argv[0]}\n" + usage)
        return 2
    root = Path(argv[0]) if argv else Path.home() / ".claude" / "skills"
    if not root.is_dir():
        print(f"not a folder: {root}\n" + usage)
        return 2
    rep = check_library(root, only=only)
    _print(rep)
    return 1 if rep["fails"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
