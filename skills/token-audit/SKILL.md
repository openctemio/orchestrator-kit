---
name: token-audit
description: Find where tokens go - per-transcript and per-task usage, contexts that should be restarted, tasks over budget. Use when usage limits are near, a session feels slow, or someone asks about token cost.
argument-hint: "[hours]"
---

1. `octl tokens --hours ${ARGUMENTS:-24}` (top transcripts by cache-read tokens; big contexts flagged).
2. `octl tokens --hours ${ARGUMENTS:-24} --task` (usage per task against its budget).
3. Advise, in this order of impact:
   - cost is roughly turns x context size; any context above the warning line should end: write a handoff
     and continue in a fresh session (for agents: stop it and dispatch a fresh one for the follow-up);
   - tasks over budget: stop and re-brief smaller, or split the task;
   - many turns with small output: polling or chatty loops; replace with one background watch;
   - large tool outputs: filter commands (`| tail -n 40`, `grep`, `jq`), Read with offset/limit,
     delegate searches to the scout agent;
   - mechanical work on opus: re-route with `octl route` (kind rebase, ci, docs go to sonnet).
4. Change nothing yourself. Report at most 8 lines with concrete restarts or re-routes.
