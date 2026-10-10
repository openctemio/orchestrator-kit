---
name: workflow
description: Drive one task through the workflow stages and their gates - intake, plan, implement, verify, review, ci, queue, deploy, handoff. Use when asked to move a task forward, check what a task needs next, or take a task to done.
argument-hint: "<task-id>"
arguments: task
---

Drive task $task one stage at a time. `octl task show $task` tells you its stage; `octl task advance $task`
moves it only when the gate passes and prints why not otherwise. Never use `--force` without the owner's yes.

| Stage | Who | Gate to leave it |
|---|---|---|
| intake | orchestrator | routed (`octl task add` did it); re-route with `octl route` if kind, risk or size was wrong |
| plan | implementer (opus tasks only) | design note exists at the path the brief names (problem, approach, threat model, tests) |
| implement | routed agent, in its own git worktree | PR recorded with `octl task pr $task N` |
| verify | same agent | touched tests pass plus a test that fails without the change (agent reports it) |
| review | reviewer agent (read-only, security lens) | verdict `pass`; high findings go back to implement |
| ci | same agent as implement | PR is CLEAN and has 0 unresolved review threads (checked by octl) |
| queue | `octl unjam` / the watcher | PR merged (checked by octl) |
| deploy | owner-approved, `deploy` skill | `octl deploy verify` succeeded after the merge (skipped when no live config) |
| handoff | orchestrator | one line in the handoff file; then `octl task advance` marks it done |

Steps:
1. `octl task show $task`. If status is todo, use the dispatch skill to start it with the routed agent.
2. If the stage belongs to an agent that is running, do nothing: wait for its report (no polling).
3. review: spawn the reviewer agent with "Review PR N for task $task" and record the verdict; on `changes needed`
   send the findings to a fresh agent of the routed type (not a resumed one).
4. A gate that failed twice: `octl task fail $task "<gate>: <why>"`; the board re-routes it one tier up.
5. Stop after one stage change and report one line: task, old stage -> new stage, or the gate that blocks it.
