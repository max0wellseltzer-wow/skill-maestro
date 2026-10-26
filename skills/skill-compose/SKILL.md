---
name: skill-compose
description: Build and run a pipeline of skill modules that declare the types they consume and produce - type-check the chain (every consumed type comes from an input or an earlier step, no ORDER inversions, no repeats, producer depth within max_depth), plan the shortest module chain from the types you have to the type you want, and run script steps with placeholders filled, recording exit code, artefact path and sha256 per step in a receipt while MANUAL judgement steps take their text from a notes file and an empty one fails at landing. Use this whenever a task needs more than one skill in sequence, when the user asks which skills get from X to Y, before handing a multi-skill job to a subagent, and when a chain of tools must leave a receipt.
---
# skill-compose

## The problem
Plan §SK2.1-SK2.6 (eager-cray, 2026-10-13) described skills as typed modules (consumes -> produces) composed into
pipelines with a receipt per step, red when a pipeline runs with a type gap or a MANUAL line is left empty at landing.
Nothing was built: multi-skill jobs were chained by hand, the hand-offs between skills were implicit, and nothing
recorded which artefact each step produced. topo-sort orders a dependency graph but knows nothing of types.

## Procedure
1. Describe each module once in a modules JSON: `consumes`, `produces`, `run` (argv list with `{type}` placeholders,
   `python` means this interpreter) or `"MANUAL"`, optional `out`, `capture` (save stdout as the artefact),
   `ok_exits`.
2. `plan --have ... --want T` to find the shortest chain; write it as a pipeline JSON (inputs, steps, max_depth).
3. `check`; fix every TYPE_GAP / ORDER / DEPTH before running.
4. `run --receipt r.json --manual notes.json --landing`; the receipt holds every step's sha256 and MANUAL text.

## Tool
```
python skill_compose.py check _work\compose_modules.json _work\compose_pipe.json
  TYPE_GAP  land             consumes pen, which no earlier step or input provides
  TYPECHECK FAILED (1 error(s))
python skill_compose.py plan _work\compose_modules.json --have repo,skills_dir --want landing_list
  PLAN doc_check -> harvest -> decide
python skill_compose.py run _work\compose_modules.json _work\compose_pipe2.json --receipt r.json --landing
  OK                harvest          0e70e235b612...
  OK                doc_check        ba6f63507973...
  EMPTY_AT_LANDING  decide
  receipt r.json: FAILED
python skill_compose.py --selftest     # 13 PASS lines
```
Real run 2026-10-16: branch-harvester on <repo> and doc-truth on the live library as script steps, a MANUAL
decision step left empty, so the landing run fails as designed. Exit 0 ok, 1 type error / NO_PLAN / failed step,
2 bad arguments.

## Proof
Selftest 13/13. Planted 7, caught 7 (`_work/p_compose.json`: ORDER, depth bound, REPEAT, BFS shortest plan, landing
MANUAL, stop on failure, run refuses an untyped pipeline).

## Provenance
skill-foundry dry run 2026-10-16: `skill-compose: PASSES ALL GATES (dry run - nothing created)` (top finder hit
lace-cycle norm 0.19). Source [REAL: <repo>/plans/...; plan SK2.1-SK2.6].

Pairs with topo-sort (ordering without types), schema-contract (the shape of one artefact), receipt-report and
chain-the-queue.
