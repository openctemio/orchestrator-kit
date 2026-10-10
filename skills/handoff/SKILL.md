---
name: handoff
description: Write a compact RESUME section at the top of the handoff file so a fresh session can continue - state, running agents, open PRs, decisions pending, next steps. Use before ending or restarting a long session, or when the context is big.
---

Write (or replace) the section between `<!-- RESUME START -->` and `<!-- RESUME END -->` at the top of the
handoff file named in octl.json (`handoff_file`, default HANDOFF.md). Keep it under 40 lines. Older sections
stay below it; do not rewrite history.

Gather with cheap commands only: `octl status --short`, `octl task list | head -30`, `octl blocked | head -20`.

Sections, terse:
- **Resume here** (UTC timestamp): one sentence on where things stand.
- **Running**: task id, agent, stage, PR - one line each.
- **Needs decision**: each with the options and your recommendation.
- **Next**: the next three actions in order, each a command or a task id.
- **Watch out**: anything surprising (flaky check, held PR, live issue).

No tool output dumps, no secrets, no personal data. After writing, say the session can be restarted and that
the new session should read the RESUME section first.
