---
name: agent-briefing
description: Write a task brief for a subagent so it works isolated, safely and cheaply - workspace, safety rules, scope, done criteria, stop conditions. Use before spawning any agent that will change files, run builds or touch shared resources.
---

A brief is the only context a fresh agent gets. Rules that are not in it do not exist for the agent. Every rule
below exists because an agent broke it once.

## Structure
1. **Common rules**: paste or reference the project's common brief (the kit's `templates/BRIEF-common.md`,
   or `octl brief <task>` which assembles it). Do not restate it per task.
2. **Task**: one concern, one PR (a small stack only when unavoidable). Link the issue, the owner decisions
   already made ("final, do not re-ask") and the research or design to follow.
3. **Prior work**: "first list existing branches and PRs for this item and build on them".
4. **Reserved resources**: migration numbers, ports, container name prefix, its own work directory.
5. **Done means**: green CI, 0 unresolved threads, the fail-before test named, the functional check done,
   scratch containers removed, workspace marked done.
6. **Stop conditions**: what to escalate instead of deciding (destructive data change, owner-merged repos,
   outward actions, a design question the decisions do not answer).
7. **Report**: once, at the end, at most N lines: PR links, states, migrations used, what was verified, open risks.

## Isolation rules live in the common brief
Check that the common brief carries them; add a missing one there, not in each task brief. The incidents
behind them, for when someone asks why:
- **Own work directory, never the live checkout:** an interactive shell `cd` wrapper returned non-zero, so
  `cd X && cmd` skipped and `cd X; cmd` ran in the live tree; a junk migration file landed where the next
  deploy would have applied it. Hence `bash -c` with absolute paths and `git -C`.
- **No `rm` in `bash -c`:** the built-in deletion check prompts the owner even in bypass mode.
- **No broad kills or host-wide prune:** they removed scratch servers of other agents and volumes.
- **Remove scratch containers at the end:** left "in case", they piled up past twenty on a shared host.
- **Private scripts and env files:** a shared env file made one agent run code generation in the clone of another agent.
- **Low parallelism, shared caches:** ten parallel builds ran the host out of memory; private caches filled
  the disk, and a full disk crashed the database.

## Cost
Fresh agent per follow-up (rebase, CI fix) instead of resuming a large-context one; filtered command output;
no polling turns. Pick the model for the work: a cheaper model for mechanical tasks, the strongest for
design, security and UI. When the owner names a model, use exactly that.
