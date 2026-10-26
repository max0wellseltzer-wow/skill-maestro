"""scaffold - write a new skill folder that passes the house conventions on the first try (part of skill-foundry).

Seed: von Neumann's self-reproducing constructor (a machine that carries the description of itself and builds the
copy) crossed with the user's "use our newly developed skills to make skills". The library's conventions are the
description; scaffold() is the constructor.

scaffold(name, description, tool_name, root) writes <root>/<name>/SKILL.md and <root>/<name>/<tool_name>.py:
  * SKILL.md: frontmatter name = folder, ONE-line description validated to contain no ": " and no " #" (both break
    unquoted YAML silently) and to include "Use this whenever"; body intro, "## The tool (ships with this skill)",
    "## Uses and limits".
  * the tool: module docstring, _selftest() skeleton printing PASS/FAIL and returning bool, main(argv) running it on
    --selftest or no args, and the `if __name__` line.
Refuses an existing folder, a name that is not kebab-case, and a description that fails validation.

    from scaffold import scaffold, validate_description
    scaffold("tide-clock", "Predict tides. Use this whenever the user ... Pairs with x.", "tides", root)
    python scaffold.py --selftest
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SK = Path(__file__).resolve().parents[1]

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOOL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

TOOL_TEMPLATE = '''"""{module} - {summary} (backs the {name} skill).

    python {module}.py --selftest
"""
from __future__ import annotations

import sys


def _selftest() -> bool:
    ok = {{}}
    ok["skeleton: replace with real checks (>= 6, one planted bad input)"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {name}

{intro}

## The tool (ships with this skill)

`{module}.py` - pure stdlib, selftest skeleton (replace with real checks):

```
python {module}.py --selftest
```

## Uses and limits

{limits}
"""


def validate_description(desc) -> list:
    """Problems with a frontmatter description written UNQUOTED (empty list = fine)."""
    if not isinstance(desc, str) or not desc.strip():
        return ["empty description"]
    out = []
    if "\n" in desc.strip():
        out.append("description must be ONE line")
    if ": " in desc or desc.rstrip().endswith(":"):
        out.append("contains ': ' (YAML mapping indicator - the whole frontmatter fails silently)")
    if re.search(r"\s#", desc):
        out.append("contains ' #' (YAML comment - the rest of the description is dropped)")
    if desc.strip()[0] in "\"'[{&*!|>%@`":
        out.append("starts with a YAML special character")
    if "Use this whenever" not in desc:
        out.append("missing the 'Use this whenever' routing clause")
    return out


def scaffold(name: str, description: str, tool_name: str, root=None, intro: str = "", limits: str = "") -> Path:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError(f"skill name must be kebab-case (a-z, 0-9, single hyphens): {name!r}")
    module = (tool_name or "").removesuffix(".py")
    if not TOOL_RE.match(module):
        raise ValueError(f"tool name must be a python module name: {tool_name!r}")
    probs = validate_description(description)
    if probs:
        raise ValueError("bad description: " + "; ".join(probs))
    root = Path(root) if root else Path.home() / ".claude" / "skills"
    d = root / name
    if d.exists():
        raise FileExistsError(f"refusing to overwrite existing skill folder {d}")
    summary = description.split(". ")[0].strip().rstrip(".")[:100]
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL_TEMPLATE.format(
        name=name, description=description.strip(), module=module,
        intro=intro or f"TODO intro - cite the seed prompt. {summary}.",
        limits=limits or "TODO - what it is for, what it cannot tell you, how slow it is."), encoding="utf-8")
    (d / f"{module}.py").write_text(TOOL_TEMPLATE.format(module=module, name=name, summary=summary), encoding="utf-8")
    return d


def _selftest() -> bool:
    import shutil
    import subprocess
    import tempfile
    sys.path.insert(0, str(SK / "skill-health"))
    from skill_health import check_library
    ok = {}
    tmp = Path(tempfile.mkdtemp(prefix="scaffold_"))
    good = ("Predict harbour tides from lunar phase. Use this whenever the user asks when the water rises. "
            "Pairs with skill-foundry.")
    try:
        d = scaffold("tide-clock", good, "tides", tmp)
        rep = check_library(tmp, only={"tide-clock"})
        ok["a scaffolded skill passes skill-health check_library OK on the first try"] = (
            rep["skills"] == 1 and rep["rows"][0]["status"] == "OK")
        md = (d / "SKILL.md").read_text(encoding="utf-8")
        ok["SKILL.md has name = folder and both house sections"] = (
            "\nname: tide-clock\n" in md and "## The tool (ships with this skill)" in md and "## Uses and limits" in md)
        r = subprocess.run([sys.executable, "-B", str(d / "tides.py")], capture_output=True, text=True, cwd=str(tmp))
        ok["the tool runs its selftest with no args and prints PASS"] = r.returncode == 0 and r.stdout.startswith("PASS")
        for bad, label in (("Track tides: by moon. Use this whenever the user asks.", "colon-space"),
                           ("Track tides on issue #41. Use this whenever the user asks.", "space-hash"),
                           ("Track tides by the moon.", "no routing clause")):
            try:
                scaffold("bad-" + label.replace(" ", "-"), bad, "t", tmp)
                ok[f"planted bad description ({label}) is rejected"] = False
            except ValueError:
                ok[f"planted bad description ({label}) is rejected"] = not (tmp / ("bad-" + label.replace(" ", "-"))).exists()
        for bad_name in ("TideClock", "tide_clock", "-tide", "tide--clock"):
            try:
                scaffold(bad_name, good, "t", tmp)
                ok["non-kebab names are refused"] = False
                break
            except ValueError:
                ok["non-kebab names are refused"] = True
        before = md
        try:
            scaffold("tide-clock", good, "tides", tmp)
            ok["an existing folder is never overwritten"] = False
        except FileExistsError:
            ok["an existing folder is never overwritten"] = (d / "SKILL.md").read_text(encoding="utf-8") == before
        ok["no __pycache__ left behind"] = not any(tmp.rglob("__pycache__"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    if len(argv) < 3:
        print("usage: scaffold.py NAME DESCRIPTION TOOL_NAME [ROOT]")
        return 2
    print(scaffold(argv[0], argv[1], argv[2], argv[3] if len(argv) > 3 else None))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
