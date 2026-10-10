# CLAUDE.md

<!-- Keep this file short (under ~60 lines). It loads into EVERY session and every turn re-reads it.
     Put area-specific rules in a CLAUDE.md inside that directory (see "Nested CLAUDE.md" below);
     it loads only when Claude works on files there. Put procedures in skills, not here. -->

## Project
- What it is: <one sentence>.
- Layout: `<dir>/` <purpose>; `<dir>/` <purpose>.
- Base branch: `<main|develop>`. PRs target it; humans merge.

## Commands
- Build: `<cmd>` - Test one package: `<cmd>` - Lint changed files: `<cmd>`
- Orchestration: `octl status`, `octl task next`, `octl brief <ID>` (see `.claude/octl.json` or `octl.json`).

## Rules
- Security first: state the threat model for every change; authorization and data-isolation tests are part of done.
- Never commit secrets; never read `.env` files into output; credentials come from env vars.
- Ask before outward or irreversible actions: merging, releasing, deploying, deleting data, messaging people.
- Small PRs, one concern each. Verify by running the touched tests, not by "it compiles".

## Working lean (token budget)
- Filter every command output (`| tail -n 40`, `grep`, `jq`); Read with offset/limit; never dump big files.
- No polling: one background `gh pr checks N --watch --fail-fast | tail -5`, then act once.
- Independent tool calls go in parallel in one turn. Lookups go to the scout agent.
- Context above ~400k (status line warns): run the handoff skill and continue in a fresh session.
- Agents report once at the end and stop; follow-ups go to a fresh agent with `octl brief`.

## Nested CLAUDE.md
Add `CLAUDE.md` files next to the code they govern, for example `api/CLAUDE.md` (handler, migration and
query rules) and `web/CLAUDE.md` (component, test and styling rules). Each one: under ~40 lines, only rules
that apply in that directory, no repetition of this file.
