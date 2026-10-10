# Council: combine opinions on one decision

`bin/consult` asks several independent advisors the same question and records their answers and a synthesis.
Use it for decisions (design choice, security trade-off, risky migration), not for doing tasks.

```
consult "Queue: Postgres SKIP LOCKED or Redis streams for scan jobs? Constraints: ..." -c docs/design.md --dry-run
consult "..." -c docs/design.md --risk high --rounds 2 --synth
```

## How it works

1. **Context**: only the question and the files listed with `-c`. No conversation, no repository access.
   Files must be inside the project, not secrets files (`.env`, keys, credentials), and within
   `max_file_kb`/`max_total_kb`. Token-like strings are redacted before anything is sent.
2. **Advisors**: default three - architect (sonnet), security reviewer (sonnet), devil's advocate (opus).
   `--risk high` adds a pragmatic implementer and an operations/cost advisor (five). Each call is fresh and
   blind to the others, and answers in a fixed schema: `position`, `reasons`, `risks`, `change_my_mind`,
   `confidence` (0 to 1). Answers are validated; an agent CLI that ignores the schema is kept as raw text and
   marked unstructured.
3. **Round 2** (`--rounds 2` or `rounds: 2`): each advisor sees the others' answers, anonymised, and may revise.
4. **Synthesis**: `--synth` runs one opus call (agreement, disagreements with the strongest argument per side,
   recommendation, open questions). Without it, the main session writes the synthesis into the record
   (the `council` skill says how).
5. **Record**: `.claude/council/<timestamp>-<slug>.md` plus a JSON sidecar; `audit.log` lists, per call, the
   provider, model, files sent, redaction count, cost and outcome. Keys are never logged.

## Providers (`octl.json` -> `council.providers`)

| Type | Uses | Notes |
|---|---|---|
| `claude-cli` (default) | `claude -p --no-session-persistence --json-schema ... --max-budget-usd ... --permission-mode dontAsk --disallowedTools Bash,Edit,Write,...` | your Claude Code login; prompt on stdin; `bare: true` skips hooks/plugins/CLAUDE.md but needs `ANTHROPIC_API_KEY` |
| `anthropic-api` | Messages API with `output_config.format` json_schema | `ANTHROPIC_API_KEY`, pay per token, separate from subscription limits; disabled by default |
| `openai-compatible` | any HTTP chat-completions endpoint | another vendor or a local model server; loopback hosts are local, any other host is external |
| `agent-cli` | any coding-agent CLI from a command template | runs in a temp, read-only copy of only the listed files with a stripped environment (PATH, HOME, locale + `env_keep`); external by default |

`examples/council-providers.json` has presets. The `claude` presets are verified against CLI 2.1.293; the other
agent-CLI presets are **unverified** (those CLIs were not installed) - check `<cli> --help` before enabling.

## Safety and budget

- Every provider except `claude-cli` is disabled by default. External providers additionally need
  `allow_external: true` in their config **and** `--allow-external` on the command line, and must use https.
- No advisor gets write tools. `claude-cli` advisors get no tools at all unless `allow_read: true`
  (then only Read, Grep, Glob).
- Budget: per call (`max_budget_usd` for the CLI, `max_tokens` and `est_usd_per_call` for HTTP and agent CLIs)
  and per council (`max_council_usd`, default $3). The worst case is checked **before** any call; a council
  that could exceed the cap is refused. `--dry-run` prints the plan and calls nothing.
- Timeouts on every call; one failed advisor does not sink the council.
