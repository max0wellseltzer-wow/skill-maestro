"""hindsight - the Maestro learns from what actually happened (v15, 2026-10-22).

Every real prompt in the session transcripts (~/.claude/projects/**/*.jsonl) is followed by the skills Claude actually
reached for before the next prompt: Skill tool calls, and any tool input naming a path under skills/<name>/. That
pairing is free, it is real, and until v15 the Maestro never looked at it (its held-out file holds 58 hand labels;
the transcripts held 120 labelled real prompts on the day this was written). It is used four ways:

    python maestro.py hindsight build [--paths DIR ...]   scan the transcripts once, incrementally (a file whose size
                                       and mtime are unchanged keeps its rows) into STATE/hindsight.jsonl. A SWEEP
                                       (more than SWEEP_MAX skills after one prompt: a library audit, not a choice)
                                       is kept but never used as a label. skill-maestro itself is never a label.
    python maestro.py hindsight probes [--out FILE]        write STATE/probes_hindsight.tsv (prompt <TAB> skills used),
                                       the eval format, so `maestro.py eval --probes` measures the Maestro on real
                                       prompts with real labels
    python maestro.py hindsight regret [--limit N] [--since YYYY-MM-DD] [--top 3] [--json]
                                       for each labelled prompt: would the Maestro have found what Claude used?
                                       REACHED (in its top 3) / IN_POOL (in the 40 it hands the judge) / BLIND (not
                                       in the pool: its index cannot see that skill from these words) / GONE (the
                                       skill no longer exists). Then the most-missed skills, the over-recommended
                                       ones (in the top 3 again and again, never used) and the blind rate by week.
                                       A blind audition: no ratings, no favourites, so a rating on the same prompt
                                       cannot leak into the measurement.
    python maestro.py hindsight propose [--min 2] [--k 8]   per skill, the words that recur in the prompts before
                                       Claude reached for it and that its own description and meaning line never
                                       say: information bias fixed at the source (FAIRNESS.md). Printed, never applied.
    python maestro.py hindsight similar "<task>"           the skills reached for after past prompts like this one
    python maestro.py hindsight reach [--since DATE]       v19: the whisper hook in the real transcripts: how often a
                                       whispered pick was then reached for (any pick; the first pick), the recall of
                                       the whisper over every skill used, the diversity of real skill use (distinct
                                       skills, the share the ten most-used take), the picks whispered most and never
                                       used, and the CONTEXT-DRIVEN skills: reached for again and again after prompts
                                       that share no words with their description (the session's phase chooses them,
                                       not the prompt; no words reading can see them). The owner's ruling (2026-10-24):
                                       "perfect, diverse use of all the skills"; this is that number, measured.
    python maestro.py hindsight status                     what the cache holds
    python hindsight.py --selftest

The HINDSIGHT line of a score sheet comes from `hindsight_line()`: the skills reached for after similar past prompts,
labelled a self-report. It is shown to the judge and never scored: Claude's own choices are not evidence (SKILL.md
rule "only the owner's ratings count"), and a skill used often must not rise for being used often (dial M32's rule,
applied here too: similar prompts only, never global counts).

Privacy: the cache lives in the state folder, never in the skill folder; prompts are stored redacted and cut to
MAX_CHARS; --no-ledger (or MAESTRO_NO_LEDGER=1) means build writes nothing and only reports.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _maestro():
    """The running maestro module: `__main__` when maestro.py dispatched here (its dials are applied there; a second
    import would carry the defaults instead), else a plain import."""
    main = sys.modules.get("__main__")
    if main is not None and Path(getattr(main, "__file__", "") or "").name == "maestro.py":
        return main
    import maestro
    return maestro


M = _maestro()

CACHE = "hindsight.jsonl"
INDEX = "hindsight_index.json"
PROBES = "probes_hindsight.tsv"
SWEEP_MAX = 12          # more skills than this after one prompt is a library sweep, not a choice: kept, never a label
MIN_TOKENS = 4          # "go", "yes", "MORE" are not asks (demand-scan's bar)
MAX_CHARS = 1500        # a pasted wall of text is cut so it does not match everything
EXCERPT = 160
SKILL_PATH = re.compile(r"skills[\\/]+([a-z0-9]+(?:-[a-z0-9]+)*)[\\/]")
MAESTRO_RUN = re.compile(r"maestro\.py\\?\"?\s+(?:score|play|triage|whisper)\b|\"skill\":\s*\"skill-maestro\"")   # the echo flag
CACHE_V = 8            # the cache's row shape; an older index is rescanned whole (v4: the whisper's picks per prompt; v5: queued and pasted owner prompts; v6: the queued flag; v7: whispers on text the owner did not write; v8: the v20.0.7 whisper lines read)
WHISPER_RX = re.compile(r"WHISPER \(([\d.]+)s(.*?)\): (.*)")   # the UserPromptSubmit hook's line (v19). 2026-10-28: the
# v20.0.7 lines "(1.6s, FULL: <reason>; 2 by task size)", "(s, QUICK, 2 by ...)", "(s, SKIP: <reason>)" were unread
# (the reach counted 0 owner whispers after 2026-10-27); the reason is cut before its first colon, so "): " ends the head
PICK_RX = re.compile(r"/([a-z0-9][a-z0-9_.:-]*)")
BLIND_OVERLAP = 1       # v19: a use is BLIND when the prompt shares at most this many words with the skill's description
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
NOT_OWNER = ("<", "Another Claude session", "This session is being continued", "Base directory", "[Request interrupted")
TEXT_KINDS = (("Another Claude session", "peer message"), ("<cross-session-message", "peer message"),
              ("<task-notification", "task notice"), ("<agent-message", "agent message"),
              ("<local-command-", "local command"), ("<command-name", "slash command"), ("<system-reminder", "reminder"),
              ("<bash-", "shell output"), ("This session is being continued", "summary"),
              ("[Request interrupted", "interrupt"))   # 2026-10-28, from whisper_census.py (session b0f113f4)
WHISPER_SKIP_LANDED = "2026-10-27 03:42"   # UTC: the hook's not_owner_prompt skip reached git (d7c408c); live was earlier
SECRET = re.compile(r"(?i)(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\b[A-Fa-f0-9]{32,}\b|"
                    r"\b(?:api[_ -]?key|token|secret|password)\s*[=:]\s*\S+)")


def redact(s: str) -> str:
    return SECRET.sub("[redacted]", s)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def text_kind(rec) -> str | None:
    """The kind of a prompt-bearing row the owner did not write (a peer's message, a task notice, ...): a main-thread
    user row that is not a tool result, or a queued_command attachment. None for any other row."""
    if rec.get("type") == "attachment":
        att = rec.get("attachment") or {}
        if not (isinstance(att, dict) and att.get("type") == "queued_command"):
            return None
        t = att.get("prompt") if isinstance(att.get("prompt"), str) else _text(att.get("prompt"))
    elif rec.get("type") == "user":
        c = (rec.get("message") or {}).get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return None
        t = _text(c)
    else:
        return None
    s = (t or "").lstrip()
    return next((k for p, k in TEXT_KINDS if s.startswith(p)), "other") if s else None


def transcript_files(paths) -> list[Path]:
    """The transcripts under the paths. A folder walk skips subagents/ (about 0.7 GB on this machine, with no owner
    turn in it); a file named outright is kept."""
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            out.extend(f for f in sorted(p.rglob("*.jsonl")) if "subagents" not in f.relative_to(p).parts)
        elif p.exists():
            out.append(p)
    return out


def iter_turns(f: Path, names: set | None = None, stats: dict | None = None):
    """{ts, session, text, used, observed} per owner prompt in one transcript. `used` = the skills the main assistant
    reached for before the next prompt: Skill tool calls (OBSERVED: the harness ran that skill) and any tool INPUT
    naming a path skills/<name>/ (INFERRED: a script of that skill was named; v17, k-dense-byok's edge confidence).
    Tool results and plain prose never count. Sidechains (subagents) and meta records are skipped; with `names`, a
    path hit counts only for a real skill name. Streams line by line: a transcript can be hundreds of MB. `stats`
    (optional) counts what was skipped: unreadable files and unparsable lines, so a gap is visible, not silent."""
    import phase as P  # beside this file (HERE is on sys.path)
    try:
        fh = f.open(encoding="utf-8", errors="replace")
    except OSError:
        if stats is not None:
            stats["unreadable"] = stats.get("unreadable", 0) + 1
        return
    cur, last_kind = None, None             # last_kind: who wrote the newest prompt row, so a whisper goes to its own text
    with fh:
        for raw in fh:
            is_user = '"user"' in raw and '"tool_result"' not in raw
            is_whisper = "WHISPER (" in raw and '"hookEvent"' in raw      # v19: the whisper hook's attachment record
            is_queued = '"queued_command"' in raw           # 2026-10-27: a prompt typed while Claude worked
            if not is_user and '"tool_use"' not in raw and not is_whisper and not is_queued:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                if stats is not None:
                    stats["bad_lines"] = stats.get("bad_lines", 0) + 1
                continue
            if not isinstance(rec, dict) or rec.get("isSidechain") or rec.get("isMeta"):
                continue
            msg = rec.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            text = P.owner_text(rec) if (is_user or is_queued) and rec.get("type") in ("user", "attachment") else ""
            if text:                                        # the one owner filter (phase.owner_text), 2026-10-27
                last_kind = "owner"
                if cur and text == cur["text"]:              # a queued prompt written again as a user row
                    continue
                if cur:
                    yield cur
                cur = {"ts": str(rec.get("timestamp") or "")[:16].replace("T", " "),
                       "session": str(rec.get("sessionId") or f.stem)[:8], "text": text, "used": set(), "observed": set(),
                       "maestro": False, "whispered": [], "whisper_s": None, "stray": [],
                       "queued": rec.get("type") == "attachment"}   # 2026-10-27: typed while Claude worked
                continue
            if (is_user or is_queued) and text_kind(rec):    # 2026-10-28: a peer's or a tool's text, not a new turn
                last_kind = text_kind(rec)
                continue
            if rec.get("type") == "attachment":              # v19: what the whisper hook showed after this prompt
                att = rec.get("attachment") or {}
                m = WHISPER_RX.search(str(att.get("content") or att.get("stdout") or "")) \
                    if isinstance(att, dict) and att.get("hookEvent") == "UserPromptSubmit" else None
                if m and cur is not None:
                    picks = [p.split(":")[-1] for p in PICK_RX.findall(m.group(3).split("   (")[0])]
                    if last_kind in (None, "owner"):
                        cur["whispered"], cur["whisper_s"] = picks, float(m.group(1))
                    else:                                    # 2026-10-28: it answered a peer's text; before, it overwrote
                        cur["stray"].append({"kind": last_kind, "n": len(picks),   # the owner's own whisper
                                             "ts": str(rec.get("timestamp") or "")[:16].replace("T", " ")})
                continue
            if rec.get("type") == "assistant" and cur is not None and isinstance(content, list):
                for b in content:
                    if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                        continue
                    inp = b.get("input") or {}
                    blob = json.dumps(inp)
                    if MAESTRO_RUN.search(blob):          # the Maestro's own sheet was shown in this turn (an echo risk)
                        cur["maestro"] = True
                    if b.get("name") == "Skill" and isinstance(inp, dict) and inp.get("skill"):
                        cur["used"].add(str(inp["skill"]).split(":")[-1])
                        cur["observed"].add(str(inp["skill"]).split(":")[-1])
                    for m in SKILL_PATH.finditer(blob):
                        if names is None or m.group(1) in names:
                            cur["used"].add(m.group(1))
    if cur:
        yield cur


def rows_of(state: Path) -> list[dict]:
    f = Path(state) / CACHE
    if not f.is_file():
        return []
    out = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def build(state: Path, paths, names: set, tokens, write: bool = True, log=None) -> dict:
    """Scan the transcripts into STATE/hindsight.jsonl, incrementally. Returns the counts; with write=False it only
    counts (the --no-ledger mode)."""
    state = Path(state)
    index = state / INDEX
    old_index = json.loads(index.read_text(encoding="utf-8")) if index.is_file() else {}
    if old_index.get("_v") != CACHE_V:                 # an older row shape: everything is read again
        old_index = {}
    by_file: dict[str, list] = {}
    for r in rows_of(state):
        by_file.setdefault(r.get("file", ""), []).append(r)
    new_index, stats = {}, {"files": 0, "rescanned": 0, "unchanged": 0}
    out: list[dict] = []
    for f in transcript_files(paths):
        key, st_ = str(f), f.stat()
        sig = {"size": st_.st_size, "mtime": int(st_.st_mtime)}
        stats["files"] += 1
        if old_index.get(key) == sig:                   # unchanged: its rows stay (none, when they were duplicates)
            out += by_file.get(key, [])
            new_index[key] = sig
            stats["unchanged"] += 1
            continue
        stats["rescanned"] += 1
        if log:
            log(f"  scanning {f.name} ({st_.st_size // 1_000_000} MB)")
        for t in iter_turns(f, names, stats):
            text = " ".join(t["text"][:MAX_CHARS].split())
            used = sorted(u for u in t["used"] if u != M.SELF)
            out.append({"ts": t["ts"], "session": t["session"], "file": key, "words": sorted(set(tokens(text))),
                        "used": used, "observed": sorted(u for u in t.get("observed", ()) if u != M.SELF),
                        "sweep": len(used) > SWEEP_MAX, "excerpt": redact(text[:EXCERPT]),
                        "text": redact(text), "maestro": bool(t.get("maestro")),
                        "whispered": list(t.get("whispered") or []), "whisper_s": t.get("whisper_s"), "queued": bool(t.get("queued")),
                        "stray": list(t.get("stray") or [])})   # v19; queued 2026-10-27; stray 2026-10-28
        new_index[key] = sig
    new_index["_v"] = CACHE_V
    seen, dedup = set(), []                      # a continued session repeats its earlier prompts in a new file
    for r in sorted(out, key=lambda r: (r["ts"], r.get("file", ""))):
        k = (r["ts"], r["text"][:300])
        if k not in seen:
            seen.add(k)
            dedup.append(r)
    if write:
        state.mkdir(parents=True, exist_ok=True)
        (state / CACHE).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in dedup), encoding="utf-8")
        index.write_text(json.dumps(new_index, sort_keys=True), encoding="utf-8")
    lab = labels(dedup)
    stats.update({"prompts": len(dedup), "labelled": len(lab), "sweeps": sum(bool(r["sweep"]) for r in dedup),
                  "skills_used": len({u for r in lab for u in r["used"]}), "written": write,
                  "observed": sum(1 for r in lab if r.get("observed")),
                  "unreadable": stats.get("unreadable", 0), "bad_lines": stats.get("bad_lines", 0)})
    return stats


def labels(rows: list[dict], since: str | None = None, min_tokens: int = MIN_TOKENS, observed_only: bool = False) -> list[dict]:
    """The prompts that can be labels: a skill was reached for, it was not a sweep, and the prompt is an ask.
    `observed_only` (v17) keeps only Skill-tool labels (the harness ran the skill) and drops path-inferred ones."""
    out = [r for r in rows if r.get("used") and not r.get("sweep") and len(r.get("words", [])) >= min_tokens
           and (not since or r["ts"][:10] >= since)]
    if observed_only:
        out = [{**r, "used": r["observed"]} for r in out if r.get("observed")]
    return out


def with_context(rows: list[dict], r: dict, k: int) -> str:
    """O2/O9 (2026-10-22): 54% of real labelled prompts are BLIND because their words never name the skill ("okay
    proceed with the still open"). The session's previous k prompts carry the missing words. Returns the prompt
    text with those k earlier prompts of the same session (by ts) in front of it; k = 0 returns the text alone."""
    if k <= 0:
        return r["text"]
    prev = [x for x in rows if x.get("session") == r.get("session") and x.get("ts", "") < r.get("ts", "") and x.get("text")]
    prev.sort(key=lambda x: x.get("ts", ""))
    return " ".join(x["text"][:300] for x in prev[-k:]) + " " + r["text"]


def recent_prompts(k: int, exclude: str = "", paths=None, max_age_s: int = 6 * 3600, transcript=None,
                   session_id=None, why: dict | None = None) -> list[str]:
    """The last k owner prompts of the RUNNING session written within max_age_s, the prompt being scored and the
    Maestro's own runs left out. The transcript is the one phase.running_transcript finds: the hook's path, else this
    session's id (CLAUDE_CODE_SESSION_ID), else the newest one, a guess. Before 2026-10-26 it was always the newest
    file, and with two sessions open that was often the peer's. `why` (optional) gets how the transcript was found
    and, when nothing comes back, the reason. Nothing is written."""
    why = why if why is not None else {}
    if k <= 0:
        return []
    import phase as P  # beside this file (HERE is on sys.path)
    f, src = P.running_transcript(transcript, paths, session_id, max_age_s, why)
    h = max_age_s / 3600
    if f is None:
        why["empty"] = ("this session's transcript is not on disk" if src.startswith("session id")
                        else "no transcript on disk" if src == "none on disk"
                        else f"no transcript written in the last {h:g} h")
        return []
    ex = (exclude or "").strip()
    texts = [t["text"] for t in iter_turns(f) if P.fresh(t["ts"], max_age_s=max_age_s)]
    texts = [t for t in texts if t.strip() != ex and not MAESTRO_RUN.search(t)]
    if not texts:
        last = P.last_stamp(f) if src in ("session id", "hook") else ""
        why["empty"] = (f"this session's transcript has had no record since {last[:16].replace('T', ' ')} UTC; "
                        "Claude Code may have stopped writing it" if last and not P.fresh(last, max_age_s=max_age_s)
                        else f"no other prompt from the last {h:g} h in that transcript")
    return [t[:300] for t in texts[-k:]]


def write_probes(rows: list[dict], out: Path, context: int = 0, observed_only: bool = False, since: str | None = None) -> int:
    """The eval format: prompt <TAB> comma-separated skills. Comment lines start with #. `context` = how many of the
    session's earlier prompts to prepend (0 = the prompt alone). `observed_only`: Skill-tool labels alone (v17).
    `since`: prompts from that date on only (the test side of a walk-forward split)."""
    lab = labels(rows, since=since, observed_only=observed_only)
    lines = [("# hindsight probes: real prompts, labelled by the skills Claude actually reached for afterwards "
              f"(built {time.strftime('%Y-%m-%d %H:%M')}, {len(lab)} prompts, context {context}"
              f"{', observed labels only (Skill tool calls)' if observed_only else ', observed + inferred labels'}). "
              "A label is what was used, not what was best: a miss here is a question, not a verdict.")]
    for r in lab:
        lines.append(with_context(rows, r, context).replace("\t", " ").replace("\n", " ") + "\t" + ",".join(r["used"]))
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lab)


def regret(lib, rows: list[dict], top: int = 3, limit: int | None = None, since: str | None = None, log=None) -> dict:
    """Blind audition on the real prompts: no ratings, no favourites, the Maestro's own fused pool and its top picks
    against what Claude actually used."""
    lab = sorted(labels(rows, since), key=lambda r: r["ts"], reverse=True)
    if limit:
        lab = lab[:limit]
    known = set(lib.desc)
    out_rows, missed, rec, weeks = [], Counter(), {}, {}
    echo = {True: [0, 0], False: [0, 0]}               # the Maestro's sheet shown in that turn or not: [prompts, reached]
    calib: list[tuple[float, int, bool]] = []          # (fit, rank, hit) per top pick: is the fit score calibrated?
    for i, r in enumerate(lab):
        if log and i and i % 50 == 0:
            log(f"  ... {i}/{len(lab)}")
        text = r["text"][:MAX_CHARS]
        M.TOOL_BONUS = (M.task_kinds(text)[0][0] not in M.CREATIVE_KINDS) if M.KINDS_ON else True
        pool = [c for c in lib.fused(text)[:M.POOL + 1] if c["name"] != M.SELF][:M.POOL]   # no self-pick, as score()
        chosen, _ = M.select(M.weigh(pool, {}, set()), top, lib.family)
        M.TOOL_BONUS = True
        top_names = [c["name"] for c in chosen]
        pool_names = {c["name"] for c in pool}
        used = set(r["used"]) & known
        status = ("GONE" if not used else "REACHED" if used & set(top_names)
                  else "IN_POOL" if used & pool_names else "BLIND")
        if used:
            e = echo[bool(r.get("maestro"))]
            e[0] += 1
            e[1] += status == "REACHED"
            for k, c in enumerate(chosen, 1):
                calib.append((c.get("fit", 0.0), k, c["name"] in used))
        for u in used - pool_names:
            missed[u] += 1
        for n in top_names:
            rec.setdefault(n, [0, 0])
            rec[n][0] += 1
            rec[n][1] += n in used
        wk = _week(r["ts"])
        weeks.setdefault(wk, [0, 0])
        weeks[wk][0] += 1
        weeks[wk][1] += status == "BLIND"
        out_rows.append({"ts": r["ts"], "status": status, "used": sorted(used), "top": top_names,
                         "excerpt": r["excerpt"]})
    n = len(out_rows)
    counts = Counter(x["status"] for x in out_rows)
    over = sorted(((k, v[0], v[1]) for k, v in rec.items() if v[0] >= 3 and v[1] == 0), key=lambda x: (-x[1], x[0]))
    bins = [(0.95, "0.95-1"), (0.8, "0.80-0.95"), (0.6, "0.60-0.80"), (0.4, "0.40-0.60"), (0.0, "<0.40")]
    by_fit = {}
    for fit, _, hit in calib:
        lab_ = next(l for lo, l in bins if fit >= lo)
        by_fit.setdefault(lab_, [0, 0])
        by_fit[lab_][0] += 1
        by_fit[lab_][1] += hit
    by_rank = {}
    for _, k, hit in calib:
        by_rank.setdefault(k, [0, 0])
        by_rank[k][0] += 1
        by_rank[k][1] += hit
    return {"n": n, "top": top, "reached": counts["REACHED"], "in_pool": counts["IN_POOL"], "blind": counts["BLIND"],
            "gone": counts["GONE"], "rows": out_rows, "missed": missed.most_common(15), "over": over[:10],
            "weeks": sorted((k, v[0], v[1]) for k, v in weeks.items()),
            "echo": {"shown": echo[True], "not_shown": echo[False]},
            "calibration": {"by_fit": [(l, by_fit[l][0], by_fit[l][1]) for _, l in bins if l in by_fit],
                            "by_rank": sorted((k, v[0], v[1]) for k, v in by_rank.items())}}


def _week(ts: str) -> str:
    try:
        y, mth, d = (int(x) for x in ts[:10].split("-"))
        import datetime
        iso = datetime.date(y, mth, d).isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except (ValueError, TypeError):
        return "?"


def propose(rows: list[dict], lib, mechs: dict, min_uses: int = 2, k: int = 8, discriminative: bool = False,
            min_share: float = 0.6, before: str | None = None) -> list[dict]:
    """Per skill reached for at least `min_uses` times: the words that recur (in 2+ of its prompts) and that its
    name, description and meaning line never say, weighted by rarity across all labelled prompts.
    `discriminative` (v17, ruflo learned-routing.ts:45-123): keep a word only when at least `min_share` of the labelled
    prompts that contain it reached for THIS skill (share = support / df), and weight by support x share x idf; a word
    the owner uses before many different skills ("fix", "check") then teaches nothing. `before` (YYYY-MM-DD) learns
    from labels before that date only, so an eval on later prompts is honest (walk-forward)."""
    lab = [r for r in labels(rows) if not before or r["ts"][:10] < before]
    n_all = len(lab)
    df = Counter(w for r in lab for w in set(r["words"]))
    per: dict[str, Counter] = {}
    nuse: Counter = Counter()
    for r in lab:
        for u in r["used"]:
            nuse[u] += 1
            per.setdefault(u, Counter()).update(set(r["words"]))
    stop = set(M.META) | set(M.ASK_WORDS)
    out = []
    for s, c in per.items():
        if nuse[s] < min_uses or s not in lib.desc:
            continue
        m = mechs.get(s, {})
        own = set(lib.fs._tokens(" ".join([s, lib.desc[s], m.get("does", ""), " ".join(m.get("tags", [])), m.get("world", "")])))
        cand = []
        for w, cnt in c.items():
            if cnt < 2 or w in own or w in stop or len(w) < 4 or w.isdigit():
                continue
            share = cnt / max(1, df[w])
            if discriminative and share < min_share:
                continue
            idf = math.log((n_all + 1) / (df[w] + 0.5))
            cand.append(((cnt * share * idf) if discriminative else cnt * idf, cnt, w))
        cand.sort(key=lambda x: (-x[0], x[2]))
        if cand:
            out.append({"skill": s, "uses": nuse[s], "words": [(w, cnt) for _, cnt, w in cand[:k]],
                        "weights": {w: round(sc, 3) for sc, _, w in cand[:k]}})
    out.sort(key=lambda x: (-x["uses"], x["skill"]))
    return out


def similar(rows: list[dict], words: set, k: int = 5, floor: float | None = None) -> tuple[list, int]:
    """The skills reached for after the k past prompts most like this one (word Jaccard at or above the Maestro's
    own memory bar). Sweeps and promptless rows never count."""
    floor = M.MEMORY_SIM if floor is None else floor
    sims = []
    for r in rows:
        if r.get("sweep") or not r.get("used"):
            continue
        sim = M.jaccard(set(r["words"]), words)
        if sim >= floor:
            sims.append((sim, r["ts"], r))
    sims.sort(key=lambda x: (-x[0], x[1]))
    top = sims[:k]
    c = Counter(u for _, _, r in top for u in r["used"] if u != M.SELF)
    return c.most_common(), len(top)


def hindsight_line(state: Path, words: set, k: int = 5) -> str | None:
    rows = rows_of(Path(state))
    if not rows:
        return None
    c, n = similar(rows, words, k)
    if not c:
        return None
    return (f"HINDSIGHT (self-report, not evidence): after {n} similar past prompt(s) Claude reached for "
            + ", ".join(f"{s} ({cnt})" for s, cnt in c[:6]))


# --- rendering -----------------------------------------------------------------------------------------------------

def render_build(s: dict) -> str:
    return (f"HINDSIGHT BUILD: {s['files']} transcript file(s), {s['rescanned']} scanned, {s['unchanged']} unchanged; "
            f"{s['prompts']} prompts, {s['labelled']} labelled (a skill was reached for; {s.get('observed', 0)} OBSERVED by a "
            f"Skill call, the rest INFERRED from a script path), {s['sweeps']} sweep(s) "
            f"excluded, {s['skills_used']} distinct skills used; GAPS: {s.get('unreadable', 0)} unreadable file(s), "
            f"{s.get('bad_lines', 0)} unparsable line(s)"
            + ("" if s.get("written") else "  (not written: --no-ledger)"))


def render_regret(res: dict) -> str:
    n = res["n"] or 1
    L = [f"REGRET on {res['n']} labelled real prompt(s), blind audition (no ratings): REACHED {res['reached']} "
         f"({res['reached'] / n:.0%}, a top-{res['top']} pick was what Claude used), IN_POOL {res['in_pool']} "
         f"({res['in_pool'] / n:.0%}), BLIND {res['blind']} ({res['blind'] / n:.0%}: the pool of {M.POOL} never held it)"
         + (f", GONE {res['gone']}" if res["gone"] else "")]
    if res["missed"]:
        L.append("MOST MISSED (used, but outside the pool for that prompt): "
                 + ", ".join(f"{s} ({c})" for s, c in res["missed"]))
    if res["over"]:
        L.append("OVER-RECOMMENDED (in the top picks 3+ times, never used): "
                 + ", ".join(f"{s} ({r}x)" for s, r, _ in res["over"]))
    wk = [f"{w} {b}/{t}" for w, t, b in res["weeks"][-8:]]
    if wk:
        L.append("BLIND BY WEEK (blind/prompts): " + "  ".join(wk))
    e = res.get("echo") or {}
    if e:
        s, ns = e.get("shown", [0, 0]), e.get("not_shown", [0, 0])
        L.append(f"ECHO CHECK: REACHED {s[1]}/{s[0]} when the Maestro's own sheet was shown in that turn, {ns[1]}/{ns[0]} when it "
                 "was not (the second number is the honest one: a shown sheet can cause the use it predicts)")
    c = res.get("calibration") or {}
    if c.get("by_fit"):
        L.append("CALIBRATION of fit (top picks: n, used): " + "  ".join(f"{l}: {h}/{n}" for l, n, h in c["by_fit"])
                 + " | by rank: " + "  ".join(f"#{k} {h}/{n}" for k, n, h in c["by_rank"]))
    for x in [x for x in res["rows"] if x["status"] == "BLIND"][:6]:
        L.append(f"  BLIND {x['ts']} used {','.join(x['used'])[:40]:<40} top {','.join(x['top'])[:50]:<50} | {x['excerpt'][:70]}")
    L.append("READ IT AS: a label is what Claude used, not what was best. BLIND = the index cannot reach that skill "
             "from these words (propose fixes the skill's text); OVER-RECOMMENDED = a description that matches many "
             "asks it does not serve.")
    return "\n".join(L)


def render_propose(rows: list[dict], show: int = 20) -> str:
    if not rows:
        return "PROPOSE: no skill was reached for often enough to learn its words (min uses not met)"
    L = ["PROPOSE (printed, never applied): words the owner used before reaching for a skill, absent from its text"]
    for r in rows[:show]:
        L.append(f"  {r['skill']:<28} used {r['uses']:>3}  add: " + ", ".join(f"{w} ({c})" for w, c in r["words"]))
    L.append("APPLY BY HAND: a word that names the skill's job goes into its description; one that names the owner's "
             "situation goes into its meaning line (cards/mechanisms.jsonl, 'does'); then `maestro.py findable <skill>`.")
    return "\n".join(L)


def render_status(rows: list[dict], state: Path) -> str:
    if not rows:
        return f"HINDSIGHT: no cache at {Path(state) / CACHE}; run `maestro.py hindsight build`"
    lab = labels(rows)
    obs = labels(rows, observed_only=True)
    return (f"HINDSIGHT: {len(rows)} prompts ({rows[0]['ts'][:10]} .. {rows[-1]['ts'][:10]}), {len(lab)} labelled "
            f"({len(obs)} with an OBSERVED Skill-call label; `probes --observed-only` writes those alone), "
            f"{len({u for r in lab for u in r['used']})} distinct skills used; cache {Path(state) / CACHE}")


# --- reach (v19): the whisper hook measured in the transcripts, and the diversity of real use ------------------------

def reach(rows: list[dict], desc: dict[str, str] | None = None, tokens=None, since: str | None = None,
          min_uses: int = 3, blind_share: float = 0.6) -> dict:
    """What the one Maestro surface every prompt meets (the UserPromptSubmit whisper) achieved in real sessions.
    `whispered` rows are prompts the hook answered; a label row is a prompt after which a skill was reached for
    (labels(): not a sweep, ask-sized). skill-maestro itself never counts as a pick or a use. Nothing here is a
    rating: a whispered pick that was then used is a self-report of the session, kept apart from the owner's ratings
    (SKILL.md), and shown so the hook's reach can be seen instead of assumed (TRY 13 showed a session note changes
    nothing; this is the number that says whether the whisper does)."""
    rs = [r for r in rows if not since or r.get("ts", "")[:10] >= since]
    self_ = M.SELF
    wh = [r for r in rs if r.get("whispered")]
    lab = labels(rs)
    lab_w = [r for r in lab if r.get("whispered")]
    picks = {id(r): [p for p in r["whispered"] if p != self_] for r in lab_w}
    hit_any = sum(1 for r in lab_w if set(r["used"]) & set(picks[id(r)]))
    hit_first = sum(1 for r in lab_w if picks[id(r)][:1] and picks[id(r)][0] in r["used"])
    uses = [(r, u) for r in lab_w for u in r["used"]]
    recalled = sum(1 for r, u in uses if u in picks[id(r)])
    wcount = Counter(p for r in wh for p in r["whispered"] if p != self_)
    wused = Counter(p for r in lab_w for p in set(picks[id(r)]) & set(r["used"]))
    ucount = Counter(u for r in lab for u in r["used"])
    uwhisp = {u for r in lab_w for u in r["used"] if u in picks[id(r)]}
    never_used = [(p, n) for p, n in wcount.most_common() if not wused.get(p)][:8]
    never_whispered = [(u, n) for u, n in ucount.most_common() if u not in uwhisp and any(r.get("whispered") for r in lab)][:8]
    top10 = sum(n for _, n in ucount.most_common(10))
    ks = sorted(len(picks[id(r)]) for r in lab_w)
    by_kind = {k: [sum(1 for r in lab_w if bool(r.get("queued")) == q and set(r["used"]) & set(picks[id(r)])),
                   sum(1 for r in lab_w if bool(r.get("queued")) == q)] for k, q in (("typed", False), ("mid-turn", True))}
    by_text = {"owner": [sum(1 for r in wh if r.get("ts", "") < WHISPER_SKIP_LANDED),   # whispers by the text they
                         sum(1 for r in wh if r.get("ts", "") >= WHISPER_SKIP_LANDED)]}  # answered, before | after
    for s in (s for r in rs for s in r.get("stray") or []):
        by_text.setdefault(s["kind"], [0, 0])[s.get("ts", "") >= WHISPER_SKIP_LANDED] += 1
    weeks: dict[str, list[int]] = {}
    for r in lab_w:
        y, m_, d = (int(x) for x in r["ts"][:10].split("-"))
        import datetime
        wk = datetime.date(y, m_, d).isocalendar()
        key = f"{wk[0]}-W{wk[1]:02d}"
        weeks.setdefault(key, [0, 0])
        weeks[key][0] += bool(set(r["used"]) & set(picks[id(r)]))
        weeks[key][1] += 1
    context_driven = []
    if desc and tokens:
        blind: dict[str, list[int]] = {}
        for r in lab:
            words = set(r.get("words") or [])
            for u in r["used"]:
                d = desc.get(u)
                if d is None:
                    continue
                ov = len(words & set(tokens(d)))
                b = blind.setdefault(u, [0, 0])
                b[0] += ov <= BLIND_OVERLAP
                b[1] += 1
        context_driven = sorted(((u, b[0], b[1]) for u, b in blind.items() if b[1] >= min_uses and b[0] / b[1] >= blind_share),
                                key=lambda x: (-x[2], x[0]))
    secs = sorted(r["whisper_s"] for r in wh if isinstance(r.get("whisper_s"), (int, float)))
    recent = [r for r in sorted(wh, key=lambda r: r.get("ts", "")) if isinstance(r.get("whisper_s"), (int, float))][-10:]
    rsecs = sorted(r["whisper_s"] for r in recent)
    rks = sorted(len([p for p in r["whispered"] if p != self_]) for r in recent)
    return {"since": since, "prompts": len(rs), "whispered": len(wh), "first_whisper": wh[0]["ts"][:10] if wh else None,
            "recent_s_median": rsecs[len(rsecs) // 2] if rsecs else None, "recent_k_median": rks[len(rks) // 2] if rks else None,
            "recent_n": len(recent),
            "labelled": len(lab), "labelled_whispered": len(lab_w), "by_kind": by_kind, "by_text": by_text,
            "hit_any": hit_any, "hit_first": hit_first,
            "uses": len(uses), "recalled": recalled, "k_median": ks[len(ks) // 2] if ks else 0,
            "distinct_used": len(ucount), "library": len(desc) if desc else None, "uses_total": sum(ucount.values()),
            "top10_share": (top10 / sum(ucount.values())) if ucount else None, "top_used": ucount.most_common(10),
            "never_used": never_used, "never_whispered": never_whispered, "weeks": weeks, "context_driven": context_driven,
            "whisper_s_median": secs[len(secs) // 2] if secs else None}


def render_reach(x: dict) -> str:
    def pct(a, b):
        return f"{a}/{b} ({100 * a // b}%)" if b else f"{a}/0"
    since = f" since {x['since']}" if x.get("since") else ""
    L = [f"REACH (the whisper hook in the real transcripts{since}): {x['prompts']} prompts, {x['whispered']} with a whisper line"
         + (f" (first {x['first_whisper']})" if x.get("first_whisper") else "") + f"; {x['labelled']} labelled, "
         f"{x['labelled_whispered']} of them whispered"]
    if len(x.get("by_text") or {}) > 1:
        L.append(f"  BY TEXT (whispers by who wrote the text, before | after the hook's skip landed {WHISPER_SKIP_LANDED} UTC; "
                 "every row but owner should read 0 after): "
                 + "; ".join(f"{k} {b} | {a}" for k, (b, a) in sorted(x["by_text"].items(), key=lambda kv: (kv[0] != "owner", -sum(kv[1])))))
    if not x["labelled_whispered"]:
        L.append("  no labelled prompt carries a whisper line yet: nothing to measure (the hook was installed on 2026-10-22; "
                 "transcripts before it have no line)")
    else:
        L.append(f"  FOLLOWED: a whispered pick was reached for after {pct(x['hit_any'], x['labelled_whispered'])} of the whispered "
                 f"labelled prompts; the FIRST pick alone {pct(x['hit_first'], x['labelled_whispered'])}; picks per whisper, median {x['k_median']}"
                 + (f"; the hook took {x['whisper_s_median']:.1f} s (median over all)" if x.get("whisper_s_median") is not None else "")
                 + (f"; the last {x['recent_n']} whispers: {x['recent_s_median']:.1f} s, {x['recent_k_median']} picks (medians)"
                    if x.get("recent_s_median") is not None else ""))
        if x.get("by_kind", {}).get("mid-turn", [0, 0])[1]:
            L.append("  BY KIND: " + "; ".join(f"{k} {pct(*v)}" for k, v in x["by_kind"].items())
                     + " (mid-turn = typed while Claude worked; its follow-on skills often belong to the turn before)")
        L.append(f"  RECALL: of the {x['uses']} skills reached for after whispered prompts, {pct(x['recalled'], x['uses'])} had been "
                 "whispered; the rest were found another way (a sheet, memory, the listing)")
        if x["never_used"]:
            L.append("  whispered most, never then used: " + ", ".join(f"{p} ({n})" for p, n in x["never_used"]))
        if x["never_whispered"]:
            L.append("  used most, never whispered first: " + ", ".join(f"{p} ({n})" for p, n in x["never_whispered"]))
        if x["weeks"]:
            L.append("  by week: " + "  ".join(f"{w} {h}/{n}" for w, (h, n) in sorted(x["weeks"].items())))
    lib = f" of {x['library']} in the library ({100 * x['distinct_used'] // x['library']}%)" if x.get("library") else ""
    L.append(f"  DIVERSITY: {x['distinct_used']} distinct skills reached for{lib} across {x['uses_total']} uses"
             + (f"; the ten most used take {100 * x['top10_share']:.0f}%: " + ", ".join(f"{u} {n}" for u, n in x["top_used"])
                if x.get("top10_share") is not None else ""))
    if x["context_driven"]:
        L.append("  CONTEXT-DRIVEN (used >= 3 times, the prompt shared <= 1 word with the description in >= 60% of them): "
                 + ", ".join(f"{u} ({b}/{n} blind)" for u, b, n in x["context_driven"][:14])
                 + "  -> the session's phase picks these, not the prompt's words; only context (dial M41) or the meaning reading can reach them")
    L.append("  (labels are OBSERVED Skill calls + INFERRED script paths; the whisper line itself is never a label; "
             "none of this is an owner rating)")
    return "\n".join(L)


# --- command line ----------------------------------------------------------------------------------------------------

CMD_RX = re.compile(r"maestro\.py\\?\"?\s+(--selftest|[a-z]+)((?:\s+\S+){0,8})")
FLAG_RX = re.compile(r"\s(--[a-z][a-z-]+)")


def command_demand(files, known: set | None = None) -> dict:
    """Count, per Maestro command (and its first flag), how many transcript lines of tool INPUT ran it. Tool results
    and prose never count (a sheet that shows a command is not a run of it). With `known`, a word after maestro.py
    that is not a command (prose inside a tool input: 'maestro.py was changed') is ignored. Only assistant records
    count: an api-request-blob line replays earlier messages. Streams line by line."""
    cmds: Counter = Counter()
    flags: Counter = Counter()
    sessions: dict[str, set] = {}
    for f in files:
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                if '"tool_use"' not in raw or "maestro.py" not in raw:
                    continue
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if rec.get("isSidechain") or rec.get("type") != "assistant":
                    continue
                content = ((rec.get("message") or {}).get("content")) or []
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        blob = json.dumps(b.get("input") or {})
                        for m in CMD_RX.finditer(blob):
                            if known is not None and m.group(1) not in known:
                                continue
                            cmds[m.group(1)] += 1
                            sessions.setdefault(m.group(1), set()).add(str(rec.get("sessionId", f.stem))[:8])
                            fl = FLAG_RX.search(m.group(2) or "")
                            if fl:
                                flags[(m.group(1), fl.group(1))] += 1
    return {"commands": dict(cmds), "flags": {f"{c} {fl}": n for (c, fl), n in flags.items()},
            "sessions": {k: len(v) for k, v in sessions.items()}}


def documented_commands(doc: str) -> set[str]:
    return set(re.findall(r"python maestro\.py ([a-z]+)", doc)) | {"--selftest"}


def dead_switches(src: str) -> list[str]:
    """Module globals (UPPER_CASE = ...) that no other line of maestro.py reads: defined, never consulted."""
    names = re.findall(r"^([A-Z][A-Z0-9_]{2,}) *(?::[^=]+)?= ", src, re.MULTILINE)
    out = []
    for n in sorted(set(names)):
        uses = len(re.findall(r"\b" + re.escape(n) + r"\b", src))
        if uses <= 1:
            out.append(n)
    return out


def render_commands(dem: dict, doc: str, switches: bool, src: str) -> str:
    cmds = dem["commands"]
    docd = documented_commands(doc)
    L = [f"COMMAND DEMAND from the transcripts: {sum(cmds.values())} run(s) of {len(cmds)} command(s)"]
    for c, n in sorted(cmds.items(), key=lambda kv: -kv[1]):
        fl = ", ".join(f"{k.split(' ', 1)[1]} x{v}" for k, v in dem["flags"].items() if k.split(" ", 1)[0] == c)
        L.append(f"  {c:<12} {n:>4} run(s) in {dem['sessions'].get(c, 0)} session(s)" + (f"   flags: {fl}" if fl else ""))
    never = sorted(docd - set(cmds))
    L.append(f"NEVER RUN (documented, no transcript ran them): {', '.join(never) if never else 'none'}")
    undoc = sorted(set(cmds) - docd)
    if undoc:
        L.append(f"RUN BUT UNDOCUMENTED: {', '.join(undoc)}")
    if switches:
        ds = dead_switches(src)
        L.append(f"DEAD SWITCHES (globals maestro.py defines and never reads): {', '.join(ds) if ds else 'none'}")
    L.append("  (a never-run command is a take-away candidate; nothing is removed by this report)")
    return "\n".join(L)


def _val(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def _vals(argv: list[str], flag: str) -> list[str]:
    out, take = [], False
    for a in argv:
        if a == flag:
            take = True
        elif take and not a.startswith("--"):
            out.append(a)
        else:
            take = False
    return out


def cli(argv: list[str], lib, st, root: Path) -> int:
    """argv starts with 'hindsight'."""
    import phase as P  # beside this file (HERE is on sys.path)
    sub = argv[1] if len(argv) > 1 else "status"
    state = Path(st.d)
    rows = rows_of(state)
    if sub == "build":
        paths = [Path(p) for p in _vals(argv, "--paths")] or [P.projects_root()]
        write = getattr(st.append, "__name__", "") != "<lambda>"           # --no-ledger: nothing is written
        s = build(state, paths, set(lib.desc), lib.fs._tokens, write=write, log=print)
        print(render_build(s))
        return 0
    if sub == "commands":                                   # v15 items 26-27: command demand and dead switches
        paths = [Path(p) for p in _vals(argv, "--paths")] or [P.projects_root()]
        src = (M.HERE / "maestro.py").read_text(encoding="utf-8")
        known = documented_commands(M.__doc__ or "") | set(re.findall(r'cmd == "([a-z]+)"', src)) \
            | set(re.findall(r'"([a-z]+)"', src.split("# v15 modules")[0][-600:]))
        dem = command_demand(transcript_files(paths), known)
        print(render_commands(dem, M.__doc__ or "", "--switches" in argv, src))
        return 0
    if sub == "probes":
        ctx = int(_val(argv, "--context", 0))
        obs = "--observed-only" in argv
        default = PROBES if not ctx else PROBES.replace(".tsv", f"_ctx{ctx}.tsv")
        out = Path(_val(argv, "--out", state / (default.replace(".tsv", "_observed.tsv") if obs else default)))
        n = write_probes(rows, out, context=ctx, observed_only=obs, since=_val(argv, "--since"))
        print(f"PROBES: {n} labelled prompt(s) -> {out}\n  measure: python maestro.py eval --probes \"{out}\"")
        return 0 if n else 1
    if sub == "regret":
        lim = _val(argv, "--limit")
        res = regret(lib, rows, top=int(_val(argv, "--top", 3)), limit=int(lim) if lim else None,
                     since=_val(argv, "--since"), log=print)
        print(json.dumps(res, indent=1) if "--json" in argv else render_regret(res))
        return 0
    if sub == "propose":
        disc = "--discriminative" in argv
        pr = propose(rows, lib, M.load_mechanisms(), min_uses=int(_val(argv, "--min", 2)), k=int(_val(argv, "--k", 8)),
                     discriminative=disc, min_share=float(_val(argv, "--share", 0.6)), before=_val(argv, "--before"))
        print(render_propose(pr) + (f"\n  (discriminative filter on: a word counts only when >= {_val(argv, '--share', 0.6)} of the "
                                    "prompts holding it reached for that skill; v17, ruflo learned-routing)" if disc else ""))
        if "--write-lexicon" in argv:                   # the owner-lexicon reading's data (dial M37 weight_owner)
            lex = {p["skill"]: p["weights"] for p in pr}
            out = Path(_val(argv, "--out", M.HERE / "cards" / "owner_lexicon.json"))
            out.write_text(json.dumps(lex, indent=0, sort_keys=True), encoding="utf-8")
            print(f"WROTE {out}: {len(lex)} skill(s), {sum(len(v) for v in lex.values())} word weights (reading 'owner', weight dial M37"
                  f"{'; discriminative' if disc else ''}{'; labels before ' + _val(argv, '--before') if _val(argv, '--before') else ''})")
        return 0
    if sub == "reach":                                      # v19: the whisper hook, measured; the diversity of real use
        print(render_reach(reach(rows, lib.desc, lib.fs._tokens, since=_val(argv, "--since"))))
        return 0
    if sub == "similar":
        task = " ".join(a for a in argv[2:] if not a.startswith("--"))
        words = set(lib.fs._tokens(lib.variants(task)["_plain"])) if task else set()
        line = hindsight_line(state, words)
        print(line or "HINDSIGHT: no similar past prompt in the cache (or no cache: `maestro.py hindsight build`)")
        return 0
    print(render_status(rows, state))
    return 0


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    import tempfile
    ok: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        root = td / "skills"
        skills = [("hysteresis", ("Two-threshold latch that stops a flapping alert from chattering. Use this whenever "
                                  "an alert flaps on and off.")),
                  ("plain-terms", ("Rewrite a report in plain words for a reader. Use this whenever the owner wants plain "
                                   "language."))]
        sweep = [f"sw-{i}" for i in range(13)]
        for name, desc in skills + [(s, f"sweep skill {s}.") for s in sweep]:
            (root / name).mkdir(parents=True)
            (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n",
                                                   encoding="utf-8")
        tr = td / "projects" / "p"
        tr.mkdir(parents=True)

        def user(ts, text, side=False):
            return json.dumps({"type": "user", "timestamp": ts, "sessionId": "abcdef12", "isSidechain": side,
                               "message": {"role": "user", "content": text}})

        def tool(name, inp, side=False):
            return json.dumps({"type": "assistant", "isSidechain": side,
                               "message": {"role": "assistant", "content": [{"type": "tool_use", "name": name, "input": inp}]}})

        def whisper(line):                                  # v19: the UserPromptSubmit hook's attachment record
            return json.dumps({"type": "attachment", "attachment": {"type": "hook_success", "hookName": "UserPromptSubmit",
                                                                    "hookEvent": "UserPromptSubmit", "content": line}})

        lines = [
            user("2026-10-20T10:00:00Z", "stop my beeper alert from flapping on and off every minute, the beeper keeps flapping"),
            whisper("WHISPER (0.50s, 2 by task size): /skill-maestro, /hysteresis, /plain-terms   (by meaning; `score` for the sheet)"),
            tool("Bash", {"command": "python C:/x/skills/hysteresis/hysteresis.py --selftest"}),
            tool("Skill", {"skill": "plain-terms"}),
            tool("Bash", {"command": "python skills/skill-maestro/maestro.py score x"}),      # SELF: never a label
            tool("Bash", {"command": "python skills/nosuch/x.py"}),                            # not a skill name
            tool("Bash", {"command": "python skills/sw-1/t.py"}, side=True),                   # a subagent: ignored
            user("2026-10-20T11:00:00Z", "check every skill in the library for broken selftests and list them all"),
            *[tool("Bash", {"command": f"python skills/{s}/t.py"}) for s in sweep],
            user("2026-10-21T09:00:00Z", "the beeper alert is flapping again; explain the latch in plain words please"),
            whisper("WHISPER (0.40s): /sw-1   (words only)"),
            tool("Read", {"file_path": "C:\\Users\\x\\.claude\\skills\\hysteresis\\SKILL.md"}),
            user("2026-10-21T09:30:00Z", "ok"),
            json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}}),
            user("2026-10-21T10:00:00Z", "<command-name>/model</command-name>"),
            user("2026-10-21T10:05:00Z", "my key=sk-abcdefghijklmnop mail me@example.com", side=False),
        ]
        (tr / "a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (tr / "b.jsonl").write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")   # a continued session: duplicates
        state = td / "state"
        lib = M.Library(root, everything=False)
        s1 = build(state, [tr], set(lib.desc), lib.fs._tokens)
        rows = rows_of(state)
        ok["5 owner prompts kept once across two files (tool results, commands skipped)"] = len(rows) == 5
        r1 = next((r for r in rows if r["ts"].startswith("2026-10-20 10:00")), {})
        ok["used = Skill calls + tool paths under skills/, minus self, non-skills and sidechains"] = \
            r1.get("used") == ["hysteresis", "plain-terms"]
        ok["13 skills after one prompt is a SWEEP"] = any(r["sweep"] and len(r["used"]) == 13 for r in rows)
        ok["Read of a SKILL.md path counts as reached for"] = \
            any(r["used"] == ["hysteresis"] for r in rows if r["ts"].startswith("2026-10-21 09:00"))
        ok["2 labelled prompts, 1 sweep"] = s1["labelled"] == 2 and s1["sweeps"] == 1
        ok["v19: the whisper's picks are kept per prompt (the Maestro itself included, the trailer dropped)"] = \
            r1.get("whispered") == ["skill-maestro", "hysteresis", "plain-terms"] and r1.get("whisper_s") == 0.5
        rc = reach(rows, lib.desc, lib.fs._tokens)
        ok["v19 reach: 2 whispered labelled prompts, 1 followed (any pick), 1 by its first pick, recall 2 of 3 uses"] = \
            rc["labelled_whispered"] == 2 and rc["hit_any"] == 1 and rc["hit_first"] == 1 and rc["uses"] == 3 and rc["recalled"] == 2
        ok["v19 reach: diversity counts distinct skills over the library; sw-1 was whispered and never used"] = \
            rc["distinct_used"] == 2 and rc["library"] == 15 and ("sw-1", 1) in rc["never_used"]
        ok["v19 reach: --since cuts the window; render names FOLLOWED and DIVERSITY"] = \
            reach(rows, lib.desc, lib.fs._tokens, since="2026-10-21")["labelled_whispered"] == 1 \
            and "FOLLOWED" in render_reach(rc) and "DIVERSITY" in render_reach(rc)
        ok["2026-10-27 reach: BY KIND splits typed from mid-turn; the line is silent with no mid-turn prompt"] = \
            sum(v[1] for v in rc["by_kind"].values()) == rc["labelled_whispered"] and "BY KIND" not in render_reach(rc) \
            and "BY KIND" in render_reach({**rc, "by_kind": {"typed": [1, 1], "mid-turn": [0, 1]}})
        tw = td / "projects-w" / "p"
        tw.mkdir(parents=True)
        (tw / "w.jsonl").write_text("\n".join([
            user("2026-10-26T10:00:00Z", "explain the latch in plain words please"),
            whisper("WHISPER (0.30s, FULL: open-ended work (design / invent / explore); 1 by task size): candidates "
                    "/plain-terms\nNEXT STEP: before any other tool, call the Skill tool with skill \"skill-maestro\""),
            user("2026-10-26T10:05:00Z", "Another Claude session sent a message: rebuild the index"),
            json.dumps({**json.loads(whisper("WHISPER (0.30s, QUICK, 4 by task size): /sw-1, /sw-2, /sw-3, /sw-4\n"
                                             "NEXT STEP: if /sw-1 fits this prompt, call the Skill tool")),
                        "timestamp": "2026-10-26T10:05:01Z"}),
            user("2026-10-27T09:00:00Z", "<task-notification><task-id>x</task-id></task-notification>"),
            json.dumps({**json.loads(whisper("WHISPER (0.30s, SKIP: a plan card names the tests): build from the card; "
                                             "/sw-5 only if a helper is wanted (call it via the Skill tool).")),
                        "timestamp": "2026-10-27T09:00:01Z"})]) + "\n", encoding="utf-8")
        build(td / "state-w", [tw], set(lib.desc), lib.fs._tokens)
        wrows = rows_of(td / "state-w")
        bt = reach(wrows, lib.desc, lib.fs._tokens)["by_text"]
        ok["2026-10-28 reach: a whisper on a peer's text is kept apart (BY TEXT), not laid over the owner's own; "
           "the FULL / QUICK / SKIP lines (v20.0.7) are read"] = \
            len(wrows) == 1 and wrows[0]["whispered"] == ["plain-terms"] and wrows[0]["whisper_s"] == 0.3 \
            and bt == {"owner": [1, 0], "peer message": [1, 0], "task notice": [0, 1]} \
            and "BY TEXT" in render_reach(reach(wrows, lib.desc, lib.fs._tokens)) and "BY TEXT" not in render_reach(rc)
        ok["secrets and mail addresses are redacted in the cache"] = \
            all("sk-abcdefghijklmnop" not in r["text"] and "me@example.com" not in r["text"] for r in rows)
        s2 = build(state, [tr], set(lib.desc), lib.fs._tokens)
        ok["a second build rescans nothing and keeps the rows"] = \
            s2["unchanged"] == 2 and s2["rescanned"] == 0 and len(rows_of(state)) == 5
        s3 = build(td / "state2", [tr], set(lib.desc), lib.fs._tokens, write=False)
        ok["write=False counts but writes nothing"] = s3["labelled"] == 2 and not (td / "state2" / CACHE).exists()
        n = write_probes(rows, td / "p.tsv")
        body = [ln for ln in (td / "p.tsv").read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
        ok["probes: one TSV line per labelled prompt, in eval's format"] = \
            n == 2 and len(body) == 2 and all(ln.count("\t") == 1 for ln in body) and body[0].endswith("hysteresis,plain-terms")
        words = set(lib.fs._tokens("my beeper alert flaps on and off"))
        c, nsim = similar(rows, words)
        ok["similar: the skills reached for after prompts like this one, sweeps excluded"] = \
            nsim >= 1 and c and c[0][0] == "hysteresis"
        ok["hindsight_line is a self-report line naming the skill"] = \
            "self-report" in (hindsight_line(state, words) or "") and "hysteresis" in (hindsight_line(state, words) or "")
        ok["hindsight_line is None without a cache"] = hindsight_line(td / "nowhere", words) is None
        pr = propose(rows, lib, {}, min_uses=2)
        hy = next((p for p in pr if p["skill"] == "hysteresis"), None)
        ok["propose: 'beeper' recurs before hysteresis and its text never says it; 'flapping' (in its description) is not proposed"] = \
            hy is not None and any(w == "beeper" for w, _ in hy["words"]) and not any(w == "flapping" for w, _ in hy["words"])
        rg = regret(lib, rows)
        ok["regret: both labelled prompts REACHED in a blind audition on the fixture library"] = \
            rg["n"] == 2 and rg["reached"] == 2 and rg["blind"] == 0 and rg["weeks"]
        # a label the library no longer has -> GONE, never BLIND
        rows2 = rows + [{"ts": "2026-10-19 08:00", "session": "x", "file": "f", "words": ["alert", "beeper", "flaps", "latch", "noise"],
                         "used": ["deleted-skill"], "sweep": False, "excerpt": "e", "text": "alert beeper flaps latch noise"}]
        ok["regret: a used skill that no longer exists is GONE"] = regret(lib, rows2)["gone"] == 1
        ok["redact keeps ordinary text"] = redact("plain words stay") == "plain words stay"
        tf = Path(td_) / "t.jsonl"
        tf.write_text(json.dumps({"type": "assistant", "sessionId": "s1", "message": {"content": [
            {"type": "tool_use", "input": {"command": "python maestro.py score \"x\" --full"}}]}}) + "\n"
            + json.dumps({"type": "assistant", "sessionId": "s2", "message": {"content": [
                {"type": "tool_use", "input": {"command": "python maestro.py score \"y\""}},
                {"type": "tool_use", "input": {"command": "python maestro.py --selftest"}}]}}) + "\n"
            + json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "python maestro.py eval"}]}}) + "\n"
            + json.dumps({"type": "assistant", "isSidechain": True, "message": {"content": [
                {"type": "tool_use", "input": {"command": "python maestro.py grade"}}]}}) + "\n"
            + json.dumps({"type": "api-request-blob", "sessionId": "s1", "hash": "h", "message": {
                "role": "assistant", "content": [{"type": "tool_use", "input": {"command": "python maestro.py score 'x' --full"}}]}})
            + "\n", encoding="utf-8")
        dem = command_demand([tf])
        ok["commands: counts tool inputs only (a result, a sidechain and a replayed request blob never count), per session, with flags"] = \
            dem["commands"] == {"score": 2, "--selftest": 1} and dem["sessions"]["score"] == 2 \
            and dem["flags"] == {"score --full": 1}
        ok["commands: dead switch = a global read nowhere else"] = \
            dead_switches("ALPHA = 1\nBETA = 2\nx = ALPHA + 1\n") == ["BETA"]
        rc = render_commands(dem, "python maestro.py score\npython maestro.py eval\n", False, "")
        ok["commands: NEVER RUN names the documented command no transcript ran"] = "NEVER RUN" in rc and "eval" in rc.split("NEVER RUN")[1]
        import os  # 2026-10-26: the running session's prompts, not a peer's
        rp = td / "rp"
        own_f, peer_f = rp / "proj" / "own-sess-0001.jsonl", rp / "proj" / "peer-sess-0002.jsonl"
        sub_f = rp / "proj" / "own-sess-0001" / "subagents" / "agent-x.jsonl"
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        for f, recs in ((own_f, [user("2026-01-01T00:00:00Z", "an old prompt from before the file stopped growing"),
                                 user(now_ts, "fix the beeper latch so it stops flapping on and off"),
                                 user(now_ts, "python maestro.py score this is the echo")]),
                        (peer_f, [user(now_ts, "a peer session's prompt about something else entirely")]),
                        (sub_f, [user(now_ts, "a subagent's prompt")])):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("\n".join(recs) + "\n", encoding="utf-8")
        ok["walk: a folder walk skips subagents/; a subagent file named outright is kept"] = \
            [f.name for f in transcript_files([rp])] == ["own-sess-0001.jsonl", "peer-sess-0002.jsonl"] \
            and transcript_files([sub_f]) == [sub_f]
        t0 = time.time()
        os.utime(own_f, (t0 - 300, t0 - 300))
        os.utime(peer_f, (t0 - 30, t0 - 30))
        w1, w2, w3, w4 = {}, {}, {}, {}
        ok["context: this session's own prompts by id, the stale one and the Maestro's echo left out"] = \
            recent_prompts(2, paths=[rp], session_id="own-sess-0001", why=w1) == ["fix the beeper latch so it stops flapping on and off"] \
            and w1.get("source") == "session id" and "empty" not in w1
        ok["context: with no session id the newest file is a guess, and here it is the peer's"] = \
            recent_prompts(2, paths=[rp], session_id="", why=w2) == ["a peer session's prompt about something else entirely"] \
            and w2.get("source") == "newest (a guess)"
        ok["context: a session id with no file gives nothing and says why"] = \
            recent_prompts(2, paths=[rp], session_id="gone-sess-0003", why=w3) == [] \
            and w3.get("empty") == "this session's transcript is not on disk"
        ok["context: when the only fresh prompt is the task itself, the reason is given"] = \
            recent_prompts(2, exclude="fix the beeper latch so it stops flapping on and off", paths=[rp],
                           session_id="own-sess-0001", why=w4) == [] \
            and w4.get("empty") == "no other prompt from the last 6 h in that transcript"
        ok["context: the hook's path wins"] = \
            recent_prompts(2, paths=[rp], session_id="own-sess-0001", transcript=peer_f) == ["a peer session's prompt about something else entirely"]
        rs = td / "rs"                                      # a transcript Claude Code stopped writing says so
        (rs / "proj").mkdir(parents=True)
        (rs / "proj" / "stale-sess-0004.jsonl").write_text(user("2026-01-01T00:00:00Z", "an old prompt") + "\n", encoding="utf-8")
        w5 = {}
        ok["context: a transcript with no recent record says when it stopped, not that no prompt came"] = \
            recent_prompts(2, paths=[rs], session_id="stale-sess-0004", why=w5) == [] \
            and w5.get("empty", "").startswith("this session's transcript has had no record since 2026-01-01 00:00 UTC")
    ok = {k: bool(v) for k, v in ok.items()}
    print(f"hindsight selftest: {sum(ok.values())}/{len(ok)} " + ("PASS" if all(ok.values()) else "FAIL"))
    for k, v in ok.items():
        if not v:
            print(f"  FAIL {k}")
    return all(ok.values())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(M.main(["hindsight", *sys.argv[1:]]))
