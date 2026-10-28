"""scrub.py - take this machine's paths out of the survey (cards/tested.jsonl) so the public copy carries none.

The survey's rows are written by agents that tested each skill on the owner's PC, so their `subject`, `command` and
`result` strings name that PC's folders. The public package must not. Every string in every row goes through one list
of rules, built from where THIS machine keeps things (the home folder, Claude Code's temp folder, the workspace roots),
so the module needs no editing when someone else publishes their own survey:

    <home>/AppData/Local/Temp/claude/<slug>/<session>/scratchpad  -> <scratchpad>
    <home>/AppData/Local/Temp/claude                              -> <tmp>
    <home>/.claude/skills  /  <home>/.claude  /  <home>/venvs       -> ~/.claude/skills  /  ~/.claude  /  ~/venvs
    <home>  (C:\\Users\\name, C:/Users/name, /c/Users/name)         -> ~
    each workspace root (MAESTRO_SCRUB_ROOTS, default C:/Autotrade)  -> <workspace>
    the project slug Claude Code derives from the home folder        -> C--workspace

`maestro.py survey build` runs every row through `scrub_row` as it writes them (v20.0.3), so a fresh survey is clean.
This file's own command is the full pass over an existing survey:

    python scrub.py                     dry run on cards/tested.jsonl beside this file: path shapes found, leftovers
    python scrub.py FILE                dry run on another JSONL file
    python scrub.py [FILE] --write      rewrite in place (LF line ends; every line stays valid JSON)
    python scrub.py --selftest

The owner's name (the home folder's name, or MAESTRO_SCRUB_OWNER) goes too, as a whole word and case-sensitive:
"whenever Owner asks" -> "whenever the user asks", "Owner's call" -> "the user's call" (the owner's ruling, 2026-10-25:
"switch out every instance of my name for the word user"). Lower-case words, handles and MAX_* names are not touched.
The dry run counts what is left under `<the word NAME>` so a leftover is visible, not hidden.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTED = HERE / "cards" / "tested.jsonl"
SEP = r"(?:\\|/)"


def _path_rx(p: str) -> str:
    """A regex that matches path `p` written with either separator, any drive-letter case, or in the
    Git Bash form (/c/Users/...)."""
    p = p.replace("\\", "/").rstrip("/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        drive, rest = m.group(1), m.group(2)
        parts = [re.escape(x) for x in rest.split("/") if x]
        body = SEP.join(parts)
        return rf"(?:[{drive.upper()}{drive.lower()}]:{SEP}|/{drive.lower()}/){body}"
    return SEP.join(re.escape(x) for x in p.split("/") if x)


def build_rules(home: Path | None = None, tmp: Path | None = None, roots: list[str] | None = None,
                owner: str | None = None) -> list[tuple[re.Pattern, str]]:
    """The rules for THIS machine, most specific first. `roots` are the workspace folders (default from
    MAESTRO_SCRUB_ROOTS, `;`-separated, else C:/Autotrade); `owner` is the name to turn into "the user" (default
    MAESTRO_SCRUB_OWNER, else the home folder's name)."""
    home = Path(home or Path.home())
    tmp = Path(tmp or tempfile.gettempdir())
    if roots is None:
        roots = [r for r in os.environ.get("MAESTRO_SCRUB_ROOTS", "C:/Autotrade").split(";") if r.strip()]
    if owner is None:
        owner = os.environ.get("MAESTRO_SCRUB_OWNER") or home.name
    h = _path_rx(str(home))
    claude_tmp = _path_rx(str(tmp / "claude"))
    tmp_rules = [
        (claude_tmp + SEP + r"[A-Za-z0-9_.-]+" + SEP + r"[0-9a-fA-F-]+" + SEP + "scratchpad", "<scratchpad>"),
        (claude_tmp, "<tmp>"),
    ]
    home_rules = [
        (h + SEP + r"\.claude" + SEP + "skills", "~/.claude/skills"),
        (h + SEP + r"\.claude", "~/.claude"),
        (h + SEP + "venvs", "~/venvs"),
        (h, "~"),
    ]
    # a sandboxed run (home inside Claude Code's temp folder): the home is the more specific path, so it goes first
    sandboxed = Path(str(home).replace("\\", "/").lower()).is_relative_to(str(tmp / "claude").replace("\\", "/").lower())
    rules: list[tuple[str, str]] = home_rules + tmp_rules if sandboxed else tmp_rules + home_rules
    for r in roots:
        rules.append((_path_rx(r), "<workspace>"))
    slug = re.sub(r"[:\\/]", "-", str(home))           # C:\Users\name -> C--Users-name (Claude Code's project folder)
    rules.append((re.escape(slug), "C--workspace"))
    if owner:                                           # the name itself, after every path that carries it is gone
        rules.append((r"\b" + re.escape(owner) + r"'s\b", "the user's"))
        rules.append((r"\b" + re.escape(owner) + r"\b", "the user"))
    return [(re.compile(rx), rep) for rx, rep in rules]


_RULES: list[tuple[re.Pattern, str]] | None = None


def rules() -> list[tuple[re.Pattern, str]]:
    global _RULES
    if _RULES is None:
        _RULES = build_rules()
    return _RULES


def scrub_text(s: str, rs: list[tuple[re.Pattern, str]] | None = None) -> str:
    for rx, rep in (rs or rules()):
        s = rx.sub(rep, s)
    return s


def scrub_row(x, rs: list[tuple[re.Pattern, str]] | None = None):
    """Every string inside a JSON value, recursively; keys and non-strings untouched."""
    if isinstance(x, str):
        return scrub_text(x, rs)
    if isinstance(x, list):
        return [scrub_row(v, rs) for v in x]
    if isinstance(x, dict):
        return {k: scrub_row(v, rs) for k, v in x.items()}
    return x


_SHAPE = re.compile(r"(?:[A-Za-z]:|/[a-z])" + SEP + r"[A-Za-z0-9_.-]+(?:" + SEP + r"[A-Za-z0-9_.-]+){0,2}")


def scrub_file(path: Path, write: bool = False, rs: list[tuple[re.Pattern, str]] | None = None,
               owner: str | None = None) -> dict:
    """Scrub a JSONL file. Returns {rows, changed, shapes, leftovers, written}; writes only with write=True."""
    rs = rs or rules()
    owner = owner if owner is not None else Path.home().name
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    out, shapes, changed = [], collections.Counter(), 0
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        row = json.loads(ln)
        for m in _SHAPE.finditer(json.dumps(row, ensure_ascii=False)):
            shapes[m.group(0)] += 1
        new = scrub_row(row, rs)
        if new != row:
            changed += 1
        out.append(json.dumps(new, ensure_ascii=False, sort_keys=True))
    leftovers: collections.Counter = collections.Counter()
    for ln in out:
        for m in _SHAPE.finditer(ln):
            leftovers[m.group(0)] += 1
        if owner and owner in ln:
            leftovers[f"<the word {owner}>"] += ln.count(owner)
    if write:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out))
    return {"rows": sum(1 for l in lines if l.strip()), "changed": changed, "shapes": shapes,
            "leftovers": leftovers, "written": write}


def _selftest() -> bool:
    ok: dict[str, bool] = {}
    home, tmp = Path("C:/Users/Owner"), Path("C:/Users/Owner/AppData/Local/Temp")
    rs = build_rules(home, tmp, ["C:/Work"])
    s = scrub_text
    ok["home in both separators and the Git Bash form -> ~"] = (
        s(r"C:\Users\Owner\x.txt", rs) == "~\\x.txt" and s("C:/Users/Owner/x", rs) == "~/x"
        and s("/c/Users/Owner/x", rs) == "~/x" and s("C:/Users/Owner", rs) == "~")
    ok["the skills folder, .claude and venvs keep their tail"] = (
        s(r"C:\Users\Owner\.claude\skills\foo\SKILL.md", rs) == "~/.claude/skills\\foo\\SKILL.md"
        and s("C:/Users/Owner/.claude/settings.json", rs) == "~/.claude/settings.json"
        and s("C:/Users/Owner/venvs/m/Scripts/python.exe", rs) == "~/venvs/m/Scripts/python.exe")
    ok["scratchpad and the claude temp folder"] = (
        s(r"C:\Users\Owner\AppData\Local\Temp\claude\C--Users-Owner\0123abcd-ef\scratchpad\a.py", rs) == "<scratchpad>\\a.py"
        and s("C:/Users/Owner/AppData/Local/Temp/claude/other", rs) == "<tmp>/other")
    ok["workspace roots from the argument; the project slug"] = (
        s("cd C:/Work/tv-x && ls /c/Work", rs) == "cd <workspace>/tv-x && ls <workspace>"
        and s("projects/C--Users-Owner/x.jsonl", rs) == "projects/C--workspace/x.jsonl")
    ok["unrelated paths and a stranger's home untouched"] = (
        s(r"C:\Data\x.csv", rs) == r"C:\Data\x.csv" and s("C:/Users/Other/x", rs) == "C:/Users/Other/x"
        and s("D:/Work/x", rs) == "D:/Work/x")
    ok["the owner's name becomes the user; lower case, handles and OWNER_MAX untouched"] = (
        s("whenever Owner asks (Owner's call, not owner0wellseltzer or OWNER_MAX or owner)", rs)
        == "whenever the user asks (the user's call, not owner0wellseltzer or OWNER_MAX or owner)"
        and s("C:/Users/Owner/x.txt by Owner", rs) == "~/x.txt by the user")
    row = {"name": "k", "does": "x", "asks": ["run C:/Users/Owner/a", 3], "n": {"cmd": "/c/Work/run.py"}}
    ok["scrub_row walks lists and dicts, leaves keys and numbers"] = scrub_row(row, rs) == {
        "name": "k", "does": "x", "asks": ["run ~/a", 3], "n": {"cmd": "<workspace>/run.py"}}
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "t.jsonl"
        f.write_text(json.dumps({"name": "a", "result": "wrote C:/Users/Owner/o.txt"}) + "\r\n"
                     + json.dumps({"name": "b", "result": "fine"}) + "\r\n", encoding="utf-8")
        before = f.read_bytes()
        r1 = scrub_file(f, write=False, rs=rs, owner="Owner")
        dry_untouched = f.read_bytes() == before
        r2 = scrub_file(f, write=True, rs=rs, owner="Owner")
        text = f.read_bytes()
        rows = [json.loads(x) for x in text.decode().split("\n") if x.strip()]
        ok["dry run touches nothing and counts; --write rewrites LF with every line valid JSON"] = (
            dry_untouched and r1["rows"] == 2 and r1["changed"] == 1 and r1["shapes"]["C:/Users/Owner/o.txt"] == 1
            and not r1["leftovers"] and r2["written"] and b"\r" not in text
            and rows[0]["result"] == "wrote ~/o.txt" and rows[1]["result"] == "fine")
    box = "C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner/0123abcd-ef/scratchpad"
    rb = build_rules(Path(box + "/box/home"), tmp, ["C:/Work"], owner="Owner")
    ok["a home inside Claude Code's temp folder still goes to ~; the scratchpad outside it to <scratchpad>"] = (
        s(box + "/box/home/q", rb) == "~/q" and s(box + "/box/home/.claude/x", rb) == "~/.claude/x"
        and s(box + "/other.py", rb) == "<scratchpad>/other.py")
    ok["the real rules build from this machine and send its home to ~"] = scrub_text(str(Path.home()) + "/q") == "~/q"
    for k, v in ok.items():
        print(f"  {'PASS' if v else 'FAIL'} scrub: {k}")
    print(f"scrub selftest: {sum(ok.values())}/{len(ok)} {'PASS' if all(ok.values()) else 'FAIL'}")
    return all(ok.values())


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    write = "--write" in argv
    pos = [a for a in argv if not a.startswith("--")]
    path = Path(pos[0]) if pos else TESTED
    if not path.is_file():
        print(f"scrub: no such file {path}")
        return 2
    r = scrub_file(path, write=write)
    print(f"rows {r['rows']} changed {r['changed']}" + ("  (dry run; add --write to rewrite)" if not write else ""))
    print("shapes before:", r["shapes"].most_common(15))
    print("leftovers after:", r["leftovers"].most_common(15))
    if write:
        print("written", path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
