# Skill ideas waiting to be built

Seeds for skill-foundry. Each one names who asked, why, and what it would compute. Run it through the gates with
`python foundry.py <name> "<mechanism>" --pitch "..."` before building.

## token-usage-guide (2026-10-19)

**Why:** the user asked whether switching to Haiku mid-conversation saved or wasted tokens. The answer needed the price
list, cache rules and the conversation's size worked out by hand. It came out to about break-even. Haiku saved
about $0.75-$1 over its stretch, and Opus re-reading the whole conversation when switching back cost about $1, once.

**What it would compute:** for a planned switch (from model A to model B for about N steps, then back), the net cost:
- B's fresh read of the context, once;
- the per-step savings while on B;
- A's fresh re-read when switching back, if A's cache expired (about 1 hour);
- the verdict: worth it, break-even or wasteful, and the number of steps on B where it starts paying.

**Inputs:**
- the context size;
- the prices of the two models (from the claude-api skill's model table, never from memory);
- the minutes away from A (the cache lifetime);
- whether the user is on a subscription (usage limits) or the API (dollars).

**Also worth folding in:**
- effort level versus model choice;
- `/clear` or a fresh session versus carrying a long context;
- subagents on a cheaper model;
- the rule of thumb that a short detour costs about what it saves.
