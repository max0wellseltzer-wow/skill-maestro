# Skill Maestro: the 5-year-old version

**Skill** = recipe card. One thing Claude does well. Your library = a box of cards.
**Maestro** = the helper. Reads your ask. Looks at every card. Says: use THESE, in THIS order, like THIS. Watches
if they helped. Remembers.

## Use it. 3 steps.
1. Ask, your words: `python maestro.py score "write a funny poem about my cat"`
2. Read the picks. Each pick = one line: how to use it on YOUR thing. Copy the `CONDUCTOR PROMPT` line. Paste it to Claude. Done.
3. Say if it helped: `python maestro.py thumbs last up` (or `down`). One keystroke. No rating = no learning.

Want to help the Maestro itself? `python maestro.py contribute` lists how, by the time it takes (30 seconds to an hour).
Nothing is ever sent by itself. Not helping costs nothing.

Want it to think your way? `python maestro.py modes add mark-essays "mark student essays against a rubric"` teaches it a
new kind of job; `maestro.py modes` lists the built-in ones (yours marked *).

## Dictionary. Tiny.
- **pick**: card it chose. **pool**: all cards it looked at. Look at the pool too. Maestro can be wrong.
- **fit**: how well the card matches your words. 1.0 best.
- **[T]** card has a program. **[D]** card is only words.
- **STABLE**: same pick even if you say it a bit differently. Good.
- **antibody**: card was WRONG on an ask like this before. Not picked again. (Body remembers a germ.)
- **opening book**: card was GOOD on an ask like this before. Head start. (Chess player remembers first moves.)
- **MODE**: what kind of job your ask is (fix a bug, write a doc, decide...). Sets how many cards and how to use them. You can add your own.
- **verifier / critic**: one extra card. Job: break the result (numbers) or argue against it (creative). So you don't fool yourself.
- **BROKEN**: card's own self-test fails on this computer. Fix first.
- **OFF HERE**: card switched off in settings. Line tells you the exact switch.
- **SIDE EFFECTS**: card can delete / push / post / send / pay. Say yes first.
- **LIMIT**: your project rules (CLAUDE.md or MAESTRO_PROJECT.md). Card shares words with a rule. Look first.
  **TASK vs LIMIT**: your whole ask may break a rule. Stop. Ask a human.
- **SPECTRUM**: kind of ask. numbers / building / creative / role-play / writing / teaching / deciding / research /
  talking to people / running jobs / data / play. Each kind = its own steps.
- **PICKS 1-22**: more asks = more cards. Tiny ask = 1. Big ask = up to 22.
- **ledger**: Maestro's diary. Every run, read, try, rating. Never erased. Cloud session: diary lives in your
  project (`shared/skill-maestro/ledger.jsonl`). Commit it or lose it.
- **STANDALONE**: helper cards (skill-finder etc.) missing. Fine. Still works. Bit less sharp.

## The one rule
Not a pick until it ran on YOUR real thing. `try` it. `fit works` or `fit misfit`. THEN `rate`.
Maestro refuses "useful" for a card that never ran. On purpose.

## One line to remember
`score` -> read picks + pool -> `try` each -> `fit` -> `rate`. Next time better.

## Tell it your project. 1 minute. Optional.
File `MAESTRO_PROJECT.md` in your project folder:
```
GOAL: a website that sells hats
LIMIT: never email real customers from a test
LIMIT: don't touch payments code without asking
```
Now every score starts with your goals + limits. Warns when an ask or a pick crosses one.
