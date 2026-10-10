---
name: dispatch
description: One orchestrator tick - fill free agent slots from the octl task board with the routed agent and model, record starts, merge clean PRs. Use when asked to dispatch, start the next tasks, or run a routine tick (also headless via claude -p).
argument-hint: "[max-new-agents]"
---

Run one dispatch tick and stop. Keep it short: no exploration, no reading of code.

1. `octl status --short`, then `octl task next`. If no slot is free or nothing is todo, go to step 5.
2. For each task `octl task next` lists (at most $ARGUMENTS when given):
   - `octl brief <ID>` and read its first line: `[agent: A  model: M  effort: E  maxTurns: T]`.
   - Spawn ONE fresh background subagent with the Agent tool: subagent type A (this plugin's agent of that
     name), model M, effort E, prompt = the full brief text. Never resume an old large-context agent.
   - `octl task start <ID> <agent-name-or-id>`.
   (Headless alternative: `octl spawn <ID> --run` starts a detached `claude -p` run with the same routing.)
3. Do not wait for agents and do not poll them. Their final reports arrive as notifications.
4. When a report arrives: record it (`octl task pr`, `octl task advance`, `octl task fail` or `octl task block`)
   in one line each; relay only what the owner must decide.
5. `octl unjam` to merge or enqueue clean PRs in stack order.
6. Escalate to the main session (do not decide yourself) when: a task is blocked on a decision, a gate failed
   twice after escalation to opus, a security finding is high, or a deploy is due. Write one line to the
   handoff file under "Needs decision" and stop.

Output at most 6 lines: started, recorded, merged, needs decision.
