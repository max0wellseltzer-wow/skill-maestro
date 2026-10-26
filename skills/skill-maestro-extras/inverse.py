"""inverse - the Maestro's opposite function (v15, 2026-10-22).

The Maestro reads a task and finds skills (task -> skills). Its mirror image reads a skill and finds tasks, and reads
the library and finds what it can and cannot play:

    python maestro.py inverse <skill> [--k 8]
        skill -> what it is for (its meaning line), the real prompts after which Claude reached for it (hindsight),
        the prompts the Maestro would have handed it to and Claude did not use it (should-have-served), the prompts
        it was used on where the Maestro's pool never held it (found BLIND), its rating record and antibodies, its
        best synthetic query, and a verdict: ALIVE (used in the last 30 days), DORMANT (used before, not lately),
        NEVER-USED.
    python maestro.py repertoire [--kind K]
        library -> what it can play: per operation (cards/vocab.json) how many skills, how many tool-backed, how many
        ever used, how many rated useful -> STRONG / THIN / UNTESTED; per task kind, how many labelled real prompts we
        have and the skills used for them; and WHAT WE WILL NOT LEARN: kinds with no labelled prompt, operations with
        no skill (seeds for skill-foundry), skills used but never carded.
    python maestro.py anti "<task>"
        the un-pick: the skills rated wrong or found misfit on tasks like this one (the antibodies), so a judge sees
        what to avoid as plainly as what to try.
    python inverse.py --selftest

Everything here reads: the ledger, the hindsight cache, the cards. Nothing is written.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _core_dir() -> Path:
    """v20: this module ships in skill-maestro-extras; maestro.py is beside it, at MAESTRO_HOME, or in the sibling skill-maestro."""
    env = os.environ.get("MAESTRO_HOME")
    for d in (HERE, Path(env).expanduser() if env else None, HERE.parent / "skill-maestro"):
        if d is not None and (d / "maestro.py").is_file():
            return d
    return HERE

sys.path.insert(0, str(HERE))


def _maestro():
    main = sys.modules.get("__main__")
    if main is not None and Path(getattr(main, "__file__", "") or "").name == "maestro.py":
        return main
    if str(_core_dir()) not in sys.path:
        sys.path.insert(0, str(_core_dir()))
    import maestro
    return maestro


M = _maestro()


def _hindsight():
    try:
        return M._load(HERE / "hindsight.py", "hindsight")
    except Exception:  # noqa: BLE001
        return None


def days_since(ts: str, now: float | None = None) -> float | None:
    try:
        t = time.mktime(time.strptime(ts[:16], "%Y-%m-%d %H:%M"))
        return ((now or time.time()) - t) / 86400.0
    except (ValueError, TypeError):
        return None


def inverse(lib, st, rows: list[dict], skill: str, k: int = 8, top: int = 3, now: float | None = None) -> dict:
    """rows: the hindsight cache rows (may be empty)."""
    H = _hindsight()
    lab = H.labels(rows) if (H and rows) else []
    served = sorted([r for r in lab if skill in r["used"]], key=lambda r: r["ts"], reverse=True)
    should, blind = [], []
    for r in lab:
        if len(should) + len(blind) > 400:            # a cap: this is a mirror, not an audit
            break
        pool = lib.fused(r["text"][:1500])[:M.POOL]
        names = [c["name"] for c in pool]
        chosen = [c["name"] for c in M.select(M.weigh(pool, {}, set()), top, lib.family)[0]] if pool else []
        if skill in r["used"] and skill not in names:
            blind.append(r)
        elif skill in chosen and skill not in r["used"]:
            should.append(r)
    record = st.stats().get(skill, {})
    anti = [(w, rating) for w, s, rating in st.memory() if s == skill and rating == "wrong"]
    intents = None                                   # v20: intents.json left the package
    mech = M.load_mechanisms().get(skill, {})
    last = served[0]["ts"] if served else None
    age = days_since(last, now) if last else None
    verdict = "NEVER-USED" if not served else "ALIVE" if age is not None and age <= 30 else "DORMANT"
    return {"skill": skill, "known": skill in lib.desc, "desc": lib.desc.get(skill, ""), "mech": mech,
            "served": served[:k], "n_served": len(served), "should": should[:k], "n_should": len(should),
            "blind": blind[:k], "n_blind": len(blind), "record": record, "antibodies": anti[:k], "intent": intents,
            "family": lib.family(skill), "neighbours": sorted(lib.graph().get(skill, set()))[:8],
            "verdict": verdict, "last_used": last, "has_cache": bool(rows)}


def render_inverse(a: dict) -> str:
    if not a["known"]:
        return f"INVERSE: {a['skill']} is not a skill in this library"
    L = [f"INVERSE {a['skill']} [{a['verdict']}" + (f", last used {a['last_used']}" if a["last_used"] else "") + "]"]
    L.append(f"  for: {a['desc'].split('. ')[0][:150]}")
    if a["mech"]:
        L.append(f"  does: {a['mech'].get('does', '')[:140]}  tags: {', '.join(a['mech'].get('tags', []))}")
    L.append(f"  family {a['family']}; pairs with: {', '.join(a['neighbours']) or 'nobody'}")
    if not a["has_cache"]:
        L.append("  (no hindsight cache: `maestro.py hindsight build` fills served / should-have-served / blind)")
    L.append(f"  SERVED {a['n_served']} real prompt(s) (Claude reached for it afterwards):")
    for r in a["served"]:
        L.append(f"    {r['ts']}  {r['excerpt'][:90]}")
    L.append(f"  SHOULD HAVE SERVED {a['n_should']} (the Maestro would have handed it the prompt; Claude did not use it):")
    for r in a["should"]:
        L.append(f"    {r['ts']}  {r['excerpt'][:90]}")
    L.append(f"  FOUND BLIND {a['n_blind']} (used, but the Maestro's pool never held it: its text lacks those asks' words):")
    for r in a["blind"]:
        L.append(f"    {r['ts']}  {r['excerpt'][:90]}")
    rec = ", ".join(f"{k} {v}" for k, v in a["record"].items()) or "no ratings"
    L.append(f"  RECORD: {rec}" + (f"; antibodies on {len(a['antibodies'])} task(s)" if a["antibodies"] else ""))
    if a["intent"]:
        L.append(f"  a user might ask: \"{a['intent'][:100]}\"")
    L.append("  READ IT AS: SHOULD-HAVE-SERVED is the Maestro's claim against the record (maybe the skill was not needed, "
             "maybe it was missed); FOUND BLIND is the record's claim against the Maestro (fix with `hindsight propose`).")
    return "\n".join(L)


def repertoire(lib, st, rows: list[dict], mechs: dict, vocab: dict) -> dict:
    H = _hindsight()
    lab = H.labels(rows) if (H and rows) else []
    used = Counter(u for r in lab for u in r["used"])
    useful = {s for s, rec in st.stats().items() if rec.get("useful", 0) > 0}
    ops = []
    for tag, desc in vocab.items():
        members = [n for n, m in mechs.items() if tag in m.get("tags", []) and n in lib.desc]
        tools = sum(1 for n in members if next((s.get("tool") for s in lib.skills if s["name"] == n), False))
        ever = sum(1 for n in members if used.get(n))
        rated = sum(1 for n in members if n in useful)
        strength = ("NONE" if not members else "UNTESTED" if not ever and not rated
                    else "THIN" if (ever + rated) < 2 or len(members) < 3 else "STRONG")
        ops.append({"op": tag, "desc": desc, "skills": len(members), "tools": tools, "used": ever, "useful": rated,
                    "strength": strength})
    kinds = {}
    for r in lab:
        k = M.task_kinds(r["text"])[0][0]
        kinds.setdefault(k, {"prompts": 0, "used": Counter()})
        kinds[k]["prompts"] += 1
        kinds[k]["used"].update(r["used"])
    all_kinds = list(M.TASK_KINDS) + ["ANALYZE"]
    unlearnable_kinds = [k for k in all_kinds if k not in kinds]
    uncarded_used = sorted(u for u in used if u not in mechs and u in lib.desc)
    return {"ops": ops, "kinds": {k: {"prompts": v["prompts"], "used": v["used"].most_common(5)} for k, v in kinds.items()},
            "no_prompt_kinds": unlearnable_kinds, "no_skill_ops": [o["op"] for o in ops if o["strength"] == "NONE"],
            "untested_ops": [o["op"] for o in ops if o["strength"] == "UNTESTED"],
            "uncarded_used": uncarded_used, "labelled": len(lab), "has_cache": bool(rows)}


def render_repertoire(r: dict) -> str:
    L = [f"REPERTOIRE: what this library can play ({len(r['ops'])} operations; {r['labelled']} labelled real prompts"
         + ("" if r["has_cache"] else "; no hindsight cache, so 'used' is zero everywhere") + ")"]
    L.append(f"  {'operation':<22} {'skills':>6} {'tools':>5} {'used':>4} {'useful':>6}  strength")
    for o in sorted(r["ops"], key=lambda o: (-o["skills"], o["op"])):
        L.append(f"  {o['op']:<22} {o['skills']:>6} {o['tools']:>5} {o['used']:>4} {o['useful']:>6}  {o['strength']}")
    if r["kinds"]:
        L.append("  BY TASK KIND (labelled prompts; the skills used most):")
        for k, v in sorted(r["kinds"].items(), key=lambda kv: -kv[1]["prompts"]):
            L.append(f"    {k:<12} {v['prompts']:>4}  " + ", ".join(f"{s} ({c})" for s, c in v["used"]))
    L.append("  WHAT WE WILL NOT LEARN (from this record, as it stands):")
    L.append("    kinds with no labelled prompt: " + (", ".join(r["no_prompt_kinds"]) or "none"))
    L.append("    operations with no skill (skill-foundry seeds): " + (", ".join(r["no_skill_ops"]) or "none"))
    L.append("    operations whose skills were never used nor rated: " + (", ".join(r["untested_ops"][:12]) or "none"))
    L.append("    skills used but never carded (the meaning reading cannot see them): " + (", ".join(r["uncarded_used"][:12]) or "none"))
    return "\n".join(L)


def anti(st, words: set, k: int = 8) -> list[tuple[str, float, str]]:
    """The antibodies for this task: skills rated wrong or found misfit on similar past tasks, by similarity."""
    out = {}
    for w, skill, rating in st.memory():
        if rating != "wrong":
            continue
        sim = M.jaccard(w, words)
        if sim >= M.MEMORY_SIM and sim > out.get(skill, (0.0, ""))[0]:
            out[skill] = (sim, " ".join(sorted(w))[:60])
    return sorted(((s, sim, t) for s, (sim, t) in out.items()), key=lambda x: -x[1])[:k]


def render_anti(rows: list, task: str) -> str:
    if not rows:
        return f"ANTI: no antibody for a task like \"{task[:60]}\" (no skill was rated wrong or found misfit on a similar one)"
    L = [f"ANTI (skills to avoid on a task like \"{task[:60]}\"):"]
    for s, sim, t in rows:
        L.append(f"  {s:<28} sim {sim:.2f}  was wrong on: {t}")
    return "\n".join(L)


# --- command line ----------------------------------------------------------------------------------------------------

def _val(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def cli(argv: list[str], lib, st, root: Path) -> int:
    sub = argv[0]
    H = _hindsight()
    rows = H.rows_of(Path(st.d)) if H else []
    if sub == "inverse":
        pos = [a for a in argv[1:] if not a.startswith("--") and a != _val(argv, "--k")]
        if not pos:
            print("INVERSE needs a skill: maestro.py inverse <skill>")
            return 2
        a = inverse(lib, st, rows, pos[0], k=int(_val(argv, "--k", 8)))
        print(json.dumps(a, indent=1, default=list) if "--json" in argv else render_inverse(a))
        return 0
    if sub == "repertoire":
        r = repertoire(lib, st, rows, M.load_mechanisms(), M.load_vocab())
        print(json.dumps(r, indent=1, default=list) if "--json" in argv else render_repertoire(r))
        return 0
    if sub == "anti":
        task = " ".join(a for a in argv[1:] if not a.startswith("--"))
        words = set(lib.fs._tokens(lib.variants(task)["_plain"])) if task else set()
        print(render_anti(anti(st, words), task))
        return 0
    print(__doc__)
    return 2


# --- selftest --------------------------------------------------------------------------------------------------------

@contextlib.contextmanager
def _words_only():
    """v19: the selftest's three-skill library ranks by WORDS alone. 'blind' means the skill's words never reach the
    prompt; with the meaning, personal and mode readings on, a three-skill library puts every skill in every pool (and
    each run embedded the temp library into the shared state folder: 25 stray vector files on 2026-10-24)."""
    saved = dict(M.WEIGHTS)
    M.WEIGHTS.update({"meaning": 0.0, "personal": 0.0, "mode": 0.0, "phase": 0.0})
    try:
        yield
    finally:
        M.WEIGHTS.clear()
        M.WEIGHTS.update(saved)


def _selftest() -> bool:
    import tempfile
    ok: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td_, _words_only():
        td = Path(td_)
        root = td / "skills"
        for name, desc in [("hysteresis", "Two-threshold latch that stops a flapping alert. Use this whenever an alert flaps."),
                           ("plain-terms", "Rewrite a report in plain words. Use this whenever the user wants plain language."),
                           ("lindy", "Age predicts remaining life. Use this whenever the user asks how long a thing will last.")]:
            (root / name).mkdir(parents=True)
            (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n", encoding="utf-8")
        lib = M.Library(root, everything=False)
        st = M.State(td / "state")
        st.append({"kind": "SCORE", "run": "r1", "t": 1, "words": ["alert", "flapping", "noise"], "chosen": ["lindy"]})
        st.append({"kind": "RATE", "run": "r1", "skill": "lindy", "rating": "wrong", "t": 2})
        st.append({"kind": "RATE", "run": "r1", "skill": "hysteresis", "rating": "useful", "t": 3})
        now = time.mktime(time.strptime("2026-10-22 10:00", "%Y-%m-%d %H:%M"))
        rows = [{"ts": "2026-10-20 10:00", "session": "a", "file": "f", "words": ["alert", "flapping", "stop", "beeper", "minute"],
                 "used": ["hysteresis"], "sweep": False, "excerpt": "stop my beeper alert from flapping every minute",
                 "text": "stop my beeper alert from flapping every minute"},
                {"ts": "2026-09-01 10:00", "session": "a", "file": "f", "words": ["alert", "flapping", "plain", "words", "explain"],
                 "used": ["plain-terms"], "sweep": False, "excerpt": "explain the flapping alert in plain words",
                 "text": "explain the flapping alert in plain words"},
                {"ts": "2026-10-21 10:00", "session": "a", "file": "f", "words": ["lindy", "effect", "lasting", "ages", "things"],
                 "used": ["hysteresis"], "sweep": False, "excerpt": "which things last by the lindy effect",
                 "text": "which things last by the lindy effect"}]
        a = inverse(lib, st, rows, "hysteresis", now=now)
        ok["served: the prompts after which the skill was reached for, newest first"] = \
            a["n_served"] == 2 and a["served"][0]["ts"].startswith("2026-10-21")
        ok["blind: used on a prompt whose words never reach it"] = a["n_blind"] == 1 and "lindy" in a["blind"][0]["text"]
        ok["should-have-served: the Maestro would pick it, Claude used another"] = \
            a["n_should"] == 1 and "plain words" in a["should"][0]["text"]
        ok["verdict ALIVE within 30 days; record from the ledger"] = a["verdict"] == "ALIVE" and a["record"].get("useful") == 1
        ok["DORMANT after 30 days; NEVER-USED when no prompt served"] = \
            inverse(lib, st, rows, "plain-terms", now=now)["verdict"] == "DORMANT" and \
            inverse(lib, st, rows, "lindy", now=now)["verdict"] == "NEVER-USED"
        txt = render_inverse(a)
        ok["render names the three lists and the verdict"] = "SERVED 2" in txt and "FOUND BLIND 1" in txt and "ALIVE" in txt
        mechs = {"hysteresis": {"does": "latch", "tags": ["threshold-latch"]}, "lindy": {"does": "age", "tags": ["forecast"]}}
        vocab = {"threshold-latch": "trigger or hold state", "forecast": "predict", "name-coin": "invent names"}
        r = repertoire(lib, st, rows, mechs, vocab)
        by = {o["op"]: o for o in r["ops"]}
        ok["repertoire: strength per operation from use and ratings"] = \
            by["threshold-latch"]["used"] == 1 and by["threshold-latch"]["strength"] == "THIN" and \
            by["forecast"]["strength"] == "UNTESTED" and by["name-coin"]["strength"] == "NONE"
        ok["repertoire: what we will not learn names the empty operation and the uncarded used skill"] = \
            "name-coin" in r["no_skill_ops"] and "plain-terms" in r["uncarded_used"] and len(r["no_prompt_kinds"]) >= 1
        ok["repertoire renders"] = "WHAT WE WILL NOT LEARN" in render_repertoire(r)
        an = anti(st, {"alert", "flapping", "stop"})
        ok["anti: the skill rated wrong on a similar task, not the useful one"] = \
            [s for s, _, _ in an] == ["lindy"]
        ok["anti renders an empty case plainly"] = "no antibody" in render_anti([], "zzz")
    ok = {k: bool(v) for k, v in ok.items()}
    print(f"inverse selftest: {sum(ok.values())}/{len(ok)} " + ("PASS" if all(ok.values()) else "FAIL"))
    for k, v in ok.items():
        if not v:
            print(f"  FAIL {k}")
    return all(ok.values())


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(M.main(sys.argv[1:]))
