---
name: unjam
description: Get stuck pull requests moving - list why each open PR is blocked, merge or enqueue the clean ones in stack order, and queue a rebaser task per blocked stack. Use when PRs pile up, the merge queue is idle, or someone asks why PRs are not merging.
---

1. `octl blocked` (one line per PR: conflicts, failing checks, unresolved threads, held).
2. `octl unjam` merges or enqueues every CLEAN PR in stack order (a PR containing another goes after it).
3. Group the rest by cause and act once per group, cheapest first:
   - conflicts or a migration-number clash: `octl task add P1 conflict "Merge base into #N (stack: #A,#B)" --size S`
     (one task per stack, bottom PR first; the rebaser agent handles it)
   - failing check with an obvious cause: `octl task add P1 ci "Fix <check> on #N" --size S`
   - unresolved threads: the PR's own agent kind, e.g. `octl task add P2 change "Resolve review threads on #N"`
   - held PRs: leave them; mention them.
4. Do not fix anything yourself in this session and do not read diffs here.

Report at most 5 lines: merged or enqueued, tasks added, held.
