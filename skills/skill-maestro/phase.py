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

import calendar
import json
import os
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
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"   # 2026-10-26: Claude Code names the running session; its file is <id>.jsonl
SESSION_ID = re.compile(r"[0-9A-Za-z-]{8,64}")   # an id, never a glob or a path
STAMP = re.compile(r'"timestamp":\s*"(\d{4}-\d\d-\d\d[T ][^"]*)"')   # a record's own stamp; an escaped quote never matches
SKILL_PATH = re.compile(r"skills[\\/]+([a-z0-9]+(?:-[a-z0-9]+)*)[\\/]")
NOT_OWNER = ("<", "Another Claude session", "This session is being continued", "Base directory", "[Request interrupted")
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PASTED = re.compile(r"</?pasted_content\b[^>]*>")   # the paste wrapper; the words inside are the owner's
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


def owner_text(rec) -> str:
    """The owner's own words in one transcript row, else "". Two rows carry them: a main-thread `user` row (system
    reminders and a <pasted_content> wrapper taken out) whose text does not start NOT_OWNER, and a prompt the owner
    typed while Claude worked (a `queued_command` attachment, commandMode "prompt", origin human). Before 2026-10-27
    the readers skipped both a queued and a pasted prompt, so a mid-turn ask never started its own turn and its
    whisper landed on the turn before. Every transcript reader calls this one copy."""
    if not isinstance(rec, dict) or rec.get("isSidechain") or rec.get("isMeta"):
        return ""
    if rec.get("type") == "user":
        msg = rec.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return ""
        text = _text(content)
    elif rec.get("type") == "attachment":
        att = rec.get("attachment") or {}
        origin = att.get("origin") if isinstance(att, dict) else None
        if not (isinstance(att, dict) and att.get("type") == "queued_command" and att.get("commandMode") == "prompt"
                and (not isinstance(origin, dict) or origin.get("kind", "human") == "human")):
            return ""
        text = att.get("prompt") if isinstance(att.get("prompt"), str) else _text(att.get("prompt"))
    else:
        return ""
    text = REMINDER.sub("", text or "").strip()
    if not text or (text.startswith(NOT_OWNER) and not text.startswith("<pasted_content")):
        return ""
    return PASTED.sub("", text).strip()


def tail_used(transcript: Path, k: int = RECENT, max_bytes: int = TAIL_BYTES,
              max_age_s: int | None = None) -> list[list[str]]:
    """The used lists of the last k owner turns (that used anything) in a transcript's tail: Skill tool calls and
    skills/<name>/ paths in tool inputs, as hindsight.py reads them, from the last `max_bytes` only. The newest turn
    (the prompt being ranked, when the harness has already written it) has no uses yet and is skipped. With max_age_s,
    a turn whose prompt is older than that is dropped: a file's tail is not the session's tail when the file stopped
    growing (2026-10-26: a continued session's transcript held only the day before)."""
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
    turns: list[tuple] = []
    cur: set | None = None
    for raw in data.splitlines():
        is_user = '"user"' in raw and '"tool_result"' not in raw
        is_queued = '"queued_command"' in raw
        if not is_user and not is_queued and '"tool_use"' not in raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain") or rec.get("isMeta"):
            continue
        msg = rec.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if rec.get("type") in ("user", "attachment"):
            if owner_text(rec):
                cur = set()
                turns.append((rec.get("timestamp"), cur))
        elif rec.get("type") == "assistant" and cur is not None and isinstance(content, list):
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Skill" and isinstance(inp, dict) and inp.get("skill"):
                    cur.add(str(inp["skill"]).split(":")[-1])
                for m in SKILL_PATH.finditer(json.dumps(inp)):
                    cur.add(m.group(1))
    out = [used_of({"used": sorted(t)}) for ts, t in turns if fresh(ts, max_age_s=max_age_s)]
    return [u for u in out if u][-k:]


def fresh(ts, now: float | None = None, max_age_s: int | None = MAX_AGE_S) -> bool:
    """A transcript stamp ("2026-10-26T13:05:00.123Z", UTC, or a hindsight row's "2026-10-26 13:05") written within
    max_age_s of now. None means no limit. An empty or unreadable stamp counts as fresh: only a dated turn is dropped."""
    if max_age_s is None:
        return True
    try:
        t = calendar.timegm(time.strptime(str(ts)[:16].replace("T", " "), "%Y-%m-%d %H:%M"))
    except (TypeError, ValueError, OverflowError):
        return True
    return (time.time() if now is None else now) - t <= max_age_s + 60     # the stamp is cut to the minute


def projects_root() -> Path:
    """Where Claude Code keeps session transcripts: <CLAUDE_CONFIG_DIR>/projects when that is set, else
    ~/.claude/projects."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"


def last_stamp(path, tail: int = 1 << 20) -> str:
    """The newest record stamp in a transcript ("2026-10-25T18:05:11.653Z", UTC), or "" when it has none or cannot be
    read. Reads backwards `tail` bytes at a time, so a 100 MB transcript costs one chunk. A file's mtime is not its
    age: on 2026-10-26 a running session's transcript had a fresh mtime while its newest record was a day old."""
    try:
        with open(path, "rb") as fh:
            end = fh.seek(0, 2)
            while end > 0:
                start = max(0, end - tail)
                fh.seek(start)
                found = STAMP.findall(fh.read(end - start + 64).decode("utf-8", errors="replace"))   # 64: a stamp on the cut
                if found:
                    return max(found)
                end = start
    except OSError:
        pass
    return ""


def _candidates(roots, name: str = "*") -> list[Path]:
    """Session transcripts under the roots: <root>/<name>.jsonl and <root>/*/<name>.jsonl (a project folder), never a
    subagent's file one level further down (<session>/subagents/agent-*.jsonl). A root that is a .jsonl file counts
    when the name is "*" or its stem."""
    seen: set = set()
    out: list[Path] = []
    for r in map(Path, roots):
        if r.is_dir():
            found = [*r.glob(f"{name}.jsonl"), *r.glob(f"*/{name}.jsonl")]
        else:
            found = [r] if r.suffix == ".jsonl" and name in ("*", r.stem) else []
        for f in found:
            if f.is_file() and f not in seen:
                seen.add(f)
                out.append(f)
    return out


def _mtime(f: Path) -> float:
    try:
        return f.stat().st_mtime
    except OSError:
        return 0.0


def running_transcript(transcript=None, paths=None, session_id=None, max_age_s: int | None = MAX_AGE_S,
                       why: dict | None = None) -> tuple:
    """(the running session's transcript or None, how it was found). In order: the path the hook names
    (transcript_path); the session id (CLAUDE_CODE_SESSION_ID, or `session_id`, where "" means none) as <id>.jsonl
    under projects_root(); else the newest transcript written within max_age_s, which is only a guess. Found
    2026-10-26: with two sessions open the newest file was the peer's, so its prompts ranked this session's tasks.
    `why` (optional) gets {"source", "session"}: how it was found and the first 8 characters of the session."""
    why = why if why is not None else {}
    roots = [Path(p) for p in (paths or [projects_root()])]
    p = Path(transcript) if transcript else None
    if p is not None and p.is_file():
        why.update(source="hook", session=p.stem[:8])
        return p, "hook"
    sid = os.environ.get(SESSION_ENV, "") if session_id is None else str(session_id)
    if sid and SESSION_ID.fullmatch(sid):
        files = _candidates(roots, sid)
        if files:
            why.update(source="session id", session=sid[:8])
            return max(files, key=_mtime), "session id"
        why.update(source="session id (no transcript on disk)", session=sid[:8])
        return None, why["source"]
    files = _candidates(roots)
    if not files:
        why.update(source="none on disk", session="")
        return None, "none on disk"
    newest = max(files, key=_mtime)
    if max_age_s is not None and time.time() - _mtime(newest) > max_age_s:
        why.update(source="newest (stale)", session=newest.stem[:8])
        return None, "newest (stale)"
    why.update(source="newest (a guess)", session=newest.stem[:8])
    return newest, "newest (a guess)"


def live_context(state: Path, transcript: str | Path | None = None, k: int = RECENT, max_age_s: int = MAX_AGE_S,
                 paths=None, session_id=None, why: dict | None = None) -> list[list[str]]:
    """The running session's context: the used turns of the last max_age_s in the transcript running_transcript
    finds (the hook's path, else this session's id, else the newest one, a guess). Empty when there is none."""
    p, _ = running_transcript(transcript, paths, session_id, max_age_s, why)
    return tail_used(p, k, max_age_s=max_age_s) if p is not None else []


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
                 tool("Bash", {"command": "python ~/.claude/skills/skill-health/health.py"}),
                 json.dumps({"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ghost"}}]}}),
                 user("<system-reminder>not the owner</system-reminder>"), user("and now?")]
        t.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok["the transcript tail yields the used turns in order, the newest prompt (no uses yet) skipped"] = tail_used(t) == [["skills-index"], ["skill-health"]]
        ok["a sidechain's Skill call is not this session's"] = all("ghost" not in u for u in tail_used(t))
        ok["a tail cut inside the first prompt reads the whole turns after it"] = tail_used(t, max_bytes=t.stat().st_size - 10) == [["skill-health"]]
        def queued(text, kind="human", mode="prompt"):
            return json.dumps({"type": "attachment", "attachment": {"type": "queued_command", "prompt": text,
                                                                    "commandMode": mode, "origin": {"kind": kind}}})
        ok["owner_text: a queued owner prompt and a pasted one are the owner's; a peer, a task notice, a tool result, "
           "a non-prompt queue and a sidechain are not"] = \
            owner_text(json.loads(queued("go on"))) == "go on" \
            and owner_text(json.loads(user('<pasted_content id="7">fix the cap</pasted_content>'))) == "fix the cap" \
            and owner_text(json.loads(user("<system-reminder>r</system-reminder>\nland it"))) == "land it" \
            and not owner_text(json.loads(user("<cross-session-message from=x>hi"))) \
            and not owner_text(json.loads(user("<task-notification>done"))) \
            and not owner_text(json.loads(queued("hi", kind="agent"))) \
            and not owner_text(json.loads(queued("/clear", mode="bash"))) \
            and not owner_text({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}) \
            and not owner_text({"type": "user", "isSidechain": True, "message": {"content": "sub ask"}})
        q = Path(td) / "q.jsonl"
        q.write_text("\n".join([user("index please"), tool("Skill", {"skill": "skills-index"}), queued("and check"),
                                tool("Skill", {"skill": "skill-health"}), user("now?")]) + "\n", encoding="utf-8")
        ok["a queued owner prompt starts its own turn in the tail"] = tail_used(q) == [["skills-index"], ["skill-health"]]
        ok["live_context takes the named transcript"] = live_context(Path(td), t) == [["skills-index"], ["skill-health"]]
        ok["no fresh transcript, no context"] = live_context(Path(td), Path(td) / "missing.jsonl", max_age_s=-1,
                                                             paths=[Path(td)], session_id="") == []
        projects = Path(td) / "projects"                    # 2026-10-26: this session's transcript, found by its id
        own_sid, peer_sid = "own-sess-0001", "peer-sess-0002"
        own, peer = projects / "projA" / f"{own_sid}.jsonl", projects / "projB" / f"{peer_sid}.jsonl"
        sub = projects / "projA" / own_sid / "subagents" / "agent-x.jsonl"
        for f in (own, peer, sub):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        now = time.time()
        os.utime(own, (now - 600, now - 600))
        os.utime(peer, (now - 60, now - 60))
        os.utime(sub, (now, now))
        why: dict = {}
        ok["the session id finds this session's transcript, not the newer peer's"] = \
            running_transcript(None, [projects], own_sid, why=why) == (own, "session id") \
            and why == {"source": "session id", "session": "own-sess"}
        ok["no session id: the newest top-level transcript, called a guess; a subagent's file is never picked"] = \
            running_transcript(None, [projects], "") == (peer, "newest (a guess)")
        ok["a session id with no transcript on disk gives none, never a guess"] = \
            running_transcript(None, [projects], "gone-sess-0003") == (None, "session id (no transcript on disk)")
        ok["a session id that is not an id (a glob) is not used as one"] = \
            running_transcript(None, [projects], "*")[1] == "newest (a guess)"
        ok["the hook's path wins over the session id"] = running_transcript(peer, [projects], own_sid) == (peer, "hook")
        ok["live_context reads the session id's transcript"] = \
            live_context(Path(td), None, paths=[projects], session_id=own_sid) == [["skills-index"], ["skill-health"]]
        stale = Path(td) / "stale.jsonl"
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        stale.write_text("\n".join([
            json.dumps({"type": "user", "timestamp": "2026-01-01T00:00:00.000Z", "message": {"role": "user", "content": "old ask"}}),
            tool("Skill", {"skill": "skills-index"}),
            json.dumps({"type": "user", "timestamp": now_ts, "message": {"role": "user", "content": "fresh ask"}}),
            tool("Skill", {"skill": "skill-health"}), user("the prompt being ranked")]) + "\n", encoding="utf-8")
        ok["a turn older than max_age_s is not the session's context; a fresh one is"] = \
            tail_used(stale, max_age_s=MAX_AGE_S) == [["skill-health"]] and tail_used(stale) == [["skills-index"], ["skill-health"]]
        ok["fresh(): an old stamp is stale, now is fresh, no stamp or no limit counts as fresh"] = \
            not fresh("2026-01-01T00:00:00Z") and fresh(now_ts) and fresh("") and fresh(None) \
            and fresh("2026-01-01 00:00", max_age_s=None)
        ok["last_stamp: the newest record's stamp, read backwards in chunks; no stamp or no file gives nothing"] = \
            last_stamp(stale) == now_ts and last_stamp(stale, tail=10) == now_ts and last_stamp(t) == "" \
            and last_stamp(Path(td) / "missing.jsonl") == ""
        old_cfg = os.environ.get("CLAUDE_CONFIG_DIR")
        try:
            os.environ["CLAUDE_CONFIG_DIR"] = td
            in_cfg = projects_root() == Path(td) / "projects"
            os.environ.pop("CLAUDE_CONFIG_DIR")
            ok["projects_root: <CLAUDE_CONFIG_DIR>/projects when it is set, else ~/.claude/projects"] = \
                in_cfg and projects_root() == Path.home() / ".claude" / "projects"
        finally:
            if old_cfg is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = old_cfg
    bad = [k for k, v in ok.items() if not v]
    print(f"phase selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
