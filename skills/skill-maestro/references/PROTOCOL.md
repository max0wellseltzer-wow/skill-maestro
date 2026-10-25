# The Conductor's Protocol (SKILL Maestro v8)

For any human or AI choosing tools from a large library. It works on paper; `maestro.py` makes each step cheaper
and leaves a receipt. It exists because word-matching picks badly: on Max's real prompts the right first pick
came back about 1 time in 7. Queries and tool descriptions rarely share words (ToolRet, arXiv 2503.01763). What
did separate good picks from bad on 2026-10-18 was the subject's kind, the skill's hidden assumptions, whether its
output depended on the subject, and the verdict afterwards. The protocol is built on those four.

## Part A: choosing (run it)

**0. SUBJECT.** Name exactly what the work is about: a file, a section, a dataset, a function. Then cut it to the
narrowest part the work needs. A 3,300-line plan made every lens say "all covered"; the same lenses on the 48 lines
a builder follows found four real gaps.

**0b. MEANING (v10).** Restate the task as 3-6 operations (`maestro.py vocab` lists the tags) and 1-2 analogies,
and score with `--concepts`. Keywords find the skills that share the task's words. Operations find the skills that do
the task's work, which on 2026-10-19 were six skills sharing almost no word with it. Then read the SPARK panel and
ask how this could be invented, not only checked. Choose one creative operator and run it.

**1. QUESTIONS.** Say which of the fourteen questions the task asks (most tasks ask one or two):
FIND_GAPS, FIND_CONFLICTS, ORDER, VERIFY_CLAIM, MEASURE, GENERATE, BUILD, EXPLAIN, CHOOSE, GUARD, RECORD,
TRANSFORM, FORECAST, SIMPLIFY. Subject + kind + questions + limits = the **task card**.

**2. CANDIDATES by meaning, not words.** Every skill has a **card** (written by reading its SKILL.md: questions,
input kind and shape, the assumptions it makes, output, cost, a probe command, the trap it is not for). Keep the
skills whose questions meet the task's and whose input kind is the subject's kind. Then read each kept card's
`assumes` against the real subject: holds / breaks / unknown. One "breaks" removes it (cross-cutting-check assumes
rows cite only ids above them; a plan whose cards cite later cards breaks that). Word search only breaks ties and
finds what has no card yet.

**3. TASTE.** Run each candidate's probe on the subject and on three controls built from it: HALF (less of it),
SALAD (its words, no structure), BLANKED (its structure, no words). Compare the skill's own words, with echoes of
the subject masked out. CONSTANT (the same on all three): it ignores the subject. SATURATED: it says the same
without the subject's substance. LEXICAL / STRUCTURAL / SIZE_ONLY say what it actually reads. A taste is evidence
only once its version has passed its pre-registered bench test; until then it is marked UNCALIBRATED.

**4. COMMIT, 4-6 picks.** One or two best fits plus one or two that bring a different idea (curiosity, a far
family, a checker). Write the **use plan**, one line each: runs on what, takes what, expect what, would change what.
A pick you will not run on the subject is not a pick.

> **Pause point 1 (before using anything):** is the subject named and cut? does every pick have a use-plan line, a
> card whose assumptions hold, and a taste? If not, stop and finish step 0-4.

**5. USE.** Read each pick's SKILL.md, run it on the subject, build with what it found.

**6. VERDICT.** Each pick gets `works` (it read the subject as what it is and gave the task something it used) or
`misfit` (and why). "Works" needs a run on the subject; "misfit" teaches the library to avoid it on similar tasks.
The person the work is for rates afterwards in plain words; their rating outranks the chooser's own.

**7. LEARN.** Verdicts accumulate per skill and per question, so the next choice for the same kind of question
starts from what worked. The chooser may mark its own pick a misfit, never a success on its own word.

> **Pause point 2 (before reporting):** does every pick have a verdict? is each finding traced to the pick and the
> subject that produced it? are misfits named as such? Then re-read, yourself, everything the person asked since the
> work began (the transcript, not your memory of it) and every promise you made; anything open is listed with its
> state. The person should never have to tell you what you forgot.

With the tool, `maestro.py plan RUN SKILL --on SUBJECT "..."` records step 4 and `maestro.py baton RUN` shows which
steps and pause points a run has met, so a skipped step is visible, not remembered.

## Part B: using the result (run off it)

- **STABLE beats unstable.** A pick that stays in the top six when any one sentence of the task is left out was
  right three times as often on Max's labelled prompts (E34). Judge unstable picks harder.

- **The ranking is organized, not verified.** S1 = useful on a similar task before, S2 = read at this version,
  S3 = unread. Treat S3 as a lead.
- **Menus are ideas, not ranks.** A (best fit), B (never tried), C (a far family), D (readers and a checker), E (what
  the person liked before). Offering them lets the person choose the idea, not just the tool.
- **A verdict travels with its evidence.** Quote the taste line and the fit line next to any finding a pick made.
- **Silence is not a pass.** A pick that found nothing on a subject it CAN read is evidence; one that cannot read the
  subject proves nothing.
- **Stop rules.** Two misfits in a row: go back to step 0 (the subject is wrong or too wide). A taste CONSTANT on
  every candidate: the subject is not the kind the task thinks it is.
