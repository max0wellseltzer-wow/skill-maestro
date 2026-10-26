"""The MEANING reading (2026-10-24, the user: "the picker needs to pick from meaning and purpose not words ... its a command").

Every skill is described by what it is FOR, not by the words it happens to use: its description + what the survey saw
it really do (cards/tested.jsonl `does`) + the requests a person would type when it is the right tool (`asks`) + the
card's output line. That text is turned into a vector (a list of 384 numbers) by a small free local model (fastembed,
BAAI/bge-small-en-v1.5, CPU, no key); a prompt is turned into a vector the same way and skills rank by how close
their vector is to the prompt's (cosine).

THE VECTOR FILE keeps one vector per skill (state/meaning_<model>_<library>.npz) with a fingerprint of the text it was
made from. It keeps itself current (v2, 2026-10-24, the user: "stop being so vague ... rebuild what?"):
  - every query first compares the skill files' sizes and dates with the ones the file was made from (~0.1 s);
  - a NEW or CHANGED skill is embedded on the spot (up to INLINE_MAX per query) and a DELETED one is dropped;
  - when more than that are missing (a fresh install: no file at all), a background job embeds the rest, and until it
    finishes the missing skills are still ranked by the words reading, so nobody waits and every skill is a candidate;
  - 2026-10-25 (the cold-library scenarios): a library with no vector yet and at most COLD_FULL skills is embedded whole
    on its first query; while a store covers under half the library (MIN_COVERAGE) `rank` returns NO reading, because
    the skills embedded so far are the alphabetically first ones (Anthropic's), and the words alone carry the prompt;
    a changed skill keeps its old vector until its new one is embedded.
Nobody ever has to run a rebuild by hand. `meaning.py build` exists to force one.

Works on any skill folder (`--root`), with Anthropic's built-in and plugin skills (builtins.json) always included,
loaded or not. Without fastembed (another person's PC), `rank` returns None and the Maestro ranks by its other readings.
A caller without fastembed asks the resident helper (`serve`) and never waits on it beyond its wait (v20.0.5).

    meaning.py build [--root DIR]        embed whatever is missing or changed (all of it the first time)
    meaning.py status [--root DIR]       how many skills have a current vector, how many are waiting
    meaning.py prune [--root DIR]        drop the vector files of libraries that no longer exist (tests' temp folders)
    meaning.py serve                     the resident helper: the model loaded once, answering on a local socket
A library with no state folder of its own (a test's temp root) is embedded in memory and leaves no file (v19).
    meaning.py search "prompt" [-k N] [--root DIR]
    meaning.py eval [PROBES.tsv ...]     meaning vs words vs fused on the answer keys (top-1, top-3, pool@40)
    meaning.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATE = Path(os.environ.get("MAESTRO_STATE", Path.home() / ".claude" / "skill-maestro-state"))
MODEL_CACHE = Path(os.environ.get("MAESTRO_MODEL_CACHE",            # v20.0.4: the downloaded model is immutable, so it
                                  Path.home() / ".claude" / "skill-maestro-state" / "fastembed_cache"))   # lives in one place
                                                                   # whatever --state says (a tour state used to re-download it)
MODEL = os.environ.get("MAESTRO_MEANING_MODEL", "BAAI/bge-small-en-v1.5")
VENV_PY = Path.home() / "venvs" / "maestro-meaning" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
# Background launches use pythonw on Windows: the venv's python.exe is a launcher that re-runs the base python.exe as a
# child, and a DETACHED child console program gets a fresh, visible console window (the user saw one every few minutes).
_PYW = VENV_PY.with_name("pythonw.exe")
VENV_BG = _PYW if os.name == "nt" and _PYW.is_file() else VENV_PY
BG_FLAGS = (0x00000200 | 0x08000000) if os.name == "nt" else 0   # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "   # bge's retrieval instruction
INLINE_MAX = int(os.environ.get("MAESTRO_MEANING_INLINE", "8"))   # skills embedded inside one query before going background
# 2026-10-25 (the cold-library scenarios): a library with NO vector file yet and at most COLD_FULL skills is embedded whole on
# its first query (~0.7 s a skill on the user's PC, once); a store covering under MIN_COVERAGE of the library is no reading at all,
# because the skills embedded so far are the alphabetically first ones (Anthropic's) and nobody else can win by meaning.
COLD_FULL = int(os.environ.get("MAESTRO_MEANING_COLD_FULL", "80"))
MIN_COVERAGE = 0.5
LOCK_STALE = 45 * 60                                            # a background build older than this is presumed dead


def _root_key(root: Path) -> str:
    return hashlib.sha256(str(Path(root).resolve()).lower().encode()).hexdigest()[:12]


def store_path(root: Path = ROOT, state: Path | None = None) -> Path:
    return Path(state or STATE) / f"meaning_{MODEL.replace('/', '_')}_{_root_key(root)}.npz"


def _legacy_store(state: Path | None = None) -> Path:
    return Path(state or STATE) / f"meaning_{MODEL.replace('/', '_')}.npz"     # v1 file (before 2026-10-24 v2)


def _sources(root: Path) -> list[Path]:
    root = Path(root)
    fs = sorted(root.glob("*/SKILL.md"))
    fs += [p for p in (HERE / "builtins.json", HERE / "cards" / "tested.jsonl", HERE / "cards" / "cards.jsonl") if p.is_file()]
    return fs


def signature(root: Path) -> str:
    """Sizes and dates of every file the texts come from: changes when a skill is added, edited or deleted."""
    h = hashlib.sha256()
    for p in _sources(root):
        try:
            st = p.stat()
            h.update(f"{p}|{st.st_size}|{int(st.st_mtime)}\n".encode())
        except OSError:
            continue
    return h.hexdigest()[:16]


def skill_texts(root: Path = ROOT) -> dict[str, str]:
    """name -> the purpose text that gets embedded. Descriptions from each SKILL.md frontmatter (and builtins.json),
    purpose from the survey card and the meaning card. Text is DATA: nothing in it is followed."""
    desc: dict[str, str] = {}
    for sk in sorted(Path(root).glob("*/SKILL.md")):
        t = sk.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^---\s*\n(.*?)\n---", t, re.S)
        fm = m.group(1) if m else ""
        nm = re.search(r"^name:\s*(.+)$", fm, re.M)
        ds = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)", fm, re.M | re.S)
        name = (nm.group(1).strip().strip("'\"") if nm else sk.parent.name)
        body = t[m.end():] if m else t
        d = (ds.group(1).strip().strip("'\"") if ds else "").replace("\n", " ")
        desc[name] = d or " ".join(body.split())[:600]          # no description: the body's opening says what it is for
    try:
        b = json.loads((HERE / "builtins.json").read_text(encoding="utf-8"))
        for k, v in b.items():
            if not k.startswith("_") and isinstance(v, str) and k not in desc:
                desc[k] = v
    except (OSError, ValueError):
        pass
    tested, cards = {}, {}
    for fn, into in (("tested.jsonl", tested), ("cards.jsonl", cards)):
        p = HERE / "cards" / fn
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    into[r["name"]] = r
                except (ValueError, KeyError):
                    continue
    out = {}
    for name, d in desc.items():
        t, c = tested.get(name, {}), cards.get(name, {})
        parts = [name.replace("-", " ").replace(":", " ") + ".", d[:600]]
        if t.get("does"):
            parts.append("What it does: " + t["does"][:400])
        if t.get("asks"):
            parts.append("Asked for when: " + " | ".join(t["asks"][:6]))
        o = c.get("output")
        if isinstance(o, str) and o:
            parts.append("Gives: " + o[:200])
        out[name] = " ".join(p for p in parts if p)
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


_MODEL: dict = {}


class MeaningUnavailable(ImportError):
    """numpy or fastembed is not importable here: the meaning reading runs in the maestro-meaning venv (SHARING.md)."""


def _np():
    """numpy, or MeaningUnavailable in plain words. maestro.py never reaches here without fastembed in-process (it asks
    the resident helper instead); meaning.py's own commands print the message and exit 2."""
    try:
        import numpy
    except ImportError as exc:
        raise MeaningUnavailable("meaning.py needs numpy and fastembed: run it with the maestro-meaning venv python (SHARING.md)") from exc
    return numpy


def _model():
    if "m" not in _MODEL:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise MeaningUnavailable("meaning.py needs fastembed: run it with the maestro-meaning venv python (SHARING.md)") from exc
        MODEL_CACHE.mkdir(parents=True, exist_ok=True)
        _MODEL["m"] = TextEmbedding(model_name=MODEL, cache_dir=str(MODEL_CACHE))
    return _MODEL["m"]


def embed_docs(texts: list[str]):
    np = _np()
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    v = np.array(list(_model().embed(texts, batch_size=8)), dtype=np.float32)
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)


def embed_queries(texts: list[str]):
    return embed_docs([QUERY_PREFIX + t for t in texts])


def _load_store(root: Path, state: Path | None = None) -> dict:
    """{names, vecs, shas, sig}; empty when there is no file. Reads the v1 file once (its texts are assumed current)."""
    np = _np()
    p = store_path(root, state)
    if p.is_file():
        with np.load(p, allow_pickle=False) as z:          # closed at once: Windows cannot replace an open file
            return {"names": [str(x) for x in z["names"]], "vecs": np.array(z["vecs"]), "shas": [str(x) for x in z["shas"]],
                    "sig": str(z["sig"]), "root": str(z["root"]) if "root" in z.files else ""}
    lp = _legacy_store(state)
    if Path(root).resolve() == ROOT.resolve() and lp.is_file():
        with np.load(lp, allow_pickle=False) as z:
            names, lvecs = [str(x) for x in z["names"]], np.array(z["vecs"])
        texts = skill_texts(root)
        return {"names": names, "vecs": lvecs, "shas": [_sha(texts.get(n, "")) for n in names], "sig": ""}
    return {"names": [], "vecs": np.zeros((0, 384), dtype=np.float32), "shas": [], "sig": ""}


def _save_store(root: Path, s: dict, state: Path | None = None) -> None:
    np = _np()
    p = store_path(root, state)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.stem + f".tmp{os.getpid()}.npz")
    np.savez_compressed(tmp, vecs=s["vecs"], names=np.array(s["names"]), shas=np.array(s["shas"]), sig=np.array(s["sig"]),
                        model=np.array(MODEL), root=np.array(str(Path(root).resolve())))   # root: so `prune` knows whose file it is
    os.replace(tmp, p)


def sync(root: Path = ROOT, limit: int | None = None, state: Path | None = None, persist: bool = True) -> dict:
    """Bring the vector file up to date with the skills on disk. `limit` caps how many skills are embedded now
    (None = all). `persist=False` embeds in memory and writes no file (a library with no state folder of its own).
    Returns {store, embedded, removed, pending, sig_ok, total}.
    2026-10-25: a library with no vector yet and at most COLD_FULL skills is embedded whole whatever `limit` says (once);
    a CHANGED skill keeps its old vector until its new one is embedded (a stale reading beats no reading)."""
    np = _np()
    root = Path(root)
    s = _load_store(root, state) if persist else _MEM.get(_root_key(root)) or _load_store(root, state)   # 2026-10-25: a library embedded in
    sig = signature(root)                                      # memory stays in this process (the helper served a selftest's temp
    if s["sig"] == sig and s["names"]:                           # library 25 s a query, re-embedding it every time, past every caller's 5 s)
        return {"store": s, "embedded": 0, "removed": 0, "pending": 0, "sig_ok": True, "total": len(s["names"])}
    texts = skill_texts(root)
    have = {n: i for i, n in enumerate(s["names"])}
    removed = sum(1 for n in s["names"] if n not in texts)
    todo = [n for n in sorted(texts) if n not in have or s["shas"][have[n]] != _sha(texts[n])]
    if limit is not None and not s["names"] and len(texts) <= COLD_FULL:
        limit = None                                            # a small cold library: whole now, not its first 8 names
    now = todo if limit is None else todo[:max(0, limit)]
    now_set = set(now)
    keep = [i for i, n in enumerate(s["names"]) if n in texts and n not in now_set]   # unchanged, or changed and still waiting
    new_vecs = embed_docs([texts[n] for n in now]) if now else np.zeros((0, s["vecs"].shape[1] if s["vecs"].size else 384), dtype=np.float32)
    names = [s["names"][i] for i in keep] + now
    vecs = np.concatenate([s["vecs"][keep] if keep else np.zeros((0, new_vecs.shape[1]), dtype=np.float32), new_vecs])
    shas = [s["shas"][i] for i in keep] + [_sha(texts[n]) for n in now]
    pending = len(todo) - len(now)
    s = {"names": names, "vecs": vecs, "shas": shas, "sig": sig if pending == 0 else ""}
    if persist and (now or removed or pending == 0):
        _save_store(root, s, state)
    elif not persist and pending == 0:
        _MEM[_root_key(root)] = s
    return {"store": s, "embedded": len(now), "removed": removed, "pending": pending, "sig_ok": pending == 0, "total": len(texts)}


def _lock(root: Path, state: Path | None = None) -> Path:
    return Path(state or STATE) / f"meaning_build_{_root_key(root)}.lock"


def prune(root: Path = ROOT, state: Path | None = None) -> list[str]:
    """v19: remove the vector files of libraries that no longer exist (a test's temp folder) and dead build locks and
    temp files. This root's file and the v1 file are kept. A v2 file written before the root was recorded in it
    (2026-10-24 evening) and not this root's goes too: another library's file comes back by itself at its next query."""
    np = _np()
    st = Path(state or STATE)
    keep = {store_path(root, state).name, _legacy_store(state).name}
    gone: list[str] = []
    for p in sorted(st.glob(f"meaning_{MODEL.replace('/', '_')}_*.npz")):
        if p.name in keep:
            continue
        r = ""
        if ".tmp" not in p.name:
            try:
                with np.load(p, allow_pickle=False) as z:
                    r = str(z["root"]) if "root" in z.files else ""
            except (OSError, ValueError):
                r = ""
        if not r or not Path(r).is_dir():
            try:
                p.unlink()
                gone.append(p.name)
            except OSError:
                pass
    for lk in sorted(st.glob("meaning_build_*.lock")):
        try:
            if time.time() - lk.stat().st_mtime > LOCK_STALE:
                lk.unlink()
                gone.append(lk.name)
        except OSError:
            pass
    return gone


def background_build(root: Path, state: Path | None = None) -> bool:
    """Start `meaning.py build --root ROOT` detached, once (a lock file); True when one was started."""
    lk = _lock(root, state)
    try:
        if lk.is_file() and time.time() - lk.stat().st_mtime < LOCK_STALE:
            return False
        lk.parent.mkdir(parents=True, exist_ok=True)
        lk.write_text(str(time.time()), encoding="utf-8")
        py = str(VENV_BG) if VENV_PY.is_file() else sys.executable
        env = dict(os.environ, MAESTRO_STATE=str(state or STATE))
        subprocess.Popen([py, str(Path(__file__)), "build", "--root", str(root), "--release-lock"], creationflags=BG_FLAGS,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
                         close_fds=True)
        return True
    except OSError:
        return False


LAST: dict = {}
_MEM: dict[str, dict] = {}   # 2026-10-25: root key -> store, for libraries that persist no file


def rank(prompts: list[str], k: int = 40, root: Path = ROOT, state: Path | None = None) -> list[list[tuple[str, float]]]:
    """For each prompt, the top k skills by meaning with their cosine. Keeps the vector file current first."""
    np = _np()
    persist = state is not None or Path(root).resolve() == ROOT.resolve()   # v19: a library with no state folder of its own
    st = sync(root, INLINE_MAX if persist else None, state, persist)         # (a selftest's temp root) is embedded in memory only
    if st["pending"] and persist:
        LAST["background"] = background_build(root, state)
    s = st["store"]
    coverage = len(s["names"]) / max(1, st["total"])
    LAST.update(embedded=st["embedded"], pending=st["pending"], removed=st["removed"], coverage=round(coverage, 3))
    if not s["names"] or coverage < MIN_COVERAGE:     # 2026-10-25: a partial store ranks only its first names; the words carry this prompt
        return [[] for _ in prompts]
    q = embed_queries(prompts)
    sims = q @ s["vecs"].T
    out = []
    for row in sims:
        idx = np.argsort(-row)[:k]
        out.append([(s["names"][i], round(float(row[i]), 4)) for i in idx])
    return out


def meaning_rank_subprocess(prompt: str, k: int = 40, timeout: float = 20.0, root: Path = ROOT) -> list[tuple[str, float]] | None:
    """From a Python without fastembed: run this file in its venv, once. None when the venv is missing or the run exceeds
    `timeout`. v20.0.5: the venv's python.exe is a launcher whose child kept the pipes open after the launcher was killed,
    so the timeout never returned; the whole tree is killed now. `rank_anywhere` no longer falls back to this."""
    if not VENV_PY.is_file():
        return None
    p = None
    try:
        p = subprocess.Popen([str(VENV_PY), str(Path(__file__)), "search", "--json", "-k", str(k), "--stdin", "--root", str(root)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        out, _ = p.communicate(prompt, timeout=timeout)
        return [tuple(x) for x in json.loads(out)] if p.returncode == 0 else None
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
        try:
            p.communicate(timeout=5)
        except (subprocess.SubprocessError, OSError):
            pass
        return None
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


# --- the resident helper (2026-10-24: the whisper hook took 11-16 s a prompt, nearly all of it loading the model) ---
# `meaning.py serve` keeps the model loaded in ONE small background process (about 150 MB) and answers rank requests on
# a local socket (127.0.0.1 only, a random key in the state folder). Callers without fastembed ask it first; when it is
# not up they start it and use the word readings this once. It exits by itself after SERVE_IDLE seconds unused.
SERVE_IDLE = int(os.environ.get("MAESTRO_MEANING_IDLE", str(3 * 3600)))


def _serve_info(state: Path | None = None) -> Path:
    return Path(state or STATE) / "meaning_server.json"


def serve(state: Path | None = None) -> int:
    import secrets
    from multiprocessing.connection import Listener
    try:                                                        # one helper per state folder: a live one wins
        if _alive(int(json.loads(_serve_info(state).read_text(encoding="utf-8"))["pid"])):
            return 0
    except (OSError, ValueError, KeyError, TypeError):
        pass
    _model()                                                    # load once, before saying we are up
    key = secrets.token_bytes(24)
    with Listener(("127.0.0.1", 0), authkey=key) as ls:
        info = _serve_info(state)
        info.parent.mkdir(parents=True, exist_ok=True)
        info.write_text(json.dumps({"port": ls.address[1], "key": key.hex(), "pid": os.getpid(), "t": time.time()}), encoding="utf-8")
        import socket
        ls._listener._socket.settimeout(60)                    # wake once a minute to check the idle clock
        last = time.time()
        while time.time() - last < SERVE_IDLE:
            try:
                conn = ls.accept()
            except (socket.timeout, OSError):
                continue
            except Exception:  # noqa: BLE001 (a caller with a wrong key)
                continue
            last = time.time()
            try:
                req = conn.recv()
                if req.get("op") == "rank":
                    out = rank(req["prompts"], int(req.get("k", 40)), Path(req.get("root") or ROOT),
                               Path(req["state"]) if req.get("state") else None)
                    conn.send({"ok": True, "r": out, "last": dict(LAST)})
                elif req.get("op") == "embed":
                    vs = (embed_queries if req.get("kind") == "query" else embed_docs)(req["texts"])
                    conn.send({"ok": True, "v": [list(map(float, v)) for v in vs]})
                else:
                    conn.send({"ok": True, "pong": os.getpid()})
            except Exception as exc:  # noqa: BLE001
                try:
                    conn.send({"ok": False, "err": f"{type(exc).__name__}: {exc}"})
                except Exception:  # noqa: BLE001
                    pass
            finally:
                conn.close()
    try:
        info = _serve_info(state)
        if json.loads(info.read_text(encoding="utf-8")).get("pid") == os.getpid():
            info.unlink()
    except (OSError, ValueError):
        pass
    return 0


def ask_server(req: dict, timeout: float = 5.0, state: Path | None = None) -> dict | None:
    """One request to the resident helper; None when it is not running or does not answer in time. v20.0.5: the whole
    exchange (connect, key handshake, send, answer) runs in a daemon thread joined for `timeout` seconds: Client() has no
    timeout on its handshake, and a helper that is up but busy (embedding, or paged out) accepts the connection into its
    backlog and handshakes only when it gets to it, so a `score` once sat on it for ten minutes. A thread left behind
    ends when the helper answers or the process exits."""
    import threading
    box: list[dict] = []

    def go() -> None:
        from multiprocessing.connection import Client
        try:
            info = json.loads(_serve_info(state).read_text(encoding="utf-8"))
            conn = Client(("127.0.0.1", int(info["port"])), authkey=bytes.fromhex(info["key"]))
        except Exception:  # noqa: BLE001 (refused, stale file, wrong key)
            return
        try:
            conn.send(req)
            if conn.poll(timeout):
                r = conn.recv()
                if r.get("ok"):
                    box.append(r)
        except (OSError, EOFError):
            pass
        finally:
            conn.close()

    th = threading.Thread(target=go, daemon=True)
    th.start()
    th.join(timeout + 1.0)
    return box[0] if box else None


def _alive(pid: int) -> bool:
    """True when process pid is running. (Never os.kill(pid, 0) on Windows: it terminates the process.)"""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)                       # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259                       # STILL_ACTIVE


def start_server(state: Path | None = None) -> bool:
    """Start `meaning.py serve` in the background, at most once a minute (a lock) and never while the recorded helper
    is still alive (a busy helper misses the 5 s answer window; starting a second one each time piled them up)."""
    if not VENV_PY.is_file():
        return False
    lk = Path(state or STATE) / "meaning_server.lock"
    try:
        if lk.is_file() and time.time() - lk.stat().st_mtime < 60:
            return False
        try:
            if _alive(int(json.loads(_serve_info(state).read_text(encoding="utf-8"))["pid"])):
                return False
        except (OSError, ValueError, KeyError, TypeError):
            pass
        lk.parent.mkdir(parents=True, exist_ok=True)
        lk.write_text(str(time.time()), encoding="utf-8")
        env = dict(os.environ, MAESTRO_STATE=str(state or STATE))
        subprocess.Popen([str(VENV_BG), str(Path(__file__)), "serve"], creationflags=BG_FLAGS, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, close_fds=True)
        return True
    except OSError:
        return False


def rank_anywhere(prompt: str, k: int = 40, root: Path = ROOT, state: Path | None = None, wait: float = 0.0):
    """From a Python without fastembed: the resident helper's answer; it is started when it is not up. With wait > 0
    the call waits that long for a fresh helper (score, eval), else it returns None at once (the hook) and the word
    readings carry this prompt. v20.0.5: when the wait runs out the answer is None, full stop. The one-shot venv run
    that used to follow re-embedded a cold library inside the score (eight minutes on the owner's PC: the selfcheck
    tour's two timeouts); a helper that is up but busy answers the next score instead."""
    ask = {"op": "rank", "prompts": [prompt], "k": k, "root": str(root), "state": str(state) if state else None}
    r = ask_server(ask, state=state)
    if r:
        LAST.update(r.get("last") or {})
        return [tuple(x) for x in r["r"][0]]
    start_server(state)
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(0.5)
        r = ask_server(ask, state=state)
        if r:
            LAST.update(r.get("last") or {})
            return [tuple(x) for x in r["r"][0]]
    return None


def fuse(lists: list[list[str]], weights: list[float], k: int = 60) -> list[str]:
    """Reciprocal-rank fusion: score = sum w / (k + rank)."""
    sc: dict[str, float] = {}
    for lst, w in zip(lists, weights):
        for r, n in enumerate(lst):
            sc[n] = sc.get(n, 0.0) + w / (k + r + 1)
    return sorted(sc, key=lambda n: -sc[n])


def _word_ranker(root: Path = ROOT):
    """The finder's word search (the reading the whisper used), for the comparison."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("maestro_index", HERE / "index.py")
    IX = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(IX)
    p = IX.index_path(root, STATE)
    d = json.loads(p.read_text(encoding="utf-8"))
    skills = [IX._as_skill(e) for e in d["skills"].values()]
    homes = [root / h for h in ("skill-finder", "core-skill-pin")] + [HERE.parent / "skill-finder"]   # pack layout last
    fsp = next((h / "find_skill.py" for h in homes if (h / "find_skill.py").is_file()), None)
    if fsp is None:   # v20.0.5: a plain message instead of StopIteration on a PC without skill-finder
        raise FileNotFoundError("find_skill.py not found (skill-finder beside the library or beside skill-maestro); "
                                "install the skill-maestro pack, which bundles it")
    fs_spec = importlib.util.spec_from_file_location("find_skill", fsp)
    fs = importlib.util.module_from_spec(fs_spec)
    fs_spec.loader.exec_module(fs)
    F = IX.FastSearch(fs, skills)
    return lambda q, k: [r["name"] for r in F.search(skills, q, k)]


def read_probes(p: Path) -> list[tuple[str, set]]:
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "\t" not in line:
            continue
        q, keys = line.rsplit("\t", 1)
        rows.append((q, {x.strip() for x in keys.split(",") if x.strip()}))
    return rows


def _mcnemar(b: int, c: int) -> float:
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 4)


def evaluate(files: list[Path]) -> dict:
    words = _word_ranker()
    res = {}
    for f in files:
        probes = read_probes(f)
        mean = rank([q for q, _ in probes], 120)
        tally = {m: {"@1": 0, "@3": 0, "pool40": 0} for m in ("words", "meaning", "fused")}
        per = []
        for (q, good), mrow in zip(probes, mean):
            w = words(q, 120)
            m = [n for n, _ in mrow]
            fz = fuse([m, w], [3.0, 1.0])
            row = {}
            for name, lst in (("words", w), ("meaning", m), ("fused", fz)):
                tally[name]["@1"] += bool(good & set(lst[:1]))
                tally[name]["@3"] += bool(good & set(lst[:3]))
                tally[name]["pool40"] += bool(good & set(lst[:40]))
                row[name] = bool(good & set(lst[:3]))
            per.append(row)
        b = sum(1 for r in per if r["meaning"] and not r["words"])
        c = sum(1 for r in per if r["words"] and not r["meaning"])
        res[f.name] = {"n": len(probes), **tally, "meaning_only_hits@3": b, "words_only_hits@3": c,
                       "mcnemar_p": _mcnemar(b, c)}
    return res


def _selftest() -> bool:
    import tempfile
    ok = {}
    ok["fuse: a name first in both lists wins"] = fuse([["a", "b"], ["a", "c"]], [1, 1])[0] == "a"
    ok["mcnemar: 10 vs 0 is significant, 3 vs 3 is not"] = _mcnemar(10, 0) < 0.01 and _mcnemar(3, 3) == 1.0
    t = skill_texts()
    n_folder = len(list(Path(ROOT).glob("*/SKILL.md")))      # any library size: the package ships with one sibling skill
    ok["skill texts: every skill incl. the Maestro and Anthropic's carry purpose"] = (
        "skill-maestro" in t and "anthropic-skills:pptx" in t and len(t) > n_folder and any("What it does:" in v for v in t.values()))
    with tempfile.TemporaryDirectory() as td:
        lib = Path(td) / "lib"
        (lib / "alpha").mkdir(parents=True)
        (lib / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: split a list of trades into wins and losses\n---\nbody", encoding="utf-8")
        s1 = signature(lib)
        (lib / "beta").mkdir()
        (lib / "beta" / "SKILL.md").write_text("---\nname: beta\n---\nTurns a spoken recipe into a shopping list.", encoding="utf-8")
        ok["signature changes when a skill is added"] = signature(lib) != s1
        ok["a skill with no description is described by its body"] = "shopping list" in skill_texts(lib).get("beta", "")
        try:
            import fastembed  # noqa: F401
            have = True
        except ImportError:
            have = False
        if have:
            st = Path(td) / "state"
            r0 = sync(lib, None, st)
            ok["sync: a fresh library is embedded, Anthropic's skills included"] = (
                r0["pending"] == 0 and {"alpha", "beta", "anthropic-skills:pdf"} <= set(r0["store"]["names"]))
            r1 = sync(lib, None, st)
            ok["sync: nothing to do when nothing changed"] = r1["sig_ok"] and r1["embedded"] == 0
            (lib / "gamma").mkdir()
            (lib / "gamma" / "SKILL.md").write_text("---\nname: gamma\ndescription: draw a weather map of rain\n---\n", encoding="utf-8")
            import shutil
            shutil.rmtree(lib / "beta")
            r2 = sync(lib, None, st)
            ok["sync: a new skill is embedded at once and a deleted one dropped"] = (
                r2["embedded"] == 1 and r2["removed"] == 1 and "gamma" in r2["store"]["names"] and "beta" not in r2["store"]["names"])
            top = rank(["show me where it will rain tomorrow on a map"], 3, lib, st)[0]
            ok["rank: the new skill is found by meaning on its first query"] = top and top[0][0] == "gamma"
            r3 = rank(["show me where it will rain tomorrow on a map"], 2, lib)[0]       # no state folder named: in memory only
            ok["rank without a state folder writes no vector file (a test's temp library leaves nothing behind)"] = (
                bool(r3) and r3[0][0] == "gamma" and not store_path(lib).is_file())
            # 2026-10-25, the cold-library scenarios: with the inline cap of 8, a cold library's first query embedded only
            # its 8 alphabetically first names (Anthropic's) and that partial reading out-voted the words 3:1.
            cold = Path(td) / "state_cold"
            r4 = sync(lib, 1, cold)                                     # cap 1, but a small cold library is embedded whole
            ok["sync: a small cold library is embedded whole on its first query, whatever the inline cap"] = (
                r4["pending"] == 0 and r4["embedded"] == r4["total"] and "gamma" in r4["store"]["names"])
            global COLD_FULL
            saved, COLD_FULL = COLD_FULL, 0
            try:
                part = Path(td) / "state_part"
                part.mkdir()
                _lock(lib, part).write_text(str(time.time()), encoding="utf-8")   # no background build from a selftest
                r5 = sync(lib, 1, part)                                 # one of many: the alphabetically first only
                r6 = rank(["show me where it will rain tomorrow on a map"], 3, lib, part)[0]
                ok["rank: a store covering under half the library is no reading (the words carry the prompt)"] = (
                    r5["embedded"] == 1 and r5["pending"] == r5["total"] - 1 and r6 == [] and LAST.get("coverage", 1) < MIN_COVERAGE)
            finally:
                COLD_FULL = saved
            (lib / "gamma" / "SKILL.md").write_text("---\nname: gamma\ndescription: draw a weather map of snow and sleet\n---\n", encoding="utf-8")   # a longer file: the signature sees it
            r7 = sync(lib, 0, st)                                       # changed, and nothing may be embedded now
            ok["sync: a changed skill keeps its old vector until its new one is embedded (stale beats absent)"] = (
                r7["pending"] == 1 and r7["embedded"] == 0 and "gamma" in r7["store"]["names"])
    # v20.0.5: a helper that is up but busy accepts the connection and handshakes only when it gets to it. A listener
    # that never accepts plays that helper; the helper record names this process so no real helper is started.
    import socket
    global meaning_rank_subprocess
    with tempfile.TemporaryDirectory() as td:
        st = Path(td)
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        _serve_info(st).write_text(json.dumps({"port": srv.getsockname()[1], "key": "00" * 24, "pid": os.getpid(), "t": time.time()}),
                                   encoding="utf-8")
        (st / "meaning_server.lock").write_text(str(time.time()), encoding="utf-8")
        t0 = time.time()
        a = ask_server({"op": "ping"}, timeout=1.0, state=st)
        t_ask = time.time() - t0
        ok["ask_server: a helper that never answers costs the timeout, not forever"] = a is None and t_ask < 4.0
        saved_sub, calls = meaning_rank_subprocess, []
        meaning_rank_subprocess = lambda *a, **kw: calls.append(1)   # noqa: E731
        try:
            t0 = time.time()
            r = rank_anywhere("where will it rain", 3, ROOT, st, wait=1.5)
            t_rank = time.time() - t0
        finally:
            meaning_rank_subprocess = saved_sub
        ok["rank_anywhere: when the wait runs out the reading is None at once, and no one-shot run follows"] = (
            r is None and t_rank < 12.0 and not calls)
        srv.close()
    bad = [k for k, v in ok.items() if not v]
    print(f"meaning selftest: {len(ok) - len(bad)}/{len(ok)} PASS" + ("" if not bad else "\n  FAIL " + "\n  FAIL ".join(bad)))
    return not bad


def _opt(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


def main(argv: list[str]) -> int:
    try:
        return _main(argv)
    except MeaningUnavailable as exc:                     # v20: a stock Python gets one line, not a traceback
        print(f"MEANING: {exc}")
        return 2


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return 0 if _selftest() else 1
    root = Path(_opt(argv, "--root", str(ROOT)))
    if argv[0] == "build":
        t0 = time.time()
        try:
            r = sync(root, None)
        finally:
            if "--release-lock" in argv:
                try:
                    _lock(root).unlink()
                except OSError:
                    pass
        print(json.dumps({"skills": len(r["store"]["names"]), "embedded": r["embedded"], "removed": r["removed"],
                          "seconds": round(time.time() - t0, 1), "file": str(store_path(root))}, indent=1))
        return 0
    if argv[0] == "serve":
        return serve()
    if argv[0] == "prune":
        gone = prune(root)
        print(f"PRUNED {len(gone)} file(s) of libraries that no longer exist" + (": " + ", ".join(gone) if gone else ""))
        return 0
    if argv[0] == "status":
        s = _load_store(root)
        texts = skill_texts(root)
        cur = sum(1 for n, h in zip(s["names"], s["shas"]) if n in texts and h == _sha(texts[n]))
        print(f"MEANING VECTORS: {cur} of {len(texts)} skills current; {len(texts) - cur} waiting "
              f"({'a background build is running' if _lock(root).is_file() else 'they are added at the next query'}); file {store_path(root)}")
        return 0
    if argv[0] == "search":
        k = int(_opt(argv, "-k", "10"))
        skip = {str(k), str(root)}
        prompt = sys.stdin.read() if "--stdin" in argv else " ".join(a for a in argv[1:] if not a.startswith("-") and a not in skip)
        r = rank([prompt], k, root)[0]
        print(json.dumps(r) if "--json" in argv else "\n".join(f"{s:.3f}  {n}" for n, s in r))
        return 0
    if argv[0] == "eval":
        files = [Path(a) for a in argv[1:] if not a.startswith("-")] or [ROOT / "skill-finder" / "probes_heldout.tsv",
                                                                       HERE / "evals" / "probes_walkforward_2026-10-16.tsv"]
        print(json.dumps(evaluate(files), indent=1))
        return 0
    print(f"unknown command {argv[0]!r}; see --help")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
