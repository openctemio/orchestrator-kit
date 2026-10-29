---
name: ci-failure-triage
description: Find why a PR, base-branch push or merge-queue run is red, decide real versus flake versus stale, and fix the root cause once. Use when checks fail, when the queue keeps dropping entries, or before rerunning anything.
---

1. Look at the newest run per workflow name. A cancelled run superseded by a newer one is not a failure.
   A run older than a base-branch fix is stale: merge the base in, don't debug it.
2. Compare with the base branch. If the same job is red there, it is not this PR. Fix it on the base
   (one PR) instead of in every branch.
3. Read the failing step's log for the first real error (`gh run view <id> --log-failed`, or
   `gh api repos/<r>/actions/jobs/<job>/logs` when that is empty). Then classify it:
   - infra (runner died, registry 429, canceled by concurrency, OOM): rerun the failed jobs once;
   - real (a test assertion, lint, type error): fix it on the branch;
   - only in the queue: it is the PR combined with the base or with entries ahead. Reproduce it on the
     branch merged with the current base.
4. Timing failures (rate limits, request budgets, shard order) need the timestamps. Count the actions
   inside the window, and look at what changed in shard balancing or test order.
5. When a UI-text change breaks a test helper, make the helper read the text from the same catalog the
   app uses, and fail fast on any unexpected error message instead of timing out.
6. When a failure was caught late (in the queue, after merge), also close the gap: make the earlier tier
   run that check for the paths that can break it.

Never quarantine a test without an issue and an owner. Never rerun a real failure hoping it passes.
