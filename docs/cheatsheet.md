# Cheat sheet

(Template mode: replace `octl` with `./.claude/bin/octl` and `consult` with `./.claude/bin/consult`.)

## Every day
| Want | Do |
|---|---|
| Where are we? | `octl status` (live, network) or `octl status --short` (local) |
| What to start? | `octl task next` |
| Add work | `octl task add P1 change "Fix X" --risk med --size S` |
| Which model? | `octl route --kind feature --risk high --size L` |
| Brief an agent | `octl brief T007` (first line: agent, model, effort, maxTurns) |
| Start it | `/dispatch` in the main session, or `octl spawn T007 --run` (headless) |
| Record progress | `octl task pr T007 123`, `octl task advance T007` |
| It failed | `octl task fail T007 "why"` (twice = one tier up) |
| PRs stuck | `octl blocked`, `octl unjam` or `/unjam` |
| Tokens | `octl tokens --hours 24`, `octl tokens --task`, `/token-audit` |
| Need opinions | `consult "question" -c note.md --dry-run`, then without `--dry-run`, or `/council` |
| Ending a session | `/handoff`, then start fresh and read RESUME |
| Deploy | `/deploy` (rehearse -> owner yes -> apply -> verify) |

## Reservations
`octl mig reserve T007 2` - `octl port reserve T007 2` - `octl release T007`

## Models
haiku: lookups, status, log triage - sonnet: rebase, CI, conflicts, docs, small changes, reviews -
opus: design, security, cross-cutting features, UI, hard debugging. Main session: opus, medium effort.

## Rules that save the most tokens
1. Fresh agent per task; never resume a big one. 2. Filter every output. 3. No polling turns.
4. Touched tests only. 5. Report once, then stop. 6. Restart the main session at BIG CONTEXT.

## Never without a human
merge - release - deploy - delete data - force push - send messages - enable external council providers.
