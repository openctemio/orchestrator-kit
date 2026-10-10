# Model routing and orchestrator layers

Cost is roughly **turns x context size**. Routing therefore decides three things for every task: which model,
how hard it thinks (effort), and how long it may run (turns and a token budget). Most savings come from
not using the strongest model for mechanical work, and from short, fresh sessions instead of long-lived ones.

## The policy (`octl route`, used by `octl task add`)

```
octl route "Fix flaky test" --kind ci --risk med --size S
-> agent=rebaser model=sonnet effort=medium max_turns=30 budget=15M
```

1. **Base tier from the kind of work**

   | Tier | Kinds | Agent |
   |---|---|---|
   | haiku | `lookup`, `status`, `triage` (find, summarise logs, answer a status question) | scout (read-only) |
   | sonnet | `rebase`, `ci`, `conflict` | rebaser |
   | sonnet | `docs`, `mechanical`, `change` (small, well-specified) | fixer |
   | sonnet | `review` | reviewer (read-only, security lens) |
   | opus | `feature`, `design`, `security`, `ui`, `debug` (cross-cutting, risky, hard) | implementer |

2. **Raise one tier** when `--risk high` or `--size L`, except for kinds that change no code
   (`lookup`, `status`, `triage`, `docs`). High risk is at least sonnet. `security` is always opus.
3. **Escalate one tier after two failed attempts** (`octl task fail ID "why"` twice). A rebaser or scout task
   that escalates moves to the next agent up (implementer or fixer).
4. **De-escalate follow-ups**: a follow-up (rebase after review, CI fix, renumber) is a *new* task routed from
   its own kind, never a resumed large-context agent.
5. **Effort**: haiku low, sonnet medium, opus high; opus with high risk gets xhigh.
6. **Budgets**: max turns S/M/L = 30/60/120 (haiku at most 20); token budget S/M/L = 15M/40M/100M cache-read
   tokens (haiku at most the S budget). `octl watch` alerts when a running task exceeds its budget;
   `octl tokens --task` shows usage per task.

Every value is overridable in `octl.json` under `routing` (dicts merge key by key):

```json
"routing": {"kind_tier": {"migration": "sonnet"}, "budget_m": {"L": 150}, "fails_to_escalate": 3}
```

The agent files in `agents/*.md` pin their own `model`, `effort` and `maxTurns`; routing picks the agent, and
the dispatcher passes the routed model and effort explicitly so an escalated task runs on the higher tier.

## Orchestrator layers

| Layer | What | Model | Runs |
|---|---|---|---|
| **L0** deterministic | `octl watch`: base-branch CI, live health, disk, merge clean PRs in stack order, token and budget alerts, migration/port allocation | none | systemd user timer or cron (`octl install-timer`) |
| **L1** routine dispatch | fill free slots from the board, record finished reports, enqueue; escalate by writing to the board and the handoff file | sonnet, low/medium effort | a fresh short session per tick, e.g. `claude -p "/orchestrator-kit:dispatch" --model sonnet --effort low --max-budget-usd 1` |
| **L2** main session | owner conversation, design and security decisions, conflict arbitration, escalations, deploy approval | opus, medium effort (high for design/security sessions) | interactive; lean context; restart from the handoff file when the status line warns |

Escalation goes **up by writing, not by polling**: L1 writes a "Needs decision" line to the handoff file and
the alert fires; L2 reads it when the owner next talks to it. L2 never keeps a loop running to watch L1.

`claude -p` expands a skill named in the prompt (`/skill-name`), and accepts `--model`, `--effort`,
`--max-budget-usd`, `--permission-mode` and `--permission-prompts none` (verified on CLI 2.1.293).
A `-p` run waits for background subagents it started, so an L1 tick that spawns subagents lasts until they
finish; to keep ticks short use `octl spawn ID --run`, which starts each task as its own detached
`claude -p --agent <agent> --model <m> --effort <e>` run and logs its JSON result in the state directory.

## Main session settings

`templates/settings.json` sets `"model": "opus"` and `"effortLevel": "medium"`. Switch per session with
`/model` and `/effort` (or `claude --model opus --effort high` for a design or security session).
Rules for the main session:

- Keep it lean: no tool-output dumps, delegate lookups to the scout, read files with offset/limit.
- Do not answer interim agent notifications; act once on final reports.
- When the status line shows **BIG CONTEXT** (default 400k tokens or 80 percent), run the handoff skill and
  start a fresh session that reads the RESUME section first.
