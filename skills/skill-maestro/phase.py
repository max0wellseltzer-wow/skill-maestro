"""The PHASE reading (2026-10-25): where the running session is heading, read from the skills it just used.

HISTORY_v19.md section 3 found that 48 of the 81 walk-forward prompts are CONTEXT-DRIVEN: the words of the prompt never
name the skill Claude reached for ("okay proceed with the still open", "now land it"); the skill follows from what
the session was doing. Words, meaning and the personal reading all look at the prompt. This reading looks at the
session instead: a transition table from this machine's own hindsight rows (predecessor skills used on the earlier
prompts of a session -> skills used on the next one, weighted 1/(1+k) over the last RECENT used turns), applied to
the last RECENT used turns of the running session. The prompt's words play no part, so a fresh session (and every
held-out probe, which carries no session) gets an empty reading and ranks exactly as before.

    live:  the whisper hook and `score` read the running transcript's tail (the Skill tool calls and skills/<name>/
           paths of the last turns; no full scan: a transcript can be 100 MB);
    eval:  a probe that is a real hindsight row gets the same-session rows before it as its context, and a table cut
           strictly before the probe's own row (never its own label) and before --before when given.

Nothing here leaves the machine; nothing is written. Fused with weight_phase (dial M52), measured on both answer keys.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path

RECENT = 3            # used turns of the session that feed the reading (the newest weighs 1, then 1/2, 1/3)
STICKY = 0.5          # the predecessor skills' own vote: a session often stays on the skill it is on
SELF = "skill-maestro"
SWEEP_MAX = 12        # as hindsight.py: more skills after one prompt is a library audit, not a choice
TAIL_BYTES = 4 * 1024 * 1024
MAX_AGE_S = 6 * 3600
SKILL_PATH = re.compile(r"skills[\\/]+([a-z0-9]+(?:-[a-z0-9]+)*)[\\/]")
NOT_OWNER = ("<", "Another Claude session", "This session is being continued", "Base directory", "[Request interrupted")
_ROWS: dict[tuple, list[dict]] = {}
_TABLES: dict[tuple, dict] = {}


def norm(text) -> str:
    return " ".join(str(text or "").split())


def cut_str(before) -> str | None:
    """A cut as the hindsight rows carry their ts ("YYYY-MM-DD HH:MM"): an epoch (the eval's --before, local midnight
    as personal.py reads it), a ts string, or None."""
    if before is None:
        return None
    if isinstance(before, (int, float)):
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(before)))
    return str(before)[:16].replace("T", " ")


def used_of(r: dict) -> list[str]:
    """The skills really used after a prompt, the Maestro itself never among them; a sweep counts as nothing."""
    used = set(r.get("used") or []) | set(r.get("observed") or [])
    used.discard(SELF)
    if not used or r.get("sweep") or len(used) > SWEEP_MAX:
        return []
    return sorted(used)


def rows_of(state: Path) -> list[dict]:
    """The hindsight rows of this machine (state/hindsight.jsonl), cached by the file's mtime and size."""
    f = Path(state) / "hindsight.jsonl"
    try:
        stt = f.stat()
    except OSError:
        return []
    key = (str(f), stt.st_mtime, stt.st_size)
    if key not in _ROWS:
        out = []
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("ts"):
                out.append(r)
        _ROWS.clear()
        _ROWS[key] = out
    return _ROWS[key]


def table(rows: list[dict], before=None, recent: int = RECENT) -> dict:
    """{"next": {a: Counter(b -> weight)}, "out": Counter(a -> weight), "rows": n}: how often skill a, used on one of
    the last `recent` used prompts of a session, was followed by skill b on the next used prompt (weight 1/(1+k) for
    the k-th previous turn). Rows at or after `before` are left out. Cached per (cut, recent, row count)."""
    cut = cut_str(before)
    key = (cut, recent, len(rows), id(rows))
    if key in _TABLES:
        return _TABLES[key]
    by_session: dict[str, list[tuple[str, list[str]]]] = {}
    for r in rows:
        ts = str(r.get("ts") or "")
        if cut is not None and ts >= cut:
            continue
        u = used_of(r)
        if u:
            by_session.setdefault(str(r.get("session") or ""), []).append((ts, u))
    nxt: dict[str, Counter] = {}
    out: Counter = Counter()
    n = 0
    for seq in by_session.values():
        seq.sort(key=lambda x: x[0])
        for i, (_, used) in enumerate(seq):
            n += 1
            for k, (_, prev) in enumerate(reversed(seq[max(0, i - recent):i])):
                w = 1.0 / (1 + k)
                for a in prev:
                    out[a] += w
                    c = nxt.setdefault(a, Counter())
                    for b in used:
                        c[b] += w
    if len(_TABLES) > 64:
        _TABLES.clear()
    _TABLES[key] = {"next": nxt, "out": out, "rows": n}
    return _TABLES[key]


def reading(tab: dict, context: list[list[str]], recent: int = RECENT, sticky: float = STICKY) -> list[str]:
    """Skills ranked by where sessions went after using what this session just used. `context` = the used lists of
    the session's earlier prompts, oldest first; the newest weighs 1, the one before 1/2, then 1/3."""
    sc: Counter = Counter()
    for k, used in enumerate(reversed(list(context)[-recent:])):
        w = 1.0 / (1 + k)
        for a in used:
            tot = tab["out"].get(a, 0.0)
            if tot:
                for b, c in tab["next"][a].items():
                    sc[b] += w * c / tot
            sc[a] += w * sticky
    return [n for n, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]


def context_of(rows: list[dict], text: str, before=None, recent: int = RECENT) -> tuple[list[list[str]], str | None]:
    """The eval's context for a probe: when the probe is a hindsight row, the used lists of the same session's last
    `recent` used prompts before it, and the table cut = the earlier of `before` and the row's own ts (its own label
    never enters the table). A prompt that is no row: ([], before) -> an empty reading."""
    cut = cut_str(before)
    t = norm(text)
    cands = [r for r in rows if norm(r.get("text")) == t]
    if not t or not cands:
        return [], cut
    r = min(cands, key=lambda x: str(x.get("ts") or ""))
    ts, ses = str(r.get("ts") or ""), r.get("session")
    prev = [(str(x.get("ts") or ""), used_of(x)) for x in rows
            if x.get("session") == ses and str(x.get("ts") or "") < ts and used_of(x)]
    prev.sort(key=lambda x: x[0])
    ctx = [u for _, u in prev[-recent:]]
    return ctx, (min(cut, ts) if cut else ts)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def tail_used(transcript: Path, k: int = RECENT, max_bytes: int = TAIL_BYTES) -> list[list[str]]:
    """The used lists of the last k owner turns (that used anything) in a transcript's tail: Skill tool calls and
    skills/<name>/ paths in tool inputs, as hindsight.py reads them, from the last `max_bytes` only. The newest turn
    (the prompt being ranked, when the harness has already written it) has no uses yet and is skipped."""
    p = Path(transcript)
    try:
        size = p.stat().st_size
        with p.open("rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
                fh.readline()                               # drop the cut line
            data = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    turns: list[set] = []
    cur: set | None = None
    for raw in data.splitlines():
        is_user = '"user"' in raw and '"tool_result"' not in raw
        if not is_user and '"tool_use"' not in raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain") or rec.get("isMeta"):
            continue
        msg = rec.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if rec.get("type") == "user" and is_user:
            text = _text(content).strip()
            if text and not text.startswith(NOT_OWNER):
                cur = set()
                turns.append(cur)
        elif rec.get("type") == "assistant" and cur is not None and isinstance(content, list):
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Skill" and isinstance(inp, dict) and inp.get("skill"):
                    cur.add(str(inp["skill"]).split(":")[-1])
                for m in SKILL_PATH.finditer(json.dumps(inp)):
                    cur.add(m.group(1))
    out = [used_of({"used": sorted(t)}) for t in turns]
    return [u for u in out if u][-k:]


def live_context(state: Path, transcript: str | Path | None = None, k: int = RECENT, max_age_s: int = MAX_AGE_S) -> list[list[str]]:
    """The running session's context: the transcript the hook names (transcript_path), else the newest transcript
    under ~/.claude/projects when it was written within max_age_s. Empty when there is none."""
    p = Path(transcript) if transcript else None
    if p is None or not p.is_file():
        home = Path.home() / ".claude" / "projects"
        files = [f for f in home.glob("*/*.jsonl") if f.is_file()] if home.is_dir() else []
        if not files:
            return []
        p = max(files, key=lambda f: f.stat().st_mtime)
        if time.time() - p.stat().st_mtime > max_age_s:
            return []
    return tail_used(p, k)


def _selftest() -> bool:
    import tempfile
    ok = {}
    rows = [{"ts": "2026-10-01 10:00", "session": "s1", "text": "index the skills", "used": ["skills-index"]},
            {"ts": "2026-10-01 10:05", "session": "s1", "text": "now check them", "used": ["skill-health"]},
            {"ts": "2026-10-01 10:09", "session": "s1", "text": "land it", "used": ["land-a-change"]},
            {"ts": "2026-10-02 09:00", "session": "s2", "text": "index the skills", "used": ["skills-index"]},
            {"ts": "2026-10-02 09:03", "session": "s2", "text": "check", "used": ["skill-health", SELF]},
            {"ts": "2026-10-02 09:04", "session": "s2", "text": "sweep", "used": [f"x{i}" for i in range(13)]},
            {"ts": "2026-10-03 09:00", "session": "s3", "text": "index the skills", "used": ["skills-index"]},
            {"ts": "2026-10-03 09:02", "session": "s3", "text": "check", "used": ["skill-health"]}]
    tab = table(rows)
    ok["skills-index -> skill-health is the strongest transition"] = tab["next"]["skills-index"].most_common(1)[0][0] == "skill-health"
    ok["the Maestro and a sweep never enter the table"] = SELF not in tab["out"] and "x1" not in tab["out"] and not any(SELF in c for c in tab["next"].values())
    ok["a cut leaves out the later rows"] = table(rows, before="2026-10-02 00:00")["rows"] == 3 and table(rows, before=time.mktime(time.strptime("2026-10-02", "%Y-%m-%d")))["rows"] == 3
    r = reading(tab, [["skills-index"]])
    ok["after skills-index the reading says skill-health first, skills-index itself second (sticky)"] = r[:2] == ["skill-health", "skills-index"]
    ok["no context, no reading"] = reading(tab, []) == []
    ctx, cut = context_of(rows, "now  check them", before=time.mktime(time.strptime("2026-10-16", "%Y-%m-%d")))
    ok["a probe that is a row gets its session's earlier uses and a cut at its own ts"] = ctx == [["skills-index"]] and cut == "2026-10-01 10:05"
    ok["the probe's own row never enters its table"] = "skill-health" not in table(rows, before=cut)["out"] and table(rows, before=cut)["rows"] == 1
    ok["an unknown prompt has no context"] = context_of(rows, "something new") == ([], None)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "t.jsonl"
        def user(text):
            return json.dumps({"type": "user", "message": {"role": "user", "content": text}})
        def tool(name, inp):
            return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})
        lines = [user("index please"), tool("Skill", {"skill": "skills-index"}), user("check"),
                 tool("Bash", {"command": "python C:/Users/Max/.claude/skills/skill-health/health.py"}),
                 json.dumps({"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ghost"}}]}}),
                 user("<system-reminder>not the owner</system-reminder>"), user("and now?")]
        t.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok["the transcript tail yields the used turns in order, the newest prompt (no uses yet) skipped"] = tail_used(t) == [["skills-index"], ["skill-health"]]
        ok["a sidechain's Skill call is not this session's"] = all("ghost" not in u for u in tail_used(t))
        ok["a tail cut inside the first prompt reads the whole turns after it"] = tail_used(t, max_bytes=t.stat().st_size - 10) == [["skill-health"]]
        ok["live_context takes the named transcript"] = live_context(Path(td), t) == [["skills-index"], ["skill-health"]]
        ok["no fresh transcript, no context"] = live_context(Path(td), Path(td) / "missing.jsonl", max_age_s=0) == []
    bad = [k for k, v in ok.items() if not v]
    print(f"phase selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
