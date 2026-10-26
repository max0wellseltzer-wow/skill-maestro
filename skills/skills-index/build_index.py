"""build_index - build a browsable, family-grouped catalog of the skill library (backs the skills-index skill).

Reads every <skills_root>/<skill>/SKILL.md, takes its frontmatter name and the first sentence of its
description as a "reach for this when" line, marks whether it ships a tool, and groups everything into
families (a curated map, then keyword fallback, then "Other"). Writes INDEX.md beside this script and prints a
summary. Re-run it after adding skills - the index is generated, never hand-maintained, so it can't go stale.

    python build_index.py                 # index ~/.claude/skills -> INDEX.md here
    python build_index.py <skills_root>   # index another library
    python build_index.py --selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

FAMILIES = {
    "Honest research & statistics": "controlled-fire pre-register forward-score signal-nulls calibration-check candidate-then-gate "
        "heritability epistasis-scan founder-effect handicap-test "
        "research-spine test-a-condition doubt-mind self-attacking-referee "
        "second-source numbers-pass benford antifragile walk-forward-split deflated-sharpe "
        "pbo-overfit isotonic-calibration sprt-sequential fdr-control seasonality-test forward-pipeline "
        "forgery-plan lag-audit dead-lane-check lane-resurrection reproduce-before-rejudge "
        "fermi-estimate distance-ladder hr-diagram influence-lens escape-velocity fork-audit",
    "Time series & signals": "hurst changepoint erosion resonance moire phase-lock dendro diauxie "
        "pulsar-timing event-stacking light-cone transit-search precursor-scan "
        "autocatalysis logistic-growth local-contrast matched-filter watershed allometry half-life cambrian",
    "Networks & graphs": "keystone-find diffuse-rank cascade flux-balance sandpile crystallize",
    "Allocation, control & rate": "capillary osmosis hysteresis homeostasis triage fission "
        "symmetry-break tropism quorum-sense",
    "Data integrity & invariants": "conserve-check entanglement ratchet sediment clone-check textbook-handshake "
        "declared-count "
        "data-hygiene fast-path-proof crossmatch",
    "Optimization & search": "anneal levy-flight mutation-forge titration convex-hull parallax evolution-arena",
    "Evolution & life models": "red-queen mullers-ratchet reproductive-strategy sandpile physarum error-threshold",
    "Code history (git lineage)": "ship-of-theseus juvenile-form linkage-map atavism-check speciation",
    "Idea generation & provenance": "prompt-genealogy rule-miner lineage-ledger collision-registry novelty-meter "
        "metaphor-to-algorithm source-labels kingdom-sweep pollinator-routing metaphor-questions",
    "Distributions, populations & dynamics": "entropy-meter gravity-cluster caustics stigmergy vestigial "
        "lindy sandpile supersaturation immune-memory apoptosis refraction lagrange-points",
    "Reproduction & combination": "word-sex word-sex word-sex signal-fusion cross-breed clone-check "
        "egg-lay metamorphose polyploid graft horizontal-transfer epigenetic-switch prion-guard bud "
        "regen symbiosis broadcast-spawn reassort chimera",
    "Coordination & landing (multi-session)": "writer-pen peer-handoff "
        "land-a-change chain-fork-guard merge-cloud-branch decision-renumber mailbox-post tree-status "
        "handoff-pack question-not-ruling "
        "precommit-bundle landing-inbox blame-failure-by-branch branch-file-copy branch-followup-scan "
        "check-under-concurrent-writers precommit-bundle landing-inbox landing-inbox precommit-bundle "
        "session-roster subagent-preamble abort-modes",
    "Long runs, memory & session continuity": "memory-gate long-job chain-the-queue momentum session-ledger "
        "promise-ledger receipt-report transcript-miner running-guard "
        "archive-without-bloat scratch-clean session-inspiration-packet paste-receipt night-shift-tripwire "
        "blind-spot-sweep memory-prune",
    "Data sourcing": "harvest-ceilings api-probe feed-poller-add terms-reader keys-in-process measure-first feed-harvest",
    "Code quality & safety": "code-cage plant-the-bug weak-assert-scan safe-bulk-edit escape-proof metamorphic-test "
        "windows-gotchas windows-port-audit guard-respect call-time-collaborators speed-proof paper-only "
        "live-only-edge scar-to-rule command-tour "
        "brittle-test-audit vacuous-success-audit test-expectation-oracle hostile-caller-pass staged-secret-scan "
        "fake-secret-sentinels hook-preflight toctou-append-audit time-semantics-contract built-not-wired "
        "code-kaleidoscope probe-kit prove-the-read live-root-pollution-guard",
    "Prompting, planning & creativity": "restriction-matrix lace-cycle living-prompt "
        "effort-relief fascination-forge playbook-from-results sunk-cost-check",
    "Algorithms & data structures": "kalman-filter fft-spectrum k-means bloom-filter reservoir-sample "
        "consistent-hash edit-distance shortest-path hyperloglog count-min-sketch minhash welford-stats "
        "stream-quantiles topo-sort union-find merkle-tree backoff-retry trie-search lru-cache interval-merge simhash "
        "token-bucket event-scheduler ring-buffer write-ahead-log content-store diff-patch "
        "replay-recorder schema-contract cron-parse matrix-lite data-intake nelder-mead rank-stats",
    "Quant & trading math": "hmm-regimes bootstrap-ci kelly-sizing drawdown-stats cointegration garch-vol risk-parity "
        "market-impact triple-barrier hac-regression vol-targeting markov-chain monte-carlo-paths "
        "cov-shrinkage sharpe-diff frac-diff ic-decay almgren-chriss hawkes evt-tail black-litterman "
        "copula-dependence regime-split mda-importance options-iv rebalance-bands ewma-vol adf-test "
        "backtest-verdict signal-vetting position-sizer pair-trade-vet dark-matter reverse-stress-test",
    "Project-specific": "autotrade-start screener-ask",
    "Working with the user (essentials)": "literal-execution token-thrift quota-prompt plain-terms finish-everything "
        "reading-dial read-as-code read-as-spec read-as-brief read-as-human smuggled-premise promise-ledger "
        "max-inbox max-inbox max-inbox rules-binding-audit retire-a-rule "
        "rule-conflict scope-creep-check max-lexicon",
    "Library organizing":"skills-index skill-finder skill-health mutation-audit route-audit wave-yield skill-finder "
        "exaptation-finder convergence-detector peacock-tail minimal-genome skill-foundry "
        "skill-graph library-vitals skill-retire skill-sync-audit skill-finder demand-scan",
}
POV_FAMILY = "Point of view (lenses on pov-core)"
FAMILY_OF = {}
for fam, names in FAMILIES.items():
    for n in names.split():
        FAMILY_OF.setdefault(n, fam)          # first family listed wins for a skill named twice
_EXTRA = Path(__file__).with_name("families_extra.json")   # {skill: family} merged from other sessions' waves
if _EXTRA.exists():
    import json as _json
    for _n, _f in _json.loads(_EXTRA.read_text(encoding="utf-8")).items():
        FAMILY_OF.setdefault(_n, _f)

KEYWORDS = [("series", "Time series & signals"), ("graph", "Networks & graphs"), ("network", "Networks & graphs"),
            ("allocat", "Allocation, control & rate"), ("rate", "Allocation, control & rate"),
            ("test", "Code quality & safety"), ("land", "Coordination & landing (multi-session)"),
            ("prompt", "Prompting, planning & creativity"), ("data", "Data sourcing")]


def _meta(skill_md: Path):
    name, desc = None, ""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        for line in text.splitlines()[1:60]:
            if line.strip() == "---":
                break
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip("'\"")
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip("'\"")
    return name, desc


def _first_sentence(desc: str, limit: int = 150) -> str:
    s = desc.split(". ")[0].strip()
    return (s[:limit - 3] + "...") if len(s) > limit else s


def _family(name: str, desc: str) -> str:
    if name in FAMILY_OF:
        return FAMILY_OF[name]
    low = desc.lower()
    for kw, fam in KEYWORDS:
        if kw in low:
            return fam
    return "Other"


def build(root: Path) -> dict:
    entries = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
        name, desc = _meta(d / "SKILL.md")
        name = name or d.name
        tools = [p for p in d.glob("*.py")]
        has_tool = bool(tools) or any(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
        family = _family(name, desc)
        if name == "pov-core" or (name not in FAMILY_OF and any(
                "from pov_core import" in p.read_text(encoding="utf-8", errors="replace") for p in tools)):
            family = POV_FAMILY                     # the point-of-view lenses are found by their engine, not listed
        entries.append({"name": name, "family": family, "tool": has_tool,
                        "when": _first_sentence(desc) or "(no description)"})
    fams = {}
    for e in entries:
        fams.setdefault(e["family"], []).append(e)
    order = [f for f in FAMILIES if f in fams] + sorted(f for f in fams if f not in FAMILIES and f != POV_FAMILY)
    order += [POV_FAMILY] if POV_FAMILY in fams else []
    lines = ["# Skills index", "",
             f"{len(entries)} skills - {sum(e['tool'] for e in entries)} ship a tool [T], "
             f"{sum(not e['tool'] for e in entries)} are doc-only [D]. Generated by build_index.py; re-run after "
             "adding skills. To search by need instead of browsing, use skill-finder.", ""]
    for f in order:
        lines += [f"## {f} ({len(fams[f])})", ""]
        for e in sorted(fams[f], key=lambda x: x["name"]):
            lines.append(f"- **{e['name']}** [{'T' if e['tool'] else 'D'}] - {e['when']}")
        lines.append("")
    return {"markdown": "\n".join(lines), "n": len(entries), "families": {f: len(v) for f, v in fams.items()}}


def _selftest() -> bool:
    import tempfile
    ok = {}
    root = Path(tempfile.mkdtemp())

    def mk(name, desc, tool=False, fm=True):
        d = root / name
        d.mkdir()
        body = f"---\nname: {name}\ndescription: {desc}\n---\nx\n" if fm else "no frontmatter\n"
        (d / "SKILL.md").write_text(body, encoding="utf-8")
        if tool:
            (d / "t.py").write_text("print(1)\n", encoding="utf-8")
    mk("hurst", "Estimate the Hurst exponent. More text.", tool=True)
    mk("mystery-net", "Walk a network of things. More.")
    mk("oddball", "Something else entirely.")
    mk("bare", "", fm=False)
    r = build(root)
    md = r["markdown"]
    ok["every skill appears exactly once"] = all(md.count(f"**{n}**") == 1 for n in ("hurst", "mystery-net", "oddball", "bare"))
    ok["a curated skill lands in its curated family"] = ("## Time series & signals (1)" in md)
    ok["an unknown skill falls back by keyword"] = ("## Networks & graphs (1)" in md)
    ok["an unmatched skill goes to Other"] = ("## Other" in md)
    ok["tool vs doc-only markers are correct"] = ("**hurst** [T]" in md and "**oddball** [D]" in md)
    ok["a skill with no frontmatter still indexes by folder name"] = ("**bare** [D] - (no description)" in md)
    ok["the 'when' line is the first sentence only"] = ("Estimate the Hurst exponent - " not in md and "More text" not in md)
    mk("odd-lens", "Look at a note sideways.", tool=False)
    (root / "odd-lens" / "lens.py").write_text("from pov_core import view\n", encoding="utf-8")
    ok["a tool importing pov_core lands in the point-of-view family"] = (f"## {POV_FAMILY} (1)" in build(root)["markdown"])
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    return all(ok.values())


def main(argv) -> int:
    if argv and argv[0] == "--selftest":
        return 0 if _selftest() else 1
    root = Path(argv[0]) if argv else Path.home() / ".claude" / "skills"
    r = build(root)
    out = Path(__file__).with_name("INDEX.md")
    out.write_text(r["markdown"] + "\n", encoding="utf-8")
    print(f"indexed {r['n']} skills into {out.name}:")
    for f, n in r["families"].items():
        print(f"  {n:3d}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
