---
name: merge-queue-stacks
description: Land stacked pull requests and migration-numbered PRs through a squash merge queue without orphaning commits or clashing numbers. Use when creating, merging or enqueueing PRs that depend on each other or that add database migrations.
---

## Stacks

A stacked PR targets another feature branch. With squash merges this breaks in two ways:
- **Orphaned work.** The parent was squash-merged first; the child was then merged into the parent's branch,
  not the base. GitHub shows the child "merged", but its code never reached the base branch. This happened
  twice before anyone noticed missing features.
- **Duplicate commits.** The child still carries the parent's pre-squash commits, so it conflicts with the
  squash commit or re-applies it.

Rules:
1. Prefer one PR per change based on the base branch. Stack only when a change truly needs another.
2. Enqueue only stack roots (PRs whose base is the base branch). When the parent merges, retarget the child to
   the base branch and drop the parent's pre-squash commits: `git rebase --onto origin/<base> <parent-tip> <child>`.
3. Never merge a PR into a feature branch.
4. Verify by content, not by ancestry: `git grep <new symbol> origin/<base>` after a stack lands. A squashed
   parent never shows as an ancestor, so `git branch --contains` proves nothing.

## Migration numbers

Parallel PRs pick the same "next" migration number, and the queue rejects a version at or below the base's
highest. Rules:
1. Reserve numbers (a band per agent, or the kit's `octl mig reserve`) instead of taking max+1.
2. Renumber at merge time with a script, not by hand in every PR: whoever merges second renames.
3. Tests find a migration by name (`MigrationVersion(t, dir, "add_widget_owner")`), never by a hard-coded
   number, so a renumber touches only file names.
4. Count only migrations a PR adds; a PR that edits an old migration is not "behind".

## Queue hygiene

- Keep PRs small and independent: the queue is the bottleneck, and one failing PR drags the PRs grouped with it.
- Files every PR appends to (a changelog, a generated spec) conflict constantly. Use one file per change
  (changelog fragments) and do not commit generated files; regenerate them in CI.
- A queue entry marked unmergeable is often a failed check, not a conflict: read the removal reason. Two PRs
  that pass alone can fail together (both mount the same route): read the merge-group test log.
- After the base branch goes red, fix the base first with a tiny PR, then update every branch that lacks it.
