"""Your own Maestro (the user, 2026-10-24: "give people the option to not send their preferences and build their own
personal custom /skill maestro that changes based on their ratings").

Every copy of the Maestro already keeps its history on its own machine (state/ledger.jsonl and state/hindsight.jsonl).
This module turns that history into a PERSONAL reading, so each person's Maestro drifts toward what works for them:

  - what you rated: useful/favourite pull a skill up on prompts like the one it was rated on, wrong pushes it down,
    unused a little; a FIT works pulls up, a misfit pushes down (your Claude's verdicts count half);
  - what you actually used: every skill that was really invoked after one of your past prompts (hindsight) counts as
    a small vote for that skill on prompts that MEAN the same thing (the meaning model compares prompts, not words).

Nothing here leaves the machine. PRIVATE MODE (`maestro.py private on`) also stops `share` from writing a file at
all; private is the default until you turn sharing on. Other people's ratings (`intake`) never enter your personal
reading: it learns from you alone.

    maestro.py personal                 what your Maestro has learned: your top skills, your pick-count habit
    maestro.py personal eval            walk-forward test: learn from prompts before a date, test on the ones after
    maestro.py private on|off|status
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

RATE_W = {"useful": 2.0, "favourite": 2.5, "fascinating": 1.0, "wrong": -2.0, "unused": -0.5}
FIT_W = {"works": 1.0, "misfit": -1.0}
USED_W = 1.0
NEIGHBOURS, MIN_SIM = 15, 0.62


def privacy_path(state: Path) -> Path:
    return Path(state) / "privacy.json"


def is_private(state: Path) -> bool:
    try:
        return json.loads(privacy_path(state).read_text(encoding="utf-8")).get("private", True)
    except (OSError, ValueError):
        return True                                   # the default: nothing is shared until the person says so


def set_private(state: Path, on: bool) -> None:
    privacy_path(state).parent.mkdir(parents=True, exist_ok=True)
    privacy_path(state).write_text(json.dumps({"private": on, "t": int(time.time())}), encoding="utf-8")


def _ts(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return time.mktime(time.strptime(str(s)[:16], "%Y-%m-%d %H:%M"))
    except ValueError:
        return 0.0


def examples(state: Path, ledger_rows: list[dict], before: float | None = None) -> list[dict]:
    """[{text, t, votes: {skill: weight}}] from this person's own history only (community rows are skipped)."""
    out = []
    hp = Path(state) / "hindsight.jsonl"
    if hp.is_file():
        from phase import (
            rows_of,  # v20.0.18: the turn view (a mid-turn ask folded into its turn)
        )
        for r in rows_of(Path(state)):
            used = set(r.get("used") or []) | set(r.get("observed") or [])
            used.discard("skill-maestro") if r.get("maestro") else None
            if used and r.get("text"):
                out.append({"text": r["text"][:1500], "t": _ts(r.get("ts")), "votes": {s: USED_W for s in used}, "src": "used"})
    runs: dict[str, dict] = {}
    for r in ledger_rows:
        if r.get("community_from"):
            continue
        k = r.get("kind")
        if k == "SCORE" and r.get("task"):
            runs.setdefault(r["run"], {"text": r["task"][:1500], "t": float(r.get("t", 0)), "votes": {}, "src": "rated"})
        elif k == "RATE" and r.get("run") in runs and r.get("skill"):
            w = RATE_W.get(r.get("rating"), 0.0) * (1.0 if r.get("by") in ("user", "max", "owner") else 0.5)
            v = runs[r["run"]]["votes"]
            v[r["skill"]] = v.get(r["skill"], 0.0) + w
        elif k == "FIT" and r.get("run") in runs and r.get("skill"):
            w = FIT_W.get(r.get("verdict"), 0.0) * 0.5
            v = runs[r["run"]]["votes"]
            v[r["skill"]] = v.get(r["skill"], 0.0) + w
    out += [x for x in runs.values() if x["votes"]]
    if before is not None:
        out = [x for x in out if x["t"] < before]
    return out


def _vectors(meaning, texts: list[str], state: Path):
    """Prompt vectors, cached by text in state/personal_vectors.npz (only new prompts are embedded)."""
    try:
        import numpy as np
    except ImportError as exc:                            # v20: reading() returns [] before this; the plain-words error for a direct caller
        raise RuntimeError("personal.py needs numpy (pip install numpy, or the maestro-meaning venv)") from exc
    p = Path(state) / "personal_vectors.npz"
    cache: dict[str, np.ndarray] = {}
    if p.is_file():
        with np.load(p, allow_pickle=False) as z:          # closed at once: Windows cannot replace an open file
            cache = {str(k): v for k, v in zip(z["keys"], z["vecs"])}
    keys = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
    if missing:
        vs = meaning.embed_queries([t for _, t in missing])
        for (k, _), v in zip(missing, vs):
            cache[k] = v
        if os.environ.get("MAESTRO_NO_LEDGER") == "1":       # v20.1.6: --no-ledger writes nothing, this cache included
            return np.array([cache[k] for k in keys], dtype=np.float32)
        tmp = p.with_name(p.stem + ".tmp.npz")
        np.savez_compressed(tmp, keys=np.array(list(cache)), vecs=np.array(list(cache.values()), dtype=np.float32))
        tmp.replace(p)
    return np.array([cache[k] for k in keys], dtype=np.float32) if keys else np.zeros((0, 384), dtype=np.float32)


def reading(meaning, task: str, exs: list[dict], state: Path, k: int = 120, exclude_text: str | None = None) -> list[tuple[str, float]]:
    """Skills ranked by what this person used and rated on prompts that mean what `task` means."""
    try:
        import numpy as np
    except ImportError:                                   # v20: no numpy means no meaning model here: nothing learned
        return []
    exs = [e for e in exs if e["text"] != (exclude_text or task)]       # never learn a prompt from itself
    if not exs:
        return []
    ev = _vectors(meaning, [e["text"] for e in exs], state)
    q = meaning.embed_queries([task])[0]
    sims = ev @ q
    idx = [i for i in np.argsort(-sims)[:NEIGHBOURS] if sims[i] >= MIN_SIM]
    sc: dict[str, float] = {}
    for i in idx:
        for s, w in exs[i]["votes"].items():
            sc[s] = sc.get(s, 0.0) + float(sims[i]) ** 2 * w
    return sorted(((s, round(v, 4)) for s, v in sc.items() if v > 0), key=lambda x: -x[1])[:k]


def profile(ledger_rows: list[dict]) -> dict:
    """The person's pick-count habit: of the skills the Maestro chose, how many they rated unused, and how many skills
    their Claude added that the sheet never named. Scale > 1 means give this person more picks, < 1 fewer."""
    chosen = unused = added = 0
    runs = {}
    for r in ledger_rows:
        if r.get("community_from"):
            continue
        if r.get("kind") == "SCORE":
            ch = r.get("chosen") or []
            runs[r.get("run")] = set(ch) if isinstance(ch, list) else set()
            chosen += len(runs[r.get("run")])
        elif r.get("kind") == "RATE" and r.get("rating") == "unused":
            unused += 1
        elif r.get("kind") in ("FIT", "TRY") and r.get("run") in runs and r.get("skill") not in runs[r.get("run")]:
            added += 1
    scale = 1.0
    if chosen >= 20:
        scale = max(0.5, min(1.5, 1.0 - 0.5 * unused / chosen + 0.5 * added / chosen))
    return {"chosen": chosen, "rated_unused": unused, "added_by_judge": added, "pick_scale": round(scale, 2)}


def report(meaning, state: Path, rows: list[dict]) -> str:
    exs = examples(state, rows)
    votes: dict[str, float] = {}
    for e in exs:
        for s, w in e["votes"].items():
            votes[s] = votes.get(s, 0.0) + w
    top = sorted(votes.items(), key=lambda x: -x[1])[:12]
    low = sorted((x for x in votes.items() if x[1] < 0), key=lambda x: x[1])[:6]
    p = profile(rows)
    L = [(f"YOUR MAESTRO learns from {len(exs)} of your past prompts ({sum(1 for e in exs if e['src'] == 'used')} where skills were really used, "
          f"{sum(1 for e in exs if e['src'] == 'rated')} rated runs). Private: {'yes, nothing is shared' if is_private(state) else 'no, `share` may write a file'}."),
         "  most useful to you: " + ", ".join(f"{s} ({v:+.1f})" for s, v in top),
         "  pushed down for you: " + (", ".join(f"{s} ({v:+.1f})" for s, v in low) or "none yet"),
         f"  pick count: {p['chosen']} picks shown, {p['rated_unused']} rated unused, {p['added_by_judge']} added by your Claude -> scale {p['pick_scale']}"]
    return "\n".join(L)


def eval_walkforward(meaning, words, state: Path, rows: list[dict], probes: list[tuple[str, set]], cut: float,
                     w_personal: float = 2.0) -> dict:
    """Learn from history before `cut`, test on probes (prompts after it): meaning+words vs meaning+words+personal."""
    exs = examples(state, rows, before=cut)
    mean = meaning.rank([q for q, _ in probes], 120)
    res = {"n": len(probes), "examples": len(exs), "base": {"@1": 0, "@3": 0, "pool40": 0}, "personal": {"@1": 0, "@3": 0, "pool40": 0}}
    for (q, good), m in zip(probes, mean):
        w = words(q, 120)
        base = meaning.fuse([[n for n, _ in m], w], [3.0, 1.0])
        per = [n for n, _ in reading(meaning, q, exs, state)]
        mixed = meaning.fuse([[n for n, _ in m], w, per], [3.0, 1.0, w_personal])
        for name, lst in (("base", base), ("personal", mixed)):
            res[name]["@1"] += bool(good & set(lst[:1]))
            res[name]["@3"] += bool(good & set(lst[:3]))
            res[name]["pool40"] += bool(good & set(lst[:40]))
    return res


def _selftest() -> bool:
    import tempfile
    ok = {}
    with tempfile.TemporaryDirectory() as td:
        st = Path(td)
        ok["private is the default"] = is_private(st)
        set_private(st, False)
        ok["private off is remembered"] = not is_private(st)
        (st / "hindsight.jsonl").write_text(json.dumps({"text": "chart my equity curve", "ts": "2026-10-01 10:00",
                                                        "used": ["dataviz"], "observed": []}) + "\n", encoding="utf-8")
        rows = [{"kind": "SCORE", "run": "r1", "task": "fix the flaky test", "t": 5, "chosen": ["a", "b"]},
                {"kind": "RATE", "run": "r1", "skill": "a", "rating": "useful", "by": "user"},
                {"kind": "RATE", "run": "r1", "skill": "b", "rating": "wrong", "by": "user"},
                {"kind": "RATE", "run": "x:r9", "skill": "z", "rating": "useful", "by": "user", "community_from": "abc"}]
        ex = examples(st, rows)
        ok["examples: used skills and own ratings, never other people's"] = (
            len(ex) == 2 and any(e["votes"].get("dataviz") == 1.0 for e in ex)
            and any(e["votes"].get("a") == 2.0 and e["votes"].get("b") == -2.0 for e in ex)
            and not any("z" in e["votes"] for e in ex))
        ok["examples: a cut date keeps only the earlier history"] = len(examples(st, rows, before=_ts("2026-09-01 00:00"))) == 1
        ok["profile: no scale until 20 picks"] = profile(rows)["pick_scale"] == 1.0
    bad = [k for k, v in ok.items() if not v]
    print(f"personal selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
