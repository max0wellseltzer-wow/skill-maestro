"""foundry - a seed idea (name + mechanism) walks every library gate in order and is born only if it passes them all
(backs the skill-foundry skill).

Seed: the user's "generate candidates then cull" x "do not stop until drained" x "use our skills to make skills".
The library already owns each step; this chains them so one call answers "should this skill exist, and if so,
make it":
  0. generate (optional)  kingdom-sweep grid() - domain x stretch-level questions to mine for seed ideas
  1. yaml-safe            scaffold.validate_description - the description will not break frontmatter
  2. metaphor             metaphor-to-algorithm reduce() - BUILD passes, FOLD INTO <skill> stops
  3. finder               skill-finder search() - the top hit's score, normalised by the query's own IDF weight,
                          must stay below finder_threshold (else the need already routes to an existing skill)
  4. collision            collision-registry score() against every library description (+ a registry file if given)
  5. source-labels        the pitch must be labelled claim lines ([REAL: src] / [IMAGINED] / [FABRICATED]) with no issues
  6. birth                only if all pass AND dry_run=False - scaffold() writes the folder, lineage-ledger record()
                          writes the birth (parents, operator "skill-foundry", prompt quote, chooser)
Every gate's verdict is returned, including the gates after the first failure (so one call shows ALL the work an idea
needs). dry_run=True is the DEFAULT: nothing is created.

    from foundry import found, drain, generate
    found("tide-clock", "predict harbour tide heights from lunar phase", pitch="- ... [IMAGINED]", dry_run=True)
    drain([{"name": ..., "mechanism": ..., "pitch": ...}, ...])     # every idea through every gate, no early stop
    python foundry.py NAME "mechanism" [--pitch TEXT] [--create]
    python foundry.py --selftest
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SK = Path(__file__).resolve().parents[1]
for _d in ("skill-foundry", "skill-finder", "metaphor-to-algorithm", "collision-registry", "source-labels",
           "lineage-ledger", "kingdom-sweep"):
    sys.path.insert(0, str(SK / _d))
from collisions import THRESHOLD as COLLISION_THRESHOLD  # noqa: E402
from collisions import read as read_registry  # noqa: E402
from collisions import score as collision_score  # noqa: E402
from collisions import skill_texts  # noqa: E402
from find_skill import _tokens, load, search  # noqa: E402
from lineage import record as record_birth  # noqa: E402
from metaphor import reduce as metaphor_reduce  # noqa: E402
from scaffold import NAME_RE, scaffold, validate_description  # noqa: E402
from source_labels import check as label_check  # noqa: E402
from sweep import grid  # noqa: E402

DEFAULT_ROOT = Path.home() / ".claude" / "skills"
GATES = ["yaml-safe", "metaphor", "finder", "collision", "source-labels"]


def generate(concept: str, domains=None, levels=None) -> list:
    """Optional generator: kingdom-sweep's domain x level questions for a concept."""
    return grid(concept, domains, levels)


def default_description(name: str, mechanism: str) -> str:
    m = " ".join(mechanism.split()).rstrip(".").replace(": ", " - ").replace(" #", " ")
    return f"{m[:1].upper()}{m[1:]}. Use this whenever the user needs to {m[:1].lower()}{m[1:]}. Pairs with skill-foundry."


def finder_strength(skills: list, query: str) -> dict:
    """Top skill-finder hit, with its score divided by the query's total IDF weight (0 = nothing, 1 = every query
    word found, up to 2 with name boosts) so one threshold works on any library size."""
    hits = search(skills, query, top=1)
    q = set(_tokens(query))
    n = len(skills)
    df = {}
    for s in skills:
        for t in set(s["toks"]):
            df[t] = df.get(t, 0) + 1
    tot = sum(math.log((n + 1) / (df.get(t, 0) + 0.5)) for t in q)
    if not hits or not tot:
        return {"top": None, "raw": 0.0, "norm": 0.0}
    return {"top": hits[0]["name"], "raw": hits[0]["score"], "norm": round(hits[0]["score"] / tot, 3)}


def found(name: str, mechanism: str, description: str | None = None, tool_name: str | None = None,
          pitch: str | None = None, root=None, ledger=None, registry=None, parents=(), prompt: str = "",
          prompt_date: str = "", chooser: str = "max", finder_threshold: float = 0.6,
          collision_threshold: float = COLLISION_THRESHOLD, metaphor_threshold: float = 0.5,
          dry_run: bool = True) -> dict:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError(f"skill name must be kebab-case: {name!r}")
    root = Path(root) if root else DEFAULT_ROOT
    ledger = Path(ledger) if ledger else SK / "lineage-ledger" / "LINEAGE.jsonl"
    description = description or default_description(name, mechanism)
    tool_name = tool_name or name.replace("-", "_")
    skills = [s for s in load(root) if s["name"] != name]
    gates = []

    def gate(g, passed, detail):
        gates.append({"gate": g, "pass": bool(passed), "detail": detail})

    probs = validate_description(description)
    gate("yaml-safe", not probs, "; ".join(probs) or "one line, no ': ' or ' #', has 'Use this whenever'")
    red = metaphor_reduce(name, mechanism, skills=skills, threshold=metaphor_threshold)
    gate("metaphor", red["verdict"] == "BUILD", f"{red['verdict']} ({red['why']})")
    fs = finder_strength(skills, f"{name.replace('-', ' ')} {mechanism}")
    gate("finder", fs["norm"] < finder_threshold,
         f"top hit {fs['top']} norm {fs['norm']:.2f} (raw {fs['raw']}) vs threshold {finder_threshold}")
    entries = [{"id": i, "name": n, "text": t} for i, (n, t) in enumerate(skill_texts(root)) if n != name]
    if registry:
        entries += [e for e in read_registry(registry)[0] if e.get("name") != name]
    hits = collision_score(name, f"{mechanism} {description}", entries, collision_threshold)
    gate("collision", not hits, ", ".join(f"{h['name']} {h['score']:.2f}" for h in hits[:3])
         or f"no entry >= {collision_threshold}")
    if not pitch or not pitch.strip():
        gate("source-labels", False, "no pitch given - write the claims as '- claim [REAL: src]/[IMAGINED]/[FABRICATED]'")
    else:
        lc = label_check(pitch)
        good = lc["ok"] and len(lc["claims"]) > 0
        gate("source-labels", good, "; ".join(lc["issues"][:3]) or
             (f"{len(lc['claims'])} labelled claim(s) {lc['counts']}" if lc["claims"] else "no claim lines found"))
    passed = all(g["pass"] for g in gates)
    first_fail = next((g["gate"] for g in gates if not g["pass"]), None)
    out = {"name": name, "gates": gates, "passed": passed, "stopped_at": first_fail, "born": False,
           "dry_run": dry_run, "description": description, "path": None, "lineage": None}
    if passed and not dry_run:
        d = scaffold(name, description, tool_name, root,
                     intro=f"Seed mechanism: {mechanism}." + (f' Prompt: "{prompt}"' if prompt else ""))
        rec = record_birth(ledger, name, parents=list(parents), operator="skill-foundry", prompt=prompt,
                           prompt_date=prompt_date, chooser=chooser)
        out.update(born=True, path=str(d), lineage=rec)
    return out


def drain(ideas: list, **kw) -> list:
    """Every idea through every gate - never stops at the first rejected idea ("do not stop until drained")."""
    out = []
    for idea in ideas:
        try:
            out.append(found(**{**kw, **idea}))
        except (ValueError, FileExistsError) as e:          # a malformed idea is a result, not a crash
            out.append({"name": idea.get("name"), "passed": False, "born": False, "error": str(e), "gates": []})
    return out


def render(r: dict) -> str:
    lines = [f"{r['name']}: " + ("BORN at " + r["path"] if r.get("born") else
                                 "PASSES ALL GATES (dry run - nothing created)" if r.get("passed") else
                                 f"STOPPED at {r.get('stopped_at') or 'error'}")]
    for g in r.get("gates", []):
        lines.append(f"  {'pass' if g['pass'] else 'FAIL'}  {g['gate']:14s} {g['detail']}")
    if r.get("error"):
        lines.append(f"  error: {r['error']}")
    return "\n".join(lines)


def _selftest() -> bool:
    import shutil
    import tempfile
    sys.path.insert(0, str(SK / "skill-health"))
    from skill_health import check_library
    ok = {}
    tmp = Path(tempfile.mkdtemp(prefix="foundry_"))
    real_ledger = SK / "lineage-ledger" / "LINEAGE.jsonl"
    real_before = real_ledger.read_bytes() if real_ledger.exists() else None
    try:
        lib, ledger = tmp / "lib", tmp / "LINEAGE.jsonl"

        def mk(name, desc):
            (lib / name).mkdir(parents=True)
            (lib / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n",
                                                 encoding="utf-8")
        mk("series-trend", "Classify a price series as trending or mean reverting via the hurst exponent. "
                           "Use this whenever the user asks if a series trends.")
        mk("alert-throttle", "Throttle noisy alerts with a token bucket cooldown so a rate limit is respected. "
                             "Use this whenever the user has an alert flood.")
        pitch = "- Sailors need tide heights for the harbour [IMAGINED]\n- Tides follow the lunar phase [REAL: tide tables]\n"
        dup = found("trend-teller", "classify a price series as trending or mean reverting via the hurst exponent",
                    pitch=pitch, root=lib, ledger=ledger, dry_run=False)
        ok["a duplicate idea stops at a gate and nothing is created"] = (
            not dup["passed"] and dup["stopped_at"] in GATES and not (lib / "trend-teller").exists())
        ok["every gate's verdict is returned, even after the first failure"] = [g["gate"] for g in dup["gates"]] == GATES
        novel = dict(name="tide-clock", mechanism="predict harbour tide heights from lunar phase and bay geometry",
                     pitch=pitch, root=lib, ledger=ledger, prompt="use our skills to make skills",
                     prompt_date="2026-10-15", parents=["kingdom-sweep"])
        dry = found(**novel)
        ok["dry_run is the default and creates nothing for a passing idea"] = (
            dry["passed"] and dry["dry_run"] and not dry["born"] and not (lib / "tide-clock").exists()
            and not ledger.exists())
        born = found(**novel, dry_run=False)
        rep = check_library(lib, only={"tide-clock"})
        ok["a novel idea is scaffolded and the folder passes skill-health"] = (
            born["born"] and rep["rows"] and rep["rows"][0]["status"] == "OK")
        rec = born["lineage"] or {}
        ok["the birth is recorded in the temp ledger with operator skill-foundry"] = (
            rec.get("operator") == "skill-foundry" and rec.get("parents") == ["kingdom-sweep"]
            and "tide-clock" in ledger.read_text(encoding="utf-8"))
        bad = found("moon-gauge", "gauge moon brightness over the harbour each night", pitch="- an unlabelled claim\n",
                    root=lib, ledger=ledger, dry_run=False)
        ok["planted bad pitch (unlabelled claim) stops at source-labels"] = (
            bad["stopped_at"] == "source-labels" and not (lib / "moon-gauge").exists())
        colon = found("moon-gauge", "gauge moon brightness", description="Gauge: the moon. Use this whenever the user asks.",
                      pitch=pitch, root=lib, ledger=ledger)
        ok["a YAML-breaking description fails the yaml-safe gate"] = colon["stopped_at"] == "yaml-safe"
        dr = drain([{"name": "Bad_Name", "mechanism": "x y z", "pitch": pitch},
                    {"name": "tide-clock", "mechanism": "predict harbour tide heights from lunar phase", "pitch": pitch}],
                   root=lib, ledger=ledger)
        ok["drain keeps going past a malformed idea (bad name -> error row) and returns one result per idea"] = (
            len(dr) == 2 and "kebab" in dr[0].get("error", "") and dr[1]["gates"] and not any(r.get("born") for r in dr))
        ok["generate() offers kingdom-sweep's domain x level questions"] = len(generate("reproduction")) >= 100
        ok["the real LINEAGE.jsonl is untouched"] = (
            (real_ledger.read_bytes() if real_ledger.exists() else None) == real_before)
        ok["no __pycache__ left behind"] = not any(tmp.rglob("__pycache__"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if not argv or argv[0] == "--selftest":
        return 0 if _selftest() else 1
    argv = list(argv)
    create = "--create" in argv
    argv = [a for a in argv if a != "--create"]
    pitch = None
    if "--pitch" in argv:
        i = argv.index("--pitch")
        pitch = argv[i + 1]
        del argv[i:i + 2]
    r = found(argv[0], " ".join(argv[1:]), pitch=pitch, dry_run=not create)
    print(render(r))
    return 0 if r["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
