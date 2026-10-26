---
name: skills-index
description: Browse the whole skill library as a generated, family-grouped catalog - every skill with a one-line "reach for this when", marked [T] if it ships a tool or [D] if doc-only - rebuilt from the SKILL.md files so it never goes stale. Use this whenever the user asks what skills we have, wants an overview/catalog/map of the skills, asks "do we have a skill for X" while wanting to browse a category, or after adding skills to refresh the catalog. One of the three library-organizing skills, with skill-finder (search) and skill-health (verify).
---

# skills-index

With 150+ skills, the library only helps if you can see it. This is the browsable map: skills grouped into families (honest research & statistics, time series & signals, networks & graphs, allocation/control/rate, data integrity, optimization & search, reproduction & combination, coordination & landing, long runs & continuity, data sourcing, code quality & safety, prompting & planning, Project-specific, library organizing), each with the first sentence of its description as a "reach for this when".

## The tool (ships with this skill)

`build_index.py` - pure stdlib, selftest 7/7:

```
python build_index.py                # regenerate INDEX.md here from ~/.claude/skills
python build_index.py <skills_root>  # index another library
python build_index.py --selftest
```

Read **`INDEX.md`** (beside this file) for the catalog. It is generated, never hand-edited: re-run `build_index.py` after adding or renaming skills. Family placement comes from a curated map in the script, then a keyword fallback, then "Other" - add new skills to the map when they deserve a specific family.

## Browse vs search vs verify

Use this to BROWSE a category. When you know the need but not the name, `skill-finder` ranks skills against a plain-English question. To check the library actually works (selftests, portability, naming), run `skill-health`.
