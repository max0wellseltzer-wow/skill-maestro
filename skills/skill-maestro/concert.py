"""concert.py - the Maestro's v15 front-of-house commands (loaded by maestro.py; never run alone except --selftest).

    play "task" --subject FILE     the whole protocol in one command: suggest concepts, score, chain, rehearse, judge
    whisper "prompt" [--hook]      the finder's 1-22 names (by task size) in one line from the prepared index (~free); --hook prints the
                                   UserPromptSubmit hook snippet, OFF until the owner pastes it into settings.json
    doctor                         fresh-install check with numbered fix steps
    welcome                        WELCOME.md with this library's own numbers
    digest SKILL                   an extractive ten-line digest of a skill (no reading of the whole SKILL.md)
    grade [--days N]               the report card: hit rates, cost, value, debt, drift
    matrix                         the Maestro's matrices from live data (kind x phases; stage x source; dial x evidence)
    suggest "task"                 operation tags for --concepts, from the vocabulary's own meanings
    brief RUN                      a subagent brief for a run: subject, picks, commands, what to report

Every function here reads through maestro.py's own loaders (M = the loaded maestro module) so there is one reading
of the library, one ledger, one dial panel. Nothing here changes a ranking: play/whisper show what score/search show.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = None   # the maestro module, set by _maestro()


def _maestro():
    global M
    if M is None:
        spec = importlib.util.spec_from_file_location("maestro", HERE / "maestro.py")
        M = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(M)
    return M


_WORD = re.compile(r"[a-z][a-z0-9-]{2,}")
STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "each", "its", "are", "was", "use", "when",
        "whenever", "use this", "max", "asks", "wants", "every", "one", "two", "all", "any", "not", "you", "your"}


def words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in STOP}


# --- suggest ---------------------------------------------------------------------------------------------------------

def suggest(task: str, vocab: dict[str, str], k: int = 4) -> list[tuple[str, float, str]]:
    """Operation tags whose meaning (and name) share words with the task, best first: (tag, score, shared words).
    A tag's name counts double (saying 'rank' in the task is a stronger hint than a meaning word)."""
    tw = words(task)
    out = []
    for tag, meaning in vocab.items():
        mw = words(meaning)
        nw = set(tag.replace("-", " ").split())
        shared = (tw & mw) | (tw & nw)
        if not shared:
            continue
        s = len(tw & mw) + 2 * len(tw & nw)
        out.append((tag, s / (1 + len(mw)) ** 0.5, ", ".join(sorted(shared))))
    out.sort(key=lambda r: (-r[1], r[0]))
    return out[:k]


def concepts_text(task: str, vocab: dict[str, str], k: int = 4) -> str:
    """A --concepts string from the suggestions: '<tag>: <the task words it matched>; ...' plus a world slot."""
    parts = [f"{tag}: {shared}" for tag, _, shared in suggest(task, vocab, k)]
    return "; ".join(parts)


def render_suggest(task: str, rows: list[tuple[str, float, str]], vocab_n: int) -> str:
    if not rows:
        return (f"SUGGEST: no operation tag shares a word with this task ({vocab_n} tags). Write the concepts by hand: "
                f"`maestro.py vocab` lists them; 'world: <where this happens in nature or a trade>' is always allowed.")
    L = [f"SUGGEST for \"{task[:70]}\": {len(rows)} tag(s) of {vocab_n}"]
    for tag, s, shared in rows:
        L.append(f"  {tag:<20} {s:.2f}  shares: {shared}")
    L.append("  --concepts \"" + "; ".join(f"{t}: {sh}" for t, _, sh in rows) + "; world: <fill in>\"")
    L.append("  (a suggestion from word overlap with the tag meanings; Claude's own reading of the task beats it)")
    return "\n".join(L)


# --- digest ----------------------------------------------------------------------------------------------------------

def digest(md: str, limit: int = 10) -> list[str]:
    """Extractive: the name, the first sentence of the description, the 'Use this whenever' sentence, up to three
    headings and up to three commands. Nothing is paraphrased; every line is a line (or sentence) of the file."""
    out: list[str] = []
    fm = re.search(r"^---\s*\n(.*?)\n---", md, re.S)
    head = fm.group(1) if fm else ""
    name = re.search(r"^name:\s*(.+)$", head, re.M)
    desc = re.search(r"^description:\s*(.+)$", head, re.M)
    if name:
        out.append(f"NAME {name.group(1).strip()}")
    if desc:
        d = desc.group(1).strip().strip('"')
        sents = re.split(r"(?<=[.!?])\s+", d)
        out.append("DOES " + sents[0][:220])
        use = next((s for s in sents if re.match(r"(Use|Trigger)", s)), None)
        if use:
            out.append("WHEN " + use[:220])
    body = md[fm.end():] if fm else md
    heads = [h.strip("# ").strip() for h in re.findall(r"^#{1,3} .+$", body, re.M)][:3]
    out += [f"PART {h[:100]}" for h in heads]
    cmds = []
    for blk in re.findall(r"```[^\n]*\n(.*?)```", body, re.S):
        for ln in blk.splitlines():
            ln = ln.strip()
            if ln.startswith("python ") and ln not in cmds:
                cmds.append(ln)
    out += [f"RUN  {c[:110]}" for c in cmds[:3]]
    tests = re.search(r"(\d+)\s*(?:/|of)\s*(\d+)\s*(?:PASS|pass|passed|tests?)", body)
    if tests:
        out.append(f"TEST {tests.group(0)}")
    return out[:limit]


# --- doctor ----------------------------------------------------------------------------------------------------------

def doctor(lib, st, root: Path) -> list[dict]:
    """Checks a fresh install needs, each {name, ok, found, fix}; fix is the numbered step a beginner follows."""
    M_ = _maestro()
    checks = []
    v = sys.version_info
    checks.append({"name": "python 3.10+", "ok": v >= (3, 10), "found": f"{v.major}.{v.minor}",
                   "fix": "install Python 3.10 or newer from python.org and reopen the terminal"})
    checks.append({"name": "a library of skills", "ok": len(lib.skills) > 0, "found": f"{len(lib.skills)} skills under {root}",
                   "fix": f"put skill folders (each with a SKILL.md) under {root}, or pass --root <folder>"})
    checks.append({"name": "skill-finder beside the Maestro (else standalone)", "ok": not lib.standalone,
                   "found": "standalone mini finder" if lib.standalone else "skill-finder found",
                   "fix": "optional: install skill-finder (find_skill.py + core_pin.py) in the same library; standalone works"})
    try:
        _, sha = M_.load_dials()
        checks.append({"name": "dial panel loads", "ok": True, "found": f"sha {sha[:12]}", "fix": ""})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "dial panel loads", "ok": False, "found": str(exc)[:80],
                       "fix": "restore maestro_dials.md from the skill folder (a LOCKED dial was changed)"})
    writable = True
    try:
        p = st.d / ".doctor_touch"
        p.write_text("x", encoding="utf-8")
        p.unlink()
    except OSError:
        writable = False
    checks.append({"name": "state folder writable", "ok": writable, "found": str(st.d),
                   "fix": f"make {st.d} writable, or pass --state <another folder>"})
    mechs = M_.load_mechanisms()
    missing = [s["name"] for s in lib.skills if s["name"] not in mechs]
    checks.append({"name": "a meaning line for every skill", "ok": not missing,
                   "found": f"{len(missing)} skill(s) without one",
                   "fix": "run: python maestro.py cards --auto   (writes cards/mechanisms_auto.jsonl)"})
    ix = sorted(st.d.glob("index_*.json"))
    checks.append({"name": "prepared index built", "ok": bool(ix), "found": ix[-1].name if ix else "none",
                   "fix": "run: python maestro.py index --build   (whisper and score read it instead of rescanning)"})
    hs = st.d / "hindsight.jsonl"
    checks.append({"name": "hindsight cache (learning from past sessions)", "ok": hs.is_file(),
                   "found": f"{sum(1 for _ in hs.open(encoding='utf-8'))} prompts" if hs.is_file() else "none",
                   "fix": "run: python maestro.py hindsight build   (reads your own transcripts; nothing leaves the machine)"})
    probes = M_.companion(root, "probes_heldout.tsv")
    checks.append({"name": "held-out probes for eval", "ok": probes.is_file(), "found": probes.name if probes.is_file() else "none",
                   "fix": "optional: python maestro.py hindsight probes   writes probes from your real prompts"})
    rows = st.rows()
    checks.append({"name": "ledger readable", "ok": True, "found": f"{len(rows)} rows", "fix": ""})
    sc = M_.stale_cards(lib, M_.load_cards())              # v17: a card whose skill changed since it was written
    checks.append({"name": "cards match their skills (skill_sha)", "ok": not sc["stale"],
                   "found": f"{sc['ok']} current, {len(sc['stale'])} STALE, {sc['unstamped']} unstamped"
                            + (f": {', '.join(sc['stale'][:4])}" if sc["stale"] else ""),
                   "fix": "re-read the STALE skills' SKILL.md, fix their card lines, then run: python maestro.py cards --stamp"})
    pins = pinned_receipts(HERE / "references" / "leitner_checks.json")     # v17: marker-pinned standing claims
    checks.append({"name": "pinned receipts hold (leitner markers)", "ok": not pins["broken"],
                   "found": f"{pins['held']} hold, {len(pins['broken'])} broken" + (f": {', '.join(pins['broken'][:3])}" if pins["broken"] else ""),
                   "fix": "a standing claim's marker text is gone from its file: re-check the claim and update references/leitner_checks.json"})
    return checks


def pinned_receipts(path: Path) -> dict:
    """v17 (ruflo verification/witness-fixes.json): each standing claim may carry a `marker` {file, contains}: the
    file must still contain that text, or the claim is BROKEN (a receipt pinned to a line that no longer exists)."""
    held, broken = 0, []
    try:
        checks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        return {"held": 0, "broken": ["leitner_checks.json unreadable"]}
    for name, spec in checks.items():
        mk = spec.get("marker") if isinstance(spec, dict) else None
        if not mk:
            continue
        f = Path(str(mk.get("file", "")).replace("~", str(Path.home())))
        try:
            ok = f.is_file() and mk.get("contains", "") in f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            ok = False
        if ok:
            held += 1
        else:
            broken.append(name)
    return {"held": held, "broken": broken}


def render_doctor(checks: list[dict]) -> str:
    bad = [c for c in checks if not c["ok"]]
    L = [f"DOCTOR: {len(checks) - len(bad)} of {len(checks)} checks pass" + ("" if not bad else f"; {len(bad)} to fix")]
    for c in checks:
        L.append(f"  [{'ok' if c['ok'] else '--'}] {c['name']:<48} {c['found'][:60]}")
    if bad:
        L.append("FIX, in order:")
        for i, c in enumerate(bad, 1):
            L.append(f"  {i}. {c['fix']}")
        L.append("  then run `python maestro.py doctor` again until every line says ok.")
    else:
        L.append("READY: python maestro.py score \"<your task in your own words>\"")
    return "\n".join(L)


# --- welcome ---------------------------------------------------------------------------------------------------------

def welcome(lib, st) -> str:
    rows = st.rows()
    runs = [r for r in rows if r.get("kind") == "SCORE"]
    ev = [r for r in rows if r.get("kind") == "EVAL"]
    tools = sum(1 for s in lib.skills if s.get("tool"))
    head = [f"YOUR LIBRARY: {len(lib.skills)} skills ({tools} with a program), {len(runs)} Maestro runs so far"
            + (f", last eval top-3 {ev[-1].get('maestro@3', '?')}" if ev else ", no eval yet"),
            ""]
    w = HERE / "WELCOME.md"
    return "\n".join(head) + (w.read_text(encoding="utf-8") if w.is_file() else "(WELCOME.md missing)")


# --- grade -----------------------------------------------------------------------------------------------------------

def grade(rows: list[dict], days: int = 30, now: float | None = None) -> dict:
    now = now or time.time()
    since = now - days * 86400
    rec = [r for r in rows if r.get("t", 0) >= since]
    runs = [r for r in rec if r.get("kind") == "SCORE"]
    tri = Counter(r.get("verdict") for r in rec if r.get("kind") == "TRIAGE")
    fits = [r for r in rec if r.get("kind") == "FIT"]
    works = sum(1 for r in fits if r.get("verdict") == "works")
    rates = [r for r in rec if r.get("kind") == "RATE"]
    owner = [r for r in rates if r.get("by") not in (None, "claude")]
    useful_owner = sum(1 for r in owner if r.get("rating") == "useful" or (r.get("scores") or {}).get("topic", 0) >= 3)
    sheets = [r for r in rec if r.get("kind") == "SHEET_COST"]
    cost = sum(r.get("sheet", 0) for r in sheets)
    evs = [r for r in rows if r.get("kind") == "EVAL" and r.get("probes") == "probes_heldout.tsv"]
    first, last = (evs[0], evs[-1]) if evs else (None, None)
    rated_runs = {r["run"] for r in rates} | {r["run"] for r in rec if r.get("kind") == "CLOSE"}
    debt = [r["run"] for r in runs if r.get("chosen") and r["run"] not in rated_runs]
    weeks: dict[str, list[int]] = {}
    for r in fits:
        wk = time.strftime("%Y-W%W", time.gmtime(r.get("t", 0)))
        weeks.setdefault(wk, []).append(1 if r.get("verdict") == "works" else 0)
    drift = {k: f"{sum(v)}/{len(v)}" for k, v in sorted(weeks.items())}
    structured = sum(1 for r in fits if r.get("judgments"))
    stale = sum(1 for r in fits + rates if r.get("stale"))
    return {"days": days, "runs": len(runs), "triage": dict(tri), "fits": len(fits), "works": works,
            "fits_structured": structured, "stale": stale,
            "ratings": len(rates), "owner_ratings": len(owner), "owner_useful": useful_owner,
            "sheet_tokens": cost, "debt": len(debt),
            "eval_first": {k: v for k, v in (first or {}).items() if "@" in k},
            "eval_last": {k: v for k, v in (last or {}).items() if "@" in k},
            "eval_dates": [time.strftime("%Y-%m-%d", time.gmtime(e["t"])) for e in (first, last) if e],
            "fit_by_week": drift}


def render_grade(g: dict) -> str:
    L = [f"REPORT CARD, last {g['days']} days"]
    L.append(f"  runs {g['runs']}; triage " + ", ".join(f"{k} {v}" for k, v in sorted(g["triage"].items())) if g["triage"]
             else f"  runs {g['runs']}; no triage rows")
    L.append(f"  picks tried {g['fits']}, worked {g['works']}"
             + (f" ({100 * g['works'] // g['fits']}%)" if g["fits"] else "")
             + f"; structured FIT {g.get('fits_structured', 0)} (labels for rerank); judged on a changed subject (STALE) {g.get('stale', 0)}")
    L.append(f"  ratings {g['ratings']}, by the owner {g['owner_ratings']} (useful {g['owner_useful']}); "
             f"unrated runs (debt) {g['debt']}")
    L.append(f"  cost: ~{g['sheet_tokens']} sheet tokens shown")
    if g["eval_last"]:
        L.append(f"  eval held-out: first {g['eval_dates'][0]} {g['eval_first'].get('maestro@3')} -> last "
                 f"{g['eval_dates'][-1]} {g['eval_last'].get('maestro@3')} (top-3); top-1 {g['eval_last'].get('maestro@1')}")
    if g["fit_by_week"]:
        L.append("  drift, FIT works per week: " + ", ".join(f"{k} {v}" for k, v in g["fit_by_week"].items()))
    verdict = ("NO USE" if not g["runs"] else "IDLE EVIDENCE" if not g["fits"] else
               "EARNING" if g["works"] * 2 >= g["fits"] else "MOSTLY MISFITS")
    L.append(f"  verdict: {verdict}" + ("; rate or close the unrated runs (`maestro.py debt`)" if g["debt"] else ""))
    return "\n".join(L)


# --- matrix ----------------------------------------------------------------------------------------------------------

def dial_rows(text: str) -> list[dict]:
    out = []
    for ln in text.splitlines():
        m = re.match(r"\|\s*(M\d+)\s*\|\s*([^|]+)\|\s*([^|]*)\|\s*(yes|no)\s*\|\s*([^|]*)\|", ln)
        if m:
            out.append({"id": m.group(1), "dial": m.group(2).strip(), "value": m.group(3).strip(),
                        "locked": m.group(4) == "yes", "meaning": m.group(5).strip()})
    return out


def matrix(lib, mechs: dict, dials_text: str, charter_text: str) -> dict:
    M_ = _maestro()
    kinds = {k: list(v) for k, v in M_.KIND_PHASES.items()}
    kinds["(analytical)"] = list(M_.PHASE_ORDER)
    # stage x source skill, from the charter's "(source: a, b)" notes per stage
    stage, sources = None, {}
    for ln in charter_text.splitlines():
        ms = re.match(r"Stage (\w+)", ln)
        if ms:
            stage = ms.group(1)
        mo = re.search(r"\(source: ([^)]+)\)", ln)
        if stage and mo:
            for s in re.split(r",\s*", mo.group(1)):
                s = s.split("'")[0].split(" ")[0].strip()
                if s and re.match(r"^[a-z0-9-]+$", s):
                    sources.setdefault(stage, Counter())[s] += 1
    ev_words = re.compile(r"\b(\d+\s*(?:/|of|->)\s*\d+|p\s*[<=]?\s*0\.\d+|held-out|measured|E\d\d)\b", re.I)
    dials = [{**d, "evidence": bool(ev_words.search(d["meaning"]))} for d in dial_rows(dials_text)]
    ops = Counter(t for m in mechs.values() for t in (m.get("tags") or []))
    return {"kind_x_phases": kinds, "stage_x_source": {k: dict(v.most_common(8)) for k, v in sources.items()},
            "dial_x_evidence": dials, "op_coverage": dict(ops.most_common(12)), "skills": len(lib.skills)}


def render_matrix(mx: dict) -> str:
    L = ["MATRIX 1  kind x phases (the sheet's phase order per task kind)"]
    for k, v in mx["kind_x_phases"].items():
        L.append(f"  {k:<14} " + " -> ".join(v))
    L.append("MATRIX 2  stage x borrowed skill (from the charter's source notes; count = items that borrowed it)")
    for k, v in mx["stage_x_source"].items():
        L.append(f"  {k:<11} " + ", ".join(f"{s} x{n}" if n > 1 else s for s, n in v.items()))
    d = mx["dial_x_evidence"]
    with_ev = sum(1 for x in d if x["evidence"])
    L.append(f"MATRIX 3  dial x evidence: {len(d)} dials, {sum(1 for x in d if x['locked'])} locked, "
             f"{with_ev} whose meaning cites a measurement, {len(d) - with_ev} that cite none")
    for x in d:
        if not x["evidence"] and not x["locked"]:
            L.append(f"  no evidence cited: {x['id']} {x['dial']} = {x['value']}")
    L.append(f"MATRIX 4  operation x skills ({mx['skills']} skills): " + ", ".join(f"{k} {v}" for k, v in mx["op_coverage"].items()))
    return "\n".join(L)


# --- whisper ---------------------------------------------------------------------------------------------------------

def whisper_count(prompt: str, scored: list[dict]) -> tuple[int, str]:
    """How many names the whisper shows: the Maestro's own pick_count rule (1 to PICKS_MAX by the task's size: one for
    four words or fewer, two per sentence, never more than the candidates whose words score at least half the best).
    Max, 2026-10-24: the hook showed a fixed top 3 while score picked 1 to 22; the whisper now follows the same rule.
    `scored` is the finder's list (name, score) for the whole candidate window."""
    M_ = _maestro()
    if scored and "fit" in scored[0]:                      # purpose_rank rows: fit already scaled; meaning-backed ones count
        return M_.pick_count(prompt, [r for r in scored if "meaning" in r.get("via", [])] or scored)
    best = max((r.get("score", 0.0) for r in scored), default=0.0) or 1.0
    weighed = [{"fit": r.get("score", 0.0) / best} for r in scored]
    return M_.pick_count(prompt, weighed)


def whisper(lib, prompt: str, k: int | None = None) -> list[str]:
    """The finder's names for a prompt (words only, no bonuses, nothing written): k names when k is given (the eval's
    finder@3 call), else 1 to PICKS_MAX by the task's size via whisper_count."""
    if k is not None:
        return [r["name"] for r in lib.search(prompt, k)]
    _maestro().MEANING_WAIT = 0.0                           # the hook never waits for the meaning helper to start
    scored = _maestro().purpose_rank(lib.search, prompt, root=lib.root, desc=lib.desc)   # 2026-10-24: meaning first, then words; 2026-10-25: desc for the deliverable vote (M51)
    n, _why = whisper_count(prompt, scored)
    return [r["name"] for r in scored[:n]]


def whisper_fast(prompt: str, state_dir: Path, root: Path, k: int | None = None) -> list[str] | None:
    """O4/O7: the whisper without building a Library: read the prepared index file for `root` straight from disk and
    search it with index.py's FastSearch (the same scoring `search` uses). None when there is no index yet, and the
    caller falls back to the full path. Measured 2026-10-22: 1.4 s -> under 0.5 s per prompt.
    k None (the hook): 1 to PICKS_MAX names by the task's size (whisper_count), the rule `score` uses."""
    try:
        ix = importlib.util.spec_from_file_location("maestro_index", HERE / "index.py")
        IX = importlib.util.module_from_spec(ix)
        ix.loader.exec_module(IX)
        p = IX.index_path(root, state_dir)
        if not p.is_file():
            return None
        seen, skills = set(), []
        for f in [p] + sorted(x for x in Path(state_dir).glob("index_*.json") if x != p):   # the library first, then
            d = json.loads(f.read_text(encoding="utf-8"))                                  # plugin roots' indexes
            for e in d["skills"].values():
                if e["name"] not in seen:
                    seen.add(e["name"])
                    skills.append(IX._as_skill(e))
        fsp = None
        for home in ("skill-finder", "core-skill-pin"):
            if (root / home / "find_skill.py").is_file():
                fsp = root / home / "find_skill.py"
                break
        if fsp is None:
            return None
        fs_spec = importlib.util.spec_from_file_location("find_skill", fsp)
        fs = importlib.util.module_from_spec(fs_spec)
        fs_spec.loader.exec_module(fs)
        if k is not None:
            return [r["name"] for r in IX.FastSearch(fs, skills).search(skills, prompt, k)]
        for n, d in _maestro().builtin_skills().items():   # 2026-10-24 (Max): Anthropic's skills are full candidates,
            if n not in seen:                              # in the words reading too, exactly as the Library adds them
                seen.add(n)
                skills.append({"name": n, "desc": d, "tool": False, "name_toks": set(fs._tokens(n)),
                               "toks": fs._tokens(n + " " + d), "sha": ""})
        F = IX.FastSearch(fs, skills)
        _maestro().MEANING_WAIT = 0.0
        scored = _maestro().purpose_rank(lambda q, d: F.search(skills, q, d), prompt, root=root, state_dir=state_dir,
                                       desc={s["name"]: s["desc"] for s in skills})   # 2026-10-24: meaning first; 2026-10-25: desc for the deliverable and phase votes
        n, _why = whisper_count(prompt, scored)
        return [r["name"] for r in scored[:n]]
    except Exception:  # noqa: BLE001
        return None


def thumbs(st, run: str, verdict: str, skill: str | None, why: str) -> str:
    """O6: the owner's one-keystroke rating. `thumbs RUN up|down [SKILL]` writes an owner rating (--by user) with
    topic 5 or 0, for every chosen pick of the run or for one skill. Only owner ratings count as evidence."""
    rows = st.rows()
    row = (next((r for r in reversed(rows) if r.get("kind") == "SCORE"), None) if run == "last"
           else next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == run), None))
    if row is None:
        return f"RUN_UNKNOWN: no score run {run!r}"
    targets = [skill] if skill else list(row.get("chosen", []))
    score = 5 if verdict == "up" else 0
    t = int(time.time())
    M_ = _maestro()
    stale = []
    for n in targets:
        ss = M_.subject_state(rows, row["run"], n)          # v17: a rating on a changed subject is marked, never hidden
        if ss and ss["stale"]:
            stale.append(n)
        st.append({"kind": "RATE", "run": row["run"], "skill": n, "by": "user", "scores": {"topic": score},
                   "rating": "useful" if score >= 3 else "unused", "why": why or f"thumbs {verdict}", "t": t, "via": "thumbs",
                   "stale": bool(ss and ss["stale"])})
    out = f"THUMBS {verdict.upper()} by the owner on run {row['run']}: {', '.join(targets)} (topic {score}); this counts as evidence"
    if stale:
        out += f"\nSTALE: the subject changed after the TRY for {', '.join(stale)}; the rating speaks about an older file"
    return out


HOOK_SNIPPET = {
    "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
              "command": "python \"%USERPROFILE%\\.claude\\skills\\skill-maestro\\maestro.py\" whisper --stdin --no-ledger"}]}]}}


def render_whisper(prompt: str, names: list[str], secs: float) -> str:
    if not names:
        return f"WHISPER: nothing shares a word with \"{prompt[:60]}\""
    size = f"{len(names)} by task size"
    return (f"WHISPER ({secs:.2f}s, {size}): " + ", ".join(f"/{n}" for n in names)
            + "   (by meaning and purpose, then words; `score` for the judged sheet)")


# --- play ------------------------------------------------------------------------------------------------------------

def play(lib, st, root: Path, task: str, subject: Path | None, concepts: str | None, top: int | None,
         workers: int = 2, timeout: int = 120, log=print) -> dict:
    M_ = _maestro()
    C = M_._load(HERE / "conduct.py", "conduct")        # v20: conduct is an extra; a core install stops here, before the score
    vocab = M_.load_vocab()
    used_concepts = concepts or concepts_text(task, vocab)
    if not used_concepts:
        used_concepts = "world: (none suggested; the task shares no word with the vocabulary)"
    log(f"PLAY 1/4 concepts: {used_concepts[:160]}")
    sheet = M_.score(lib, st, task, top, False, (), used_concepts)
    chosen = sheet["chosen"]
    log(f"PLAY 2/4 score run {sheet['run']}: {len(chosen)} picks from {sheet['pool']}: " + ", ".join(c["name"] for c in chosen))
    cards = M_.load_cards()
    steps = [C.step_of(c["name"], lib, cards) for c in chosen]
    sk = C.guess_kind(task) or "TEXT"
    order = C.order_steps(steps, sk)
    log("PLAY 3/4 chain: " + C.render_chain(sheet["run"], steps, order, sk, subject).splitlines()[0])
    rows, noprobe, judged = [], [s["name"] for s in steps], []
    if subject is not None:
        row = {"run": sheet["run"], "chosen": [c["name"] for c in chosen], "task": task}
        rows, noprobe = C.rehearse(row, lib, cards, subject, st, workers=workers, timeout=timeout)
        for r in rows:
            verdict = ("CRASH" if r["exit"] < 0 else "ERROR" if r["exit"] else "QUIET" if r["lines"] == 0
                       else "ECHO" if r.get("echo", 0) > 0.8 else "SPOKE")
            judged.append({**r, "verdict": verdict})
        log(f"PLAY 4/4 rehearsal on {subject.name}: {len(rows)} probe(s) ran, {len(noprobe)} pick(s) have no probe")
    else:
        log("PLAY 4/4 no --subject: nothing ran; pass the real file to rehearse the picks on it")
    return {"run": sheet["run"], "task": task, "concepts": used_concepts, "chosen": [c["name"] for c in chosen],
            "order": order, "subject_kind": sk, "judged": judged, "noprobe": noprobe, "sheet": sheet}


def render_play(p: dict) -> str:
    L = [f"PLAY {p['run']}: \"{p['task'][:70]}\" -> {len(p['chosen'])} picks [ORGANIZED, not VERIFIED]"]
    L.append("  concepts: " + p["concepts"][:150])
    for i, n in enumerate(p["chosen"], 1):
        j = next((x for x in p["judged"] if x["skill"] == n), None)
        if j:
            L.append(f"  {i}. {n:<28} {j['verdict']:<6} exit {j['exit']} {j['lines']} line(s) {j['secs']}s  {j['first'][:60]}")
        else:
            L.append(f"  {i}. {n:<28} {'no probe' if n in p['noprobe'] else 'not run'}")
    spoke = [x["skill"] for x in p["judged"] if x["verdict"] == "SPOKE"]
    L.append("  spoke on the subject: " + (", ".join(spoke) or "none") + "; read those SKILL.md files, then "
             f"`maestro.py fit {p['run']} <skill> works|misfit \"why\"` for each pick that ran")
    L.append(f"  NEXT: `maestro.py chain {p['run']} --subject FILE` for the ordered pipeline; `ponder {p['run']}`; "
             f"`rate {p['run']} <skill> useful|unused|wrong` when the work is done")
    return "\n".join(L)


# --- brief -----------------------------------------------------------------------------------------------------------

def brief_for(lib, st, run_row: dict, cards: dict, subject: str | None) -> str:
    M_ = _maestro()
    C = M_._load(HERE / "conduct.py", "conduct")
    task = run_row.get("task") or f"(task sha {run_row.get('task_sha')})"
    ctx = (run_row.get("session_ctx") or "").strip()        # v17 (prompt-master: the memory block in the first 30%)
    L = [f"SUBAGENT BRIEF for Maestro run {run_row['run']}",
         f"TASK: {task}"]
    if ctx:
        L.append(f"CONTEXT (the owner's prompts just before this one; carry them forward): {ctx[:400]}")
    L += [f"SUBJECT: {subject or '(name the exact file or section before starting)'}",
          "YOU MAY READ: the subject, and the SKILL.md of each pick below. Nothing else unless a pick's command needs it.",
          "PICKS (run each on the subject; judge it on the task, not the exit code):"]
    effects = []
    for n in run_row.get("chosen", []):
        s = C.step_of(n, lib, cards)
        cmd = (" ".join(C.fill(s["probe_t"], s["skill_dir"], subject or "{subject}")) if s.get("probe_t")
               else f"invoke /{n} (no script)")
        L.append(f"  - {n}: {cmd[:120]}")
        md = lib.md.get(n)
        if md is not None:
            se = sorted(set(M_.side_effects(lib.desc.get(n, ""))) | set(M_.script_side_effects(md.parent, st.d)))
            if se:
                effects.append(f"{n} can {', '.join(se)}")
    L.append("REPORT, one line per pick: WORKS | MISFIT | NOT RUN, then why in ten words, then the one number or line it produced.")
    L.append(f"RECORD: python maestro.py fit {run_row['run']} <skill> kind=yes|no question=yes|no assumes=yes|no used=yes|no \"why\""
             "   (the parent session rates later)")
    L.append("DO NOT: rate anything useful (only the owner can), write outside the scratch folder, or read picks that misfit."
             + (f" Do not let these run unasked: {'; '.join(effects)}." if effects else ""))
    return "\n".join(L)


# --- cli -------------------------------------------------------------------------------------------------------------

def _val(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def _pos(argv: list[str], valued=("--subject", "--concepts", "--top", "--days", "--workers", "--timeout", "--state",
                                   "--root", "--project")) -> list[str]:
    out, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
            continue
        if a in valued:
            skip = True
            continue
        if not a.startswith("--"):
            out.append(a)
    return out


def cli(argv: list[str], lib, st, root: Path) -> int:
    """argv starts with the command name."""
    M_ = _maestro()
    sub = argv[0]
    pos = _pos(argv)
    if sub == "suggest":
        task = " ".join(pos)
        vocab = M_.load_vocab()
        print(render_suggest(task, suggest(task, vocab), len(vocab)))
        return 0
    if sub == "digest":
        if not pos:
            print("DIGEST needs a skill name")
            return 2
        for name in pos:
            p = lib.md.get(name)
            if not p or not p.is_file():
                print(f"DIGEST {name}: not in this library (built-ins have no file; read builtins.json)")
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            print("\n".join(digest(text)) + f"\nCOST full read ~{M_.tokens_of(text)} tokens; this digest ~{M_.tokens_of(chr(10).join(digest(text)))}")
        return 0
    if sub == "doctor":
        checks = doctor(lib, st, root)
        print(render_doctor(checks))
        return 0 if all(c["ok"] for c in checks) else 1
    if sub == "welcome":
        print(welcome(lib, st))
        return 0
    if sub == "grade":
        g = grade(st.rows(), int(_val(argv, "--days", 30)))
        print(json.dumps(g, indent=1) if "--json" in argv else render_grade(g))
        return 0
    if sub == "matrix":
        dials = (HERE / "maestro_dials.md").read_text(encoding="utf-8")
        ch = sorted((HERE / "references").glob("CHARTER_*.md"))
        charter = ch[-1].read_text(encoding="utf-8") if ch else ""
        mx = matrix(lib, M_.load_mechanisms(), dials, charter)
        print(json.dumps(mx, indent=1) if "--json" in argv else render_matrix(mx))
        return 0
    if sub == "whisper":
        if "--hook" in argv:
            print(json.dumps(HOOK_SNIPPET, indent=1))
            print("Paste the hooks block into ~/.claude/settings.json to hear a whisper at every prompt. It is OFF "
                  "until you do. Preflight: python ~/.claude/skills/hook-preflight/hook_preflight.py (if installed).")
            return 0
        prompt = sys.stdin.read() if "--stdin" in argv else " ".join(pos)
        try:
            prompt = json.loads(prompt).get("prompt", prompt) if prompt.strip().startswith("{") else prompt
        except ValueError:
            pass
        t0 = time.time()
        names = whisper(lib, prompt)
        print(render_whisper(prompt, names, time.time() - t0))
        return 0
    if sub == "play":
        task = " ".join(pos)
        if not task:
            print("PLAY needs a task: maestro.py play \"<task>\" --subject FILE")
            return 2
        subj = _val(argv, "--subject")
        if subj and not Path(subj).is_file():
            print(f"PLAY_REFUSED: --subject {subj} is not a file (name the real thing the task is about)")
            return 2
        top = int(_val(argv, "--top")) if _val(argv, "--top") else None
        p = play(lib, st, root, task, Path(subj) if subj else None, _val(argv, "--concepts"), top,
                 workers=int(_val(argv, "--workers", 2)), timeout=int(_val(argv, "--timeout", 120)))
        print(render_play(p))
        st.append({"kind": "PLAY", "run": p["run"], "t": int(time.time()), "subject": subj,
                   "judged": [{k: v for k, v in j.items() if k in ("skill", "verdict", "exit", "lines")} for j in p["judged"]]})
        return 0
    if sub == "thumbs":
        if len(pos) < 2 or pos[1] not in ("up", "down"):
            print("THUMBS needs: maestro.py thumbs RUN|last up|down [SKILL] [\"why\"]")
            return 2
        skill = pos[2] if len(pos) > 2 and " " not in pos[2] else None
        why = " ".join(pos[3:] if skill else pos[2:])
        print(thumbs(st, pos[0], pos[1], skill, why))
        return 0
    if sub == "brief":
        run = pos[0] if pos else "last"
        rows = st.rows()
        row = (next((r for r in reversed(rows) if r.get("kind") == "SCORE"), None) if run == "last"
               else next((r for r in rows if r.get("kind") == "SCORE" and r.get("run") == run), None))
        if row is None:
            print(f"RUN_UNKNOWN: no score run {run!r}")
            return 3
        print(brief_for(lib, st, row, M_.load_cards(), _val(argv, "--subject")))
        return 0
    print(__doc__)
    return 2


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    ok: dict[str, bool] = {}
    vocab = {"rank": "order items by a score", "partition": "split a whole into non-overlapping parts or kinds",
             "verify": "check a claim against evidence", "decay": "weight by age so older counts less"}
    s = suggest("rank the plan cards by score and split them into kinds", vocab)
    ok["suggest: name hit beats meaning hit; a tag sharing nothing is absent"] = \
        s and s[0][0] == "rank" and "partition" in [t for t, _, _ in s] and "decay" not in [t for t, _, _ in s]
    ok["suggest: empty on a task with no shared word"] = suggest("zzz qqq", vocab) == []
    ok["suggest: a name hit outranks a bare meaning hit even when the meaning is one word"] = \
        suggest("rank these", {"rank": "order items", "tally": "rank"})[0][0] == "rank"
    md2 = "---\nname: d\ndescription: x. Use this.\n---\n```\npython d.py go\n```\n```\npython d.py go\n```\n"
    ok["digest: the same command in two blocks is shown once"] = sum(1 for x in digest(md2) if x.startswith("RUN")) == 1
    ok["concepts_text is parseable --concepts"] = concepts_text("rank the cards", vocab).startswith("rank: ")
    md = ("---\nname: demo\ndescription: Count the lines of a file quickly. Use this whenever Max asks for a count.\n---\n"
          "# demo\n\n## How\n\n```\npython demo.py count FILE\npython demo.py --selftest\n```\n\n## Notes\nSelftest 4/4 PASS.\n")
    d = digest(md)
    ok["digest: name, first sentence, the Use sentence, heading, command, test count"] = \
        d[0] == "NAME demo" and d[1].startswith("DOES Count the lines") and d[2].startswith("WHEN Use this") \
        and any(x.startswith("PART How") for x in d) and any("python demo.py count FILE" in x for x in d) \
        and any(x.startswith("TEST 4/4") for x in d) and len(d) <= 10
    ok["digest: never paraphrases (every DOES/WHEN/RUN line is in the file)"] = all(
        x.split(" ", 1)[1].strip() in md for x in d if x.split(" ", 1)[0] in ("DOES", "WHEN", "RUN"))
    now = 1_800_000_000
    rows = [{"kind": "SCORE", "run": "a", "t": now - 100, "chosen": ["x"]},
            {"kind": "TRIAGE", "t": now - 90, "verdict": "SKIP"},
            {"kind": "FIT", "run": "a", "skill": "x", "verdict": "works", "t": now - 80},
            {"kind": "SCORE", "run": "b", "t": now - 50 * 86400, "chosen": ["y"]},   # outside 30 days
            {"kind": "RATE", "run": "a", "skill": "x", "rating": "useful", "by": "max", "t": now - 70},
            {"kind": "SHEET_COST", "run": "a", "sheet": 400, "read": 3000, "t": now - 95},
            {"kind": "EVAL", "t": now - 60, "probes": "probes_heldout.tsv", "maestro@3": "13/58", "maestro@1": "8/58"}]
    g = grade(rows, 30, now=now)
    ok["grade: windows by days, counts works, owner ratings, cost, debt zero when rated"] = \
        g["runs"] == 1 and g["works"] == 1 and g["owner_useful"] == 1 and g["sheet_tokens"] == 400 and g["debt"] == 0 \
        and g["triage"] == {"SKIP": 1} and g["eval_last"]["maestro@3"] == "13/58"
    g2 = grade([{"kind": "SCORE", "run": "c", "t": now, "chosen": ["z"]}], 30, now=now)
    ok["grade: an unrated run is debt; verdict names the idle evidence"] = g2["debt"] == 1 and "IDLE" in render_grade(g2)
    dl = dial_rows("| M01 | margin | 0.15 | yes | fit-first |\n| M02 | pool | 40 | no | held-out 13/58 |\nnot a row\n")
    ok["dial rows parse: id, locked flag, meaning"] = len(dl) == 2 and dl[0]["locked"] and not dl[1]["locked"] \
        and dl[1]["meaning"] == "held-out 13/58"
    ok["brief/suggest cli positional parsing drops valued flags"] = \
        _pos(["play", "do", "the", "thing", "--subject", "F.md", "--top", "3"]) == ["do", "the", "thing"]
    ok["render_whisper: empty says nothing shares a word"] = "nothing shares" in render_whisper("x", [], 0.0) \
        and "/alpha" in render_whisper("x", ["alpha"], 0.01) and "1 by task size" in render_whisper("x", ["alpha"], 0.01)
    _sc = [{"name": "a", "score": 4.0}, {"name": "b", "score": 3.0}, {"name": "c", "score": 1.0}]
    ok["whisper_count: a short ask gets 1, a long one gets 2 per sentence capped by candidates within reach"] = (
        whisper_count("fix it", _sc)[0] == 1
        and whisper_count("Audit the plan for gaps. Then list every risk. Then write the fixes.", _sc)[0] == 2
        and whisper_count("Audit the plan for gaps. Then list every risk. Then write the fixes.",
                          _sc + [{"name": "d", "score": 3.5}] * 5)[0] == 6
        and whisper_count("Audit the plan for gaps. Then list every risk.", [])[0] == 1)
    ok["render_doctor: a failing check prints a numbered fix and no READY"] = (
        "1. do this" in render_doctor([{"name": "n", "ok": False, "found": "f", "fix": "do this"}])
        and "READY" not in render_doctor([{"name": "n", "ok": False, "found": "f", "fix": "do this"}])
        and "READY" in render_doctor([{"name": "n", "ok": True, "found": "f", "fix": ""}]))
    bad = [k for k, v in ok.items() if not v]
    print(f"concert selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
