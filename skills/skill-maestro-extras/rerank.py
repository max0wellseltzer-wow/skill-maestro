"""rerank.py - O1: a learned judge over the 40-pool (v16 experiment; OFF until dial M40 says on and a model exists).

The finder puts the right skill in the 40-pool 46 of 58 times but in the top 3 only 12-13 times (2026-10-22). The gap
is the judge. This module learns, from the hindsight labels (what Claude really reached for after a real prompt), how
to order the pool: a logistic model over per-candidate features that are FAIR by construction (no use counts, no
description length, no source; only how each reading ranked the skill for this task, the fused fit, whether it has a
tool, and task words shared with its name and description).

    python maestro.py rerank train --split YYYY-MM-DD [--epochs N] [--l2 X] [--write]
        train on labelled prompts before the split, judge on prompts after it AND on the held-out set, never on train;
        prints base vs reranked top-1 / top-3 per set and McNemar on the paired top-3 vectors; --write saves the model
        to <state>/rerank_model.json (the only way a model gets used; without --write nothing changes).
    python maestro.py rerank eval            judge the saved model again on every set (same report)
    python maestro.py rerank status          the saved model: features, weights, when, on which sets it was judged
    python maestro.py rerank off             delete the saved model (the dial stays; nothing else changes)

Walk-forward, unseen sets, McNemar: a model that moves top-3 on train only is reported as such and not written.
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _core_dir() -> Path:
    """v20: this module ships in skill-maestro-extras; maestro.py is beside it, at MAESTRO_HOME, or in the sibling skill-maestro."""
    env = os.environ.get("MAESTRO_HOME")
    for d in (HERE, Path(env).expanduser() if env else None, HERE.parent / "skill-maestro"):
        if d is not None and (d / "maestro.py").is_file():
            return d
    return HERE

M = None
MODEL = "rerank_model.json"


def _maestro():
    global M
    main = sys.modules.get("__main__")                     # v20: the running maestro.py, when there is one
    if M is None and main is not None and Path(getattr(main, "__file__", "") or "").name == "maestro.py":
        M = main
    if M is None:
        spec = importlib.util.spec_from_file_location("maestro", _core_dir() / "maestro.py")
        M = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(M)
    return M


# --- readings per task ----------------------------------------------------------------------------------------------

def pool_readings(lib, task: str, depth: int = 120) -> dict[str, list[str]]:
    """Every reading's ranked names for one task, as fused() builds them (same weights, same depth)."""
    M_ = _maestro()
    task_r = M_.ranking_text(task)
    out: dict[str, list[str]] = {}
    partial: dict[str, float] = {}
    for vname, q in lib.variants(task_r).items():
        if vname.startswith("_") or not M_.WEIGHTS.get(vname, 1.0):
            continue
        names = [r["name"] for r in lib.search(q, depth)]
        out[vname] = names
        w = M_.WEIGHTS.get(vname, 1.0)
        for rank, n in enumerate(names, 1):
            partial[n] = partial.get(n, 0.0) + w / (M_.RRF_K + rank)
    if M_.WEIGHTS.get("body"):
        out["body"] = lib.body(task_r, depth)
    for extra in ("family", "ncd", "owner", "asks", "meaning", "personal", "mode"):   # v19: every weighted reading fused() runs
        fn = getattr(lib, extra + "_reading", None)
        if M_.WEIGHTS.get(extra) and fn:
            try:
                names = fn(task_r, depth)
            except Exception:  # noqa: BLE001 - a reading that cannot run (no venv, no vectors) ranks nothing
                names = None
            out[extra] = list(names or [])            # always present: the feature set must be the same for every prompt
    if M_.WEIGHTS.get("network") and partial:
        seeds = sorted(partial.items(), key=lambda x: (-x[1], x[0]))[:M_.NET_SEEDS]
        out["network"] = lib.network(seeds)[:depth]
    return out


FEATURES_FIXED = ("fit", "tool", "pin", "shared_name", "shared_desc", "n_readings", "pos")


def feature_names(readings: dict[str, list[str]]) -> list[str]:
    return [f"r_{k}" for k in sorted(readings)] + list(FEATURES_FIXED)


def features(lib, task: str, pool: list[dict], readings: dict[str, list[str]], names: list[str]) -> list[list[float]]:
    """One row per pool candidate, in the pool's order. Reading features are 60/(60+rank) (0 when absent), so a
    rank-1 skill scores ~1 and a rank-120 one ~0.33; fit is fused score over the pool's best."""
    M_ = _maestro()
    toks = lib.fs._tokens
    words = set(toks(lib.variants(task)["_plain"]))
    top = pool[0]["score"] if pool and pool[0].get("score") else 1.0
    pos_of = {k: {n: i + 1 for i, n in enumerate(v)} for k, v in readings.items()}
    rows = []
    for i, c in enumerate(pool):
        n = c["name"]
        desc_t = set(toks(lib.desc.get(n, "")))
        name_t = set(toks(n))
        f = {}
        for k in readings:
            r = pos_of[k].get(n)
            f[f"r_{k}"] = (M_.RRF_K / (M_.RRF_K + r)) if r else 0.0
        f["fit"] = (c.get("score", 0.0) / top) if top else 0.0
        f["tool"] = 1.0 if c.get("tool") else 0.0
        f["pin"] = 1.0 if c.get("pin") else 0.0
        f["shared_name"] = 1.0 if words & name_t else 0.0
        f["shared_desc"] = min(1.0, len(words & desc_t) / 4.0)
        f["n_readings"] = len(c.get("via_q", [])) / max(1, len(readings))
        f["pos"] = 1.0 - i / max(1, len(pool))
        rows.append([f.get(k, 0.0) for k in names])
    return rows


# --- the model -----------------------------------------------------------------------------------------------------

def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def train_logistic(X: list[list[float]], y: list[int], groups: list[int], epochs: int = 200, lr: float = 0.05,
                   l2: float = 0.01, seed: int = 7) -> tuple[list[float], float]:
    """Plain SGD logistic regression. Positives are up-weighted by the class ratio so 50 positives among 2000 rows
    are not ignored. `groups` (the prompt index per row) is used only to shuffle by prompt."""
    if not X:
        return [], 0.0
    d = len(X[0])
    w, b = [0.0] * d, 0.0
    pos = sum(y)
    wpos = (len(y) - pos) / pos if pos else 1.0
    rnd = random.Random(seed)
    order = list(range(len(X)))
    for _ in range(epochs):
        rnd.shuffle(order)
        for i in order:
            p = sigmoid(sum(wi * xi for wi, xi in zip(w, X[i])) + b)
            g = (p - y[i]) * (wpos if y[i] else 1.0)
            for j in range(d):
                w[j] -= lr * (g * X[i][j] + l2 * w[j])
            b -= lr * g
    return w, b


def score_rows(w: list[float], b: float, X: list[list[float]]) -> list[float]:
    return [sigmoid(sum(wi * xi for wi, xi in zip(w, x)) + b) for x in X]


# --- datasets --------------------------------------------------------------------------------------------------------

def read_probes(path: Path) -> list[tuple[str, set[str]]]:
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.startswith("#") and "\t" in ln:
            p, ok = ln.split("\t", 1)
            out.append((p, {x.strip() for x in ok.split(",") if x.strip()}))
    return out


def fit_labels(rows: list[dict]) -> list[dict]:
    """v17 (typesafe-ai's truth table): every FIT recorded with its four judgments is a label for the task of its run:
    `works` picks are positives. Shaped like hindsight rows ({ts, text, used}) so train/test split by date applies.
    Only structured FITs count (the old works|misfit word carries no per-question record)."""
    tasks = {r["run"]: r for r in rows if r.get("kind") == "SCORE" and r.get("task")}
    good: dict[str, set] = {}
    when: dict[str, int] = {}
    for r in rows:
        if r.get("kind") == "FIT" and r.get("judgments") and r.get("verdict") == "works" and r.get("run") in tasks:
            good.setdefault(r["run"], set()).add(r["skill"])
            when[r["run"]] = max(when.get(r["run"], 0), int(r.get("t", 0)))
    out = []
    for run, skills in good.items():
        out.append({"ts": time.strftime("%Y-%m-%d %H:%M", time.gmtime(when[run])), "text": tasks[run]["task"],
                    "used": sorted(skills), "source": "fit"})
    return out


def build_set(lib, probes: list[tuple[str, set[str]]], log=None) -> list[dict]:
    """Per prompt: the pool (fused, as evaluate() takes it), its readings, feature rows, labels, the base top-3."""
    M_ = _maestro()
    out = []
    for i, (prompt, good) in enumerate(probes):
        pool = lib.fused(prompt)[:M_.POOL]
        rd = pool_readings(lib, prompt)
        names = feature_names(rd)
        X = features(lib, prompt, pool, rd, names)
        y = [1 if c["name"] in good else 0 for c in pool]
        out.append({"prompt": prompt, "good": sorted(good), "pool": [c["name"] for c in pool], "X": X, "y": y,
                    "names": names})
        if log and (i + 1) % 20 == 0:
            log(f"  featurized {i + 1}/{len(probes)}")
    return out


def judge(items: list[dict], w: list[float], b: float, names: list[str], k: int = 3) -> dict:
    """Base (pool order, which is the fused order select() starts from) vs reranked, top-1 and top-k, paired vectors."""
    base1 = base3 = re1 = re3 = 0
    vb, vr = [], []
    for it in items:
        good = set(it["good"])
        X = []
        for r in it["X"]:                                   # the item's own feature order -> the model's order
            d = dict(zip(it["names"], r))
            X.append([d.get(n, 0.0) for n in names])
        p = score_rows(w, b, X)
        order = sorted(range(len(it["pool"])), key=lambda i: (-p[i], i))
        re_top = [it["pool"][i] for i in order[:k]]
        base_top = it["pool"][:k]
        hb, hr = bool(good & set(base_top)), bool(good & set(re_top))
        base1 += bool(base_top[:1] and base_top[0] in good)
        re1 += bool(re_top[:1] and re_top[0] in good)
        base3 += hb
        re3 += hr
        vb.append(int(hb))
        vr.append(int(hr))
    M_ = _maestro()
    mc = M_.mcnemar(vb, vr) if items else {"ok": False, "why": "empty"}
    n = len(items)
    return {"n": n, "base@1": base1, "rerank@1": re1, "base@3": base3, "rerank@3": re3, "mcnemar": mc,
            "pool_has": sum(1 for it in items if set(it["good"]) & set(it["pool"]))}


def render(res: dict, sets: dict[str, dict], names: list[str], w: list[float]) -> str:
    L = [f"RERANK (logistic over {len(names)} fair features; trained on {res['train_n']} prompts before {res['split']})"]
    for label, r in sets.items():
        mc = r["mcnemar"]
        L.append(f"  {label:<8} n {r['n']:>3}  top-1 {r['base@1']:>2} -> {r['rerank@1']:>2}   top-3 {r['base@3']:>2} -> {r['rerank@3']:>2}"
                 f"   (pool has it {r['pool_has']})   McNemar " + (f"p {mc['p']} {mc['verdict']}" if mc.get("ok") else mc.get("why", "")))
    top = sorted(zip(names, w), key=lambda kv: -abs(kv[1]))[:6]
    L.append("  weights: " + ", ".join(f"{n} {v:+.2f}" for n, v in top))
    L.append(f"  verdict: {res['verdict']}")
    return "\n".join(L)


def decide(sets: dict[str, dict]) -> str:
    unseen = [r for k, r in sets.items() if k != "train" and r.get("n")]   # an empty set judges nothing
    if not unseen:
        return "NO UNSEEN SET: not written"
    if any(r["rerank@3"] < r["base@3"] for r in unseen):
        return "FALLS on an unseen set: not written"
    if all(r["rerank@3"] == r["base@3"] for r in unseen):
        return "LEVEL on every unseen set: not written (nothing gained)"
    sig = [r for r in unseen if r["mcnemar"].get("verdict") == "DIFFERENT"]
    return ("RISES on every unseen set" + (", DISTINGUISHABLE on " + str(len(sig)) if sig else ", within noise (McNemar)")
            + ": may be written with --write")


# --- cli -------------------------------------------------------------------------------------------------------------

def _val(argv, flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def _vals_(argv, flag) -> list[str]:
    """Every value given after a repeatable flag (`--test A --test B`)."""
    return [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == flag and not argv[i + 1].startswith("--")]


def cli(argv: list[str], lib, st, root: Path) -> int:
    M_ = _maestro()
    sub = argv[1] if len(argv) > 1 else "status"
    model_p = Path(st.d) / MODEL
    if sub == "off":
        if model_p.is_file():
            model_p.unlink()
            print(f"REMOVED {model_p}; the pool order is the fused order again")
        else:
            print("no saved model")
        return 0
    if sub == "status":
        if not model_p.is_file():
            print("RERANK: no saved model (train with `rerank train --split DATE`, then --write if it rises on unseen sets)")
            return 0
        m = json.loads(model_p.read_text(encoding="utf-8"))
        print(json.dumps({k: v for k, v in m.items() if k != "w"}, indent=1))
        print("weights: " + ", ".join(f"{n} {v:+.2f}" for n, v in zip(m["names"], m["w"])))
        return 0
    H = M_._load(HERE / "hindsight.py", "hindsight")
    rows = H.rows_of(Path(st.d))
    lab = H.labels(rows)
    fitlab = fit_labels(st.rows())                        # v17: judged candidates (structured FIT) are labels too
    lab = lab + fitlab
    held = M_.companion(root, "probes_heldout.tsv")
    if sub == "train":
        split = _val(argv, "--split")
        if not split or not lab:
            print("TRAIN needs --split YYYY-MM-DD and the hindsight cache (`hindsight build`)")
            return 2
        tr = [(r["text"], set(r["used"])) for r in lab if r["ts"][:10] < split]
        te = [(r["text"], set(r["used"])) for r in lab if r["ts"][:10] >= split]
        dev_held = "--dev-heldout" in argv and held.is_file()   # v19: the 58 hand labels join the training side (a dev set)
        n_dev = 0
        if dev_held:
            dev = read_probes(held)
            tr, n_dev = tr + dev, len(dev)
        print(f"  train {len(tr)} labelled prompts before {split}" + (f" (incl. the {n_dev} held-out hand labels as a dev set; "
              "they judge nothing below)" if dev_held else "") + f"; test {len(te)} after; held-out "
              f"{held.name if held.is_file() and not dev_held else 'none'}"
              f"  (labels: hindsight {len(lab) - len(fitlab)}, structured FIT {len(fitlab)}; "
              f"label skills in all {sum(len(r['used']) for r in lab)}; the in-pool positive count prints per set below)")
        t0 = time.time()
        S = {"train": build_set(lib, tr, log=print), "test": build_set(lib, te, log=print)}
        if held.is_file() and not dev_held:
            S["heldout"] = build_set(lib, read_probes(held), log=print)
        for extra in _vals_(argv, "--test"):                   # v19: more unseen answer keys (never trained on)
            p = Path(extra)
            if p.is_file():
                S[p.stem[:14]] = build_set(lib, read_probes(p), log=print)
        print(f"  featurized in {time.time() - t0:.0f}s")
        names = S["train"][0]["names"] if S["train"] else []
        X = [r for it in S["train"] for r in it["X"]]
        y = [v for it in S["train"] for v in it["y"]]
        g = [i for i, it in enumerate(S["train"]) for _ in it["X"]]
        w, b = train_logistic(X, y, g, epochs=int(_val(argv, "--epochs", 200)), l2=float(_val(argv, "--l2", 0.01)))
        sets = {k: judge(v, w, b, names) for k, v in S.items()}
        res = {"split": split, "train_n": len(tr), "verdict": decide(sets)}
        print(render(res, sets, names, w))
        st.append({"kind": "RERANK", "t": int(time.time()), "split": split, "dev_heldout": dev_held, "n_dev": n_dev,
                   "features": names, "sets": {k: {kk: vv for kk, vv in v.items() if kk != "mcnemar"} for k, v in sets.items()},
                   "verdict": res["verdict"], "code": __import__("hashlib").sha256(Path(HERE / "rerank.py").read_bytes()).hexdigest()[:12]})
        if "--write" in argv:
            if "not written" in res["verdict"]:
                print("REFUSED --write: " + res["verdict"])
                return 1
            model_p.write_text(json.dumps({"names": names, "w": w, "b": b, "split": split, "train_n": len(tr),
                                           "written": time.strftime("%Y-%m-%d %H:%M"), "sets": {k: {kk: vv for kk, vv in v.items() if kk != "mcnemar"} for k, v in sets.items()}}),
                               encoding="utf-8")
            print(f"WROTE {model_p}  (dial M40 rerank must be 'on' for score/eval to use it)")
        return 0
    if sub == "eval":
        if not model_p.is_file():
            print("no saved model")
            return 2
        m = json.loads(model_p.read_text(encoding="utf-8"))
        S = {"all_labels": build_set(lib, [(r["text"], set(r["used"])) for r in lab], log=print)}
        if held.is_file():
            S["heldout"] = build_set(lib, read_probes(held), log=print)
        sets = {k: judge(v, m["w"], m["b"], m["names"]) for k, v in S.items()}
        print(render({"split": m["split"], "train_n": m["train_n"], "verdict": decide(sets)}, sets, m["names"], m["w"]))
        return 0
    print(__doc__)
    return 2


def rerank_pool(lib, task: str, pool: list[dict], st_dir: Path) -> list[dict]:
    """Used by maestro.py when RERANK is on and a model exists: reorder the pool by the model; membership unchanged,
    each row keeps its fused score and gains 'rerank' (the probability). Any failure returns the pool untouched."""
    try:
        p = Path(st_dir) / MODEL
        if not p.is_file() or not pool:
            return pool
        m = json.loads(p.read_text(encoding="utf-8"))
        rd = pool_readings(lib, task)
        names = m["names"]
        X = features(lib, task, pool, rd, names)
        pr = score_rows(m["w"], m["b"], X)
        order = sorted(range(len(pool)), key=lambda i: (-pr[i], i))
        return [{**pool[i], "rerank": round(pr[i], 3)} for i in order]
    except Exception:  # noqa: BLE001
        return pool


# --- selftest --------------------------------------------------------------------------------------------------------

def _selftest() -> bool:
    ok: dict[str, bool] = {}
    rnd = random.Random(3)
    X, y, g = [], [], []
    for i in range(300):                       # planted world: feature 1 decides, feature 0 is noise
        a, b_ = rnd.random(), rnd.random()
        X.append([a, b_])
        y.append(1 if b_ > 0.7 else 0)
        g.append(i)
    w, b = train_logistic(X, y, g, epochs=60)
    ok["logistic learns the planted feature (w1 >> w0)"] = w[1] > 2.0 and abs(w[0]) < w[1] / 3
    ok["sigmoid is bounded and monotone"] = 0 < sigmoid(-100) < sigmoid(0) < sigmoid(100) < 1
    items = [{"prompt": "p", "good": ["b"], "pool": ["a", "b", "c", "d"], "names": ["f"],
              "X": [[0.1], [0.9], [0.2], [0.3]], "y": [0, 1, 0, 0]}]
    r = judge(items, [5.0], 0.0, ["f"], k=1)
    ok["judge: base top-1 misses, rerank top-1 hits"] = r["base@1"] == 0 and r["rerank@1"] == 1 and r["pool_has"] == 1
    ok["decide: falls on unseen -> not written; rises -> may be written; level -> nothing gained"] = (
        "not written" in decide({"train": {"n": 9, "base@3": 1, "rerank@3": 5, "mcnemar": {}}, "test": {"n": 9, "base@3": 5, "rerank@3": 4, "mcnemar": {}}})
        and "may be written" in decide({"test": {"n": 9, "base@3": 4, "rerank@3": 6, "mcnemar": {"verdict": "NOT DISTINGUISHABLE"}}})
        and "nothing gained" in decide({"test": {"n": 9, "base@3": 4, "rerank@3": 4, "mcnemar": {}}})
        and "NO UNSEEN" in decide({"test": {"n": 0, "base@3": 0, "rerank@3": 0, "mcnemar": {}}}))
    ok["no model -> pool untouched"] = rerank_pool(None, "t", [{"name": "x"}], Path("Z:/nowhere")) == [{"name": "x"}]
    ok["feature names: readings sorted then the fixed ones"] = feature_names({"raw": [], "body": []})[:2] == ["r_body", "r_raw"] \
        and feature_names({})[-1] == "pos"
    bad = [k for k, v in ok.items() if not v]
    print(f"rerank selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
