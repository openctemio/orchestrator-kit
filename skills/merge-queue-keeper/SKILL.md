---
name: merge-queue-keeper
description: Keep many open PRs flowing into a merge queue without wasting CI - a rolling window of the lowest PRs, enqueue only clean PRs, never touch queued entries, split ranges between keepers. Use when running a queue-keeper agent or when the owner asks why PRs are not merging.
---

Every queue failure or manual removal rebuilds every group behind it and restarts the full suite for each.
One bad entry costs one full CI cycle (often 30 minutes) times the number of PRs behind it.

Window:
1. Work the 3 lowest-numbered open PRs (skip the hold list). When one merges, start the next one up
   immediately. Waiting for a whole batch leaves runners idle.
2. When more than about 20 PRs are open, split them by number range between 2-3 keepers. Give a PR the
   owner is asking about a priority slot instead of reordering everything.
3. Before starting, check the keeper is alive: a dead keeper looks exactly like a slow queue.

Before enabling auto-merge on a PR:
4. Merge the base branch in and resolve conflicts by hand. Keep both sides' intent, and rerun the tests of
   every touched package (semantic conflicts merge "cleanly").
5. Read the newest run per workflow. Older runs, cancelled runs and runs from before a base-branch fix
   show red but mean nothing.
6. Run locally whatever the PR tier no longer runs but the queue does. If the PR CI is a fast tier, a PR
   touching migrations, auth, membership or repository SQL runs the integration suite on a scratch
   database first, and a PR touching pages runs the page request budget.
7. Enable auto-merge only when the PR is CLEAN against the current base. A conflicting PR in the queue
   is UNMERGEABLE and still costs a rebuild.

Never:
- remove or re-add a queued entry, or push to a PR while it is queued;
- cancel a merge-group run;
- admin-merge;
- add the security label yourself.

If two PRs conflict and one contains the other (a stack), let the larger one merge and close the smaller
as superseded. That is one queue run instead of two.

Queue width: build 4 entries at once on large hosted pools, 2 when runners are scarce. Measure the idle
runners before changing it.

Report only merges, failures you cannot fix, and anything that needs the owner.
